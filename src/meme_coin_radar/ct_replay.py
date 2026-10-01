"""Local labeled replay. Metrics evaluate parsing, never token outcomes."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from .ct_models import PostClass, Relationship
from .ct_parser import CTParser, CTRegistry, SubjectAlias, TokenAlias, measure_propagation
from .narrative import CoinIdentity
from .x_adapter import OfficialXResponseAdapter


def timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def registry_from_fixture(dataset: dict) -> CTRegistry:
    r = dataset["registry"]
    return CTRegistry(timestamp(r["known_at"]), r["version"],
        tuple(SubjectAlias(s["subject"], s["kind"], tuple(s["aliases"])) for s in r["subjects"]),
        tuple(TokenAlias(CoinIdentity(**t["coin"]), tuple(t.get("subjects", [])),
                         tuple(t.get("tickers", [])), tuple(t.get("names", []))) for t in r["tokens"]))


def run_case(dataset: dict, case: dict):
    parser = CTParser(registry_from_fixture(dataset))
    target = CoinIdentity(**dataset["target"])
    cutoff = timestamp(case["observed_at"])
    posts = tuple(raw for envelope in case["observations"]
        for raw in OfficialXResponseAdapter().normalize(envelope["response"],
            detected_at=timestamp(envelope["detected_at"]), parsed_at=timestamp(envelope["parsed_at"]),
            source_id="fixture:"+case["id"], data_mode="synthetic"))
    parsed = tuple(parser.parse(p, target=target, observed_at=cutoff) for p in posts)
    snapshot = measure_propagation(parsed, target=target, subject=dataset["subject"],
                                   window_start=timestamp(case["window_start"]), observed_at=cutoff)
    return parsed, snapshot


def evaluate(dataset: dict) -> dict:
    ids = [c["id"] for c in dataset["cases"]]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("Replay requires nonempty unique labeled cases")
    outcomes = []
    confusion = {r.value: {"tp": 0, "fp": 0, "fn": 0} for r in Relationship}
    tp = fp = fn = tn = unknown = ambiguous = errors = unsupported = 0
    matched = 0
    for case in dataset["cases"]:
        expected = case["expected"]
        try:
            parsed, snapshot = run_case(dataset, case)
        except (ValueError, TypeError, KeyError) as exc:
            accepted_rejection = expected.get("error_contains") is not None and expected["error_contains"] in str(exc)
            matched += accepted_rejection
            errors += not accepted_rejection
            outcomes.append({"id": case["id"], "matched": bool(accepted_rejection),
                             "expected_rejection": bool(accepted_rejection), "error_type": type(exc).__name__})
            continue
        actual = [dict(relationship=p.relationship.label, classification=p.classification.label,
                       subjects=list(p.subjects), possible_external_catalyst=p.possible_external_catalyst,
                       direct_coin_ids=list(p.direct_coin_ids)) for p in parsed]
        ok = "error_contains" not in expected and actual == expected["posts"]
        ok = ok and all(snapshot.facts.get(k) == v for k, v in expected.get("facts", {}).items())
        matched += ok
        gold = expected.get("posts", [])
        for i in range(max(len(parsed), len(gold))):
            p = parsed[i] if i < len(parsed) else None
            unknown += p is not None and p.classification.label == PostClass.UNKNOWN.value
            ambiguous += p is not None and p.relationship.label == Relationship.AMBIGUOUS_RELATION.value
            # Precision/recall refer only to exact-contract identity extraction.
            true = i < len(gold) and gold[i]["relationship"] == Relationship.DIRECT_CONTRACT_REFERENCE.value
            pred = p is not None and p.relationship.label == Relationship.DIRECT_CONTRACT_REFERENCE.value
            tp += pred and true
            fp += pred and not true
            fn += true and not pred
            tn += not true and not pred
            for label, counts in confusion.items():
                truth = i < len(gold) and gold[i]["relationship"] == label
                prediction = p is not None and p.relationship.label == label
                counts["tp"] += truth and prediction
                counts["fp"] += prediction and not truth
                counts["fn"] += truth and not prediction
            if p is not None:
                unsupported += not p.relationship.evidence_ids or not p.classification.rule_version
                unsupported += pred and p.target.coin_id not in p.direct_coin_ids
        outcomes.append({"id": case["id"], "matched": bool(ok), "actual_posts": actual,
                         "checked_facts": {k: snapshot.facts.get(k) for k in expected.get("facts", {})}})
    denom = tp+fp+fn+tn
    def ratio(n, d):
        return n/d if d else None
    per_label = {label: dict(**counts, precision=ratio(counts["tp"], counts["tp"]+counts["fp"]),
                            recall=ratio(counts["tp"], counts["tp"]+counts["fn"])) for label, counts in confusion.items()}
    return dict(dataset_version=dataset["version"], data_mode="synthetic", total_cases=len(ids),
        exact_match_cases=matched, exact_match_accuracy=matched/len(ids), fixture_coverage=1.0,
        identity_precision=ratio(tp, tp+fp), identity_recall=ratio(tp, tp+fn),
        identity_accuracy=ratio(tp+tn, denom), true_positive_count=tp, true_negative_count=tn,
        false_positive_count=fp, false_negative_count=fn, ambiguous_count=ambiguous, unknown_count=unknown,
        unsupported_inference_count=unsupported, unexpected_parsing_errors=errors,
        relationship_metrics=per_label, cases=outcomes,
        limitation="Small synthetic rule-conformance dataset, not real-X performance or trading evidence")


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("dataset", type=Path)
    cli.add_argument("--output", type=Path)
    args = cli.parse_args()
    report = evaluate(json.loads(args.dataset.read_text(encoding="utf-8")))
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered+"\n", encoding="utf-8")
    else:
        print(rendered)
    return 0 if report["exact_match_cases"] == report["total_cases"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
