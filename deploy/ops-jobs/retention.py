#!/usr/bin/env python3
# =============================================================
# retention.py — 이미지/PII 보존·삭제 잡 (①)
#
#  무엇을:
#   1) 리포트 생성이 끝난 Job 의 "원본" 이미지를 KEEP_ORIGINAL_HOURS 후 삭제
#      (파생 결과/리포트는 유지). 민감정보 노출 창을 최소화.
#   2) 미완료 업로드(status 가 uploaded/pending 인데 오래된 것)를
#      INCOMPLETE_TTL_HOURS 후 정리(스토리지 객체 + 행 만료 표시).
#
#  어떻게:
#   - Supabase service_role 로 Storage/DB 접근(RLS 우회 — 서버 전용).
#   - 실제 테이블/컬럼명은 환경변수로 주입(스키마에 맞게 교체). 기본값은 예시.
#   - 기본 DRY_RUN=1 (삭제 안 하고 대상만 로깅). 확인 후 DRY_RUN=0 로 실행.
#
#  실행(예: 매일 03:10, crontab.example 참고):
#   docker compose --env-file .env run --rm \
#     -e DRY_RUN=0 worker python /app/followup-P1/retention.py
#   (worker 이미지에 supabase-py 가 있다고 가정. 없으면: pip install supabase)
#
#  ★ 로그에 객체 경로/토큰을 남기지 않도록 log-scrub.py 필터와 함께 쓸 것.
# =============================================================
import os
import sys
import logging
from datetime import datetime, timedelta, timezone

log = logging.getLogger("retention")

# ---- 설정(환경변수) --------------------------------------------------------
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SERVICE_KEY  = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
BUCKET       = os.environ.get("RETENTION_BUCKET") or os.environ.get("STORAGE_BUCKET", "skin-images")

KEEP_ORIGINAL_HOURS   = int(os.environ.get("KEEP_ORIGINAL_HOURS", "24"))
INCOMPLETE_TTL_HOURS  = int(os.environ.get("INCOMPLETE_TTL_HOURS", "24"))
DRY_RUN               = os.environ.get("DRY_RUN", "1") != "0"
BATCH                 = int(os.environ.get("RETENTION_BATCH", "500"))

# 스키마 매핑 — 실제 스키마(deploy/db/migrations/0001_init.sql) 기본값.
#  jobs: id, user_id, kind, status(queued/processing/done/error), image_key, ...
#  ※ 별도의 original_deleted 플래그는 없다 — 삭제는 image_key 를 NULL 로 지워 표현한다.
#    (삭제 후 행의 image_key 가 NULL 이면 이미 원본이 제거된 것으로 간주.)
T_JOBS        = os.environ.get("T_JOBS", "jobs")
C_ID          = os.environ.get("C_JOB_ID", "id")
C_USER        = os.environ.get("C_USER", "user_id")
C_STATUS      = os.environ.get("C_STATUS", "status")
C_CREATED     = os.environ.get("C_CREATED", "created_at")
C_ORIG_KEY    = os.environ.get("C_ORIG_KEY", "image_key")      # storage object 경로
STATUS_DONE   = os.environ.get("STATUS_DONE", "done")
# worker 큐 상태: queued(대기)/processing(처리중) — 오래 머문 것을 미완료로 본다.
STATUS_OPEN   = os.environ.get("STATUS_OPEN", "queued,processing").split(",")


def _client():
    try:
        from supabase import create_client
    except ImportError:
        log.error("supabase 패키지 없음 → pip install supabase")
        raise
    if not (SUPABASE_URL and SERVICE_KEY):
        log.error("SUPABASE_URL / SUPABASE_SERVICE_KEY 미설정")
        sys.exit(2)
    return create_client(SUPABASE_URL, SERVICE_KEY)


def _iso(hours_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()


def _remove_objects(sb, keys):
    """스토리지 객체 삭제. keys 예: ['<uid>/<job>/original.jpg', ...]"""
    keys = [k for k in keys if k]
    if not keys:
        return 0
    if DRY_RUN:
        log.info("[DRY] storage remove %d개", len(keys))
        return len(keys)
    sb.storage.from_(BUCKET).remove(keys)
    return len(keys)


def purge_completed_originals(sb) -> int:
    """리포트 완료 + 오래됨 + 원본 키가 아직 남아있음 → 원본 삭제 후 image_key NULL 처리."""
    cutoff = _iso(KEEP_ORIGINAL_HOURS)
    rows = (sb.table(T_JOBS)
              .select(f"{C_ID},{C_ORIG_KEY}")
              .eq(C_STATUS, STATUS_DONE)
              .lt(C_CREATED, cutoff)
              .not_.is_(C_ORIG_KEY, "null")   # 원본이 아직 남아있는 행만
              .limit(BATCH)
              .execute()).data or []
    if not rows:
        log.info("완료 원본 삭제 대상 없음")
        return 0
    _remove_objects(sb, [r.get(C_ORIG_KEY) for r in rows])
    if not DRY_RUN:
        for r in rows:
            (sb.table(T_JOBS)
               .update({C_ORIG_KEY: None})     # 삭제됨을 키 제거로 표현
               .eq(C_ID, r[C_ID]).execute())
    log.info("완료 원본 처리 %d건 (dry=%s)", len(rows), DRY_RUN)
    return len(rows)


def purge_incomplete(sb) -> int:
    """미완료 업로드 정리(오래된 queued/processing). 행은 error 로 마감하고 원본 키 제거."""
    cutoff = _iso(INCOMPLETE_TTL_HOURS)
    rows = (sb.table(T_JOBS)
              .select(f"{C_ID},{C_ORIG_KEY}")
              .in_(C_STATUS, STATUS_OPEN)
              .lt(C_CREATED, cutoff)
              .limit(BATCH)
              .execute()).data or []
    if not rows:
        log.info("미완료 정리 대상 없음")
        return 0
    _remove_objects(sb, [r.get(C_ORIG_KEY) for r in rows])
    if not DRY_RUN:
        for r in rows:
            (sb.table(T_JOBS)
               .update({C_STATUS: "error", C_ORIG_KEY: None})
               .eq(C_ID, r[C_ID]).execute())
    log.info("미완료 정리 %d건 (dry=%s)", len(rows), DRY_RUN)
    return len(rows)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    log.info("retention 시작 bucket=%s dry_run=%s", BUCKET, DRY_RUN)
    sb = _client()
    n1 = purge_completed_originals(sb)
    n2 = purge_incomplete(sb)
    log.info("retention 완료: 원본 %d, 미완료 %d", n1, n2)


if __name__ == "__main__":
    main()
