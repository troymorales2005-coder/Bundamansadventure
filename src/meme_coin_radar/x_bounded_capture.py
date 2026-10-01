"""Explicit one-shot X capture: durable request reservations, no retry or pagination.

The existing response adapter stays offline. This transport is opt-in and limited
to api.x.com post lookup/recent search. Secrets never enter persisted metadata.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .ct_models import canonical
from .x_adapter import ApiUsageEvent

FIELDS = "created_at,author_id,entities,referenced_tweets,public_metrics,conversation_id"
VERIFY_POST_ID = "1228393702244134912"  # official X lookup quickstart example


def credential_available(env_file: Path, environ=None) -> bool:
    try:
        _credential(env_file, os.environ if environ is None else environ)
        return True
    except (ValueError, OSError):
        return False


def _credential(env_file: Path, environ) -> str:
    token = environ.get("X_BEARER_TOKEN", "").strip()
    if not token and env_file.exists():
        matches = []
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, sep, value = line.partition("=")
            if sep and key.strip() == "X_BEARER_TOKEN":
                matches.append(value.strip())
        if len(matches) != 1:
            raise ValueError("Configure exactly one X_BEARER_TOKEN locally")
        token = matches[0]
        if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
            token = token[1:-1]
    if (not token or token in {"YOUR_ACTUAL_BEARER_TOKEN", "YOUR_LOCAL_BEARER_TOKEN"}
            or not re.fullmatch(r"[\x21-\x7e]+", token)):
        raise ValueError("X_BEARER_TOKEN missing or invalid; do not paste it into chat")
    return token


@dataclass(frozen=True)
class CaptureLimits:
    max_requests: int = 4
    max_posts: int = 31
    max_resources: int = 62  # primary posts plus author expansions
    timeout_seconds: int = 20
    max_response_bytes: int = 2_000_000

    def __post_init__(self):
        for value in (self.max_requests, self.max_posts, self.max_resources,
                      self.timeout_seconds, self.max_response_bytes):
            if type(value) is not int or value <= 0:
                raise ValueError("Positive integer capture limits required")
        if self.max_requests > 4 or self.max_posts > 31 or self.max_resources > 62:
            raise ValueError("V1 ceiling cannot exceed 4 requests / 31 posts / 62 resources")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # never forward Authorization to another location


def _utc():
    return datetime.now(timezone.utc)


def _write_new(path: Path, payload: dict):
    with path.open("x", encoding="utf-8") as handle:
        handle.write(canonical(payload)+"\n")
        handle.flush()
        os.fsync(handle.fileno())


def _resource_counts(payload):
    if not isinstance(payload, dict):
        return 0, 0, (), 0
    posts = payload.get("data", [])
    posts = [posts] if isinstance(posts, dict) else posts if isinstance(posts, list) else []
    includes = payload.get("includes") or {}
    expanded = sum(len(v) for v in includes.values() if isinstance(v, list)) if isinstance(includes, dict) else 0
    ids = tuple(p["id"] for p in posts if isinstance(p, dict) and isinstance(p.get("id"), str))
    users = len(includes.get("users", [])) if isinstance(includes, dict) else 0
    return len(posts), len(posts)+expanded, ids, users


class BoundedXCapture:
    def __init__(self, directory: Path, *, env_file: Path, limits=CaptureLimits()):
        self.directory = directory
        self.env_file = env_file
        self.limits = limits
        directory.mkdir(parents=True, exist_ok=True)
        manifest = dict(version="real-x-capture/v1", limits=json.loads(canonical(limits)),
                        credential_variable="X_BEARER_TOKEN", host="api.x.com",
                        redirects=False, retries=False, pagination=False)
        manifest_path = directory/"capture_manifest.json"
        if manifest_path.exists():
            if json.loads(manifest_path.read_text(encoding="utf-8")) != manifest:
                raise ValueError("Frozen capture configuration cannot be changed")
        else:
            _write_new(manifest_path, manifest)

    def _reserve(self, path, params, maximum_posts):
        reservations = sorted(p for p in self.directory.glob("request-*.json")
                              if re.fullmatch(r"request-\d{2}\.json", p.name))
        prior = [json.loads(p.read_text(encoding="utf-8")) for p in reservations]
        # Missing response = interrupted/uncertain attempt; do not retry automatically.
        for item in prior:
            response_path = self.directory/(item["request_id"]+"-response.json")
            if not response_path.exists():
                raise ValueError("Prior attempt has no response; uncertain usage requires review")
            response = json.loads(response_path.read_text(encoding="utf-8"))
            if response["stop_reason"] is not None:
                review_file = self.directory/(item["request_id"]+"-review.json")
                reviewed_local_denial = (response["stop_reason"] == "transport_error" and
                    response["http_status"] is None and review_file.exists() and
                    json.loads(review_file.read_text(encoding="utf-8")).get("decision") == "reviewed_local_connection_denial")
                if not reviewed_local_denial:
                    raise ValueError("Capture stopped after error, rate limit or ceiling breach")
        if (len(prior) >= self.limits.max_requests or
                sum(p["reserved_posts"] for p in prior)+maximum_posts > self.limits.max_posts or
                sum(p["reserved_resources"] for p in prior)+2*maximum_posts > self.limits.max_resources):
            raise ValueError("Frozen request/post/resource ceiling reached")
        request_id = f"request-{len(prior)+1:02d}"
        reservation = dict(request_id=request_id, requested_at=_utc().isoformat(), method="GET",
                           endpoint="https://api.x.com"+path, params=params,
                           reserved_posts=maximum_posts, reserved_resources=2*maximum_posts)
        _write_new(self.directory/(request_id+".json"), reservation)
        return reservation

    def record_local_connection_review(self, request_id: str):
        """Explicit operator review only; never invoked by request/CLI retry logic.

        Use only after independent diagnostics establish local connection denial.
        This cannot reopen HTTP errors and still consumes a reservation slot.
        """
        if not re.fullmatch(r"request-\d{2}", request_id):
            raise ValueError("Explicit prior request ID required")
        record = json.loads((self.directory/(request_id+"-response.json")).read_text(encoding="utf-8"))
        if record["stop_reason"] != "transport_error" or record["http_status"] is not None:
            raise ValueError("Only reviewed local transport denial can be reopened")
        _write_new(self.directory/(request_id+"-review.json"),dict(request_id=request_id,
            reviewed_at=_utc().isoformat(),decision="reviewed_local_connection_denial",
            reason="Independent unauthenticated socket diagnostic: local PermissionError errno 13 before HTTP; no automatic retry"))

    def lookup_verification(self, *, opener=None):
        return self._get("/2/tweets/"+VERIFY_POST_ID, {
            "tweet.fields": FIELDS, "expansions":"author_id", "user.fields":"username,public_metrics,verified"},
            maximum_posts=1, opener=opener)

    def recent_sample(self, query: str, *, opener=None):
        if not isinstance(query, str) or not 1 <= len(query) <= 512:
            raise ValueError("Explicit bounded search query required")
        # A successful verification is required, not assumed endpoint entitlement.
        verified = False
        for result_file in self.directory.glob("request-*-response.json"):
            result = json.loads(result_file.read_text(encoding="utf-8"))
            reservation_file = self.directory/(result["request_id"]+".json")
            reservation = json.loads(reservation_file.read_text(encoding="utf-8"))
            if (result["http_status"] == 200 and result["stop_reason"] is None and
                    reservation["endpoint"] == "https://api.x.com/2/tweets/"+VERIFY_POST_ID):
                verified = True
        if not verified:
            raise ValueError("Verify access before sample collection")
        return self._get("/2/tweets/search/recent", {"query":query, "max_results":"10",
            "tweet.fields":FIELDS, "expansions":"author_id", "user.fields":"username,public_metrics,verified"},
            maximum_posts=10, opener=opener)

    def _get(self, path, params, *, maximum_posts, opener=None):
        token = _credential(self.env_file, os.environ)
        reservation = self._reserve(path, params, maximum_posts)
        request_id = reservation["request_id"]
        request = Request(reservation["endpoint"]+"?"+urlencode(params),
                          headers={"Authorization":"Bearer "+token, "Accept":"application/json"}, method="GET")
        open_request = (build_opener(NoRedirect()).open if opener is None else opener)
        status = None
        headers = {}
        body = b""
        transport_error = None
        transport_cause = None
        try:
            try:
                response = open_request(request, timeout=self.limits.timeout_seconds)
            except HTTPError as http_error:
                response = http_error  # retain actual API error response too
            with response:
                status = response.code
                headers = {key.lower(): value.replace(token, "[REDACTED_CREDENTIAL]") for key, value in response.headers.items()
                           if key.lower() in {"x-rate-limit-limit", "x-rate-limit-remaining", "x-rate-limit-reset", "retry-after"}}
                body = response.read(self.limits.max_response_bytes+1)
        except Exception as exc:
            transport_error = type(exc).__name__  # never log exception/request/header representations
            cause = getattr(exc, "reason", exc)
            transport_cause = {"type":type(cause).__name__, "errno":getattr(cause,"errno",None)}
        received_at = _utc()
        oversized = len(body) > self.limits.max_response_bytes
        # Credential echo protection: response content is never allowed to retain the token.
        scrubbed_body = body.replace(token.encode(), b"[REDACTED_CREDENTIAL]")
        echoed = body != scrubbed_body
        # Freeze response bytes before normalization, extraction or evaluation.
        raw_path = self.directory/(request_id+"-body.bin")
        with raw_path.open("xb") as raw_file:
            raw_file.write(scrubbed_body)
            raw_file.flush()
            os.fsync(raw_file.fileno())
        try:
            payload = json.loads(scrubbed_body)
        except (ValueError, UnicodeDecodeError):
            payload = None
        posts, resources, ids, users = _resource_counts(payload)
        previous_ids = set()
        for p in self.directory.glob("request-*-response.json"):
            previous_ids.update(json.loads(p.read_text(encoding="utf-8")).get("post_ids", []))
        duplicates = len(ids)-len(set(ids)-previous_ids)
        errors = payload.get("errors", []) if isinstance(payload, dict) else []
        stop_reason = ("transport_error" if transport_error else "response_size_limit" if oversized else
            "http_error" if status != 200 else "non_json_response" if payload is None else
            "resource_ceiling_breach" if posts > maximum_posts or resources > 2*maximum_posts else
            "partial_api_errors" if errors else None)
        event = None
        def header_int(name):
            value = headers.get(name)
            return int(value) if isinstance(value, str) and value.isdigit() else None
        if status is not None:
            event = ApiUsageEvent(request_id, received_at, status, posts_returned=posts,
                duplicates_received=duplicates, api_error_count=len(errors) if isinstance(errors, list) else 1,
                rate_limit_remaining=header_int("x-rate-limit-remaining"),rate_limit_reset=header_int("x-rate-limit-reset"))
        record = dict(request_id=request_id, received_at=received_at.isoformat(), http_status=status,
            rate_limit_metadata=headers, body_file=raw_path.name, body_sha256=hashlib.sha256(scrubbed_body).hexdigest(),
            raw_bytes=len(scrubbed_body), raw_truncated=oversized, credential_echo_redacted=echoed,
            posts_returned=posts, resources_returned=resources, expanded_users_returned=users,
            post_ids=ids, duplicates_received=duplicates,
            pagination_metadata=payload.get("meta") if isinstance(payload, dict) else None,
            payload=payload, usage_event=None if event is None else json.loads(canonical(event)),
            transport_error=transport_error, transport_cause=transport_cause, stop_reason=stop_reason, monetary_charge="not_determined",
            known_usage_units=None, pagination_used=0)
        _write_new(self.directory/(request_id+"-response.json"), record)
        return record


def public_summary(record: dict):
    payload = record.get("payload") or {}
    return dict(request_id=record["request_id"],http_status=record["http_status"],
        received_at=record["received_at"],posts_returned=record["posts_returned"],resources_returned=record["resources_returned"],
        stop_reason=record["stop_reason"],transport_error=record["transport_error"],
        error_title=payload.get("title"),error_type=payload.get("type"),
        rate_limit_metadata=record["rate_limit_metadata"],known_usage_units=None,monetary_charge="not_determined")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--credential-check", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--query")
    args = parser.parse_args()
    if args.credential_check:
        print(json.dumps({"credential_available":credential_available(args.env_file)}))
        return 0
    capture = BoundedXCapture(args.directory, env_file=args.env_file)
    if args.verify == bool(args.query):
        parser.error("Choose exactly one explicit verification or query request")
    try:
        record = capture.lookup_verification() if args.verify else capture.recent_sample(args.query)
    except (ValueError, OSError):
        print(json.dumps({"status":"stopped_before_request_or_on_storage_error"}))
        return 2
    print(json.dumps(public_summary(record),sort_keys=True))
    return 0 if record["stop_reason"] is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
