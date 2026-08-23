"""
P2-13/14/15: gateway 유틸리티(_iso, _ensure_schema, _webp), list_jobs 캡핑, debug_engines 테스트.
"""
import datetime as dt
import uuid
from unittest.mock import MagicMock, patch, call

import pytest
from fastapi import HTTPException

from tests._util import load

gw = load("gateway", "app.main")


# ---------------------------------------------------------------------------
# P2-13a: _iso()
# ---------------------------------------------------------------------------

def test_iso_converts_datetime_to_isoformat():
    """datetime 값은 ISO 포맷 문자열로 변환된다."""
    now = dt.datetime(2026, 8, 19, 12, 0, 0, tzinfo=dt.timezone.utc)
    row = {"id": "abc", "created_at": now, "updated_at": now}
    out = gw._iso(row)
    assert out["created_at"] == now.isoformat()
    assert out["updated_at"] == now.isoformat()
    assert out["id"] == "abc"


def test_iso_leaves_non_datetime_untouched():
    """datetime 이 아닌 값은 그대로 반환된다."""
    row = {"id": "abc", "status": "done", "attempts": 3, "result": None}
    out = gw._iso(row)
    assert out == row


def test_iso_returns_same_dict_object():
    """입력 dict 을 in-place 로 수정하고 동일 객체를 반환한다."""
    row = {"created_at": dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)}
    out = gw._iso(row)
    assert out is row


def test_iso_empty_dict():
    """빈 dict 도 그대로 반환된다."""
    assert gw._iso({}) == {}


# ---------------------------------------------------------------------------
# P2-13b: _ensure_schema()
# ---------------------------------------------------------------------------

def test_ensure_schema_succeeds_on_first_try(monkeypatch):
    """DB 연결이 처음부터 성공하면 재시도 없이 반환한다."""
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__ = lambda s: cur
    conn.cursor.return_value.__exit__ = lambda s, *a: None
    conn.__enter__ = lambda s: conn
    conn.__exit__ = lambda s, *a: None
    monkeypatch.setattr(gw, "db", lambda: conn)
    gw._ensure_schema()
    cur.execute.assert_called_once_with(gw.DDL)
    conn.commit.assert_called_once()


def test_ensure_schema_retries_on_failure_then_succeeds(monkeypatch):
    """처음 실패핬 재시도 후 성공하면 정상 반환한다."""
    calls = {"n": 0}

    def _flaky_db():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("DB not ready")
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value.__enter__ = lambda s: cur
        conn.cursor.return_value.__exit__ = lambda s, *a: None
        conn.__enter__ = lambda s: conn
        conn.__exit__ = lambda s, *a: None
        return conn

    monkeypatch.setattr(gw, "db", _flaky_db)
    monkeypatch.setattr(gw.time, "sleep", lambda *a: None)
    gw._ensure_schema()
    assert calls["n"] == 3


def test_ensure_schema_raises_after_30_failures(monkeypatch):
    """30회 모두 실패하면 RuntimeError 를 던진다."""
    monkeypatch.setattr(gw, "db", lambda: (_ for _ in ()).throw(ConnectionError("DB down")))
    monkeypatch.setattr(gw.time, "sleep", lambda *a: None)
    with pytest.raises(RuntimeError, match="DB 초기화 실패"):
        gw._ensure_schema()


# ---------------------------------------------------------------------------
# P2-13c: _webp()
# ---------------------------------------------------------------------------

def test_webp_accepts_valid_riff_webp():
    """RIFF + WEBP 매직 바이트를 가진 헤더는 True."""
    head = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 4
    assert gw._webp(head) is True


def test_webp_rejects_short_header():
    """12바이트 미만은 False."""
    assert gw._webp(b"RIFF") is False
    assert gw._webp(b"RIFF\x00\x00\x00\x00WEB") is False


def test_webp_rejects_no_riff():
    """RIFF 시그니처가 없으면 False."""
    head = b"XXXX" + b"\x00\x00\x00\x00" + b"WEBP"
    assert gw._webp(head) is False


def test_webp_rejects_no_webp():
    """WEBP 시그니처가 없으면 False."""
    head = b"RIFF" + b"\x00\x00\x00\x00" + b"XXXX"
    assert gw._webp(head) is False


# ---------------------------------------------------------------------------
# P2-14: list_jobs() limit 캡핑
# ---------------------------------------------------------------------------

def _list_jobs_client(monkeypatch):
    """list_jobs 테스트용 mock 클라이언트."""
    monkeypatch.setattr(gw, "require_user",
                        lambda a, b: uuid.UUID("11111111-1111-1111-1111-111111111111"))
    cur = MagicMock()
    cur.fetchall.return_value = []
    conn = MagicMock()
    conn.cursor.return_value.__enter__ = lambda s: cur
    conn.cursor.return_value.__exit__ = lambda s, *a: None
    conn.__enter__ = lambda s: conn
    conn.__exit__ = lambda s, *a: None
    monkeypatch.setattr(gw, "db", lambda: conn)
    return cur


def test_list_jobs_caps_limit_at_100(monkeypatch):
    """limit 이 100 을 초과하면 100 으로 캡핑된다."""
    cur = _list_jobs_client(monkeypatch)
    gw.list_jobs(limit=500, authorization=None, x_user_id=None)
    _, kwargs_params = cur.execute.call_args
    # execute(sql, (user_id, limit)) — 두 번째 인자가 캡핑된 limit
    assert cur.execute.call_args[0][1][1] == 100


def test_list_jobs_passes_limit_under_100_unchanged(monkeypatch):
    """limit 이 100 이하면 그대로 전달된다."""
    cur = _list_jobs_client(monkeypatch)
    gw.list_jobs(limit=50, authorization=None, x_user_id=None)
    assert cur.execute.call_args[0][1][1] == 50


def test_list_jobs_default_limit_is_20(monkeypatch):
    """기본 limit 은 20 이다."""
    cur = _list_jobs_client(monkeypatch)
    gw.list_jobs(authorization=None, x_user_id=None)
    assert cur.execute.call_args[0][1][1] == 20


# ---------------------------------------------------------------------------
# P2-15: debug_engines()
# ---------------------------------------------------------------------------

def test_debug_engines_404_when_dev_debug_off(monkeypatch):
    """DEV_DEBUG=0 이면 404."""
    monkeypatch.setattr(gw, "DEV_DEBUG", False)
    with pytest.raises(HTTPException) as e:
        gw.debug_engines()
    assert e.value.status_code == 404


def test_debug_engines_returns_engine_health(monkeypatch):
    """DEV_DEBUG=1 이면 각 엔진의 헬스 체크 결과를 반환한다."""
    monkeypatch.setattr(gw, "DEV_DEBUG", True)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"status": "ok"}
    mock_client = MagicMock()
    mock_client.__enter__ = lambda s: mock_client
    mock_client.__exit__ = lambda s, *a: None
    mock_client.get.return_value = mock_resp
    monkeypatch.setattr(gw.httpx, "Client", lambda **kw: mock_client)
    out = gw.debug_engines()
    assert "engine-analysis" in out
    assert "engine-prescription" in out
    assert out["engine-analysis"]["reachable"] is True
    assert out["engine-analysis"]["status_code"] == 200


def test_debug_engines_handles_unreachable_engine(monkeypatch):
    """엔진이 다욐 reachable=False, error 메시지를 반환한다."""
    monkeypatch.setattr(gw, "DEV_DEBUG", True)
    mock_client = MagicMock()
    mock_client.__enter__ = lambda s: mock_client
    mock_client.__exit__ = lambda s, *a: None
    mock_client.get.side_effect = ConnectionError("refused")
    monkeypatch.setattr(gw.httpx, "Client", lambda **kw: mock_client)
    out = gw.debug_engines()
    assert out["engine-analysis"]["reachable"] is False
    assert "error" in out["engine-analysis"]
