"""Deterministic, conservative CT extraction, measurement and narrative bridge."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from difflib import SequenceMatcher
from urllib.parse import urlsplit

from .ct_models import (EntityMatch, ParsedCTPost, PostClass, RawXPost, Relationship,
                        RuleInterpretation, digest)
from .narrative import (CoinIdentity, EvidenceKind, Measurement, NarrativeEvidence,
                        _text, _time, _tuple)

PARSER_VERSION = "ct-parser/v1"


def _matches(alias: str, text: str) -> tuple[str, ...]:
    return tuple(m.group() for m in re.finditer(r"(?<!\w)"+re.escape(alias)+r"(?!\w)", text, re.IGNORECASE))


@dataclass(frozen=True)
class SubjectAlias:
    subject: str
    kind: str
    aliases: tuple[str, ...]

    def __post_init__(self):
        _text(self.subject)
        if self.kind not in {"person", "company", "product", "meme", "animal_character", "event", "phrase", "subject"}:
            raise ValueError("Unsupported subject/entity kind")
        _tuple(self.aliases, str)
        if not self.aliases:
            raise ValueError("Subject requires aliases")
        for alias in self.aliases:
            _text(alias)


@dataclass(frozen=True)
class TokenAlias:
    coin: CoinIdentity
    subjects: tuple[str, ...] = ()
    tickers: tuple[str, ...] = ()
    names: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.coin, CoinIdentity):
            raise TypeError("CoinIdentity required")
        for name in ("subjects", "tickers", "names"):
            _tuple(getattr(self, name), str)
            for value in getattr(self, name):
                _text(value)


@dataclass(frozen=True)
class CTRegistry:
    """Explicit point-in-time research dictionary, not an authoritative token index."""
    known_at: datetime
    version: str
    subjects: tuple[SubjectAlias, ...] = ()
    tokens: tuple[TokenAlias, ...] = ()

    def __post_init__(self):
        _text(self.version)
        object.__setattr__(self, "known_at", _time(self.known_at))
        _tuple(self.subjects, SubjectAlias)
        _tuple(self.tokens, TokenAlias)
        if len({t.coin.coin_id for t in self.tokens}) != len(self.tokens):
            raise ValueError("Duplicate registry coin IDs")

    @property
    def record_id(self):
        return "ctregistry-" + digest(self)


class CTParser:
    def __init__(self, registry: CTRegistry):
        if not isinstance(registry, CTRegistry):
            raise TypeError("CTRegistry required")
        self.registry = registry

    def parse(self, raw: RawXPost, *, target: CoinIdentity, observed_at: datetime) -> ParsedCTPost:
        if not isinstance(raw, RawXPost) or not isinstance(target, CoinIdentity):
            raise TypeError("Typed raw observation/target required")
        observed_at = _time(observed_at)
        if raw.parsed_at > observed_at:
            raise ValueError("Future evidence/detection/parsing cannot enter CT cutoff")
        if self.registry.known_at > observed_at or self.registry.known_at > raw.parsed_at:
            raise ValueError("Future registry unavailable to this parser observation")
        text = raw.text or ""
        entities: set[tuple[str, str, str]] = set()
        subjects = set()
        for entry in self.registry.subjects:
            for alias in entry.aliases:
                for match in _matches(alias, text):
                    subjects.add(entry.subject)
                    entities.add((entry.kind, entry.subject, match))

        contracts = set(re.findall(r"(?<!\w)0x[0-9a-fA-F]{40}(?!\w)", text))
        contracts.update(re.findall(r"(?<!\w)[1-9A-HJ-NP-Za-km-z]{32,44}(?!\w)", text))
        cashtags = set(raw.cashtags) | set(re.findall(r"(?<!\w)\$([A-Za-z][A-Za-z0-9_]{0,14})(?!\w)", text))
        hashtags = set(raw.hashtags) | set(re.findall(r"(?<!\w)#(\w+)", text))
        accounts = set(raw.mentions) | set(re.findall(r"(?<!\w)@(\w+)", text))
        urls = set(raw.urls) | {u.rstrip(".,!;)") for u in re.findall(r"https?://[^\s<>]+", text)}
        for kind, values in (("contract_candidate", contracts), ("cashtag", cashtags),
                             ("hashtag", hashtags), ("account", accounts), ("url", urls)):
            entities.update((kind, value, value) for value in values)
        entities.update(("domain", urlsplit(u).hostname, u) for u in urls if urlsplit(u).hostname)

        direct = set()
        ticker_candidates = set()
        direct_address_map = {}
        for entry in self.registry.tokens:
            address = entry.coin.contract_address
            # Registry strings stay exact/case-sensitive, consistent with Narrative v0.1.
            if re.search(r"(?<!\w)"+re.escape(address)+r"(?!\w)", text):
                contracts.add(address)
                entities.add(("contract_candidate", address, address))
                direct_address_map.setdefault(address, set()).add(entry.coin.coin_id)
            for ticker in entry.tickers:
                if ticker.casefold() in {c.casefold() for c in cashtags}:
                    ticker_candidates.add(entry.coin.coin_id)
                    entities.add(("ticker", ticker, "$"+ticker))
            for name in entry.names:
                for match in _matches(name, text):
                    ticker_candidates.add(entry.coin.coin_id)
                    entities.add(("token_name", name, match))
        for ids in direct_address_map.values():
            if len(ids) == 1:
                direct.update(ids)
        address_candidates = set().union(*direct_address_map.values()) if direct_address_map else set()
        ambiguous_address = any(len(ids) > 1 for ids in direct_address_map.values())
        target_subjects = {s for t in self.registry.tokens if t.coin.coin_id == target.coin_id for s in t.subjects}
        target_alias = target.coin_id in ticker_candidates
        matched_target_subject = bool(subjects & target_subjects)
        if raw.text is None:
            relation, reason = Relationship.AMBIGUOUS_RELATION, "Post text unavailable"
        elif target.coin_id in direct and not ambiguous_address:
            relation, reason = Relationship.DIRECT_CONTRACT_REFERENCE, "Exact address mapped to one registry chain+contract"
        elif target.coin_id in address_candidates or (target_alias and len(ticker_candidates) > 1):
            relation, reason = Relationship.AMBIGUOUS_RELATION, "Address chain or ticker/name collision; no forced identity"
        elif target_alias:
            relation, reason = Relationship.DIRECT_TICKER_OR_NAME_REFERENCE, "Registry alias mention only; not proven contract identity"
        elif matched_target_subject:
            relation, reason = Relationship.INDIRECT_NARRATIVE_RELATION, "Subject alias overlaps target registry hypothesis; not token capture"
        else:
            relation, reason = Relationship.UNRELATED, "No target contract, alias or registered subject overlap"

        promo = next((p for p in ("buy now", "100x", "gem alert", "don't miss") if _matches(p, text)), None)
        ref_kinds = {r.kind for r in raw.references}
        if promo:
            label, why = PostClass.PROMOTION_OR_SHILL, f"Observed promotional phrase: {promo}; no intent/bot assertion"
        elif ref_kinds & {"replied_to", "quoted"}:
            label, why = PostClass.REACTION, "Observed reply/quote reference"
        elif "retweeted" in ref_kinds:
            label, why = PostClass.NARRATIVE_PROPAGATION, "Observed repost reference, not independent confirmation"
        elif any(_matches(word, text) for word in ("news", "announced", "launches")):
            label, why = PostClass.NEWS_OR_INFORMATION, "Observed versioned news phrase"
        elif contracts or ticker_candidates:
            label, why = PostClass.TRADER_OR_CALLER_MENTION, "Observed contract/token alias mention; no source-quality inference"
        elif subjects and any(_matches(word, text) for word in ("meme", "community")):
            label, why = PostClass.MEME_OR_COMMUNITY, "Registered subject plus observed meme/community phrase"
        elif subjects:
            label, why = PostClass.ORIGINAL_CATALYST, "Subject-only post with no observed reference: possible catalyst, originality unverified"
        else:
            label, why = PostClass.UNKNOWN, "No supported descriptive rule"
        ids = (raw.record_id, self.registry.record_id)
        def interpretation(label, reason):
            return RuleInterpretation(label.value, reason, ids, PARSER_VERSION, observed_at)
        unknowns = tuple(name+" unavailable" for name in ("text", "author_id", "posted_at", "author_username")
                         if getattr(raw, name) is None)
        unknowns += ("Account independence and reputation unverified",)
        if relation == Relationship.AMBIGUOUS_RELATION:
            unknowns += ("Target identity unresolved",)
        return ParsedCTPost(raw, target, observed_at,
            tuple(EntityMatch(*e) for e in sorted(entities)), tuple(sorted(subjects)),
            tuple(sorted(ticker_candidates | address_candidates)), tuple(sorted(direct)),
            interpretation(relation, reason), interpretation(label, why),
            bool(subjects and not contracts and not cashtags and not ticker_candidates),
            unknowns, self.registry.record_id, PARSER_VERSION)


@dataclass(frozen=True)
class PropagationConfig:
    version: str = "ct-propagation/v1"
    near_duplicate_similarity: float = 0.9
    tight_window_seconds: int = 60

    def __post_init__(self):
        if self.version != "ct-propagation/v1":
            raise ValueError("Unsupported measurement rule")
        if type(self.near_duplicate_similarity) not in (float, int) or not 0 <= self.near_duplicate_similarity <= 1:
            raise ValueError("Similarity must be in [0,1]")
        if type(self.tight_window_seconds) is not int or self.tight_window_seconds < 0:
            raise ValueError("Nonnegative timing window required")


@dataclass(frozen=True)
class CTPropagation:
    target: CoinIdentity
    subject: str
    window_start: datetime
    observed_at: datetime
    posts: tuple[ParsedCTPost, ...]
    facts_json: str
    interpretations: tuple[RuleInterpretation, ...]
    config: PropagationConfig
    catalyst_evidence: NarrativeEvidence | None = None

    def __post_init__(self):
        import json
        if not isinstance(self.target, CoinIdentity) or not isinstance(self.config, PropagationConfig):
            raise TypeError("Typed target/config required")
        _text(self.subject)
        for name in ("window_start", "observed_at"):
            object.__setattr__(self, name, _time(getattr(self, name)))
        if self.window_start > self.observed_at:
            raise ValueError("Reversed CT window")
        _tuple(self.posts, ParsedCTPost)
        _tuple(self.interpretations, RuleInterpretation)
        if not isinstance(self.facts_json, str) or not isinstance(json.loads(self.facts_json), dict):
            raise TypeError("Immutable JSON fact snapshot required")
        if any(p.observed_at > self.observed_at or p.target != self.target for p in self.posts):
            raise ValueError("Future/wrong target in CT snapshot")
        for interpretation in self.interpretations:
            if interpretation.as_of != self.observed_at:
                raise ValueError("Noise interpretation must share cutoff")
        if self.catalyst_evidence is not None:
            if (not isinstance(self.catalyst_evidence, NarrativeEvidence) or
                    self.catalyst_evidence.kind != EvidenceKind.CATALYST or
                    self.catalyst_evidence.subject != self.subject or
                    self.catalyst_evidence.detected_at > self.observed_at):
                raise ValueError("Cutoff-safe same-subject catalyst required")

    @property
    def record_id(self):
        return "ctprop-" + digest(self)

    @property
    def facts(self):
        import json
        return json.loads(self.facts_json)  # defensive copy


def measure_propagation(posts: tuple[ParsedCTPost, ...], *, target: CoinIdentity, subject: str,
                        window_start: datetime, observed_at: datetime,
                        config: PropagationConfig = PropagationConfig(),
                        catalyst: NarrativeEvidence | None = None) -> CTPropagation:
    from .ct_models import canonical
    _tuple(posts, ParsedCTPost)
    if not isinstance(target, CoinIdentity) or not isinstance(config, PropagationConfig):
        raise TypeError("Typed target/config required")
    _text(subject)
    window_start, observed_at = _time(window_start), _time(observed_at)
    if window_start > observed_at:
        raise ValueError("Reversed observation window")
    if catalyst is not None:
        if (not isinstance(catalyst, NarrativeEvidence) or catalyst.kind != EvidenceKind.CATALYST or catalyst.subject != subject
                or catalyst.detected_at > observed_at):
            raise ValueError("Cutoff-safe same-subject catalyst required")
    latest = {}
    for post in posts:
        if post.target.coin_id != target.coin_id or post.observed_at > observed_at or post.raw.parsed_at > observed_at:
            raise ValueError("Wrong target or future CT interpretation")
        # Receipt-window counts, including late receipts; not a population-wide X count.
        if post.raw.detected_at >= window_start:
            previous = latest.get(post.raw.post_id)
            if previous and previous.raw.parsed_at == post.raw.parsed_at and previous.raw.record_id != post.raw.record_id:
                raise ValueError("Conflicting same-time post snapshots")
            if previous is None or post.raw.parsed_at > previous.raw.parsed_at:
                latest[post.raw.post_id] = post
    selected = tuple(sorted(latest.values(), key=lambda p: p.raw.post_id))
    if len({p.registry_id for p in selected}) > 1:
        raise ValueError("Mixed registry versions require explicit replay under one registry")
    relevant = tuple(p for p in selected if subject in p.subjects or target.coin_id in p.candidate_coin_ids)
    subject_posts = tuple(p for p in relevant if subject in p.subjects)
    token_posts = tuple(p for p in relevant if target.coin_id in p.direct_coin_ids)
    available_text = [p.raw.text for p in relevant if p.raw.text is not None]
    normalized = [" ".join(text.casefold().split()) for text in available_text]
    duplicate_count = sum(n-1 for n in Counter(available_text).values())
    near_pairs, tight_pairs = [], []
    for i, a in enumerate(relevant):
        for b in relevant[i+1:]:
            if a.raw.text is None or b.raw.text is None:
                continue
            left, right = " ".join(a.raw.text.casefold().split()), " ".join(b.raw.text.casefold().split())
            similar = SequenceMatcher(None, left, right, autojunk=False).ratio() >= config.near_duplicate_similarity
            if similar:
                near_pairs.append((a.raw.record_id, b.raw.record_id))
                if abs((a.raw.detected_at-b.raw.detected_at).total_seconds()) <= config.tight_window_seconds:
                    tight_pairs.append((a.raw.record_id, b.raw.record_id))
    urls = Counter(e.value for p in relevant for e in p.entities if e.kind == "url")
    contracts = Counter(c for p in relevant for c in p.direct_coin_ids)
    promoted = Counter(c for p in relevant if p.classification.label == PostClass.PROMOTION_OR_SHILL.value for c in p.direct_coin_ids)
    reference_counts = {kind: sum(any(r.kind == kind for r in p.raw.references) for p in relevant)
                        for kind in ("retweeted", "quoted", "replied_to")}
    mention_times = [p.raw.posted_at for p in relevant if p.raw.posted_at is not None]
    ct_after_catalyst = [p.raw.posted_at for p in subject_posts if p.raw.posted_at is not None and catalyst is not None
                        and p.raw.posted_at >= catalyst.occurred_at and p.raw.post_id != catalyst.post_id]
    facts = dict(
        observations_received=sum(p.raw.detected_at >= window_start for p in posts),
        unique_posts_in_window=len(selected), total_relevant_posts=len(relevant),
        duplicate_post_observations=sum(p.raw.detected_at >= window_start for p in posts)-len(selected),
        unique_author_count=len({p.raw.author_id for p in relevant if p.raw.author_id is not None}),
        unknown_author_posts=sum(p.raw.author_id is None for p in relevant), independent_source_count=None,
        direct_contract_reference_count=len(token_posts), specific_token_mention_count=len(token_posts),
        ticker_name_reference_count=sum(target.coin_id in p.candidate_coin_ids and any(e.kind in {"ticker", "token_name"} for e in p.entities) for p in relevant),
        underlying_subject_mention_count=len(subject_posts),
        repost_count=reference_counts["retweeted"], quote_count=reference_counts["quoted"], reply_count=reference_counts["replied_to"],
        first_observed_mention_at=min((p.raw.detected_at for p in relevant), default=None),
        first_posted_mention_at=min(mention_times, default=None),
        most_recent_observation_at=max((p.raw.detected_at for p in relevant), default=None),
        duplicate_content_count=duplicate_count, duplicate_content_ratio=duplicate_count/len(normalized) if normalized else None,
        normalized_duplicate_content_count=sum(n-1 for n in Counter(normalized).values()),
        duplicate_ratio_denominator=len(normalized), near_duplicate_pair_count=len(near_pairs),
        near_duplicate_pairs=tuple(near_pairs), similar_posts_within_window=len(tight_pairs),
        similar_posts_within_window_evidence=tuple(tight_pairs),
        repeated_url_count=sum(n-1 for n in urls.values()),
        repeated_contract_reference_count=sum(n-1 for n in contracts.values()),
        repeated_contract_promotion_count=sum(n-1 for n in promoted.values()),
        competing_contract_count=len(set(contracts)-{target.coin_id}),
        contract_post_evidence=tuple((c, tuple(p.raw.record_id for p in relevant if c in p.direct_coin_ids)) for c in sorted(contracts)),
        catalyst_age_seconds=None if catalyst is None else (observed_at-catalyst.occurred_at).total_seconds(),
        catalyst_to_ct_latency_seconds=None if not ct_after_catalyst else (min(ct_after_catalyst)-catalyst.occurred_at).total_seconds(),
        detection_latency_seconds=tuple((p.raw.record_id, p.raw.detection_latency_seconds) for p in relevant),
        observation_window_seconds=(observed_at-window_start).total_seconds(),
        subject_evidence_ids=tuple(p.raw.record_id for p in subject_posts),
        token_evidence_ids=tuple(p.raw.record_id for p in token_posts),
        independence_evidence=(),
    )
    interpretations = ()
    if duplicate_count or tight_pairs:
        interpretations = (RuleInterpretation("possible coordinated/noisy propagation",
            "Observed duplicate text or similar pairs within configured receipt window; not proof of bots/manipulation",
            tuple(p.raw.record_id for p in relevant), config.version, observed_at),)
    return CTPropagation(target, subject, window_start, observed_at, selected, canonical(facts), interpretations, config, catalyst)


def narrative_evidence(posts: tuple[ParsedCTPost, ...], *, subject: str,
                       observed_at: datetime) -> tuple[NarrativeEvidence, ...]:
    """Bridge observation facts only. Never create identity/capture/hypothesis claims.

    A contract address in text proves a mention, not narrative capture.
    Missing account/time cannot satisfy the stricter legacy CT_X contract.
    """
    _tuple(posts, ParsedCTPost)
    _text(subject)
    observed_at = _time(observed_at)
    output = []
    seen = set()
    for post in posts:
        if post.observed_at > observed_at or post.raw.parsed_at > observed_at:
            raise ValueError("Future parsed evidence")
        raw = post.raw
        if raw.record_id in seen:
            continue
        seen.add(raw.record_id)
        if raw.posted_at is None or raw.author_id is None or raw.text is None:
            continue
        if subject not in post.subjects:
            continue  # do not fabricate a subject for contract-only chatter
        token = post.target if post.target.coin_id in post.direct_coin_ids else None
        metrics = tuple(Measurement(m.name, Decimal(m.value), "count", raw.detected_at,
                        "API public metric snapshot for post "+raw.post_id) for m in raw.public_metrics)
        evidence_id = "ctx-" + digest((raw.record_id, subject, post.parser_version, post.registry_id, post.observed_at))
        output.append(NarrativeEvidence(evidence_id, EvidenceKind.CT_X, raw.posted_at,
            raw.detected_at, raw.provenance, raw.text or "Empty post", subject, token,
            raw.author_id, raw.post_id, "Literal registered subject match; "+post.relationship.reason+
            "; rule="+post.parser_version+"; registry="+post.registry_id+"; parsed_at="+raw.parsed_at.isoformat(), metrics))
    return tuple(output)


@dataclass(frozen=True)
class NarrativeCTBridge:
    evidence: tuple[NarrativeEvidence, ...]
    exclusions: tuple[RuleInterpretation, ...]
    observed_at: datetime

    def __post_init__(self):
        _tuple(self.evidence, NarrativeEvidence)
        _tuple(self.exclusions, RuleInterpretation)
        object.__setattr__(self, "observed_at", _time(self.observed_at))


def narrative_bridge(posts: tuple[ParsedCTPost, ...], *, subject: str,
                     observed_at: datetime) -> NarrativeCTBridge:
    """Explicit exclusions preserve unknowns outside the stricter narrative schema."""
    evidence = narrative_evidence(posts, subject=subject, observed_at=observed_at)
    observed_at = _time(observed_at)
    exclusions = []
    for post in posts:
        missing = [name for name in ("posted_at", "author_id", "text") if getattr(post.raw, name) is None]
        reason = "Required narrative fields unavailable: "+", ".join(missing) if missing else None
        if subject not in post.subjects:
            reason = "No literal registered match to requested subject"
        if reason:
            exclusions.append(RuleInterpretation("narrative_bridge_exclusion", reason,
                (post.raw.record_id, post.registry_id), PARSER_VERSION, observed_at))
    return NarrativeCTBridge(evidence, tuple(exclusions), observed_at)
