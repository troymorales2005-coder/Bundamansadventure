"""Immutable CT evidence snapshots. Facts and rule outputs remain separate."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from enum import Enum

from .narrative import CoinIdentity, NarrativeProvenance, _optional_text, _text, _time, _tuple


def canonical(value) -> str:
    def encode(v):
        if is_dataclass(v):
            return {f.name: encode(getattr(v, f.name)) for f in fields(v)}
        if isinstance(v, datetime):
            return v.isoformat()
        if isinstance(v, Enum):
            return v.value
        if isinstance(v, tuple):
            return [encode(i) for i in v]
        if isinstance(v, list):
            return [encode(i) for i in v]
        if isinstance(v, dict):
            return {key: encode(value) for key, value in v.items()}
        return v
    return json.dumps(encode(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


@dataclass(frozen=True)
class PublicMetric:
    name: str
    value: int

    def __post_init__(self):
        _text(self.name)
        if type(self.value) is not int or self.value < 0:
            raise ValueError("Public metric must be a nonnegative integer")


@dataclass(frozen=True)
class PostReference:
    kind: str
    post_id: str

    def __post_init__(self):
        _text(self.kind)  # preserve new/unknown reference types too
        _text(self.post_id)


@dataclass(frozen=True)
class RawXPost:
    post_id: str
    detected_at: datetime
    parsed_at: datetime
    provenance: NarrativeProvenance
    raw_payload_json: str
    text: str | None = None
    author_id: str | None = None
    author_username: str | None = None
    posted_at: datetime | None = None
    urls: tuple[str, ...] = ()
    mentions: tuple[str, ...] = ()
    hashtags: tuple[str, ...] = ()
    cashtags: tuple[str, ...] = ()
    references: tuple[PostReference, ...] = ()
    public_metrics: tuple[PublicMetric, ...] = ()
    account_payload_json: str | None = None
    data_mode: str = "synthetic"

    def __post_init__(self):
        _text(self.post_id)
        if self.text is not None and not isinstance(self.text, str):
            raise TypeError("Post text must be a string or unavailable")
        _optional_text(self.author_id)
        _optional_text(self.author_username)
        if not isinstance(self.provenance, NarrativeProvenance):
            raise TypeError("Provenance required")
        for name in ("detected_at", "parsed_at"):
            object.__setattr__(self, name, _time(getattr(self, name)))
        if self.posted_at is not None:
            object.__setattr__(self, "posted_at", _time(self.posted_at))
            if self.posted_at > self.provenance.retrieved_at:
                raise ValueError("Post occurred after retrieval")
        if not self.provenance.retrieved_at <= self.detected_at <= self.parsed_at:
            raise ValueError("Expected retrieval <= detection <= parsing")
        for name, typ in (("urls", str), ("mentions", str), ("hashtags", str),
                          ("cashtags", str), ("references", PostReference), ("public_metrics", PublicMetric)):
            _tuple(getattr(self, name), typ)
        if len({m.name for m in self.public_metrics}) != len(self.public_metrics):
            raise ValueError("Duplicate public metric names")
        for payload in (self.raw_payload_json, self.account_payload_json):
            if payload is not None:
                if not isinstance(payload, str) or not isinstance(json.loads(payload), dict):
                    raise ValueError("Raw payload must be an immutable JSON object string")
        if self.data_mode not in {"synthetic", "retrospective", "prospective"}:
            raise ValueError("Explicit supported data mode required")

    @property
    def record_id(self) -> str:
        return "xraw-" + digest(self)

    @property
    def detection_latency_seconds(self) -> float | None:
        return None if self.posted_at is None else (self.detected_at-self.posted_at).total_seconds()

    @property
    def parsing_latency_seconds(self) -> float:
        return (self.parsed_at-self.detected_at).total_seconds()

    def referenced_post(self, kind: str) -> tuple[str, ...]:
        return tuple(r.post_id for r in self.references if r.kind == kind)


class Relationship(str, Enum):
    DIRECT_CONTRACT_REFERENCE = "DIRECT_CONTRACT_REFERENCE"
    DIRECT_TICKER_OR_NAME_REFERENCE = "DIRECT_TICKER_OR_NAME_REFERENCE"
    INDIRECT_NARRATIVE_RELATION = "INDIRECT_NARRATIVE_RELATION"
    AMBIGUOUS_RELATION = "AMBIGUOUS_RELATION"
    UNRELATED = "UNRELATED"


class PostClass(str, Enum):
    ORIGINAL_CATALYST = "ORIGINAL_CATALYST"
    REACTION = "REACTION"
    NARRATIVE_PROPAGATION = "NARRATIVE_PROPAGATION"
    TRADER_OR_CALLER_MENTION = "TRADER_OR_CALLER_MENTION"
    NEWS_OR_INFORMATION = "NEWS_OR_INFORMATION"
    MEME_OR_COMMUNITY = "MEME_OR_COMMUNITY"
    PROMOTION_OR_SHILL = "PROMOTION_OR_SHILL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class EntityMatch:
    kind: str
    value: str
    matched_text: str

    def __post_init__(self):
        for value in (self.kind, self.value, self.matched_text):
            _text(value)


@dataclass(frozen=True)
class RuleInterpretation:
    label: str
    reason: str
    evidence_ids: tuple[str, ...]
    rule_version: str
    as_of: datetime

    def __post_init__(self):
        for value in (self.label, self.reason, self.rule_version):
            _text(value)
        _tuple(self.evidence_ids, str)
        if not self.evidence_ids:
            raise ValueError("Rule interpretation requires evidence")
        object.__setattr__(self, "as_of", _time(self.as_of))


@dataclass(frozen=True)
class ParsedCTPost:
    raw: RawXPost
    target: CoinIdentity
    observed_at: datetime
    entities: tuple[EntityMatch, ...]
    subjects: tuple[str, ...]
    candidate_coin_ids: tuple[str, ...]
    direct_coin_ids: tuple[str, ...]
    relationship: RuleInterpretation
    classification: RuleInterpretation
    possible_external_catalyst: bool
    unknowns: tuple[str, ...]
    registry_id: str
    parser_version: str

    def __post_init__(self):
        if not isinstance(self.raw, RawXPost) or not isinstance(self.target, CoinIdentity):
            raise TypeError("Typed immutable raw post/target required")
        object.__setattr__(self, "observed_at", _time(self.observed_at))
        if self.raw.parsed_at > self.observed_at:
            raise ValueError("Future post/detection/parsing unavailable at CT cutoff")
        _tuple(self.entities, EntityMatch)
        for name in ("subjects", "candidate_coin_ids", "direct_coin_ids", "unknowns"):
            _tuple(getattr(self, name), str)
        for name in ("registry_id", "parser_version"):
            _text(getattr(self, name))
        if type(self.possible_external_catalyst) is not bool:
            raise TypeError("Boolean possible catalyst marker required")
        Relationship(self.relationship.label)
        PostClass(self.classification.label)
        for output in (self.relationship, self.classification):
            if not isinstance(output, RuleInterpretation) or output.as_of != self.observed_at:
                raise ValueError("Interpretation must share cutoff")
            if not {self.raw.record_id, self.registry_id} <= set(output.evidence_ids):
                raise ValueError("Interpretation must cite raw and registry evidence")


class RawXStore:
    """Temporary append-only raw snapshots; updates do not replace earlier metrics."""
    def __init__(self):
        self.__records: tuple[RawXPost, ...] = ()

    @property
    def records(self) -> tuple[RawXPost, ...]:
        return self.__records

    def append(self, post: RawXPost):
        if not isinstance(post, RawXPost):
            raise TypeError("RawXPost required")
        if any(r.record_id == post.record_id for r in self.__records):
            raise ValueError("Duplicate raw observation")
        self.__records += (post,)

    def as_of(self, cutoff: datetime) -> tuple[RawXPost, ...]:
        cutoff = _time(cutoff)
        return tuple(p for p in self.__records if p.detected_at <= cutoff)
