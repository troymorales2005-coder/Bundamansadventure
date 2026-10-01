"""Official v2 response normalization only. There is deliberately no HTTP transport."""
from __future__ import annotations

import json
import hashlib
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from .ct_models import PostReference, PublicMetric, RawXPost, canonical
from .narrative import NarrativeProvenance, _optional_text, _text, _time


@dataclass(frozen=True)
class XAdapterConfig:
    credential_env_name: str = "X_BEARER_TOKEN"

    def __post_init__(self):
        _text(self.credential_env_name)

    def credential_present(self, environ: Mapping[str, str] | None = None) -> bool:
        """Check presence only; credentials are never stored in this object."""
        return bool((os.environ if environ is None else environ).get(self.credential_env_name))


@dataclass(frozen=True)
class ApiUsageEvent:
    request_id: str
    observed_at: datetime
    status_code: int
    posts_returned: int = 0
    user_lookups: int = 0
    pagination_requests: int = 0
    duplicates_received: int = 0
    api_error_count: int = 0
    known_usage_units: int | None = None
    rate_limit_remaining: int | None = None
    rate_limit_reset: int | None = None
    estimated_usage_units: int | None = None
    usage_estimate_version: str | None = None

    def __post_init__(self):
        _text(self.request_id)
        object.__setattr__(self, "observed_at", _time(self.observed_at))
        if type(self.status_code) is not int or not 100 <= self.status_code <= 599:
            raise ValueError("Invalid HTTP status")
        for name in ("posts_returned", "user_lookups", "pagination_requests", "duplicates_received",
                     "api_error_count", "known_usage_units", "rate_limit_remaining", "rate_limit_reset", "estimated_usage_units"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("Usage counts must be nonnegative integers or unavailable")
        _optional_text(self.usage_estimate_version)
        if self.estimated_usage_units is not None:
            _text(self.usage_estimate_version)


class ApiUsageLedger:
    """Append caller-reported requests, not offline normalization operations."""
    def __init__(self):
        self.__events: tuple[ApiUsageEvent, ...] = ()

    @property
    def events(self):
        return self.__events

    def append(self, event: ApiUsageEvent):
        if not isinstance(event, ApiUsageEvent):
            raise TypeError("ApiUsageEvent required")
        if any(e.request_id == event.request_id for e in self.__events):
            raise ValueError("Duplicate request ID; retries need distinct IDs")
        self.__events += (event,)

    def summary(self, cutoff: datetime):
        cutoff = _time(cutoff)
        events = tuple(e for e in self.__events if e.observed_at <= cutoff)
        counts = {key: sum(getattr(e, key) for e in events) for key in (
            "posts_returned", "user_lookups", "pagination_requests", "duplicates_received", "api_error_count")}
        counts.update(requests_made=len(events), rate_limit_responses=sum(e.status_code == 429 for e in events),
                      api_errors=sum(e.status_code >= 400 for e in events),
                      known_usage_units=(sum(e.known_usage_units for e in events)
                                         if events and all(e.known_usage_units is not None for e in events) else None),
                      estimated_usage_units=(sum(e.estimated_usage_units for e in events)
                                             if events and all(e.estimated_usage_units is not None for e in events) else None))
        return counts


class OfficialXResponseAdapter:
    """Accept saved/fixture JSON. Calling this cannot consume X API credits."""
    def normalize(self, response: dict, *, detected_at: datetime, parsed_at: datetime,
                  source_id: str, data_mode: str = "synthetic") -> tuple[RawXPost, ...]:
        _text(source_id)
        detected_at, parsed_at = _time(detected_at), _time(parsed_at)
        # Make a defensive immutable copy before any interpretation.
        response_json = canonical(response)
        payload = json.loads(response_json)
        if not isinstance(payload, dict):
            raise ValueError("Expected official v2 response object")
        users = {u["id"]: u for u in payload.get("includes", {}).get("users", [])}
        data = payload.get("data", [])
        if isinstance(data, dict):
            data = [data]
        result = []
        for post in data:
            account = users.get(post.get("author_id"))
            entities = post.get("entities") or {}
            created = post.get("created_at")
            posted_at = None if created is None else datetime.fromisoformat(created.replace("Z", "+00:00"))
            result.append(RawXPost(
                post_id=post["id"], text=post.get("text"), author_id=post.get("author_id"),
                author_username=None if account is None else account.get("username"), posted_at=posted_at,
                detected_at=detected_at, parsed_at=parsed_at,
                provenance=NarrativeProvenance(source_id, "official_x_v2_response", detected_at,
                    f"https://x.com/i/status/{post['id']}", hashlib.sha256(response_json.encode()).hexdigest()),
                raw_payload_json=response_json, account_payload_json=None if account is None else canonical(account),
                urls=tuple(u.get("expanded_url") or u["url"] for u in entities.get("urls", [])),
                mentions=tuple(m["username"] for m in entities.get("mentions", [])),
                hashtags=tuple(h["tag"] for h in entities.get("hashtags", [])),
                cashtags=tuple(c["tag"] for c in entities.get("cashtags", [])),
                references=tuple(PostReference(r["type"], r["id"]) for r in post.get("referenced_tweets", [])),
                public_metrics=tuple(PublicMetric(k, v) for k, v in sorted((post.get("public_metrics") or {}).items())),
                data_mode=data_mode))
        return tuple(result)
