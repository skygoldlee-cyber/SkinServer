"""
Report Worker — 큐 소비 + 안정성(재시도/리퍼/데드레터) + 단계 관측 + 처방 기록.
분석 엔진 → 처방 엔진 호출 후 결과를 jobs.result 와 prescriptions 에 기록.
엔진은 enginenet(internal)에서만 호출(Case A).

보완 반영:
  [안정] 엔진 호출 재시도+backoff, processing 리퍼(멈춘 job 회수), attempts/데드레터.
  [도메인] prescriptions 테이블 기록 + status=prescribed→done.
  [관측] 구조적 JSON 로깅(job_id/stage/attempt).
"""
import os, time, json
import httpx, psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from logging_setup import get_logger
from storage import get_storage

os.environ.setdefault("SVC_NAME", "worker")
log = get_logger("worker")
storage = get_storage()

DATABASE_URL = os.environ["DATABASE_URL"]
STORAGE_DIR = os.environ.get("STORAGE_DIR", "/data/storage")
EA = os.environ["ENGINE_ANALYSIS_URL"].rstrip("/")
EP = os.environ["ENGINE_PRESCRIPTION_URL"].rstrip("/")
POLL = float(os.environ.get("POLL_INTERVAL", "2"))
STAGE_DELAY = float(os.environ.get("STAGE_DELAY_SEC", "0"))
MAX_ATTEMPTS = int(os.environ.get("MAX_ATTEMPTS", "3"))
STALE_SEC = int(os.environ.get("STALE_SECONDS", "120"))     # processing 이 이 시간 넘으면 회수
ENGINE_RETRIES = int(os.environ.get("ENGINE_RETRIES", "2")) # 엔진 호출 재시도 횟수
HEARTBEAT = "/tmp/worker_alive"

# (2-2) DB 커넥션 풀 — 잡 하나 처리에 이벤트마다 psycopg.connect 를 새로 열지 않고 재사용한다.
# claimed → validated → analysis:request → … → done 까지 8~9회 연결을 풀에서 빌려 쓴다.
_pool = ConnectionPool(
    DATABASE_URL,
    min_size=int(os.environ.get("DB_POOL_MIN", "2")),
    max_size=int(os.environ.get("DB_POOL_MAX", "5")),
    kwargs={"row_factory": dict_row},
)

# presigned 전환 후 실질 방어선(P0): 브라우저가 Supabase Storage 에 직접 PUT 하고 gateway 는
# image_key 만 받으므로, gateway 의 validate_image() 가 하던 magic-byte 검사가 서버에서 증발한다.
# worker 가 원본 fetch 직후·엔진 호출 전에 파일 시그니처를 재검증한다(4.6).
_MAGIC = {".jpg": [b"\xff\xd8\xff"], ".png": [b"\x89PNG\r\n\x1a\n"], ".webp": [b"RIFF"]}


def _is_webp(head: bytes) -> bool:
    return len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP"


def validate_image_bytes(path: str) -> str:
    """
    다운로드된 원본의 확장자와 실제 매직 바이트가 일치하는지 재검증.
    일치하면 확장자를, 아니면 ValueError 를 던진다(영구 오류 → 데드레터, 재큐 없음).
    """
    ext = os.path.splitext(path)[1].lower()
    if ext not in _MAGIC:
        raise ValueError(f"지원하지 않는 이미지 확장자: {ext or '(없음)'}")
    with open(path, "rb") as f:
        head = f.read(16)
    ok = _is_webp(head) if ext == ".webp" else any(head.startswith(s) for s in _MAGIC[ext])
    if not ok:
        raise ValueError("이미지 내용이 확장자와 불일치(magic-byte 재검증 실패)")
    return ext


def db():
    """풀에서 커넥션을 빌려 쓰는 컨텍스트매니저를 돌려준다. 기존 `with db() as conn` 패턴 유지."""
    return _pool.connection()


def event(job_id, stage, detail=None):
    try:
        with db() as conn, conn.cursor() as cur:
            cur.execute("INSERT INTO job_events (job_id, stage, detail) VALUES (%s,%s,%s)",
                        (str(job_id), stage, json.dumps(detail) if detail is not None else None))
            conn.commit()
    except Exception:
        log.exception("event 기록 실패", extra={"job_id": str(job_id), "stage": stage})


def reap_stale():
    """멈춘 processing 회수: attempts<MAX 면 재큐, 아니면 데드레터(error)."""
    with db() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE jobs SET status = CASE WHEN attempts >= %s THEN 'error' ELSE 'queued' END,
                            error  = CASE WHEN attempts >= %s THEN 'max attempts (stale reap)' ELSE error END,
                            updated_at = now()
            WHERE status='processing' AND updated_at < now() - (%s || ' seconds')::interval
            RETURNING id, status, attempts
            """, (MAX_ATTEMPTS, MAX_ATTEMPTS, STALE_SEC))
        rows = cur.fetchall(); conn.commit()
    for r in rows:
        event(r["id"], "reaped", {"to": r["status"], "attempts": r["attempts"]})
        log.warning("stale 회수", extra={"job_id": str(r["id"]), "stage": r["status"]})


def claim_one():
    """queued 하나를 원자적으로 processing 으로(+attempts)."""
    with db() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE jobs SET status='processing', attempts=attempts+1, updated_at=now()
            WHERE id = (SELECT id FROM jobs WHERE status='queued'
                        ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1)
            RETURNING *
            """)
        row = cur.fetchone(); conn.commit()
        return row


def is_retryable(exc) -> bool:
    """
    일시적 오류(재큐 대상) vs 영구 오류(데드레터) 구분.
      재시도 가치 있음: 엔진 연결 실패/타임아웃, 엔진 5xx — 다음 시도에 회복 가능.
      영구: 4xx(계약 위반·잘못된 입력), ValueError 등 우리 검증 — 재시도해도 동일.
    """
    if isinstance(exc, (httpx.TransportError, httpx.TimeoutException)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


def call_engine(fn, *, job_id, stage):
    """엔진 호출 재시도+backoff 래퍼. fn() 이 응답 json 반환."""
    last = None
    for attempt in range(1, ENGINE_RETRIES + 2):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last = e
            log.warning("엔진 호출 실패, 재시도", extra={"job_id": str(job_id), "stage": stage, "attempt": attempt})
            time.sleep(min(2 ** attempt, 8))
    raise last


def process(job):
    jid = job["id"]
    inputs = job.get("inputs") or {}

    # 스토리지 추상화로 원본 위치 확인. supabase 백엔드 미배선이면 여기서 예외가 나
    # 조용히 분석을 건너뛰는 무증상 저하를 막는다(예외 → job error 로 가시화).
    image_key = job.get("image_key")
    image_path = storage.resolve_local(image_key) if image_key else None

    try:
        analysis = None
        if image_path:
            # (4.6 P0) presigned 경로는 gateway 가 바이트를 안 본다 — 엔진 호출 전에
            # 실제 매직 바이트를 재검증한다. 위조 파일(확장자만 이미지)이면 ValueError 로
            # 던져 데드레터시켜 엔진 도달을 차단한다.
            validate_image_bytes(image_path)
            event(jid, "validated", {"image_key": image_key, "via": "magic-byte"})
            event(jid, "analysis:request", {"engine": EA, "image_key": image_key})
            if STAGE_DELAY: time.sleep(STAGE_DELAY)
            def _an():
                with open(image_path, "rb") as f, httpx.Client(timeout=60) as c:
                    r = c.post(f"{EA}/score", files={"image": (os.path.basename(image_path), f, "application/octet-stream")})
                    r.raise_for_status(); return r.json()
            analysis = call_engine(_an, job_id=jid, stage="analysis")
            event(jid, "analysis:result", analysis)
        else:
            # image_key 는 있는데 로컬에서 못 찾음(retention 삭제 등) vs 애초에 이미지 없음 구분.
            reason = "원본 없음(만료/삭제 가능)" if image_key else "이미지 없음(설문/PCR 전용)"
            event(jid, "analysis:skipped", {"reason": reason, "image_key": image_key})

        payload = {}
        if analysis is not None: payload["analysis"] = analysis
        if "survey" in inputs: payload["survey"] = inputs["survey"]
        if "pcr" in inputs: payload["pcr"] = inputs["pcr"]
        if not payload:
            raise ValueError("처방 입력 없음(분석/설문/PCR 중 최소 1종 필요)")

        event(jid, "prescription:request", {"engine": EP, "inputs": list(payload.keys())})
        if STAGE_DELAY: time.sleep(STAGE_DELAY)
        def _pr():
            with httpx.Client(timeout=60) as c:
                r = c.post(f"{EP}/prescribe", json=payload); r.raise_for_status(); return r.json()
        prescription = call_engine(_pr, job_id=jid, stage="prescription")
        event(jid, "prescription:result", prescription)
        return {"analysis": analysis, "prescription": prescription}
    finally:
        # (1-1) supabase 백엔드가 남긴 임시파일을 반드시 정리한다.
        # read_only + tmpfs(["/tmp"]) + mem_limit 환경에서 누적되면 워커가 OOM 으로 죽는다.
        # local 백엔드(실제 볼륨 원본)는 삭제하면 안 되므로 is_temp 플래그로 구분한다.
        if image_path and getattr(storage, "is_temp", False):
            try:
                os.unlink(image_path)
            except OSError:
                pass


def finish_ok(job_id, user_id, result):
    """
    처방 기록 + 상태 종료를 '한 트랜잭션'으로 처리(원자성).
    이전엔 prescriptions insert → status=prescribed → status=done 이 각기 커밋돼,
    중간 크래시 시 job 이 prescribed 로 영구 정지(리퍼는 processing 만 회수)했다.
    ON CONFLICT(job_id) 로 재처리 시 중복 처방도 막는다.
    """
    prescription = result.get("prescription", {}) or {}
    with db() as conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO prescriptions (job_id, user_id, grade, ratio_pct, score,
                                          selected_mixes, pcr_mixes, per_metric)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (job_id) DO NOTHING""",
            (str(job_id), str(user_id) if user_id else None,
             prescription.get("grade"), prescription.get("prescription_ratio_pct"),
             prescription.get("score"), json.dumps(prescription.get("selected_mixes")),
             json.dumps(prescription.get("pcr_mixes")), json.dumps(prescription.get("per_metric"))))
        cur.execute("UPDATE jobs SET status='done', result=%s, updated_at=now() WHERE id=%s",
                    (json.dumps(result), str(job_id)))
        conn.commit()
    # 이벤트는 로그성(원자성 밖) — 단계 추적용으로 둘 다 남긴다.
    event(job_id, "prescribed", {"ok": True})
    event(job_id, "done", {"ok": True})


def finish_err(job_id, error):
    with db() as conn, conn.cursor() as cur:
        cur.execute("UPDATE jobs SET status='error', error=%s, updated_at=now() WHERE id=%s",
                    (error, str(job_id))); conn.commit()
    event(job_id, "error", {"error": error})


def on_failure(job_id, attempts, exc):
    """처리 실패의 종결 정책(단위 테스트 대상): 일시적+여유 → 재큐, 그 외 → 데드레터."""
    if is_retryable(exc) and (attempts or 0) < MAX_ATTEMPTS:
        requeue(job_id, attempts, str(exc))
        return "requeued"
    finish_err(job_id, str(exc))
    return "error"


def requeue(job_id, attempts, error):
    """
    일시적 오류를 queued 로 되돌려 다음 폴에서 재클레임되게 한다(attempts 유지).
    error 컬럼은 '종료 실패'의 의미라 건드리지 않고, 사유는 이벤트로만 남긴다.
    reap_stale 와 동일한 소진 기준(attempts >= MAX_ATTEMPTS)을 쓴다.
    """
    with db() as conn, conn.cursor() as cur:
        cur.execute("UPDATE jobs SET status='queued', updated_at=now() WHERE id=%s", (str(job_id),))
        conn.commit()
    event(job_id, "requeued", {"attempts": attempts, "error": error})
    log.warning("일시적 오류 — 재큐", extra={"job_id": str(job_id), "attempt": attempts})


def main():
    log.info(f"worker up (poll={POLL}s stale={STALE_SEC}s max_attempts={MAX_ATTEMPTS})")
    tick = 0
    while True:
        open(HEARTBEAT, "w").close()
        if tick % 10 == 0:
            try: reap_stale()
            except Exception: log.exception("reap 실패")
        tick += 1
        try:
            job = claim_one()
        except Exception:
            log.exception("DB 접근 실패, 재시도"); time.sleep(POLL); continue
        if not job:
            time.sleep(POLL); continue
        jid = job["id"]
        log.info("처리 시작", extra={"job_id": str(jid), "attempt": job.get("attempts")})
        event(jid, "claimed", {"attempt": job.get("attempts")})
        try:
            result = process(job)
            finish_ok(jid, job.get("user_id"), result)
            log.info("완료", extra={"job_id": str(jid)})
        except Exception as e:  # noqa: BLE001
            # attempts 는 claim 시 이미 +1 된 값. 일시적 오류이고 아직 여유가 있으면 재큐,
            # 아니면(영구 오류이거나 소진) 데드레터. reap_stale 과 동일 기준.
            outcome = on_failure(jid, job.get("attempts") or 0, e)
            if outcome == "error":
                log.exception("실패(데드레터)", extra={"job_id": str(jid)})


if __name__ == "__main__":
    main()
