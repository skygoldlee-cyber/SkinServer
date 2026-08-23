"""
통합: gateway /analyze → worker(claim→analysis→prescription) → jobs/job_events/prescriptions.
임시 Postgres + 실제 엔진 서브프로세스에 대해 DB 기록까지 검증.
"""
import os, json, struct, zlib
import psycopg
from psycopg.rows import dict_row
from fastapi.testclient import TestClient
import pytest

from tests._util import load

pytestmark = pytest.mark.integration


def _png(w=8, h=8):
    def ch(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    raw = b''.join(b'\x00' + b'\x50\x70\x90' * w for _ in range(h))
    return (b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
            + ch(b'IDAT', zlib.compress(raw)) + ch(b'IEND', b''))


def _connect(url):
    return psycopg.connect(url, row_factory=dict_row)


def test_analyze_to_prescription_records(database_url, schema, engines, storage_dir):
    os.environ["DATABASE_URL"] = database_url
    os.environ["STORAGE_DIR"] = storage_dir
    os.environ["ENGINE_ANALYSIS_URL"] = engines["analysis"]
    os.environ["ENGINE_PRESCRIPTION_URL"] = engines["prescription"]
    os.environ["AUTO_DDL"] = "0"; os.environ["AUTH_MODE"] = "dev"

    # 1) gateway /analyze (사진 + 설문)
    gw = load("gateway", "app.main")
    client = TestClient(gw.app)
    survey = json.dumps({"skin_type": "sensitive", "sensitivity": {"a": True, "b": True}})
    r = client.post("/analyze",
                    files={"image": ("f.png", _png(), "image/png")},
                    data={"survey": survey})
    assert r.status_code == 202
    jid = r.json()["job_id"]

    with _connect(database_url) as c, c.cursor() as cur:
        cur.execute("SELECT status FROM jobs WHERE id=%s", (jid,))
        assert cur.fetchone()["status"] == "queued"
        cur.execute("SELECT stage FROM job_events WHERE job_id=%s ORDER BY at,id", (jid,))
        assert [x["stage"] for x in cur.fetchall()] == ["uploaded", "queued"]

    # 2) worker: claim → process → finish (main 루프와 동일 순서)
    w = load("worker", "worker")
    job = w.claim_one()
    assert str(job["id"]) == jid and job["attempts"] == 1
    w.event(job["id"], "claimed", {"attempt": job["attempts"]})
    result = w.process(job)
    w.finish_ok(job["id"], job["user_id"], result)

    # 3) 결과 검증
    with _connect(database_url) as c, c.cursor() as cur:
        cur.execute("SELECT status, result FROM jobs WHERE id=%s", (jid,))
        row = cur.fetchone()
        assert row["status"] == "done"
        pres = row["result"]["prescription"]
        assert pres["grade"] and "prescription_ratio_pct" in pres
        # 설문이 민감성 지표를 채웠는지
        assert pres["per_metric"]["sensitivity"]["source"] == "survey"

        cur.execute("SELECT grade, ratio_pct, jsonb_array_length(selected_mixes) AS n "
                    "FROM prescriptions WHERE job_id=%s", (jid,))
        prow = cur.fetchone()
        assert prow and prow["grade"] and prow["n"] >= 1

        cur.execute("SELECT stage FROM job_events WHERE job_id=%s ORDER BY at,id", (jid,))
        stages = [x["stage"] for x in cur.fetchall()]
    for s in ("uploaded", "queued", "claimed", "analysis:request", "analysis:result",
              "prescription:request", "prescription:result", "prescribed", "done"):
        assert s in stages, f"누락 stage: {s}"


def test_finish_ok_reprocess_dedup(database_url, schema, engines, storage_dir):
    """
    N4: 같은 잡을 두 번 finish_ok 처리필→ prescriptions 는 1걸만 남아야 한다.
    ON CONFLICT (job_id) DO NOTHING 재처리 경로의 회귀 가드.
    """
    os.environ["DATABASE_URL"] = database_url
    os.environ["STORAGE_DIR"] = storage_dir
    os.environ["ENGINE_ANALYSIS_URL"] = engines["analysis"]
    os.environ["ENGINE_PRESCRIPTION_URL"] = engines["prescription"]
    os.environ["AUTO_DDL"] = "0"; os.environ["AUTH_MODE"] = "dev"

    # 1) gateway /analyze → 잡 생성
    gw = load("gateway", "app.main")
    client = TestClient(gw.app)
    survey = json.dumps({"skin_type": "sensitive", "sensitivity": {"a": True}})
    r = client.post("/analyze",
                    files={"image": ("f.png", _png(), "image/png")},
                    data={"survey": survey})
    assert r.status_code == 202
    jid = r.json()["job_id"]

    # 2) worker: claim → process → finish (1차)
    w = load("worker", "worker")
    job = w.claim_one()
    assert str(job["id"]) == jid
    w.event(job["id"], "claimed", {"attempt": job["attempts"]})
    result = w.process(job)
    w.finish_ok(job["id"], job["user_id"], result)

    # 3) 동일 잡을 다시 finish_ok (재처리 시나리오)
    w.finish_ok(job["id"], job["user_id"], result)

    # 4) prescriptions 는 1걸만 존재해야 한다
    with _connect(database_url) as c, c.cursor() as cur:
        cur.execute("SELECT count(*) AS n FROM prescriptions WHERE job_id=%s", (jid,))
        assert cur.fetchone()["n"] == 1

        cur.execute("SELECT status, result FROM jobs WHERE id=%s", (jid,))
        row = cur.fetchone()
        assert row["status"] == "done"
        assert row["result"]["prescription"]["grade"]


def test_stale_reaper_requeue_and_deadletter(database_url, schema):
    os.environ["DATABASE_URL"] = database_url
    import uuid
    w = load("worker", "worker")

    # (a) attempts 낮은 stale processing → 재큐
    j1 = str(uuid.uuid4())
    # (b) attempts 높은 stale processing → 데드레터(error)
    j2 = str(uuid.uuid4())
    with _connect(database_url) as c, c.cursor() as cur:
        cur.execute("INSERT INTO jobs (id,kind,status,attempts,updated_at) "
                    "VALUES (%s,'analysis','processing',0, now()-interval '999 seconds')", (j1,))
        cur.execute("INSERT INTO jobs (id,kind,status,attempts,updated_at) "
                    "VALUES (%s,'analysis','processing',%s, now()-interval '999 seconds')",
                    (j2, w.MAX_ATTEMPTS))
        c.commit()

    w.reap_stale()

    with _connect(database_url) as c, c.cursor() as cur:
        cur.execute("SELECT status FROM jobs WHERE id=%s", (j1,))
        assert cur.fetchone()["status"] == "queued"
        cur.execute("SELECT status, error FROM jobs WHERE id=%s", (j2,))
        d = cur.fetchone()
        assert d["status"] == "error" and "max attempts" in (d["error"] or "")
