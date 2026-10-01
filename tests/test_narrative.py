"""Synthetic fixtures prove contract mechanics, not narrative truth or edge."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json

import pytest

from meme_coin_radar.narrative import (
    CoinIdentity, EvidenceKind as K, Measurement, NarrativeCategory as C,
    NarrativeEvidence, NarrativePacketStore, NarrativeProvenance,
    NarrativeResearchEngine, NarrativeState as S, ResearchClaim,
)

T = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
COIN = CoinIdentity("base", "0x123", "BUN", "Fixture token")
OTHER = CoinIdentity("base", "0x456")


def evidence(id, kind, **kwargs):
    defaults = dict(evidence_id=id, kind=kind, occurred_at=T-timedelta(minutes=10),
        detected_at=T-timedelta(minutes=1), provenance=NarrativeProvenance(
            "fixture:"+id, "synthetic", T-timedelta(minutes=2), "https://example.com/"+id),
        observation="Synthetic retained observation", subject="dance meme")
    if kind in {K.IDENTITY_MATCH, K.TOKEN_CAPTURE, K.MARKET_CONTEXT}:
        defaults["token"] = COIN
    if kind == K.CT_X:
        defaults.update(account="fixture-account", post_id=id, relevance="Post discusses dance meme")
    defaults.update(kwargs)
    return NarrativeEvidence(**defaults)


def inputs():
    return dict(coin=COIN, observed_at=T, completed_at=T+timedelta(seconds=30),
        evidence=(evidence("identity", K.IDENTITY_MATCH), evidence("capture", K.TOKEN_CAPTURE),
                  evidence("post", K.CT_X)),
        claims=(ResearchClaim("hypothesis", "Token is associated with the dance meme",
                              ("identity", "capture", "post")),),
        category=C.MEME_COMMUNITY, category_evidence_ids=("post",),
        unknowns=("Market cap unavailable", "Account independence unverified"))


def build(**overrides):
    args = inputs()
    args.update(overrides)
    return NarrativeResearchEngine().build(**args)


def test_valid_packet_is_deterministic_and_auditable():
    p = build()
    assert p.state == S.NARRATIVE_FOUND
    assert p.supporting_evidence_ids == ("capture", "identity", "post")
    assert p.record_id == build(evidence=tuple(reversed(inputs()["evidence"]))).record_id
    payload = json.loads(p.to_json())
    assert payload["rule_version"] == "contract-linked-narrative/v1"
    assert payload["state"] == "NARRATIVE_FOUND"
    assert payload["evidence"][0]["provenance"]["source_id"] == "fixture:capture"
    assert payload["claims"][0]["evidence_ids"] == ["identity", "capture", "post"]


def test_empty_packet_has_explicit_no_narrative():
    p = NarrativeResearchEngine().build(coin=COIN, observed_at=T, completed_at=T)
    assert p.state == S.NO_NARRATIVE_FOUND
    assert not p.supporting_evidence_ids
    assert p.category == C.UNKNOWN


@pytest.mark.parametrize("missing", ["identity", "capture", "post"])
def test_insufficient_support(missing):
    remaining = tuple(e for e in inputs()["evidence"] if e.evidence_id != missing)
    refs = tuple(e.evidence_id for e in remaining)
    p = build(evidence=remaining, claims=(ResearchClaim("hypothesis", "Unproven association", refs),),
              category=C.UNKNOWN, category_evidence_ids=())
    assert p.state == S.NO_NARRATIVE_FOUND


def test_unrelated_subject_or_ticker_mentions_do_not_supply_support():
    original = inputs()["evidence"]
    assert build(evidence=original[:2]+(replace(original[2], subject="unrelated"),)).state == S.NO_NARRATIVE_FOUND
    assert build(evidence=original[:2]+(replace(original[2], kind=K.TICKER_MENTION),)).state == S.NO_NARRATIVE_FOUND
    assert build(evidence=original[:2]+(replace(original[2], token=OTHER),)).state == S.NO_NARRATIVE_FOUND


def test_uncited_evidence_and_nonhypotheses_cannot_supply_support():
    assert build(claims=()).state == S.NO_NARRATIVE_FOUND
    assert build(claims=(ResearchClaim("continuation", "More public events may occur", ("post",)),)).state == S.NO_NARRATIVE_FOUND


@pytest.mark.parametrize("kind", [K.CATALYST, K.SUBJECT_ATTENTION, K.PRODUCT, K.CT_X])
def test_supported_narrative_evidence_families(kind):
    assert build(evidence=inputs()["evidence"][:2]+(evidence("post", kind),)).state == S.NARRATIVE_FOUND


def test_late_detection_cannot_leak_even_if_completed_later():
    late = replace(inputs()["evidence"][2], detected_at=T+timedelta(seconds=1))
    with pytest.raises(ValueError, match="Future evidence"):
        build(evidence=inputs()["evidence"][:2]+(late,))


def test_future_occurrence_or_retrieval_rejected():
    with pytest.raises(ValueError, match="occurrence"):
        evidence("bad", K.CATALYST, occurred_at=T)
    with pytest.raises(ValueError, match="occurrence"):
        evidence("bad", K.CATALYST, provenance=NarrativeProvenance("id", "fixture", T))


def test_completion_order_freshness_and_latency():
    with pytest.raises(ValueError, match="completion"):
        build(completed_at=T-timedelta(seconds=1))
    p = build(evidence=inputs()["evidence"]+(evidence("event", K.CATALYST),))
    assert p.completion_latency_seconds == 30
    assert p.catalyst_freshness_seconds == (("event", 600),)
    assert p.evidence[0].detection_latency_seconds == 540
    at_cutoff = replace(inputs()["evidence"][2], detected_at=T)
    assert build(evidence=inputs()["evidence"][:2]+(at_cutoff,), completed_at=T).state == S.NARRATIVE_FOUND


def test_timezone_normalization_and_naive_rejection():
    assert build(observed_at=T.astimezone(timezone(timedelta(hours=-4)))).observed_at == T
    with pytest.raises(ValueError, match="Timezone"):
        build(observed_at=T.replace(tzinfo=None))


@pytest.mark.parametrize("field", ["chain", "contract_address"])
def test_identity_cannot_be_ticker_only(field):
    with pytest.raises(ValueError):
        replace(COIN, **{field: " "})


@pytest.mark.parametrize("kind", [K.IDENTITY_MATCH, K.TOKEN_CAPTURE, K.MARKET_CONTEXT])
def test_exact_chain_contract_required(kind):
    wrong = evidence("wrong", kind, token=OTHER)
    with pytest.raises(ValueError, match="chain"):
        build(evidence=inputs()["evidence"]+(wrong,))
    wrong_chain = replace(wrong, token=replace(COIN, chain="solana"))
    with pytest.raises(ValueError):
        build(evidence=inputs()["evidence"]+(wrong_chain,))


def test_competition_saturation_market_and_subject_attention():
    measure = Measurement("competing_contract_count", Decimal(2), "contracts", T-timedelta(minutes=2),
                          "two observed contracts; manual fixture universe", T-timedelta(hours=1))
    extra = (evidence("competitor", K.COMPETING_TOKEN, token=OTHER),
             evidence("saturation", K.NOVELTY_SATURATION, measurements=(measure,)),
             evidence("subject", K.SUBJECT_ATTENTION, measurements=(replace(measure, name="unique_authors", unit="accounts"),)),
             evidence("ticker", K.TICKER_MENTION),
             evidence("market", K.MARKET_CONTEXT, measurements=(replace(measure, name="market_cap_usd", value=Decimal("1234.50"), unit="USD"),)))
    p = build(evidence=inputs()["evidence"]+extra)
    assert next(e for e in p.evidence if e.kind == K.COMPETING_TOKEN).token == OTHER
    assert '"1234.50"' in p.to_json()
    assert {K.SUBJECT_ATTENTION, K.TICKER_MENTION} <= {e.kind for e in p.evidence}
    with pytest.raises(ValueError, match="Competing"):
        build(evidence=inputs()["evidence"]+(replace(extra[0], token=COIN),))


@pytest.mark.parametrize("value", [Decimal("NaN"), Decimal("Infinity"), Decimal(-1), 1.0])
def test_invalid_measurements(value):
    with pytest.raises(ValueError):
        Measurement("likes", value, "count", T, "post")


def test_measurement_temporal_validation():
    with pytest.raises(ValueError, match="window"):
        Measurement("likes", Decimal(1), "count", T, "post", T+timedelta(seconds=1))
    with pytest.raises(ValueError, match="unavailable"):
        evidence("post", K.CT_X, measurements=(Measurement("likes", Decimal(1), "count", T, "post"),))


def test_provenance_and_social_fields_required():
    with pytest.raises(ValueError):
        NarrativeProvenance("", "fixture", T)
    for field in ("account", "post_id", "relevance"):
        with pytest.raises(ValueError):
            evidence("post", K.CT_X, **{field: None})
    assert evidence("event", K.CATALYST, provenance=NarrativeProvenance("native-id", "fixture", T-timedelta(minutes=2))).provenance.source_url is None


def test_references_duplicates_category_and_versions():
    with pytest.raises(ValueError, match="Dangling"):
        build(claims=(ResearchClaim("hypothesis", "Missing reference", ("missing",)),))
    with pytest.raises(ValueError, match="Duplicate"):
        build(evidence=inputs()["evidence"]+(inputs()["evidence"][0],))
    with pytest.raises(ValueError, match="Category"):
        build(category_evidence_ids=())
    with pytest.raises(ValueError, match="Unsupported"):
        replace(build(), rule_version="secret-threshold/v1")
    with pytest.raises(ValueError):
        build(data_mode="unlabeled")


@pytest.mark.parametrize("role", ["identity_confidence", "novelty_saturation", "classification"])
def test_derived_labels_require_rule_version(role):
    with pytest.raises(ValueError):
        ResearchClaim(role, "STRONG", ("identity",))
    p = build(claims=inputs()["claims"]+(ResearchClaim(role, "Rubric result", ("identity",), "fixture-rubric/v1"),))
    assert p.claims[-1].rule_version == "fixture-rubric/v1"


def test_continuation_and_risks_preserve_citations_as_annotations():
    p = build(claims=inputs()["claims"]+(
        ResearchClaim("continuation", "Another public event could renew attention; unverified hypothesis", ("post",)),
        ResearchClaim("contradiction_risk", "Single-account coverage may be coordinated", ("post",))))
    assert p.claims[-1].evidence_ids == ("post",)
    assert p.unknowns


def test_deep_immutability_and_append_only_reconstruction():
    p = build()
    for obj, name, value in ((p, "category", C.UNKNOWN), (p.coin, "chain", "other"),
                             (p.evidence[0], "subject", "other"),
                             (p.evidence[0].provenance, "source_id", "other"),
                             (p.claims[0], "text", "other")):
        with pytest.raises(FrozenInstanceError):
            setattr(obj, name, value)
    with pytest.raises(TypeError):
        build(evidence=list(inputs()["evidence"]))
    with pytest.raises(ValueError):
        replace(COIN, name=[])
    store = NarrativePacketStore()
    store.append(p)
    later = replace(p, completed_at=T+timedelta(minutes=10))
    store.append(later)
    assert store.as_of(T+timedelta(seconds=29)) == ()
    assert store.as_of(T+timedelta(seconds=30)) == (p,)
    assert store.as_of(T+timedelta(hours=1)) == (p, later)
    with pytest.raises(ValueError, match="Duplicate"):
        store.append(p)
    with pytest.raises(AttributeError):
        store.records = ()
    assert not hasattr(store.records, "append")


def test_out_of_order_append_uses_completion_time():
    store = NarrativePacketStore()
    p = build()
    store.append(replace(p, completed_at=T+timedelta(hours=1)))
    store.append(p)
    assert store.as_of(T+timedelta(minutes=1)) == (p,)
