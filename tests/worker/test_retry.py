import pytest
from tests._util import load
w = load("worker", "worker")


def test_call_engine_succeeds_after_retries(monkeypatch):
    monkeypatch.setattr(w.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(w, "ENGINE_RETRIES", 2)
    calls = {"n": 0}
    def fn():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("일시 실패")
        return {"ok": True}
    assert w.call_engine(fn, job_id="J", stage="analysis") == {"ok": True}
    assert calls["n"] == 3


def test_call_engine_raises_after_exhaustion(monkeypatch):
    monkeypatch.setattr(w.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(w, "ENGINE_RETRIES", 1)
    def fn():
        raise RuntimeError("영구 실패")
    with pytest.raises(RuntimeError):
        w.call_engine(fn, job_id="J", stage="prescription")


# ── 재시도 의미(fix): 일시적 오류만 재큐, 영구/소진은 데드레터 ──────────────
import httpx


def _http_status(code):
    req = httpx.Request("POST", "http://engine/score")
    resp = httpx.Response(code, request=req)
    return httpx.HTTPStatusError(f"{code}", request=req, response=resp)


def test_is_retryable_transient_vs_permanent():
    # 일시적: 연결 실패·타임아웃·5xx
    assert w.is_retryable(httpx.ConnectError("refused")) is True
    assert w.is_retryable(httpx.ReadTimeout("slow")) is True
    assert w.is_retryable(_http_status(503)) is True
    # 영구: 4xx(계약 위반)·우리 검증 오류
    assert w.is_retryable(_http_status(422)) is False
    assert w.is_retryable(_http_status(400)) is False
    assert w.is_retryable(ValueError("처방 입력 없음")) is False


def _route(monkeypatch):
    calls = {"requeue": [], "error": []}
    monkeypatch.setattr(w, "requeue", lambda jid, att, err: calls["requeue"].append((jid, att)))
    monkeypatch.setattr(w, "finish_err", lambda jid, err: calls["error"].append(jid))
    return calls


def test_on_failure_requeues_transient_with_attempts_left(monkeypatch):
    monkeypatch.setattr(w, "MAX_ATTEMPTS", 3)
    calls = _route(monkeypatch)
    assert w.on_failure("J", 1, httpx.ConnectError("x")) == "requeued"
    assert calls["requeue"] == [("J", 1)] and calls["error"] == []


def test_on_failure_deadletters_transient_when_exhausted(monkeypatch):
    monkeypatch.setattr(w, "MAX_ATTEMPTS", 3)
    calls = _route(monkeypatch)
    # attempts == MAX_ATTEMPTS → 소진 → 데드레터 (reap_stale 과 동일 기준)
    assert w.on_failure("J", 3, httpx.ConnectError("x")) == "error"
    assert calls["error"] == ["J"] and calls["requeue"] == []


def test_on_failure_deadletters_permanent_even_with_attempts_left(monkeypatch):
    monkeypatch.setattr(w, "MAX_ATTEMPTS", 3)
    calls = _route(monkeypatch)
    # 영구 오류는 여유가 있어도 재시도하지 않는다(무의미한 재큐 방지)
    assert w.on_failure("J", 1, ValueError("처방 입력 없음")) == "error"
    assert calls["error"] == ["J"] and calls["requeue"] == []
