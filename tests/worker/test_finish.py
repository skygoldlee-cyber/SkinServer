"""
P1-12: worker finish_ok() / finish_err() / requeue() 단위 테스트.
DB 커서를 mock 하여 SQL 호출과 커밋/이벤트 기록을 검증한다.
"""
import json
import uuid
from unittest.mock import MagicMock, call
import pytest
from tests._util import load

w = load("worker", "worker")


@pytest.fixture
def mock_db(monkeypatch):
    """DB 연결과 커서를 mock 한다."""
    cur = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value.__enter__ = lambda s: cur
    conn.cursor.return_value.__exit__ = lambda s, *a: None
    conn.__enter__ = lambda s: conn
    conn.__exit__ = lambda s, *a: None
    monkeypatch.setattr(w, "db", lambda: conn)
    return conn, cur


@pytest.fixture
def mock_event(monkeypatch):
    """event() 를 mock 하여 호출을 기록한다."""
    calls = []
    monkeypatch.setattr(w, "event", lambda jid, stage, detail=None: calls.append((jid, stage, detail)))
    return calls


# ---------------------------------------------------------------------------
# finish_ok()
# ---------------------------------------------------------------------------

def test_finish_ok_inserts_prescription_and_updates_job(mock_db, mock_event):
    """finish_ok 가 prescriptions INSERT + jobs UPDATE 를 한 트랜잭션으로 실행한다."""
    conn, cur = mock_db
    job_id = uuid.uuid4()
    user_id = uuid.uuid4()
    result = {
        "prescription": {
            "grade": "양호",
            "prescription_ratio_pct": 0.0,
            "score": 85.5,
            "selected_mixes": [{"mix": "M01", "reason": "base"}],
            "pcr_mixes": [],
            "per_metric": {"redness": {"score": 90, "grade": "양호", "ratio_pct": 0.0, "source": "cv"}},
        }
    }
    w.finish_ok(job_id, user_id, result)

    # 2개의 SQL 이 실행되어야 한다
    assert cur.execute.call_count == 2

    # 첫 번째: prescriptions INSERT (ON CONFLICT DO NOTHING)
    insert_call = cur.execute.call_args_list[0]
    assert "INSERT INTO prescriptions" in insert_call[0][0]
    assert "ON CONFLICT (job_id) DO NOTHING" in insert_call[0][0]
    params = insert_call[0][1]
    assert params[0] == str(job_id)
    assert params[1] == str(user_id)
    assert params[2] == "양호"
    assert params[3] == 0.0
    assert params[4] == 85.5
    assert json.loads(params[5]) == [{"mix": "M01", "reason": "base"}]
    assert json.loads(params[6]) == []
    assert json.loads(params[7])["redness"]["score"] == 90

    # 두 번째: jobs UPDATE
    update_call = cur.execute.call_args_list[1]
    assert "UPDATE jobs SET status='done'" in update_call[0][0]
    assert update_call[0][1][1] == str(job_id)

    # 커밋이 한 번만 호출되어야 한다 (원자성)
    conn.commit.assert_called_once()

    # 이벤트가 2개 기록되어야 한다
    assert len(mock_event) == 2
    assert mock_event[0] == (job_id, "prescribed", {"ok": True})
    assert mock_event[1] == (job_id, "done", {"ok": True})


def test_finish_ok_handles_empty_prescription(mock_db, mock_event):
    """prescription 이 비어있어도 finish_ok 가 동작한다."""
    conn, cur = mock_db
    job_id = uuid.uuid4()
    w.finish_ok(job_id, None, {})

    assert cur.execute.call_count == 2
    insert_call = cur.execute.call_args_list[0]
    params = insert_call[0][1]
    assert params[0] == str(job_id)
    assert params[1] is None  # user_id None
    assert params[2] is None  # grade
    assert params[3] is None  # ratio_pct
    assert params[4] is None  # score
    assert json.loads(params[5]) is None  # selected_mixes
    assert json.loads(params[6]) is None  # pcr_mixes
    assert json.loads(params[7]) is None  # per_metric


def test_finish_ok_serializes_result_as_json(mock_db, mock_event):
    """jobs.result 에 result 전체가 JSON 으로 직렬화된다."""
    conn, cur = mock_db
    job_id = uuid.uuid4()
    result = {"score": 85.5, "metrics": {"redness": 90}, "prescription": {"grade": "양호"}}
    w.finish_ok(job_id, uuid.uuid4(), result)

    update_call = cur.execute.call_args_list[1]
    result_json = update_call[0][1][0]
    assert json.loads(result_json) == result


# ---------------------------------------------------------------------------
# finish_err()
# ---------------------------------------------------------------------------

def test_finish_err_updates_job_and_records_event(mock_db, mock_event):
    """finish_err 가 jobs.status='error' 로 업데이트하고 이벤트를 기록한다."""
    conn, cur = mock_db
    job_id = uuid.uuid4()
    w.finish_err(job_id, "engine timeout")

    cur.execute.assert_called_once()
    sql, params = cur.execute.call_args[0]
    assert "UPDATE jobs SET status='error'" in sql
    assert params == ("engine timeout", str(job_id))
    conn.commit.assert_called_once()

    assert len(mock_event) == 1
    assert mock_event[0] == (job_id, "error", {"error": "engine timeout"})


def test_finish_err_with_empty_error(mock_db, mock_event):
    """error 가 빈 문자열이어도 동작한다."""
    conn, cur = mock_db
    job_id = uuid.uuid4()
    w.finish_err(job_id, "")

    cur.execute.assert_called_once()
    assert cur.execute.call_args[0][1][0] == ""
    conn.commit.assert_called_once()
    assert mock_event[0][2]["error"] == ""


# ---------------------------------------------------------------------------
# requeue()
# ---------------------------------------------------------------------------

def test_requeue_updates_job_and_records_event(mock_db, mock_event):
    """requeue 가 jobs.status='queued' 로 업데이트하고 이벤트를 기록한다."""
    conn, cur = mock_db
    job_id = uuid.uuid4()
    w.requeue(job_id, 2, "connection reset")

    cur.execute.assert_called_once()
    sql, params = cur.execute.call_args[0]
    assert "UPDATE jobs SET status='queued'" in sql
    assert params == (str(job_id),)
    conn.commit.assert_called_once()

    assert len(mock_event) == 1
    assert mock_event[0] == (job_id, "requeued", {"attempts": 2, "error": "connection reset"})


def test_requeue_preserves_attempts_in_event(mock_db, mock_event):
    """requeue 이벤트에 attempts 가 정확히 기록된다."""
    conn, cur = mock_db
    job_id = uuid.uuid4()
    w.requeue(job_id, 0, "first failure")
    assert mock_event[0][2]["attempts"] == 0

    mock_event.clear()
    w.requeue(job_id, 4, "last retry")
    assert mock_event[0][2]["attempts"] == 4


def test_requeue_does_not_touch_error_column(mock_db, mock_event):
    """requeue 는 error 컬럼을 업데이트하지 않는다 (SQL 에 error= 없음)."""
    conn, cur = mock_db
    job_id = uuid.uuid4()
    w.requeue(job_id, 1, "some error")

    sql = cur.execute.call_args[0][0]
    assert "error=" not in sql
    assert "status='queued'" in sql
