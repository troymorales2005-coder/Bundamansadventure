"""Real-response workflow tests use explicitly synthetic local capture doubles."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from meme_coin_radar.x_bounded_capture import BoundedXCapture
from meme_coin_radar.x_real_replay import (
    LABEL_FIELDS, deterministic_split, frozen_samples, prepare_labeling,
    replay_labeled_split, usage_report, validate_labels, development_smoke,
)

PARSER=Path(__file__).parents[1]/"src/meme_coin_radar/ct_parser.py"
T=datetime.now(timezone.utc)


class Response:
    def __init__(self,payload):
        self.body=json.dumps(payload).encode()
        self.code=200
        self.headers={"x-rate-limit-remaining":"10"}
    def __enter__(self):
        return self
    def __exit__(self,*args):
        pass
    def read(self,n):
        return self.body[:n]


@pytest.fixture
def local_sample(tmp_path,monkeypatch):
    monkeypatch.setenv("X_BEARER_TOKEN","fixture-secret")
    capture=BoundedXCapture(tmp_path,env_file=tmp_path/"missing")
    capture.lookup_verification(opener=lambda *a,**k:Response({"data":{"id":"control","text":"Example"}}))
    posts=[{"id":str(i),"author_id":"a"+str(i),"created_at":(T-timedelta(minutes=10)).isoformat(),"text":"Unrelated meal "+str(i)} for i in range(8)]
    capture.recent_sample("fixed sample",opener=lambda *a,**k:Response({"data":posts}))
    registry=dict(known_at=(T-timedelta(hours=1)).isoformat(),version="test-registry/v1",subjects=[],
                  tokens=[{"coin":{"chain":"test","contract_address":"synthetic-contract"},"tickers":["TEST"],"subjects":[]}])
    plan=dict(target=registry["tokens"][0]["coin"],subject="unregistered-subject",split_seed="test-seed")
    (tmp_path/"registry.json").write_text(json.dumps(registry))
    (tmp_path/"collection_plan.json").write_text(json.dumps(plan))
    return tmp_path


def human_labels(directory):
    """Unit-test annotations only; never applied to the actual real-X sample."""
    path=directory/"human_labels.json"
    data=json.loads(path.read_text())
    for row in data["rows"]:
        row.update(status="labeled",annotator_id="synthetic-test-annotator",labeled_at=datetime.now(timezone.utc).isoformat())
        row["labels"]={field:[] for field in LABEL_FIELDS}
        row["labels"].update(relevant=False,relationship="UNRELATED",classification="UNKNOWN",tokenless_external_catalyst=False)
    path.write_text(json.dumps(data))
    return data


def test_prepare_blinded_template_deterministic_split_and_frozen_raw(local_sample):
    result=prepare_labeling(local_sample,parser_source=PARSER)
    assert result["sample_posts"]==8 and result["pending_labels"]==8
    assert result["split_counts"]=={"development":6,"held_out":2}
    data=json.loads((local_sample/"human_labels.json").read_text())
    assert all(all(v is None for v in row["labels"].values()) for row in data["rows"])
    assert "actual" not in data and "prediction" not in data
    manifest=json.loads((local_sample/"split_manifest.json").read_text())
    rows=frozen_samples(local_sample)
    assert deterministic_split(rows,seed="test-seed")==manifest["assignments"]
    assert deterministic_split(tuple(reversed(rows)),seed="test-seed")==manifest["assignments"]
    assert "control" not in {r["post"]["id"] for r in rows}
    with pytest.raises(FileExistsError):
        prepare_labeling(local_sample,parser_source=PARSER)


def test_author_repost_and_duplicate_groups_do_not_cross_splits():
    rows=tuple(dict(post=p) for p in (
        {"id":"1","author_id":"a","text":"Text"},
        {"id":"2","author_id":"a","text":"Other"},
        {"id":"3","author_id":"b","text":" text "},
        {"id":"4","author_id":"c","text":"Reply","referenced_tweets":[{"id":"1"}]},
        {"id":"5","author_id":"d","text":"Separate"}))
    assignments=deterministic_split(rows,seed="fixed")
    shared={a["split"] for a in assignments if a["post_id"] in {"1","2","3","4"}}
    assert len(shared)==1


def test_pending_human_labels_never_produce_accuracy_or_heldout_predictions(local_sample):
    prepare_labeling(local_sample,parser_source=PARSER)
    for split in ("development","held_out"):
        result=replay_labeled_split(local_sample,split=split,parser_source=PARSER)
        assert result["metrics"] is None and result["status"]=="human_labels_pending"
    assert not list(local_sample.glob("*-metrics.json"))
    assert not list(local_sample.glob("*-evaluation-lock.json"))


def test_development_smoke_checks_integrity_without_groundtruth_or_heldout(local_sample):
    prepare_labeling(local_sample,parser_source=PARSER)
    report=development_smoke(local_sample,parser_source=PARSER)
    assert report["posts_checked"]==6 and report["passing_posts"]==6
    assert not report["held_out_predictions_accessed"]
    assert report["human_performance_metrics"] is None
    assert all(o["checks"]["no_narrative_found"] for o in report["outcomes"])


def test_human_annotations_scored_separately_and_narrative_default_preserved(local_sample):
    prepare_labeling(local_sample,parser_source=PARSER)
    human_labels(local_sample)
    dev=replay_labeled_split(local_sample,split="development",parser_source=PARSER)
    assert dev["metrics"]["exact_match_accuracy"]==1
    assert dev["metrics"]["subject_extraction"]["precision"] is None
    assert all(o["narrative_state"]=="NO_NARRATIVE_FOUND" and o["bridge_checks_passed"] for o in dev["outcomes"])
    assert all(o["computed_at"]>=o["source_cutoff_at"] for o in dev["outcomes"])
    with pytest.raises(ValueError,match="sealed"):
        replay_labeled_split(local_sample,split="held_out",parser_source=PARSER)
    held=replay_labeled_split(local_sample,split="held_out",parser_source=PARSER,release_held_out=True)
    assert held["sample_posts"]==2 and dev["sample_posts"]==6


def test_changed_parser_labels_registry_and_sources_fail_closed(local_sample,tmp_path):
    prepare_labeling(local_sample,parser_source=PARSER)
    data=human_labels(local_sample)
    fake_parser=tmp_path/"changed.py"
    fake_parser.write_text("changed")
    with pytest.raises(ValueError,match="Parser differs"):
        replay_labeled_split(local_sample,split="development",parser_source=fake_parser)
    replay_labeled_split(local_sample,split="development",parser_source=PARSER)
    dev_ids={a["post_id"] for a in json.loads((local_sample/"split_manifest.json").read_text())["assignments"] if a["split"]=="development"}
    next(r for r in data["rows"] if r["post_id"] in dev_ids)["labels"]["relevant"]=True
    (local_sample/"human_labels.json").write_text(json.dumps(data))
    with pytest.raises(ValueError,match="Labels changed"):
        replay_labeled_split(local_sample,split="development",parser_source=PARSER)
    raw_path=local_sample/"request-02-body.bin"
    raw_path.write_bytes(b"tampered")
    with pytest.raises(ValueError,match="bytes changed"):
        frozen_samples(local_sample)


def test_label_schema_requires_human_provenance_and_aware_time(local_sample):
    prepare_labeling(local_sample,parser_source=PARSER)
    data=human_labels(local_sample)
    manifest=json.loads((local_sample/"split_manifest.json").read_text())
    validate_labels(data,manifest)
    data["rows"][0]["annotator_id"]=None
    with pytest.raises(ValueError,match="annotator"):
        validate_labels(data,manifest)
    data["rows"][0]["annotator_id"]="human"
    data["rows"][0]["labeled_at"]="2026-10-01T12:00:00"
    with pytest.raises(ValueError,match="Timezone"):
        validate_labels(data,manifest)


def test_future_dictionary_cannot_enter_original_receipt_cutoff(local_sample):
    path=local_sample/"registry.json"
    registry=json.loads(path.read_text())
    registry["known_at"]=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
    path.write_text(json.dumps(registry))
    with pytest.raises(ValueError,match="original source cutoff"):
        prepare_labeling(local_sample,parser_source=PARSER)


def test_error_analysis_preserves_failures_without_tuning(local_sample):
    prepare_labeling(local_sample,parser_source=PARSER)
    labels=human_labels(local_sample)
    # Artificial test ground truth mismatch to check analysis; not a parser fix.
    for row in labels["rows"]:
        row["labels"]["subjects"]=["missed-subject"]
        row["error_categories"]=["subject_extraction"]
    (local_sample/"human_labels.json").write_text(json.dumps(labels))
    report=replay_labeled_split(local_sample,split="development",parser_source=PARSER)
    assert report["metrics"]["exact_match_accuracy"]==0
    assert report["metrics"]["subject_extraction"]["fn"]==6
    assert report["error_categories"]["subject_extraction"]==6


def test_usage_report_is_not_billing_inference(local_sample):
    report=usage_report(local_sample)
    assert report["request_attempts_reserved"]==2 and report["successful_api_requests"]==2
    assert report["posts_received"]==9 and report["resources_received"]==9
    assert report["pagination_used"]==0 and report["known_usage_units"] is None
    assert report["monetary_charge"]=="not_determined_from_response_metadata"


def test_actual_saved_real_responses_remain_frozen_and_asof_safe():
    """Read-only optional real-capture contract test; never issues an API request."""
    directory=Path("data/real_x_replay_v1")
    if not (directory/"registry.json").exists():
        pytest.skip("Local real capture not present; fixture-only CI")
    registry=json.loads((directory/"registry.json").read_text())
    rows=frozen_samples(directory)
    assert 0 < len(rows) <= 20
    known=datetime.fromisoformat(registry["known_at"])
    for row in rows:
        received=datetime.fromisoformat(row["source_cutoff_at"])
        assert known<=received
        posted=row["post"].get("created_at")
        if posted:
            assert datetime.fromisoformat(posted.replace("Z","+00:00"))<=received
