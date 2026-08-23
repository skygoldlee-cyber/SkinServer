"""
P2-16: worker main() 루프 / claim_one() / event() 단위 테스트.
"""
import json
import uuid
from unittest.mock import MagicMock, patch, call

import pytest

from tests._util import load

w = load("worker", "worker")


# ---------------------------------------------------------------------------
# 공용 mock 헬퍼
# ---------------------------------------------------------------------------

def _mock_db(monkeypatch, fetchone_val=None, fetchall_val=None):
    """w.db 를 mock 하고 (conn, cur) 를 돌려준다."""
    cur = MagicMock()
    cur.fetchone.return_value = fetchone_val
    cur.fetchall.return_value = fetchall_val or []
    conn = MagicMock()
    conn.cursor.return_value.__enter__ = lambda s: cur
    conn.cursor.return_value.__exit__ = lambda s, *a: None
    conn.__enter__ = lambda s: conn
    conn.__exit__ = lambda s, *a: None
    monkeypatch.setattr(w, "db", lambda: conn)
    return conn, cur


# ---------------------------------------------------------------------------
# claim_one()
# ---------------------------------------------------------------------------

def test_claim_one_returns_row_when_job_available(monkeypatch):
    """queued job 이 있으면 해당 row 를 반환한다."""
    job = {"id": uuid.uuid4(), "user_id": uuid.uuid4(), "status": "processing", "attempts": 1}
    conn, cur = _mock_db(monkeypatch, fetchone_val=job)
    result = w.claim_one()
    assert result == job
    conn.commit.assert_called_once()
    # SQL 이 원자적 UPDATE...RETURNING 패턴인지 확인
    sql = cur.execute.call_args[0][0]
    assert "FOR UPDATE SKIP LOCKED" in sql
    assert "RETURNING" in sql
    assert "status='processing'" in sql


def test_claim_one_returns_none_when_no_job(monkeypatch):
    """queued job 이 없으면 None 을 반환한다."""
    conn, cur = _mock_db(monkeypatch, fetchone_val=None)
    result = w.claim_one()
    assert result is None
    conn.commit.assert_called_once()


def test_claim_one_increments_attempts(monkeypatch):
    """claim 시 attempts 가 +1 되는 SQL 이 실행된다."""
    conn, cur = _mock_db(monkeypatch, fetchone_val=None)
    w.claim_one()
    sql = cur.execute.call_args[0][0]
    assert "attempts=attempts+1" in sql


# ---------------------------------------------------------------------------
# event()
# ---------------------------------------------------------------------------

def test_event_inserts_job_event(monkeypatch):
    """job_events 에 INSERT 하고 commit 한다."""
    conn, cur = _mock_db(monkeypatch)
    jid = uuid.uuid4()
    w.event(jid, "claimed", {"attempt": 1})
    cur.execute.assert_called_once()
    sql, params = cur.execute.call_args[0]
    assert "INSERT INTO job_events" in sql
    assert params[0] == str(jid)
    assert params[1] == "claimed"
    assert params[2] == json.dumps({"attempt": 1})
    conn.commit.assert_called_once()


def test_event_detail_none_stores_null(monkeypatch):
    """detail 이 None 이면 NULL 로 저장한다."""
    conn, cur = _mock_db(monkeypatch)
    w.event(uuid.uuid4(), "done", None)
    _, params = cur.execute.call_args[0]
    assert params[2] is None


def test_event_db_failure_logs_exception_does_not_raise(monkeypatch):
    """DB 예외가 나도 event() 는 예외를 던지지 않고 로그만 남긴다."""
    monkeypatch.setattr(w, "db", lambda: (_ for _ in ()).throw(ConnectionError("down")))
    with patch.object(w.log, "exception") as mock_log:
        w.event(uuid.uuid4(), "claimed")  # 예외 없이 반환돼야 함
        mock_log.assert_called_once()
        assert "event 기록 실패" in mock_log.call_args[0][0]


# ---------------------------------------------------------------------------
# main() 루프
# ---------------------------------------------------------------------------

def _run_main(monkeypatch, stop_after_n_sleeps, jobs=None, process_side_effect=None):
    """
    main() 루프를 time.sleep() 호출 횟수로 제어하는 헬퍼.

    main() 의 제어 흐름:
      - claim_one() → None (job 없음)  → sleep(POLL) → 다음 틱
      - claim_one() → job               → process → finish_ok → 다음 틱 (sleep 없음)
      - claim_one() → 예외               → sleep(POLL) → 다음 틱
      - process()  → 예외               → on_failure → 다음 틱 (sleep 없음)

    stop_after_n_sleeps 번째 sleep 호출에서 KeyboardInterrupt 를 발생시켜 루프를 중단한다.
    반환: mocks dict
    """
    mocks = {
        "reap_stale": MagicMock(),
        "claim_one": MagicMock(),
        "process": MagicMock(),
        "finish_ok": MagicMock(),
        "on_failure": MagicMock(return_value="queued"),
        "event": MagicMock(),
    }

    job_list = list(jobs or [])
    job_iter = iter(job_list)

    def _claim():
        try:
            return next(job_iter)
        except StopIteration:
            return None

    mocks["claim_one"].side_effect = _claim
    mocks["process"].side_effect = process_side_effect or (
        lambda job: {"prescription": {"grade": "양호"}})

    sleep_count = {"n": 0}

    def _sleep_and_stop(*a):
        sleep_count["n"] += 1
        if sleep_count["n"] >= stop_after_n_sleeps:
            raise KeyboardInterrupt

    monkeypatch.setattr(w, "reap_stale", mocks["reap_stale"])
    monkeypatch.setattr(w, "claim_one", mocks["claim_one"])
    monkeypatch.setattr(w, "process", mocks["process"])
    monkeypatch.setattr(w, "finish_ok", mocks["finish_ok"])
    monkeypatch.setattr(w, "on_failure", mocks["on_failure"])
    monkeypatch.setattr(w, "event", mocks["event"])
    monkeypatch.setattr(w.time, "sleep", _sleep_and_stop)

    with patch("builtins.open", MagicMock()):
        with pytest.raises(KeyboardInterrupt):
            w.main()

    return mocks


def test_main_loop_writes_heartbeat(monkeypatch):
    """main() 은 매 틱 heartbeat 파일을 갱신한다 (open 호출)."""
    with patch("builtins.open", MagicMock()) as mock_open:
        monkeypatch.setattr(w, "reap_stale", MagicMock())
        monkeypatch.setattr(w, "claim_one", MagicMock(return_value=None))
        monkeypatch.setattr(w, "event", MagicMock())
        monkeypatch.setattr(w.time, "sleep",
                            lambda *a: (_ for _ in ()).throw(KeyboardInterrupt))
        with pytest.raises(KeyboardInterrupt):
            w.main()
        # heartbeat 파일 열기가 최소 1회 발생
        assert mock_open.called


def test_main_loop_calls_reap_stale_every_10_ticks(monkeypatch):
    """tick % 10 == 0 일 때 reap_stale() 을 호출한다 (tick 0, 10 → 2회)."""
    # job 없이 11틱 돌리면 tick 0 과 tick 10 에서 reap_stale 호출
    mocks = _run_main(monkeypatch, stop_after_n_sleeps=11)
    assert mocks["reap_stale"].call_count == 2


def test_main_loop_processes_job_and_finishes_ok(monkeypatch):
    """job 이 있으면 process → finish_ok 순으로 호출한다."""
    job = {"id": uuid.uuid4(), "user_id": uuid.uuid4(), "attempts": 1}
    # job 1개 소진 후 빈 폴 1회에서 중단
    mocks = _run_main(monkeypatch, stop_after_n_sleeps=1, jobs=[job])
    mocks["process"].assert_called_once_with(job)
    mocks["finish_ok"].assert_called_once()
    assert mocks["finish_ok"].call_args[0][0] == job["id"]


def test_main_loop_emits_claimed_event(monkeypatch):
    """job 클레임 시 'claimed' 이벤트를 기록한다."""
    job = {"id": uuid.uuid4(), "user_id": uuid.uuid4(), "attempts": 1}
    mocks = _run_main(monkeypatch, stop_after_n_sleeps=1, jobs=[job])
    claimed_calls = [c for c in mocks["event"].call_args_list if c[0][1] == "claimed"]
    assert len(claimed_calls) == 1
    assert claimed_calls[0][0][0] == job["id"]


def test_main_loop_calls_on_failure_on_process_error(monkeypatch):
    """process() 가 예외를 던지면 on_failure() 가 호출된다."""
    job = {"id": uuid.uuid4(), "user_id": uuid.uuid4(), "attempts": 1}
    mocks = _run_main(monkeypatch, stop_after_n_sleeps=1, jobs=[job],
                      process_side_effect=ValueError("permanent error"))
    mocks["on_failure"].assert_called_once()
    # on_failure 의 첫 번째 인자는 job id
    assert mocks["on_failure"].call_args[0][0] == job["id"]


def test_main_loop_continues_when_no_job(monkeypatch):
    """job 이 없으면 process/finish_ok 는 호출되지 않고 계속 폴한다."""
    mocks = _run_main(monkeypatch, stop_after_n_sleeps=3)
    mocks["process"].assert_not_called()
    mocks["finish_ok"].assert_not_called()
    # claim_one 은 여러 번 호출됨
    assert mocks["claim_one"].call_count >= 3


def test_main_loop_db_error_continues(monkeypatch):
    """claim_one() 이 예외를 던져도 루프가 중단되지 않고 계속 시도한다."""
    claim_calls = {"n": 0}

    def _failing_claim():
        claim_calls["n"] += 1
        raise ConnectionError("DB down")

    monkeypatch.setattr(w, "reap_stale", MagicMock())
    monkeypatch.setattr(w, "claim_one", _failing_claim)
    monkeypatch.setattr(w, "event", MagicMock())

    sleep_count = {"n": 0}

    def _sleep_and_stop(*a):
        sleep_count["n"] += 1
        if sleep_count["n"] >= 3:
            raise KeyboardInterrupt

    monkeypatch.setattr(w.time, "sleep", _sleep_and_stop)

    with patch("builtins.open", MagicMock()):
        with pytest.raises(KeyboardInterrupt):
            w.main()

    # 3회 sleep → claim_one 도 3회 이상 호출됨
    assert claim_calls["n"] >= 3
