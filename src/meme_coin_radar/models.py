from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class FomoExecutability(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNVERIFIED = "UNVERIFIED"

    @classmethod
    def validate(cls, value: Any) -> "FomoExecutability":
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            normalized = value.strip().upper()
            for member in cls:
                if member.value == normalized:
                    return member
        raise ValueError(f"Unsupported FOMO executability state: {value!r}")


@dataclass
class Provenance:
    source_id: str
    source_type: str
    observed_at: datetime
    source_url: Optional[str] = None
    retrieved_at: Optional[datetime] = None
    content_hash: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.source_id or not self.source_type:
            raise ValueError("Provenance requires source_id and source_type.")
        if self.observed_at is None:
            raise ValueError("Provenance requires observed_at.")
        self.observed_at = _ensure_utc(self.observed_at)
        if self.retrieved_at is not None:
            self.retrieved_at = _ensure_utc(self.retrieved_at)


@dataclass
class TokenIdentity:
    chain: str
    contract_address: str
    symbol: Optional[str] = None
    name: Optional[str] = None
    observed_at: Optional[datetime] = None
    provenance: Optional[Provenance] = None
    launchpad: Optional[str] = None
    deployer: Optional[str] = None
    chain_namespace: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.chain or not self.contract_address:
            raise ValueError("Token identity requires both chain and contract address.")
        if self.observed_at is not None:
            self.observed_at = _ensure_utc(self.observed_at)
        if self.provenance is not None and self.observed_at is None:
            self.observed_at = self.provenance.observed_at

    @property
    def coin_id(self) -> str:
        namespace = self.chain_namespace or self.chain
        return f"{namespace}:{self.contract_address}"


@dataclass
class NarrativeAnalysis:
    category: str = "unknown"
    summary: Optional[str] = None
    result: str = "NO_NARRATIVE_FOUND"
    strength: Optional[float] = None
    freshness_hours: Optional[float] = None
    source_count: Optional[int] = None
    evidence_ids: Optional[List[str]] = None


@dataclass
class MarketData:
    price_usd: Optional[float] = None
    market_cap_usd: Optional[float] = None
    liquidity_usd: Optional[float] = None
    volume_usd: Optional[float] = None
    price_change_24h: Optional[float] = None
    circulatingsupply: Optional[float] = None
    fdv_usd: Optional[float] = None
    earliness_score: Optional[float] = None
    remaining_potential: Optional[float] = None
    market_behavior: Optional[str] = None
    as_of: Optional[datetime] = None


@dataclass
class StructureSafety:
    holder_count: Optional[int] = None
    top_10_holder_share: Optional[float] = None
    top_1_holder_share: Optional[float] = None
    dev_or_insider_share: Optional[float] = None
    liquidity_locked: Optional[bool] = None
    transfer_tax: Optional[float] = None
    mintable: Optional[bool] = None
    freeze_authority_present: Optional[bool] = None
    as_of: Optional[datetime] = None


@dataclass
class SmartWalletEvidence:
    unique_wallets: Optional[int] = None
    sample_size: Optional[int] = None
    qualified_clusters: Optional[int] = None
    early_entry_behavior: Optional[str] = None
    net_accumulation: Optional[float] = None
    as_of: Optional[datetime] = None


@dataclass
class AttentionEvidence:
    attention_score: Optional[float] = None
    unique_authors: Optional[int] = None
    mentions_24h: Optional[int] = None
    as_of: Optional[datetime] = None


@dataclass
class SocialEvidence:
    platform: str = "x"
    post_id: Optional[str] = None
    author_handle: Optional[str] = None
    engagement_score: Optional[float] = None
    message_summary: Optional[str] = None
    timestamp: Optional[datetime] = None
    evidence_ids: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if self.timestamp is not None:
            self.timestamp = _ensure_utc(self.timestamp)


@dataclass
class ProjectCredibility:
    product_observed: Optional[bool] = None
    developer_identity_known: Optional[bool] = None
    reputation_notes: Optional[str] = None
    as_of: Optional[datetime] = None


@dataclass
class ExternalCatalyst:
    catalyst_id: str
    timestamp: datetime
    summary: Optional[str] = None
    classification: Optional[str] = None
    evidence_ids: Optional[List[str]] = None

    def __post_init__(self) -> None:
        self.timestamp = _ensure_utc(self.timestamp)


@dataclass
class FomoVerification:
    status: str = "unknown"
    checked_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    source_url: Optional[str] = None
    quote_currency: Optional[str] = None
    test_notional: Optional[float] = None
    route_status: str = "unknown"
    failure_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if self.checked_at is not None:
            self.checked_at = _ensure_utc(self.checked_at)
        if self.expires_at is not None:
            self.expires_at = _ensure_utc(self.expires_at)


@dataclass
class OutcomeObservation:
    horizon_seconds: int
    observed_at: datetime
    status: str = "unobservable"
    mfe: Optional[float] = None
    mae: Optional[float] = None
    market_cap_usd: Optional[float] = None
    liquidity_usd: Optional[float] = None
    estimated_slippage: Optional[float] = None
    executable_return: Optional[float] = None
    evidence_ids: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if self.horizon_seconds <= 0:
            raise ValueError("Outcome horizon must be positive.")
        self.observed_at = _ensure_utc(self.observed_at)


@dataclass
class CandidateObservation:
    coin_id: str
    observed_at: datetime
    narrative: Optional[str] = None
    provenance: Optional[Provenance] = None
    record_id: str = field(default_factory=lambda: _new_record_id("cand"))
    schema_version: str = "0.1"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    record_type: str = "candidate_observation"
    _locked: bool = field(default=False, init=False, repr=False, compare=False)
    token_identity: Optional[TokenIdentity] = None
    market_data: Optional[MarketData] = None
    structure_safety: Optional[StructureSafety] = None
    narrative_analysis: Optional[NarrativeAnalysis] = None
    social_evidence: Optional[Dict[str, Any] | List[SocialEvidence]] = None
    smart_wallet_evidence: Optional[SmartWalletEvidence] = None
    attention: Optional[AttentionEvidence] = None
    project_credibility: Optional[ProjectCredibility] = None
    external_catalysts: Optional[List[ExternalCatalyst]] = None
    fomo_verification: Optional[FomoVerification] = None
    fomo_executability: Optional[FomoExecutability | str] = None
    outcomes: Optional[Dict[str, OutcomeObservation]] = None
    evidence_ids: Optional[List[str]] = None
    as_of: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.coin_id or ":" not in self.coin_id:
            raise ValueError("Candidate observations require a chain:contract coin_id, not ticker-only identity.")
        if self.observed_at is None:
            raise ValueError("CandidateObservation requires observed_at.")
        self.observed_at = _ensure_utc(self.observed_at)
        self.created_at = _ensure_utc(self.created_at)
        if self.as_of is not None:
            self.as_of = _ensure_utc(self.as_of)
        if self.provenance is None:
            raise ValueError("CandidateObservation requires provenance metadata.")
        if self.provenance.observed_at is None:
            raise ValueError("CandidateObservation provenance requires observed_at.")
        if self.fomo_executability is not None:
            self.fomo_executability = FomoExecutability.validate(self.fomo_executability)
        if self.token_identity is not None and self.token_identity.coin_id != self.coin_id:
            raise ValueError("coin_id and token_identity.coin_id must match.")
        self.evidence_ids = self.evidence_ids or []
        self.outcomes = self.outcomes or {}
        self.external_catalysts = self.external_catalysts or []
        self.freeze()

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, '_locked', False) and name != '_locked':
            raise AttributeError(f"{self.__class__.__name__} is immutable after creation.")
        super().__setattr__(name, value)

    def freeze(self) -> None:
        object.__setattr__(self, '_locked', True)


class ObservationStore:
    def __init__(self) -> None:
        self.records: List[CandidateObservation] = []
        self._snapshots: List[tuple[datetime, List[CandidateObservation]]] = []

    def append(self, record: CandidateObservation) -> CandidateObservation:
        if not isinstance(record, CandidateObservation):
            raise TypeError("ObservationStore append requires a CandidateObservation instance.")
        frozen_record = copy.deepcopy(record)
        frozen_record.freeze()
        self.records.append(frozen_record)
        self._snapshots.append((frozen_record.observed_at, copy.deepcopy(self.records)))
        return copy.deepcopy(frozen_record)

    def as_of(self, cutoff: datetime) -> List[CandidateObservation]:
        cutoff = _ensure_utc(cutoff)
        latest_snapshot: List[CandidateObservation] = []
        for snapshot_time, snapshot in self._snapshots:
            if snapshot_time <= cutoff:
                latest_snapshot = snapshot
        return copy.deepcopy(latest_snapshot)


def _ensure_utc(value: datetime) -> datetime:
    if value is None:
        raise ValueError("Timestamp cannot be null.")
    if value.tzinfo is None:
        value = value.replace(tzinfo=__import__("datetime").timezone.utc)
    return value.astimezone(__import__("datetime").timezone.utc)


STANDARD_OUTCOME_HORIZONS = {
    "5m": 300,
    "30m": 1800,
    "2h": 7200,
    "6h": 21600,
    "24h": 86400,
}


def _new_record_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"
