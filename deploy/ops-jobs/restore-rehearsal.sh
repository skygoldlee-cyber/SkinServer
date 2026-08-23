#!/usr/bin/env bash
# =============================================================
# restore-rehearsal.sh — 백업 복구 리허설 (③, 스테이징 전용)
#
#  목적: "백업은 있는데 복구는 안 해" 함정 닫기.
#        최신 백업을 버려도 되는 임시 DB 에 복구해고 RPO/RTO 를 측정.
#
#  3-Tier 이후 백업 경로 (Phase 6.3):
#   - 운영 DB = Supabase. 백업은 두 가지:
#       (a) PITR (Pro 플랜): 콘솔에서 특정 시점으로 복원 — 이 스크립트가 안내
#       (b) pg_dump over 연결문자열: pg_backup.sh 가 만든 *.dump 를 복구
#   - 이 스크립트는 (b) pg_dump 산출물 복구 + (a) PITR 은 콘솔 수동 검증 안내.
#
#  전제:
#   - pg_backup.sh 가 Supabase 연결문자열로 덤프 생성 (DATABASE_URL 직접 사용).
#     예: pg_dump "postgresql://postgres:[pw]@db.<ref>.supabase.co:5432/postgres" -Fc -f backup.dump
#   - 복구 대상은 버려도 되는 임시 DB (스테이징 또는 새 Supabase 프로젝트).
#
#  안전장치: 운영에서 실행 방지(ENV=production 이면 거부).
#  사용: ENV=staging BACKUP_DIR=~/backups ./restore-rehearsal.sh
#        ENV=staging PITR=1 ./restore-rehearsal.sh   # PITR 절차 안낧만 출력
# =============================================================
set -euo pipefail

ENVN="${ENV:-staging}"
[ "$ENVN" = "production" ] && { echo "거부: 운영에서 실행 금지(스테이징 전용)"; exit 3; }

# ── PITR 경로 안내 (Supabase Pro) ────────────────────────────
if [ "${PITR:-0}" = "1" ]; then
  cat <<'EOF'
== Supabase PITR 복구 리허설 (콘솔 수동 절차) ==
Pro 플랜은 PITR(Point-In-Time Recovery)로 특정 시점 복원이 가능하다.
이 절차는 운영 데이터를 건드리지 않도록 **새 프로젝트/브랜치**에서 수행할 것.

 1. Supabase Dashboard → 대상 프로젝트 → Settings → Backups → PITR.
 2. 복원할 시점 선택(가능 범위는 플랜의 보존 기간 내).
 3. "Restore to new project"(또는 새 브랜치)로 복원 — 운영 덮어쓰기 금지.
 4. 복원 완료까지 소요 시간 = RTO 로 기록.
 5. 복원본에서 스모크 쿼리:
      select count(*) from jobs;
      select count(*) from job_events;
      select count(*) from prescriptions;
 6. Supabase Storage: 삭제 테스트 객체 복원(버전ing/휴지통 정책) 확인.
 7. RPO/RTO 를 restore-rehearsal.md 표에 기록.

RPO 기준: PITR 은 WAL 아카이브 주기에 의해 결정(통상 분 단위).
EOF
  exit 0
fi

# ── pg_dump 복구 경로 (로컬/스테이징 임시 DB) ─────────────────
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups}"
PG_IMAGE="${PG_IMAGE:-postgres:16-alpine}"
TMP_CONT="skinlens_restore_rehearsal"
TMP_PW="rehearsal_pw"
# 실제 스키마(deploy/db/migrations/0001_init.sql)에 맞춘 스모크 쿼리
SMOKE_SQL="${SMOKE_SQL:-select count(*) from jobs; select count(*) from job_events; select count(*) from prescriptions;}"

# 1) 최신 백업 선택 (형식은 환경에 맞게 glob 교체)
latest="$(ls -1t "$BACKUP_DIR"/*.dump "$BACKUP_DIR"/*.sql.gz 2>/dev/null | head -1 || true)"
[ -n "$latest" ] || { echo "백업 없음: $BACKUP_DIR (pg_backup.sh 먼저 실행/경로 확인)"; exit 1; }

# RPO: 백업 파일의 나이(지금 - 파일 mtime)
now=$(date +%s); mt=$(date -r "$latest" +%s); rpo_min=$(( (now - mt) / 60 ))
echo "백업: $latest"
echo "RPO(백업 신선도): ${rpo_min}분 전"

# 2) 임시 postgres 기동
echo "임시 DB 기동…"
docker rm -f "$TMP_CONT" >/dev/null 2>&1 || true
docker run -d --name "$TMP_CONT" -e POSTGRES_PASSWORD="$TMP_PW" "$PG_IMAGE" >/dev/null
for i in $(seq 1 30); do
  docker exec "$TMP_CONT" pg_isready -U postgres >/dev/null 2>&1 && break
  sleep 1
done

# 3) 복구 + RTO 측정
echo "복구 시작…"; t0=$(date +%s)
case "$latest" in
  *.dump)    docker exec -i "$TMP_CONT" pg_restore -U postgres -d postgres --clean --if-exists < "$latest" ;;
  *.sql.gz)  gunzip -c "$latest" | docker exec -i "$TMP_CONT" psql -U postgres -d postgres -q ;;
  *)         echo "알 수 없는 백업 형식: $latest"; exit 2 ;;
esac
t1=$(date +%s); rto_s=$(( t1 - t0 ))
echo "RTO(복구 소요): ${rto_s}초"

# 4) 스모크 검증
echo "스모크 쿼리: $SMOKE_SQL"
if docker exec -i "$TMP_CONT" psql -U postgres -d postgres -tAc "$SMOKE_SQL"; then
  echo "✅ 복구 데이터 접근 성공"
else
  echo "⛔ 스모크 실패 — 복구본 점검 필요"; docker rm -f "$TMP_CONT" >/dev/null; exit 1
fi

# 5) 정리 + 요약
docker rm -f "$TMP_CONT" >/dev/null
echo "────────────────────────"
echo "리허설 요약  RPO=${rpo_min}분  RTO=${rto_s}초  → restore-rehearsal.md 목표치와 대조"
echo "참고: 운영 DB 복구는 Supabase 콘솔 PITR 로 별도 검증(PITR=1 $0 로 절차 확인)."
