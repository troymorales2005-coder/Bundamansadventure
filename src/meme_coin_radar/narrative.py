"""BUNDAR's offline, cutoff-safe narrative research foundation (no scoring).

Annotations are human/fixture supplied. The engine validates their lineage;
it does not verify source truth or perform semantic inference.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum


def _text(value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Nonempty text required")


def _optional_text(value: str | None) -> None:
    if value is not None:
        _text(value)


def _time(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timezone-aware timestamp required; do not guess receipt time")
    return value.astimezone(timezone.utc)


def _tuple(value: tuple, item_type: type) -> None:
    if not isinstance(value, tuple) or any(not isinstance(v, item_type) for v in value):
        raise TypeError("Immutable tuple with correctly typed members required")


class NarrativeCategory(str, Enum):
    MEME_COMMUNITY = "meme/community"
    PERSON_CELEBRITY = "person/celebrity"
    EXTERNAL_CATALYST = "event/tweet/external_catalyst"
    PRODUCT_TECH = "product/tech"
    UNKNOWN = "unknown"


class EvidenceKind(str, Enum):
    IDENTITY_MATCH = "identity_match"
    CATALYST = "catalyst"
    CT_X = "ct_x"
    SUBJECT_ATTENTION = "subject_attention"
    TICKER_MENTION = "ticker_mention"
    TOKEN_CAPTURE = "token_capture"
    COMPETING_TOKEN = "competing_token"
    NOVELTY_SATURATION = "novelty_saturation"
    PRODUCT = "product"
    CONTRADICTION_RISK = "contradiction_risk"
    MARKET_CONTEXT = "market_context"


class NarrativeState(str, Enum):
    NARRATIVE_FOUND = "NARRATIVE_FOUND"
    NO_NARRATIVE_FOUND = "NO_NARRATIVE_FOUND"


@dataclass(frozen=True)
class CoinIdentity:
    chain: str
    contract_address: str
    symbol: str | None = None
    name: str | None = None

    def __post_init__(self):
        _text(self.chain)
        _text(self.contract_address)
        _optional_text(self.symbol)
        _optional_text(self.name)

    @property
    def coin_id(self) -> str:
        return f"{self.chain}:{self.contract_address}"


@dataclass(frozen=True)
class NarrativeProvenance:
    source_id: str
    source_type: str
    retrieved_at: datetime
    source_url: str | None = None
    content_hash: str | None = None
    retention_notes: str | None = None

    def __post_init__(self):
        _text(self.source_id)
        _text(self.source_type)
        for value in (self.source_url, self.content_hash, self.retention_notes):
            _optional_text(value)
        object.__setattr__(self, "retrieved_at", _time(self.retrieved_at))


@dataclass(frozen=True)
class Measurement:
    """Raw value with explicit scope/window; classifications use ResearchClaim."""
    name: str
    value: Decimal
    unit: str
    as_of: datetime
    scope: str
    window_start: datetime | None = None

    def __post_init__(self):
        for text in (self.name, self.unit, self.scope):
            _text(text)
        if not isinstance(self.value, Decimal) or not self.value.is_finite() or self.value < 0:
            raise ValueError("Measurements require finite nonnegative Decimal values")
        object.__setattr__(self, "as_of", _time(self.as_of))
        if self.window_start is not None:
            object.__setattr__(self, "window_start", _time(self.window_start))
            if self.window_start > self.as_of:
                raise ValueError("Measurement window is reversed")


@dataclass(frozen=True)
class NarrativeEvidence:
    evidence_id: str
    kind: EvidenceKind
    occurred_at: datetime
    detected_at: datetime
    provenance: NarrativeProvenance
    observation: str
    subject: str
    token: CoinIdentity | None = None
    account: str | None = None
    post_id: str | None = None
    relevance: str | None = None
    measurements: tuple[Measurement, ...] = ()

    def __post_init__(self):
        for text in (self.evidence_id, self.observation, self.subject):
            _text(text)
        if not isinstance(self.kind, EvidenceKind) or not isinstance(self.provenance, NarrativeProvenance):
            raise TypeError("Typed evidence kind and provenance required")
        if self.token is not None and not isinstance(self.token, CoinIdentity):
            raise TypeError("Immutable CoinIdentity required")
        _tuple(self.measurements, Measurement)
        for value in (self.account, self.post_id, self.relevance):
            _optional_text(value)
        for name in ("occurred_at", "detected_at"):
            object.__setattr__(self, name, _time(getattr(self, name)))
        if not self.occurred_at <= self.provenance.retrieved_at <= self.detected_at:
            raise ValueError("Expected occurrence <= retrieval <= Radar detection")
        if any(m.as_of > self.detected_at for m in self.measurements):
            raise ValueError("Measurement unavailable at detection")
        if self.kind == EvidenceKind.CT_X:
            for text in (self.account, self.post_id, self.relevance):
                _text(text)
        if self.kind in (EvidenceKind.IDENTITY_MATCH, EvidenceKind.TOKEN_CAPTURE, EvidenceKind.COMPETING_TOKEN):
            if self.token is None:
                raise ValueError("Contract-specific evidence requires chain + contract")

    @property
    def detection_latency_seconds(self) -> float:
        return (self.detected_at - self.occurred_at).total_seconds()


@dataclass(frozen=True)
class ResearchClaim:
    """Cited annotation, never an engine prediction.

    role: hypothesis, continuation, contradiction_risk, identity_confidence,
    novelty_saturation, or classification. Derived labels require rule_version.
    """
    role: str
    text: str
    evidence_ids: tuple[str, ...]
    rule_version: str | None = None

    def __post_init__(self):
        if self.role not in {"hypothesis", "continuation", "contradiction_risk", "identity_confidence", "novelty_saturation", "classification"}:
            raise ValueError("Unsupported claim role")
        _text(self.text)
        _optional_text(self.rule_version)
        _tuple(self.evidence_ids, str)
        if not self.evidence_ids or len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Claims require unique evidence references")
        for ref in self.evidence_ids:
            _text(ref)
        if self.role in {"identity_confidence", "novelty_saturation", "classification"}:
            _text(self.rule_version)


SUPPORT_RULE_VERSION = "contract-linked-narrative/v1"
NARRATIVE_KINDS = frozenset({EvidenceKind.CATALYST, EvidenceKind.CT_X,
                           EvidenceKind.SUBJECT_ATTENTION, EvidenceKind.PRODUCT})


@dataclass(frozen=True)
class NarrativeResearchPacket:
    coin: CoinIdentity
    observed_at: datetime
    completed_at: datetime
    category: NarrativeCategory
    evidence: tuple[NarrativeEvidence, ...] = ()
    claims: tuple[ResearchClaim, ...] = ()
    unknowns: tuple[str, ...] = ()
    category_evidence_ids: tuple[str, ...] = ()
    data_mode: str = "synthetic"
    schema_version: str = "bundar-narrative/0.1"
    rule_version: str = SUPPORT_RULE_VERSION

    def __post_init__(self):
        if not isinstance(self.coin, CoinIdentity) or not isinstance(self.category, NarrativeCategory):
            raise TypeError("Typed identity and category required")
        for name, typ in (("evidence", NarrativeEvidence), ("claims", ResearchClaim),
                          ("unknowns", str), ("category_evidence_ids", str)):
            _tuple(getattr(self, name), typ)
        for unknown in self.unknowns:
            _text(unknown)
        if self.schema_version != "bundar-narrative/0.1" or self.rule_version != SUPPORT_RULE_VERSION:
            raise ValueError("Unsupported schema/support rule version")
        if self.data_mode not in {"synthetic", "retrospective", "prospective"}:
            raise ValueError("Explicit data mode required")
        for name in ("observed_at", "completed_at"):
            object.__setattr__(self, name, _time(getattr(self, name)))
        if self.completed_at < self.observed_at:
            raise ValueError("Packet completion precedes observation")
        ids = {e.evidence_id for e in self.evidence}
        if len(ids) != len(self.evidence):
            raise ValueError("Duplicate evidence IDs")
        for evidence in self.evidence:
            if evidence.detected_at > self.observed_at:
                raise ValueError("Future evidence: not available at observation cutoff")
            if evidence.kind in {EvidenceKind.IDENTITY_MATCH, EvidenceKind.TOKEN_CAPTURE, EvidenceKind.MARKET_CONTEXT}:
                if evidence.token is None or evidence.token.coin_id != self.coin.coin_id:
                    raise ValueError("Evidence must match packet chain + contract")
            if evidence.kind == EvidenceKind.COMPETING_TOKEN and evidence.token.coin_id == self.coin.coin_id:
                raise ValueError("Competing token cannot be the packet token")
        refs = self.category_evidence_ids + tuple(r for c in self.claims for r in c.evidence_ids)
        if any(ref not in ids for ref in refs):
            raise ValueError("Dangling evidence reference")
        if self.category != NarrativeCategory.UNKNOWN and not self.category_evidence_ids:
            raise ValueError("Category requires evidence lineage")

    @property
    def supporting_evidence_ids(self) -> tuple[str, ...]:
        """v1: one hypothesis must cite same-subject identity, capture, narrative.

        Presence/lineage only, not independent confirmation or verified truth.
        """
        by_id = {e.evidence_id: e for e in self.evidence}
        supporting = set()
        for claim in self.claims:
            if claim.role != "hypothesis":
                continue
            cited = [by_id[ref] for ref in claim.evidence_ids]
            for subject in {e.subject for e in cited}:
                group = [e for e in cited if e.subject == subject and
                         (e.token is None or e.token.coin_id == self.coin.coin_id)]
                kinds = {e.kind for e in group}
                if {EvidenceKind.IDENTITY_MATCH, EvidenceKind.TOKEN_CAPTURE} <= kinds and kinds & NARRATIVE_KINDS:
                    supporting.update(e.evidence_id for e in group)
        return tuple(sorted(supporting))

    @property
    def state(self) -> NarrativeState:
        return NarrativeState.NARRATIVE_FOUND if self.supporting_evidence_ids else NarrativeState.NO_NARRATIVE_FOUND

    @property
    def result_reason(self) -> str:
        return ("Cited same-subject identity, contract capture and narrative evidence present"
                if self.supporting_evidence_ids else
                "No hypothesis cites same-subject identity, contract capture and narrative evidence")

    @property
    def completion_latency_seconds(self) -> float:
        return (self.completed_at - self.observed_at).total_seconds()

    @property
    def catalyst_freshness_seconds(self) -> tuple[tuple[str, float], ...]:
        return tuple((e.evidence_id, (self.observed_at - e.occurred_at).total_seconds())
                     for e in self.evidence if e.kind == EvidenceKind.CATALYST)

    @property
    def record_id(self) -> str:
        return "narrative-" + hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()

    def to_json(self) -> str:
        def encode(value):
            if is_dataclass(value):
                return {f.name: encode(getattr(value, f.name)) for f in fields(value)}
            if isinstance(value, datetime):
                return value.isoformat()
            if isinstance(value, Enum):
                return value.value
            if isinstance(value, Decimal):
                return str(value)
            if isinstance(value, tuple):
                return [encode(v) for v in value]
            return value
        payload = encode(self)
        payload.update(state=self.state.value, result_reason=self.result_reason,
                       supporting_evidence_ids=self.supporting_evidence_ids)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


class NarrativeResearchEngine:
    """Explicit timestamps, no clock, network, random IDs or hidden classifications."""

    def build(self, *, coin: CoinIdentity, observed_at: datetime, completed_at: datetime,
              evidence: tuple[NarrativeEvidence, ...] = (), claims: tuple[ResearchClaim, ...] = (),
              category: NarrativeCategory = NarrativeCategory.UNKNOWN,
              category_evidence_ids: tuple[str, ...] = (), unknowns: tuple[str, ...] = (),
              data_mode: str = "synthetic") -> NarrativeResearchPacket:
        _tuple(evidence, NarrativeEvidence)
        _tuple(claims, ResearchClaim)
        return NarrativeResearchPacket(coin=coin, observed_at=observed_at, completed_at=completed_at,
            evidence=tuple(sorted(evidence, key=lambda e: e.evidence_id)), claims=claims,
            category=category, category_evidence_ids=category_evidence_ids,
            unknowns=unknowns, data_mode=data_mode)


class NarrativePacketStore:
    """In-memory append-only API; no persistence or tamper-proof security claim."""
    def __init__(self):
        self.__records: tuple[NarrativeResearchPacket, ...] = ()

    @property
    def records(self) -> tuple[NarrativeResearchPacket, ...]:
        return self.__records

    def append(self, packet: NarrativeResearchPacket) -> None:
        if not isinstance(packet, NarrativeResearchPacket):
            raise TypeError("NarrativeResearchPacket required")
        if any(p.record_id == packet.record_id for p in self.__records):
            raise ValueError("Duplicate packet")
        self.__records += (packet,)

    def as_of(self, cutoff: datetime) -> tuple[NarrativeResearchPacket, ...]:
        cutoff = _time(cutoff)
        return tuple(p for p in self.__records if p.completed_at <= cutoff)
