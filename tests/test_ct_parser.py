"""Local rule-conformance tests; no network or credentials required."""
import json
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from pathlib import Path

import pytest

from meme_coin_radar.ct_models import PostReference, PublicMetric, RawXStore, Relationship, canonical
from meme_coin_radar.ct_parser import (
    CTParser, CTRegistry, PropagationConfig, SubjectAlias, TokenAlias,
    measure_propagation, narrative_evidence, narrative_bridge,
)
from meme_coin_radar.ct_replay import evaluate, registry_from_fixture, run_case, timestamp
from meme_coin_radar.narrative import (
    CoinIdentity, EvidenceKind, NarrativeEvidence, NarrativeProvenance,
    NarrativeResearchEngine, NarrativeState, ResearchClaim,
)
from meme_coin_radar.x_adapter import ApiUsageEvent, ApiUsageLedger, OfficialXResponseAdapter, XAdapterConfig

DATASET = json.loads((Path(__file__).parent/"fixtures/ct_x_v1.json").read_text(encoding="utf-8"))
T = timestamp("2026-10-01T12:15:00Z")
REGISTRY = registry_from_fixture(DATASET)
TARGET = CoinIdentity(**DATASET["target"])
A = TARGET.contract_address
B = REGISTRY.tokens[1].coin.contract_address


def raw(text="viral monkey "+A, *, posted_at="2026-10-01T12:00:00Z", detected_at=None,
        parsed_at=None, author="a", id="raw-1", **extra):
    p = dict(id=id, text=text)
    if posted_at is not None:
        p["created_at"] = posted_at
    if author is not None:
        p["author_id"] = author
    p.update(extra)
    return OfficialXResponseAdapter().normalize({"data":p}, detected_at=detected_at or T-timedelta(minutes=5),
        parsed_at=parsed_at or T-timedelta(minutes=4), source_id="test:raw")[0]


def parsed(post=None, *, registry=REGISTRY, cutoff=T):
    return CTParser(registry).parse(post or raw(), target=TARGET, observed_at=cutoff)


def measure(posts, **kwargs):
    return measure_propagation(posts, target=TARGET, subject="viral-monkey",
                               window_start=T-timedelta(hours=1), observed_at=T, **kwargs)


@pytest.mark.parametrize("case", DATASET["cases"], ids=lambda case: case["id"])
def test_labeled_replay_cases(case):
    if "error_contains" in case["expected"]:
        with pytest.raises(ValueError, match=case["expected"]["error_contains"]):
            run_case(DATASET, case)
    else:
        report = evaluate(dict(DATASET, cases=[case]))
        assert report["exact_match_accuracy"] == 1, report


def test_replay_evaluation_separates_parsing_and_trading():
    report = evaluate(DATASET)
    assert report["exact_match_cases"] == 19
    assert report["identity_precision"] == report["identity_recall"] == report["identity_accuracy"] == 1
    assert report["false_positive_count"] == report["false_negative_count"] == 0
    assert report["ambiguous_count"] == 3
    assert report["unknown_count"] == 3
    assert report["unexpected_parsing_errors"] == report["unsupported_inference_count"] == 0
    assert report["fixture_coverage"] == 1


def test_harness_detects_wrong_gold_and_unexpected_error():
    bad = json.loads(json.dumps(DATASET))
    bad["cases"][0]["expected"]["posts"][0]["relationship"] = "UNRELATED"
    assert evaluate(bad)["false_positive_count"] == 1
    bad["cases"][0]["observations"][0]["response"]["data"][0]["created_at"] = "invalid timestamp"
    assert evaluate(bad)["unexpected_parsing_errors"] == 1
    bad = json.loads(json.dumps(DATASET))
    bad["cases"][8]["expected"]["posts"][0]["relationship"] = "DIRECT_CONTRACT_REFERENCE"
    assert evaluate(bad)["false_negative_count"] == 1


def test_raw_deep_immutability_and_defensive_payload():
    response = {"data":{"id":"1", "text":"viral monkey", "created_at":"2026-10-01T12:00:00Z", "author_id":"a",
                        "public_metrics":{"like_count":3}}, "includes":{"users":[{"id":"a", "username":"fixture", "verified":True, "public_metrics":{"followers_count":100000}}]}}
    post = OfficialXResponseAdapter().normalize(response, detected_at=T, parsed_at=T, source_id="fixture")[0]
    response["data"]["text"] = "changed"
    assert json.loads(post.raw_payload_json)["data"]["text"] == "viral monkey"
    assert json.loads(post.account_payload_json)["verified"] is True
    assert post.author_username == "fixture"
    for obj, name, value in ((post,"text","changed"),(post.provenance,"source_id","changed"),
                             (post.public_metrics[0],"value",100)):
        with pytest.raises(FrozenInstanceError):
            setattr(obj,name,value)
    with pytest.raises(TypeError):
        replace(post,urls=[])
    with pytest.raises(ValueError):
        PublicMetric("likes",-1)
    with pytest.raises(ValueError):
        PublicMetric("likes",True)


def test_api_entities_references_metrics_and_raw_unknown_fields():
    post = raw(entities={"urls":[{"url":"https://t.co/test", "expanded_url":"https://example.com/story"}],
                         "mentions":[{"username":"person"}], "hashtags":[{"tag":"Monkey"}], "cashtags":[{"tag":"MON"}]},
               referenced_tweets=[{"type":"quoted","id":"q"},{"type":"replied_to","id":"r"},{"type":"retweeted","id":"s"}],
               public_metrics={"like_count":12,"quote_count":2}, context_annotations=[{"domain":{"name":"Meme"}}])
    assert post.urls == ("https://example.com/story",)
    assert post.mentions == ("person",) and post.hashtags == ("Monkey",) and post.cashtags == ("MON",)
    assert post.referenced_post("quoted") == ("q",)
    assert post.referenced_post("replied_to") == ("r",) and post.referenced_post("retweeted") == ("s",)
    assert "context_annotations" in json.loads(post.raw_payload_json)["data"]


@pytest.mark.parametrize("timestamp_field", ["posted_at","detected_at","parsed_at"])
def test_future_time_rejected(timestamp_field):
    post = raw()
    future = T+timedelta(seconds=1)
    if timestamp_field == "posted_at":
        with pytest.raises(ValueError, match="retrieval"):
            replace(post,posted_at=future)
    elif timestamp_field == "detected_at":
        with pytest.raises(ValueError, match="Future"):
            parsed(replace(post,detected_at=future,parsed_at=future))
    else:
        with pytest.raises(ValueError, match="Future"):
            parsed(replace(post,parsed_at=future))


def test_timestamp_order_latency_naive_inputs_and_boundary():
    post = raw()
    assert post.detection_latency_seconds == 600
    assert post.parsing_latency_seconds == 60
    with pytest.raises(ValueError):
        replace(post, parsed_at=post.detected_at-timedelta(seconds=1))
    with pytest.raises(ValueError,match="Timezone"):
        raw(detected_at=T.replace(tzinfo=None))
    assert parsed(raw(detected_at=T,parsed_at=T)).observed_at == T


def test_future_registry_cannot_backdate_token_association():
    with pytest.raises(ValueError,match="Future registry"):
        parsed(registry=replace(REGISTRY,known_at=T+timedelta(seconds=1)))
    with pytest.raises(ValueError,match="Future registry"):
        parsed(registry=replace(REGISTRY,known_at=T-timedelta(minutes=3)))


def test_conservative_identity_and_chain_collision():
    assert parsed(raw(A)).relationship.label == Relationship.DIRECT_CONTRACT_REFERENCE.value
    assert parsed(raw("$SOLO")).relationship.label == Relationship.DIRECT_TICKER_OR_NAME_REFERENCE.value
    assert parsed(raw("$MON")).relationship.label == Relationship.AMBIGUOUS_RELATION.value
    assert parsed(raw("viral monkey")).relationship.label == Relationship.INDIRECT_NARRATIVE_RELATION.value
    assert parsed(raw("unrelated dinner")).relationship.label == Relationship.UNRELATED.value
    other_chain = TokenAlias(CoinIdentity("ethereum",A))
    collision = replace(REGISTRY,tokens=REGISTRY.tokens+(other_chain,))
    result = parsed(raw(A),registry=collision)
    assert result.relationship.label == "AMBIGUOUS_RELATION"
    assert result.direct_coin_ids == ()
    assert len(result.candidate_coin_ids) == 2


def test_case_sensitive_addresses_and_no_substring_aliases():
    custom = CoinIdentity("solana","AbCdEfgHijKLMnopQRstuVwXYZ12345678")
    registry = replace(REGISTRY,tokens=REGISTRY.tokens+(TokenAlias(custom),))
    p = CTParser(registry).parse(raw(custom.contract_address.lower()),target=custom,observed_at=T)
    assert custom.coin_id not in p.direct_coin_ids
    assert parsed(raw("Monkey Alphabet")).relationship.label == "UNRELATED"


def test_entity_kinds_urls_and_unknown_subject_retention():
    kinds = ("person","company","product","meme","animal_character","event","phrase","subject")
    aliases = tuple(SubjectAlias("subject-"+k,k,("phrase"+str(i),)) for i,k in enumerate(kinds))
    registry = replace(REGISTRY,subjects=aliases)
    post = parsed(raw(" ".join(a.aliases[0] for a in aliases)+" #party @source $SOLO https://example.org/news"),registry=registry)
    extracted = {e.kind for e in post.entities}
    assert set(kinds) | {"url","domain","hashtag","account","cashtag"} <= extracted
    p = parsed(raw("Never-seen new phrase"))
    assert p.subjects == () and p.raw.text == "Never-seen new phrase"
    assert p.classification.label == "UNKNOWN"


def test_subject_token_counts_are_separate_and_no_fake_independence():
    posts = (parsed(raw("viral monkey",id="1",author="a")),
             parsed(raw("viral monkey "+A,id="2",author="b")),
             parsed(raw("viral monkey "+B,id="3",author=None)))
    facts = measure(posts).facts
    assert facts["underlying_subject_mention_count"] == 3
    assert facts["specific_token_mention_count"] == 1
    assert facts["unique_author_count"] == 2 and facts["unknown_author_posts"] == 1
    assert facts["independent_source_count"] is None
    assert facts["competing_contract_count"] == 1
    assert len(facts["contract_post_evidence"]) == 2
    facts["specific_token_mention_count"] = 999
    assert measure(posts).facts["specific_token_mention_count"] == 1


def test_duplicate_near_duplicate_and_noise_rule_lineage():
    posts = tuple(parsed(raw("viral monkey buy now "+A+suffix,id=str(i),author=str(i)))
                  for i,suffix in enumerate(("","","!")))
    snapshot = measure(posts)
    f = snapshot.facts
    assert f["duplicate_content_count"] == 1 and f["near_duplicate_pair_count"] == 3
    assert f["similar_posts_within_window"] == 3
    assert f["repeated_contract_promotion_count"] == 2
    assert snapshot.interpretations[0].label == "possible coordinated/noisy propagation"
    assert snapshot.interpretations[0].rule_version == "ct-propagation/v1"
    assert snapshot.interpretations[0].as_of == T
    assert snapshot.interpretations[0].evidence_ids
    assert "bot" not in snapshot.interpretations[0].label
    with pytest.raises(FrozenInstanceError):
        snapshot.facts_json = "{}"


def test_repeated_urls_reference_behavior_and_empty_windows():
    posts = tuple(parsed(raw("viral monkey https://example.com/s",id=str(i),referenced_tweets=[{"type":kind,"id":"source"}]))
                  for i,kind in enumerate(("retweeted","quoted","replied_to")))
    facts = measure(posts).facts
    assert facts["repeated_url_count"] == 2
    assert facts["repost_count"] == facts["quote_count"] == facts["reply_count"] == 1
    empty = measure(()).facts
    assert empty["duplicate_content_ratio"] is None
    assert empty["first_observed_mention_at"] is None
    assert empty["independent_source_count"] is None


def test_latest_metric_snapshot_dedup_and_window():
    first = raw(id="1",public_metrics={"like_count":1})
    later = raw(id="1",public_metrics={"like_count":100},detected_at=T-timedelta(minutes=2),parsed_at=T-timedelta(minutes=1))
    snap = measure((parsed(later),parsed(first)))
    assert len(snap.posts) == 1 and snap.posts[0].raw.public_metrics[0].value == 100
    assert snap.facts["duplicate_post_observations"] == 1
    old = raw(id="old",posted_at="2026-10-01T10:00:00Z",detected_at=T-timedelta(hours=2),parsed_at=T-timedelta(hours=2))
    assert measure((parsed(old),)).facts["unique_posts_in_window"] == 0
    future = parsed(raw(),cutoff=T+timedelta(seconds=1))
    with pytest.raises(ValueError,match="future"):
        measure((future,))


def test_catalyst_propagation_latency_is_measured_not_predicted():
    event = NarrativeEvidence("catalyst",EvidenceKind.CATALYST,T-timedelta(minutes=30),T-timedelta(minutes=20),
        NarrativeProvenance("event","fixture",T-timedelta(minutes=20)),"Subject event","viral-monkey",post_id="origin")
    snap = measure((parsed(raw()),),catalyst=event)
    assert snap.facts["catalyst_age_seconds"] == 1800
    assert snap.facts["catalyst_to_ct_latency_seconds"] == 900
    assert snap.catalyst_evidence.evidence_id == "catalyst"
    with pytest.raises(ValueError,match="catalyst"):
        measure((parsed(raw()),),catalyst=replace(event,subject="unrelated"))
    future = replace(event,detected_at=T+timedelta(seconds=1))
    with pytest.raises(ValueError,match="catalyst"):
        measure((parsed(raw()),),catalyst=future)


def test_narrative_bridge_does_not_invent_identity_capture_or_hypothesis():
    posts = (parsed(raw()),parsed(raw("viral monkey",id="subject")))
    evidence = narrative_evidence(posts,subject="viral-monkey",observed_at=T)
    assert len(evidence) == 2
    assert all(e.kind == EvidenceKind.CT_X for e in evidence)
    p = NarrativeResearchEngine().build(coin=TARGET,observed_at=T,completed_at=T,evidence=evidence)
    assert p.state == NarrativeState.NO_NARRATIVE_FOUND
    # Existing support rule can use CT alongside separately supplied evidence.
    def supplied(id,kind):
        return NarrativeEvidence(id,kind,T-timedelta(hours=1),T-timedelta(minutes=10),
            NarrativeProvenance(id,"manual",T-timedelta(minutes=10)),"Manual retained observation","viral-monkey",TARGET)
    extra = (supplied("identity",EvidenceKind.IDENTITY_MATCH),supplied("capture",EvidenceKind.TOKEN_CAPTURE))
    refs = ("identity","capture",evidence[0].evidence_id)
    supported = NarrativeResearchEngine().build(coin=TARGET,observed_at=T,completed_at=T,evidence=evidence+extra,
        claims=(ResearchClaim("hypothesis","Manual association hypothesis",refs),))
    assert supported.state == NarrativeState.NARRATIVE_FOUND


def test_bridge_missing_fields_false_association_future_and_provenance():
    p = parsed(raw("viral monkey is not associated with "+A))
    ct = narrative_evidence((p,),subject="viral-monkey",observed_at=T)
    assert ct[0].provenance == p.raw.provenance
    assert ct[0].post_id == p.raw.post_id
    assert ct[0].kind == EvidenceKind.CT_X  # lexical cooccurrence, never capture
    assert narrative_evidence((parsed(raw(posted_at=None,author=None)),),subject="viral-monkey",observed_at=T) == ()
    assert narrative_evidence((parsed(raw(A)),),subject="viral-monkey",observed_at=T) == ()
    with pytest.raises(ValueError,match="Future"):
        narrative_evidence((p,),subject="viral-monkey",observed_at=T-timedelta(seconds=1))


def test_bridge_reports_exclusions_and_versioned_multisubject_lineage():
    missing = parsed(raw(posted_at=None,author=None))
    bridge = narrative_bridge((missing,),subject="viral-monkey",observed_at=T)
    assert bridge.evidence == ()
    assert "posted_at" in bridge.exclusions[0].reason
    assert bridge.exclusions[0].evidence_ids[0] == missing.raw.record_id
    p = parsed(raw("Zara introduces viral monkey"))
    a = narrative_bridge((p,),subject="viral-monkey",observed_at=T).evidence[0]
    b = narrative_bridge((p,),subject="zara",observed_at=T).evidence[0]
    assert a.evidence_id != b.evidence_id
    assert "ct-parser/v1" in a.relevance and p.registry_id in a.relevance
    assert a.provenance.content_hash


def test_meme_classification_is_explicit_versioned_rule():
    p = parsed(raw("viral monkey community meme"))
    assert p.classification.label == "MEME_OR_COMMUNITY"
    assert p.classification.rule_version == "ct-parser/v1"
    assert p.classification.as_of == T


def test_mixed_registry_replay_rejected():
    old = parsed(raw(id="old"))
    new = parsed(raw(id="new"),registry=replace(REGISTRY,version="synthetic-registry/v2"))
    with pytest.raises(ValueError,match="Mixed registry"):
        measure((old,new))


def test_raw_append_only_snapshots_and_availability():
    store = RawXStore()
    p = raw()
    store.append(p)
    later = raw(detected_at=T,parsed_at=T,public_metrics={"like_count":20})
    store.append(later)
    assert store.as_of(T-timedelta(minutes=1)) == (p,)
    assert store.as_of(T) == (p,later)
    with pytest.raises(ValueError,match="Duplicate"):
        store.append(p)
    with pytest.raises(AttributeError):
        store.records = ()


def test_later_engagement_cannot_leak_into_earlier_ct_state():
    earlier = raw(public_metrics={"like_count":1})
    later = raw(public_metrics={"like_count":999},detected_at=T+timedelta(seconds=1),parsed_at=T+timedelta(seconds=2))
    store = RawXStore()
    store.append(earlier)
    store.append(later)
    safe = tuple(parsed(post) for post in store.as_of(T))
    assert measure(safe).posts[0].raw.public_metrics[0].value == 1
    with pytest.raises(ValueError,match="Future"):
        parsed(later)


def test_future_reference_body_is_retained_but_not_interpreted():
    payload = {"data":{"id":"parent","text":"Dinner","created_at":"2026-10-01T12:00:00Z"},
               "includes":{"tweets":[{"id":"future","text":"viral monkey "+A,"created_at":"2026-10-01T12:30:00Z"}]}}
    post = OfficialXResponseAdapter().normalize(payload,detected_at=T,parsed_at=T,source_id="fixture")[0]
    assert "future" in post.raw_payload_json
    result = parsed(post)
    assert result.subjects == () and result.direct_coin_ids == ()
    assert result.relationship.label == "UNRELATED"


def test_adapter_config_never_contains_credentials(monkeypatch):
    config = XAdapterConfig()
    assert not config.credential_present({})
    assert config.credential_present({"X_BEARER_TOKEN":"synthetic-secret"})
    assert "synthetic-secret" not in repr(config)
    monkeypatch.setenv("X_BEARER_TOKEN","another-synthetic-secret")
    assert config.credential_present()
    assert not hasattr(OfficialXResponseAdapter(),"request")
    assert not hasattr(OfficialXResponseAdapter(),"fetch")
    assert Path(".env.example").read_text().strip() == "X_BEARER_TOKEN="
    ignore = Path(".gitignore").read_text()
    assert ".env" in ignore and "!.env.example" in ignore


def test_usage_accounting_cutoff_unknown_units_errors_and_duplicates():
    ledger = ApiUsageLedger()
    assert ledger.summary(T)["requests_made"] == 0
    ledger.append(ApiUsageEvent("r1",T-timedelta(minutes=1),200,posts_returned=5,user_lookups=1,
                                pagination_requests=1,duplicates_received=2,known_usage_units=5))
    ledger.append(ApiUsageEvent("r2",T,429,api_error_count=1,rate_limit_remaining=0,rate_limit_reset=123))
    ledger.append(ApiUsageEvent("future",T+timedelta(seconds=1),500))
    f = ledger.summary(T)
    assert f["requests_made"] == 2 and f["posts_returned"] == 5
    assert f["user_lookups"] == 1 and f["pagination_requests"] == 1 and f["duplicates_received"] == 2
    assert f["rate_limit_responses"] == f["api_errors"] == f["api_error_count"] == 1
    assert f["known_usage_units"] is None
    assert "cost" not in f
    assert ledger.summary(T-timedelta(seconds=1))["known_usage_units"] == 5
    with pytest.raises(ValueError):
        ledger.append(ledger.events[0])
    with pytest.raises(FrozenInstanceError):
        ledger.events[0].posts_returned = 99
    with pytest.raises(ValueError):
        ApiUsageEvent("bad",T,200,posts_returned=-1)


def test_usage_estimates_require_explicit_method_and_never_invent_costs():
    with pytest.raises(ValueError):
        ApiUsageEvent("estimate",T,200,estimated_usage_units=4)
    ledger = ApiUsageLedger()
    ledger.append(ApiUsageEvent("estimate",T,200,estimated_usage_units=4,usage_estimate_version="configured-fixture/v1"))
    assert ledger.summary(T)["estimated_usage_units"] == 4
    assert ledger.summary(T)["known_usage_units"] is None
    assert "cost" not in ledger.summary(T)


def test_typed_registry_rule_config_and_invalid_inputs():
    with pytest.raises(TypeError):
        replace(REGISTRY, tokens=list(REGISTRY.tokens))
    with pytest.raises(ValueError):
        replace(REGISTRY, tokens=REGISTRY.tokens+REGISTRY.tokens)
    with pytest.raises(ValueError):
        SubjectAlias("subject","score",("x",))
    with pytest.raises(ValueError):
        PropagationConfig(near_duplicate_similarity=2)
    with pytest.raises(ValueError):
        PropagationConfig(tight_window_seconds=-1)
    with pytest.raises(TypeError):
        measure_propagation([],target=TARGET,subject="viral-monkey",window_start=T,observed_at=T)
    with pytest.raises(ValueError):
        measure_propagation((),target=TARGET,subject="viral-monkey",window_start=T+timedelta(seconds=1),observed_at=T)
