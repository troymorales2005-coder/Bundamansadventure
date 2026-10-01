"""Transport tests inject local responses; no genuine API calls or credentials."""
import io
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

from meme_coin_radar.x_bounded_capture import (
    BoundedXCapture, CaptureLimits, NoRedirect, credential_available, public_summary,
)


class LocalResponse(io.BytesIO):
    def __init__(self, payload, *, status=200, headers=None):
        super().__init__(json.dumps(payload).encode())
        self.code = status
        self.headers = headers or {}


@pytest.fixture
def configured(tmp_path,monkeypatch):
    monkeypatch.delenv("X_BEARER_TOKEN",raising=False)
    env = tmp_path/".env"
    env.write_text("X_BEARER_TOKEN=fixture-secret\n",encoding="utf-8")
    return BoundedXCapture(tmp_path/"capture",env_file=env)


def response(payload=None):
    return LocalResponse(payload or {"data":{"id":"1","text":"Example"}},headers={"x-rate-limit-remaining":"5"})


def test_env_loader_only_reports_availability(tmp_path):
    env=tmp_path/".env"
    assert not credential_available(env,{})
    env.write_text('# local only\nX_BEARER_TOKEN="fixture-secret"\nOTHER=ignored\n')
    assert credential_available(env,{})
    assert "fixture-secret" not in json.dumps({"credential_available":credential_available(env,{})})
    env.write_text("X_BEARER_TOKEN=one\nX_BEARER_TOKEN=two\n")
    assert not credential_available(env,{})
    assert credential_available(env,{"X_BEARER_TOKEN":"environment-wins"})


def test_capture_freezes_raw_before_parser_and_never_persists_secrets(configured):
    requests=[]
    def opener(req,timeout):
        requests.append(req.full_url)
        assert req.get_header("Authorization") == "Bearer fixture-secret"
        return response()
    record=configured.lookup_verification(opener=opener)
    assert len(requests)==1 and requests[0].startswith("https://api.x.com/2/tweets/")
    assert record["http_status"]==200 and record["posts_returned"]==1
    assert record["usage_event"]["posts_returned"]==1
    assert record["rate_limit_metadata"]["x-rate-limit-remaining"]=="5"
    assert (configured.directory/record["body_file"]).exists()
    for file in configured.directory.iterdir():
        assert b"fixture-secret" not in file.read_bytes()


def test_ceiling_is_persistent_across_restart_and_no_pagination(configured):
    configured.lookup_verification(opener=lambda *a,**k: response())
    for index in range(3):
        configured.recent_sample("specific subject",opener=lambda *a,**k: LocalResponse(
            {"data":[{"id":str(index+2),"text":"Post"}],"meta":{"next_token":"unused"}}))
    restarted=BoundedXCapture(configured.directory,env_file=configured.env_file)
    with pytest.raises(ValueError,match="ceiling"):
        restarted.recent_sample("specific subject",opener=lambda *a,**k: pytest.fail("No request beyond ceiling"))
    records=list(configured.directory.glob("*-response.json"))
    assert len(records)==4
    assert all(json.loads(p.read_text())["pagination_used"]==0 for p in records)


@pytest.mark.parametrize("status",[401,402,403,404,429,500])
def test_http_error_stops_future_requests_without_retry(configured,status):
    calls=[]
    def opener(*a,**k):
        calls.append(1)
        return LocalResponse({"title":"Not available","type":"api-error"},status=status)
    r=configured.lookup_verification(opener=opener)
    assert len(calls)==1 and r["stop_reason"]=="http_error"
    with pytest.raises(ValueError):
        configured.lookup_verification(opener=lambda *a,**k: pytest.fail("No automatic retry"))
    assert r["monetary_charge"]=="not_determined" and r["known_usage_units"] is None


def test_actual_httperror_body_is_saved(configured):
    def opener(*a,**k):
        raise HTTPError("https://api.x.com/2/tweets/example",403,"Forbidden",{},
                        io.BytesIO(b'{"title":"Forbidden"}'))
    r=configured.lookup_verification(opener=opener)
    assert r["http_status"]==403 and r["payload"]["title"]=="Forbidden"


def test_redirect_cannot_forward_authorization():
    assert NoRedirect().redirect_request(None,None,302,"Redirect",{},"https://other.example") is None


def test_secret_echo_is_redacted_from_all_outputs(configured):
    r=configured.lookup_verification(opener=lambda *a,**k: LocalResponse(
        {"title":"fixture-secret","detail":"Bearer fixture-secret"},status=401,
        headers={"retry-after":"fixture-secret","Authorization":"fixture-secret"}))
    assert r["credential_echo_redacted"]
    assert "fixture-secret" not in json.dumps(public_summary(r))
    for file in configured.directory.iterdir():
        assert b"fixture-secret" not in file.read_bytes()


def test_uncertain_transport_attempt_is_recorded_and_not_retried(configured):
    def fail(*a,**k):
        raise TimeoutError("sensitive exception with fixture-secret")
    r=configured.lookup_verification(opener=fail)
    assert r["transport_error"]=="TimeoutError" and r["http_status"] is None
    assert "fixture-secret" not in json.dumps(r)
    with pytest.raises(ValueError):
        configured.lookup_verification(opener=lambda *a,**k: pytest.fail("No retry"))


def test_explicit_review_cannot_reopen_http_failure(configured):
    configured.lookup_verification(opener=lambda *a,**k: LocalResponse({"title":"Unauthorized"},status=401))
    with pytest.raises(ValueError):
        configured.record_local_connection_review("request-01")


def test_explicit_local_denial_review_preserves_attempt_and_budget(configured):
    def fail(*a,**k):
        raise PermissionError(13,"Local test connection denied")
    first = configured.lookup_verification(opener=fail)
    assert first["transport_cause"] == {"type":"PermissionError","errno":13}
    configured.record_local_connection_review("request-01")
    second = configured.lookup_verification(opener=lambda *a,**k: response())
    assert second["request_id"]=="request-02"
    assert (configured.directory/"request-01-response.json").exists()
    assert (configured.directory/"request-01-review.json").exists()


def test_resources_errors_duplicates_and_size_stop(configured):
    r=configured.lookup_verification(opener=lambda *a,**k: LocalResponse(
        {"data":[{"id":"same"},{"id":"same"}],"includes":{"users":[{"id":"u"}]}}))
    assert r["stop_reason"]=="resource_ceiling_breach" and r["duplicates_received"]==1
    assert r["resources_returned"]==3


def test_limits_cannot_be_increased_and_missing_credential_prevents_request(tmp_path,monkeypatch):
    with pytest.raises(ValueError):
        CaptureLimits(max_requests=5)
    monkeypatch.delenv("X_BEARER_TOKEN",raising=False)
    capture=BoundedXCapture(tmp_path/"capture",env_file=tmp_path/"missing")
    with pytest.raises(ValueError):
        capture.lookup_verification(opener=lambda *a,**k: pytest.fail("Missing credential"))
    assert not list(capture.directory.glob("request-*.json"))
