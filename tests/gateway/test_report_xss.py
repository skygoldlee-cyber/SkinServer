"""
P1-11: get_report() XSS 방어 테스트 (별도 파일).
"""
import html
import uuid
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from tests._util import load

gw = load("gateway", "app.main")


def _report_client(monkeypatch, row):
    """get_report 를 테스트하기 위한 헬퍼."""
    monkeypatch.setattr(gw, "require_user", lambda a, b: uuid.UUID("11111111-1111-1111-1111-111111111111"))
    cur = MagicMock()
    cur.fetchone.return_value = row
    conn = MagicMock()
    conn.cursor.return_value.__enter__ = lambda s: cur
    conn.cursor.return_value.__exit__ = lambda s, *a: None
    conn.__enter__ = lambda s: conn
    conn.__exit__ = lambda s, *a: None
    monkeypatch.setattr(gw, "db", lambda: conn)
    return gw


def test_get_report_404_when_job_not_found(monkeypatch):
    """남의 job 이거나 없는 job 이면 404."""
    _report_client(monkeypatch, None)
    with pytest.raises(HTTPException) as e:
        gw.get_report(job_id=uuid.uuid4(), authorization=None, x_user_id=None)
    assert e.value.status_code == 404


def test_get_report_not_ready_returns_status_html(monkeypatch):
    """status != 'done' 이면 준비 안 됨 HTML 을 반환한다."""
    _report_client(monkeypatch, {"status": "processing", "result": None})
    out = gw.get_report(job_id=uuid.uuid4(), authorization=None, x_user_id=None)
    assert "아직 준비 안 됨" in out.body.decode()
    assert "status=processing" in out.body.decode()


def test_get_report_escapes_xss_in_status(monkeypatch):
    """status 에 XSS 페이로드가 있어도 이스케이프된다."""
    payload = "<script>alert(1)</script>"
    _report_client(monkeypatch, {"status": payload, "result": None})
    out = gw.get_report(job_id=uuid.uuid4(), authorization=None, x_user_id=None)
    body = out.body.decode()
    assert payload not in body
    assert html.escape(payload) in body


def test_get_report_escapes_xss_in_metric_names(monkeypatch):
    """per_metric 키에 XSS 페이로드가 있어도 이스케이프된다."""
    payload = "<script>alert(1)</script>"
    result = {
        "prescription": {
            "grade": "양호",
            "prescription_ratio_pct": 0.0,
            "per_metric": {payload: {"grade": "양호", "ratio_pct": 0.0, "source": "cv"}},
            "selected_mixes": [],
        }
    }
    _report_client(monkeypatch, {"status": "done", "result": result})
    out = gw.get_report(job_id=uuid.uuid4(), authorization=None, x_user_id=None)
    body = out.body.decode()
    assert payload not in body
    assert html.escape(payload) in body


def test_get_report_escapes_xss_in_mix_names(monkeypatch):
    """selected_mixes 의 mix 이름에 XSS 페이로드가 있어도 이스케이프된다."""
    payload = "<img src=x onerror=alert(1)>"
    result = {
        "prescription": {
            "grade": "양호",
            "prescription_ratio_pct": 0.0,
            "per_metric": {},
            "selected_mixes": [{"mix": payload, "reason": "base"}],
        }
    }
    _report_client(monkeypatch, {"status": "done", "result": result})
    out = gw.get_report(job_id=uuid.uuid4(), authorization=None, x_user_id=None)
    body = out.body.decode()
    assert payload not in body
    assert html.escape(payload) in body


def test_get_report_escapes_xss_in_grade_and_ratio(monkeypatch):
    """grade / ratio_pct 에 XSS 페이로드가 있어도 이스케이프된다."""
    payload1 = "<script>alert(1)</script>"
    payload2 = "<script>alert(2)</script>"
    result = {
        "prescription": {
            "grade": payload1,
            "prescription_ratio_pct": payload2,
            "per_metric": {},
            "selected_mixes": [],
        }
    }
    _report_client(monkeypatch, {"status": "done", "result": result})
    out = gw.get_report(job_id=uuid.uuid4(), authorization=None, x_user_id=None)
    body = out.body.decode()
    assert payload1 not in body
    assert payload2 not in body
    assert html.escape(payload1) in body
    assert html.escape(payload2) in body


def test_get_report_done_returns_full_html(monkeypatch):
    """status='done' 이면 완전한 리포트 HTML 을 반환한다."""
    result = {
        "prescription": {
            "grade": "양호",
            "prescription_ratio_pct": 0.0,
            "per_metric": {"redness": {"grade": "양호", "ratio_pct": 0.0, "source": "cv"}},
            "selected_mixes": [{"mix": "M01", "reason": "base"}],
        }
    }
    _report_client(monkeypatch, {"status": "done", "result": result})
    out = gw.get_report(job_id=uuid.uuid4(), authorization=None, x_user_id=None)
    body = out.body.decode()
    assert "SkinLens 리포트" in body
    assert "양호" in body
    assert "M01" in body
    assert "<table" in body
