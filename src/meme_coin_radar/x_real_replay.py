"""Blinded human labeling and sealed development/held-out real-response replay.

No live transport and no automatic labels. Original source cutoffs and actual
later computation times are distinct; historical parsing times are not invented.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .ct_models import PostClass, Relationship, canonical, digest
from .ct_parser import CTParser, narrative_bridge
from .ct_replay import registry_from_fixture, timestamp
from .narrative import CoinIdentity, EvidenceKind, NarrativeResearchEngine, NarrativeState, _time
from .x_adapter import OfficialXResponseAdapter
from .x_bounded_capture import _write_new

LABEL_FIELDS = ("relevant", "subjects", "relationship", "classification", "tokenless_external_catalyst",
                "direct_coin_ids", "competing_coin_ids", "duplicate_of_post_ids", "repost_of_post_ids",
                "quote_of_post_ids", "reply_to_post_ids")
ERROR_CATEGORIES = frozenset({"ticker_collision", "contract_extraction", "subject_extraction", "insufficient_context",
    "quote_repost_lineage", "slang", "meme_language", "indirect_catalyst", "competing_token_confusion",
    "missing_api_field", "deterministic_rule_limitation", "annotation_ambiguity"})


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def frozen_samples(directory: Path):
    """Verify persisted bytes; exclude verification/control posts from sample."""
    rows = []
    for response_file in sorted(directory.glob("request-*-response.json")):
        response = _load(response_file)
        reservation = _load(directory/(response["request_id"]+".json"))
        raw_bytes = (directory/response["body_file"]).read_bytes()
        if hashlib.sha256(raw_bytes).hexdigest() != response["body_sha256"]:
            raise ValueError("Frozen response bytes changed")
        payload = json.loads(raw_bytes) if raw_bytes else None
        if payload != response["payload"]:
            raise ValueError("Response envelope does not match frozen source bytes")
        if reservation["endpoint"] != "https://api.x.com/2/tweets/search/recent" or response["http_status"] != 200:
            continue
        for post in payload.get("data", []):
            rows.append(dict(post=post, request_id=response["request_id"], source_cutoff_at=response["received_at"],
                             source_body_sha256=response["body_sha256"], response=payload))
    # Preserve every response. The labelable sample uses first receipt per post.
    first = {}
    for row in sorted(rows, key=lambda r:(r["source_cutoff_at"], r["post"]["id"])):
        first.setdefault(row["post"]["id"], row)
    return tuple(first.values())


def deterministic_split(rows: tuple, *, seed: str):
    """Group known authors, direct reference lineage and identical normalized text.

    Prevent these obvious duplicates from crossing splits; narrative-level
    independence is not asserted on a small convenience sample.
    """
    ids = {r["post"]["id"] for r in rows}
    parent = {id:id for id in ids}
    def root(id):
        while parent[id] != id:
            parent[id] = parent[parent[id]]
            id = parent[id]
        return id
    def join(a,b):
        parent[root(b)] = root(a)
    authors, texts, references = {}, {}, {}
    for row in rows:
        post = row["post"]
        id = post["id"]
        author = post.get("author_id")
        if author:
            if author in authors:
                join(id,authors[author])
            authors[author] = id
        text = post.get("text")
        if text:
            normalized = " ".join(text.casefold().split())
            if normalized in texts:
                join(id,texts[normalized])
            texts[normalized]=id
        for reference in post.get("referenced_tweets", []):
            ref_id = reference["id"]
            if ref_id in ids:
                join(id,ref_id)
            if ref_id in references:
                join(id,references[ref_id])
            references[ref_id]=id
    groups = {}
    for id in sorted(ids):
        groups.setdefault(root(id),[]).append(id)
    ordered = sorted(tuple(sorted(group)) for group in groups.values())
    ordered.sort(key=lambda group:digest((seed,group)))
    heldout_count = min(len(ordered)-1, max(1, math.ceil(len(ordered)*0.25))) if len(ordered)>1 else 0
    result=[]
    for i, group in enumerate(ordered):
        result.extend(dict(post_id=id, group_id=digest(group), split="held_out" if i<heldout_count else "development")
                      for id in group)
    return sorted(result,key=lambda r:r["post_id"])


def prepare_labeling(directory: Path, *, parser_source: Path):
    rows=frozen_samples(directory)
    if not rows:
        raise ValueError("No genuine search sample available")
    registry_json=_load(directory/"registry.json")
    registry=registry_from_fixture({"registry":registry_json})
    if any(registry.known_at > timestamp(r["source_cutoff_at"]) for r in rows):
        raise ValueError("Registry was not available at original source cutoff")
    plan=_load(directory/"collection_plan.json")
    manifest=dict(version="real-x-split/v1",seed=plan["split_seed"],
        grouping="known_author+reference_lineage+normalized_duplicate_components",
        parser_sha256=hashlib.sha256(parser_source.read_bytes()).hexdigest(),
        registry_id=registry.record_id,plan_id=digest(plan),
        source_rows=tuple(dict(post_id=r["post"]["id"],request_id=r["request_id"],
                              source_cutoff_at=r["source_cutoff_at"],body_sha256=r["source_body_sha256"]) for r in rows),
        assignments=deterministic_split(rows,seed=plan["split_seed"]),
        limitation="Related narratives may overlap; this is a tiny convenience sample, not independent population coverage")
    _write_new(directory/"split_manifest.json",manifest)
    template=dict(version="real-x-human-labels/v1",split_manifest_id=digest(manifest),
        instructions="Human labels only. Predictions intentionally absent. Null=pending; UNKNOWN=reviewed insufficient evidence. Mark status labeled and supply annotator_id/labeled_at for each row.",
        target=plan["target"],canonical_known_subjects=[s["subject"] for s in registry_json["subjects"]],
        rows=[dict(post_id=r["post"]["id"],raw_source=dict(request_id=r["request_id"],source_cutoff_at=r["source_cutoff_at"],
            body_sha256=r["source_body_sha256"]),status="pending",annotator_id=None,labeled_at=None,
            labels={field:None for field in LABEL_FIELDS},error_categories=[],notes="") for r in rows])
    _write_new(directory/"human_labels.json",template)
    review=["# Real X labeling review — parser predictions hidden", "",
        "Edit human_labels.json locally. Every label is blank until a human supplies it.",
        "Target: "+canonical(plan["target"]),
        "Relevance means relation to this target or its underlying subject; other tokens can be unrelated to this target.",
        "Known subject IDs: "+", ".join(template["canonical_known_subjects"])+". Add unseen subjects honestly; do not force a dictionary match.",
        "Use empty arrays for known none, UNKNOWN for reviewed insufficient evidence, null for pending.",
        "Relationship choices: "+", ".join(r.value for r in Relationship)+", UNKNOWN.",
        "Class choices: "+", ".join(c.value for c in PostClass)+".",
        "Direct coin IDs require chain:contract certainty. Ticker names alone do not prove a contract.",
        "API reference IDs are raw facts; referenced bodies were not downloaded. Do not infer their text.",
        "Annotator ID can be a local alias. Set labeled_at to an aware ISO timestamp and status to labeled.",
        "No parser predictions or split membership are shown here to avoid labeling bias.", ""]
    for row in rows:
        post=row["post"]
        review.extend(["## Post "+post["id"],"", "Source: https://x.com/i/status/"+post["id"],
            "Author ID: "+str(post.get("author_id")),"Posted: "+str(post.get("created_at")),
            "Received: "+row["source_cutoff_at"],"", "```text",post.get("text", "[TEXT UNAVAILABLE]"),"```",
            "Raw references: "+canonical(post.get("referenced_tweets",[])),
            "Raw entities: "+canonical(post.get("entities",{})),""])
    with (directory/"LABEL_REVIEW.md").open("x",encoding="utf-8") as f:
        f.write("\n".join(review)+"\n")
    return dict(sample_posts=len(rows),split_counts=dict(Counter(a["split"] for a in manifest["assignments"])),
                pending_labels=len(rows),split_manifest_id=digest(manifest))


def validate_labels(labels, manifest):
    if labels.get("version") != "real-x-human-labels/v1" or labels.get("split_manifest_id") != digest(manifest):
        raise ValueError("Label schema/split lineage mismatch")
    rows=labels["rows"]
    expected={a["post_id"] for a in manifest["assignments"]}
    if len(rows)!=len(expected) or {r["post_id"] for r in rows} != expected:
        raise ValueError("Labels must cover the frozen sample exactly once")
    for row in rows:
        if row["status"] == "pending":
            continue
        if row["status"] != "labeled" or not isinstance(row.get("annotator_id"),str) or not row["annotator_id"].strip():
            raise ValueError("Explicit human annotator and status required")
        labeled_at=_time(timestamp(row["labeled_at"]))
        source=next(r for r in manifest["source_rows"] if r["post_id"]==row["post_id"])
        if row.get("raw_source") != dict(request_id=source["request_id"],source_cutoff_at=source["source_cutoff_at"],body_sha256=source["body_sha256"]):
            raise ValueError("Human label source lineage changed")
        if labeled_at < timestamp(source["source_cutoff_at"]):
            raise ValueError("Human annotation cannot precede source receipt")
        ground=row["labels"]
        if set(ground)!=set(LABEL_FIELDS) or any(v is None for v in ground.values()):
            raise ValueError("Reviewed labels must be complete; UNKNOWN is an explicit abstention")
        for field in ("relevant","tokenless_external_catalyst"):
            if type(ground[field]) is not bool and ground[field]!="UNKNOWN":
                raise ValueError("Boolean label or UNKNOWN required")
        if ground["relationship"] not in {r.value for r in Relationship}|{"UNKNOWN"}:
            raise ValueError("Invalid relationship label")
        if ground["classification"] not in {c.value for c in PostClass}:
            raise ValueError("Invalid post-class label")
        for field in set(LABEL_FIELDS)-{"relevant","tokenless_external_catalyst","relationship","classification"}:
            value=ground[field]
            if value!="UNKNOWN" and (not isinstance(value,list) or any(not isinstance(v,str) for v in value)):
                raise ValueError("String array or UNKNOWN required")
        if any(c not in ERROR_CATEGORIES for c in row.get("error_categories",[])):
            raise ValueError("Invalid error-analysis category")


def _f1_metrics(truth, prediction):
    tp=len(truth & prediction); fp=len(prediction-truth); fn=len(truth-prediction)
    return dict(tp=tp,fp=fp,fn=fn,precision=tp/(tp+fp) if tp+fp else None,recall=tp/(tp+fn) if tp+fn else None)


def replay_labeled_split(directory: Path, *, split: str, parser_source: Path, release_held_out=False):
    if split not in {"development","held_out"}:
        raise ValueError("Explicit split required")
    manifest=_load(directory/"split_manifest.json")
    if hashlib.sha256(parser_source.read_bytes()).hexdigest()!=manifest["parser_sha256"]:
        raise ValueError("Parser differs from frozen experiment; create a versioned development experiment")
    labels=_load(directory/"human_labels.json")
    validate_labels(labels,manifest)
    registry=registry_from_fixture({"registry":_load(directory/"registry.json")})
    plan=_load(directory/"collection_plan.json")
    if registry.record_id != manifest["registry_id"] or digest(plan)!=manifest["plan_id"]:
        raise ValueError("Registry/plan changed after split freeze")
    assigned={a["post_id"] for a in manifest["assignments"] if a["split"]==split}
    selected=[r for r in labels["rows"] if r["post_id"] in assigned]
    pending=sum(r["status"]!="labeled" for r in selected)
    if pending:
        return dict(split=split,status="human_labels_pending",sample_posts=len(selected),pending_labels=pending,metrics=None)
    if not selected:
        return dict(split=split,status="insufficient_sample",sample_posts=0,metrics=None)
    if split=="held_out" and not release_held_out:
        raise ValueError("Held-out evaluation sealed until explicit final release")
    # Freeze labels before evaluation. A second run cannot silently replace them.
    receipt=dict(split=split,labels_sha256=digest(selected),split_manifest_id=digest(manifest),
                 parser_sha256=manifest["parser_sha256"])
    receipt_file=directory/(split+"-evaluation-lock.json")
    if receipt_file.exists():
        if _load(receipt_file)!=receipt:
            raise ValueError("Labels changed after evaluation; append a separate correction experiment")
    else:
        _write_new(receipt_file,receipt)
    rows_by_id={r["post"]["id"]:r for r in frozen_samples(directory)}
    if {r["post"]["id"] for r in rows_by_id.values()} != {a["post_id"] for a in manifest["assignments"]}:
        raise ValueError("Frozen source set changed")
    parser=CTParser(registry)
    target=CoinIdentity(**plan["target"])
    outcomes=[]
    subject_true=set();subject_pred=set();identity_true=set();identity_pred=set()
    correct=errors=ambiguous=unknown=unsupported=0
    scored_posts=annotation_unknown_fields=0
    field_correct=Counter();field_total=Counter();categories=Counter()
    all_raw_text={id:r["post"].get("text") for id,r in rows_by_id.items()}
    for label in selected:
        id=label["post_id"]; source=rows_by_id[id]; cutoff=timestamp(source["source_cutoff_at"])
        if registry.known_at>cutoff:
            raise ValueError("Future registry cannot enter original source cutoff")
        computed_at=datetime.now(timezone.utc)
        try:
            raw_posts=OfficialXResponseAdapter().normalize(source["response"],detected_at=cutoff,parsed_at=computed_at,
                source_id="official-x:"+source["request_id"],data_mode="retrospective")
            raw=next(p for p in raw_posts if p.post_id==id)
            parsed=parser.parse(raw,target=target,observed_at=computed_at)
            references={kind:list(raw.referenced_post(kind)) for kind in ("retweeted","quoted","replied_to")}
            actual=dict(relevant=(parsed.relationship.label!="UNRELATED" and raw.text is not None),
                subjects=list(parsed.subjects),relationship=parsed.relationship.label,classification=parsed.classification.label,
                tokenless_external_catalyst=parsed.possible_external_catalyst,direct_coin_ids=list(parsed.direct_coin_ids),
                competing_coin_ids=[c for c in parsed.direct_coin_ids if c!=target.coin_id],
                duplicate_of_post_ids=sorted(other for other,text in all_raw_text.items() if other!=id and text==raw.text and text is not None),
                repost_of_post_ids=references["retweeted"],quote_of_post_ids=references["quoted"],reply_to_post_ids=references["replied_to"])
            ambiguous+=parsed.relationship.label=="AMBIGUOUS_RELATION"
            unknown+=parsed.classification.label=="UNKNOWN"
            unsupported+=not parsed.classification.evidence_ids or not parsed.relationship.rule_version
            bridge=narrative_bridge((parsed,),subject=plan["subject"],observed_at=computed_at)
            packet=NarrativeResearchEngine().build(coin=target,observed_at=computed_at,completed_at=computed_at,
                evidence=bridge.evidence,data_mode="retrospective")
            bridge_ok=(packet.state==NarrativeState.NO_NARRATIVE_FOUND and
                all(e.kind==EvidenceKind.CT_X and e.provenance==raw.provenance and
                    e.occurred_at==raw.posted_at and e.detected_at==cutoff for e in bridge.evidence))
            mismatches=[]
            scored_fields=0
            for field,gold in label["labels"].items():
                if gold=="UNKNOWN":
                    annotation_unknown_fields+=1
                    continue
                scored_fields+=1
                field_total[field]+=1
                match=set(actual[field])==set(gold) if isinstance(gold,list) else actual[field]==gold
                field_correct[field]+=match
                if not match:
                    mismatches.append(field)
            scored_posts+=bool(scored_fields)
            correct+=bool(scored_fields) and not mismatches
            if label["labels"]["subjects"]!="UNKNOWN":
                subject_true.update((id,s) for s in label["labels"]["subjects"])
                subject_pred.update((id,s) for s in actual["subjects"])
            if label["labels"]["direct_coin_ids"]!="UNKNOWN":
                identity_true.update((id,c) for c in label["labels"]["direct_coin_ids"])
                identity_pred.update((id,c) for c in actual["direct_coin_ids"])
            failure_categories=label.get("error_categories",[]) if mismatches else []
            if mismatches and not failure_categories:
                inferred=set()
                if "subjects" in mismatches:
                    inferred.add("subject_extraction")
                if "direct_coin_ids" in mismatches:
                    inferred.add("contract_extraction")
                if "competing_coin_ids" in mismatches:
                    inferred.add("competing_token_confusion")
                if any(f.endswith("post_ids") for f in mismatches):
                    inferred.add("quote_repost_lineage")
                if "relationship" in mismatches:
                    inferred.add("ticker_collision" if parsed.relationship.label=="AMBIGUOUS_RELATION" else "insufficient_context")
                if "tokenless_external_catalyst" in mismatches:
                    inferred.add("indirect_catalyst")
                failure_categories=sorted(inferred or {"deterministic_rule_limitation"})
            categories.update(failure_categories)
            outcomes.append(dict(post_id=id,source_cutoff_at=cutoff.isoformat(),computed_at=computed_at.isoformat(),
                actual=actual,ground_truth=label["labels"],mismatched_fields=mismatches,error_categories=failure_categories,
                rule_version=parsed.parser_version,registry_id=parsed.registry_id,raw_record_id=raw.record_id,
                bridge_checks_passed=bridge_ok,bridge_evidence_ids=[e.evidence_id for e in bridge.evidence],
                bridge_exclusions=[e.reason for e in bridge.exclusions],narrative_state=packet.state.value))
        except (ValueError,TypeError,KeyError,StopIteration) as exc:
            errors+=1
            categories["missing_api_field" if isinstance(exc,(KeyError,StopIteration)) else "deterministic_rule_limitation"]+=1
            outcomes.append(dict(post_id=id,parsing_error=type(exc).__name__,source_cutoff_at=cutoff.isoformat()))
    report=dict(split=split,status="evaluated",data_mode="retrospective",sample_posts=len(selected),
        metrics=dict(exact_match_accuracy=correct/(scored_posts+errors) if scored_posts+errors else None,
            scored_posts=scored_posts,annotation_unknown_fields=annotation_unknown_fields,
            identity_resolution=_f1_metrics(identity_true,identity_pred),
            subject_extraction=_f1_metrics(subject_true,subject_pred),
            field_accuracy={field:dict(correct=field_correct[field],evaluated=n,accuracy=field_correct[field]/n) for field,n in field_total.items()},
            ambiguous_count=ambiguous,unknown_count=unknown,unsupported_inference_count=unsupported,parsing_errors=errors,
            coverage=(len(selected)-errors)/len(selected)),error_categories=dict(categories),outcomes=outcomes,
        limitation="Human labels required; convenience sample; source cutoff is original receipt, computation is later; not trading performance")
    _write_new(directory/(split+"-metrics.json"),report)
    return report


def usage_report(directory: Path):
    reservations=[_load(p) for p in directory.glob("request-*.json") if p.stem.count("-")==1]
    responses=[_load(p) for p in directory.glob("request-*-response.json")]
    successful=[r for r in responses if r["http_status"]==200]
    report=dict(request_attempts_reserved=len(reservations),http_responses_received=sum(r["http_status"] is not None for r in responses),
        successful_api_requests=len(successful),posts_received=sum(r["posts_returned"] for r in responses),
        resources_received=sum(r["resources_returned"] for r in responses),
        expanded_users_received=sum(r["expanded_users_returned"] for r in responses),
        duplicates_received=sum(r["duplicates_received"] for r in responses),
        http_errors=sum(r["http_status"] is not None and r["http_status"]>=400 for r in responses),
        transport_errors=sum(r["transport_error"] is not None for r in responses),
        rate_limit_responses=sum(r["http_status"]==429 for r in responses),pagination_used=0,known_usage_units=None,
        monetary_charge="not_determined_from_response_metadata",purchases_or_plan_changes=0,
        requests=[dict(**r,**{k:v for k,v in next(p for p in responses if p["request_id"]==r["request_id"]).items()
                            if k in {"http_status","received_at","rate_limit_metadata","posts_returned","resources_returned",
                                     "duplicates_received","transport_error","stop_reason","pagination_metadata"}}) for r in reservations])
    return report


def development_smoke(directory: Path, *, parser_source: Path):
    """Unlabeled integrity diagnostics only; never accesses held-out predictions."""
    manifest=_load(directory/"split_manifest.json")
    if hashlib.sha256(parser_source.read_bytes()).hexdigest()!=manifest["parser_sha256"]:
        raise ValueError("Parser changed after experiment freeze")
    registry=registry_from_fixture({"registry":_load(directory/"registry.json")})
    plan=_load(directory/"collection_plan.json")
    if registry.record_id!=manifest["registry_id"] or digest(plan)!=manifest["plan_id"]:
        raise ValueError("Frozen research context changed")
    development={a["post_id"] for a in manifest["assignments"] if a["split"]=="development"}
    outcomes=[]
    for source in frozen_samples(directory):
        id=source["post"]["id"]
        if id not in development:
            continue
        cutoff=timestamp(source["source_cutoff_at"])
        if registry.known_at>cutoff:
            raise ValueError("Future registry")
        computed=datetime.now(timezone.utc)
        try:
            raw=next(p for p in OfficialXResponseAdapter().normalize(source["response"],detected_at=cutoff,parsed_at=computed,
                source_id="official-x:"+source["request_id"],data_mode="retrospective") if p.post_id==id)
            parsed=CTParser(registry).parse(raw,target=CoinIdentity(**plan["target"]),observed_at=computed)
            bridge=narrative_bridge((parsed,),subject=plan["subject"],observed_at=computed)
            packet=NarrativeResearchEngine().build(coin=parsed.target,observed_at=computed,completed_at=computed,
                evidence=bridge.evidence,data_mode="retrospective")
            future_guard=False
            try:
                narrative_bridge((parsed,),subject=plan["subject"],observed_at=cutoff)
            except ValueError:
                future_guard=True  # actual later parsing cannot masquerade as receipt-time completed evidence
            checks=dict(ct_only=all(e.kind==EvidenceKind.CT_X for e in bridge.evidence),
                provenance_preserved=all(e.provenance==raw.provenance for e in bridge.evidence),
                timestamps_preserved=all(e.occurred_at==raw.posted_at and e.detected_at==cutoff for e in bridge.evidence),
                no_narrative_found=packet.state==NarrativeState.NO_NARRATIVE_FOUND,
                future_completion_excluded=future_guard,
                ambiguous_target_not_forced=parsed.relationship.label!="AMBIGUOUS_RELATION" or all(e.token is None for e in bridge.evidence))
            outcomes.append(dict(post_id=id,checks=checks,all_checks_passed=all(checks.values()),
                ct_evidence_count=len(bridge.evidence),bridge_exclusion_count=len(bridge.exclusions),
                source_cutoff_at=cutoff.isoformat(),computed_at=computed.isoformat()))
        except (ValueError,TypeError,KeyError,StopIteration) as exc:
            outcomes.append(dict(post_id=id,parsing_error=type(exc).__name__,all_checks_passed=False))
    report=dict(status="unlabeled_development_integrity_checks_only",split="development",posts_checked=len(outcomes),
        passing_posts=sum(o["all_checks_passed"] for o in outcomes),
        parsing_errors=sum("parsing_error" in o for o in outcomes),
        held_out_predictions_accessed=False,human_performance_metrics=None,outcomes=outcomes)
    _write_new(directory/"development-integrity-checks.json",report)
    return report


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("directory",type=Path)
    cli.add_argument("--prepare-labels",action="store_true")
    cli.add_argument("--split",choices=("development","held_out"))
    cli.add_argument("--release-held-out",action="store_true")
    cli.add_argument("--usage",action="store_true")
    cli.add_argument("--development-smoke",action="store_true")
    args=cli.parse_args()
    parser_source=Path(__file__).with_name("ct_parser.py")
    if args.prepare_labels:
        result=prepare_labeling(args.directory,parser_source=parser_source)
    elif args.split:
        result=replay_labeled_split(args.directory,split=args.split,parser_source=parser_source,release_held_out=args.release_held_out)
    elif args.usage:
        result=usage_report(args.directory)
    elif args.development_smoke:
        result=development_smoke(args.directory,parser_source=parser_source)
    else:
        cli.error("Choose preparation, split replay or usage")
    print(json.dumps(result,sort_keys=True,indent=2))


if __name__=="__main__":
    main()
