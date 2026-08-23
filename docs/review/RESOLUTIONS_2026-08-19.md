# 리뷰 지적 해결 기록 — 2026-08-19 후속

> 대상: [`REVIEW_FINDINGS_2026-08-19.md`](./REVIEW_FINDINGS_2026-08-19.md) 의 미해결 항목.
> 각 항목은 **코드 변경 파일**과 **검증 방법**을 함께 적는다. 검증: 단위 테스트 96건 통과, TypeScript `tsc --noEmit` 클린, `node --check next.config.mjs` 통과.

| # | 항목 | 상태 | 변경 파일 | 비고 |
|---|---|---|---|---|
| P1-1 | SW Supabase `PUT` NetworkOnly 누락 | ✅ 해결 | [`apps/webapp-next/next.config.mjs`](../../apps/webapp-next/next.config.mjs) | `/api`·`*.supabase.co` 양쪽에 PUT/DELETE NetworkOnly 추가 |
| P1-2 | 절대 `NEXT_PUBLIC_AI_API_BASE` 와 SW 상대 패턴 불일치 | ✅ 해결 | [`apps/webapp-next/next.config.mjs`](../../apps/webapp-next/next.config.mjs) | `url.pathname.startsWith("/api/")` 함수 패턴으로 교차 오리진 차단 |
| P2-1 | `requirements-dev.txt` 미핀·누락 | ✅ 해결 | [`requirements-dev.txt`](../../requirements-dev.txt) | 전 의존 핀 고정 + `psycopg-pool==3.2.4`·`pyjwt==2.10.1` 추가 |
| P2-2 | `redis` 의존 선반영 | ✅ 해결 | [`services/gateway/requirements.txt`](../../services/gateway/requirements.txt) | 미사용 `redis==5.2.1` 제거(큐는 Postgres SKIP LOCKED) |
| N1 | presign/analyze `job_id` 분리 | ✅ 해결 | [`services/gateway/app/main.py`](../../services/gateway/app/main.py), [`apps/webapp-next/src/lib/api.ts`](../../apps/webapp-next/src/lib/api.ts) | `/analyze` 가 `image_key` 의 `job_id` 재사용 + 명시 `job_id` 는 키와 일치 검증. 웹앱이 presign `job_id` 를 되돌려 본냄 |
| N2 | `authHeaders()` 무인증 진행 | ✅ 해결 | [`apps/webapp-next/src/lib/api.ts`](../../apps/webapp-next/src/lib/api.ts) | 토큰 부재 시 `AuthRequiredError("로그인이 필요합니다")` 즉시 throw |
| N4 | `finish_ok` 재처리 미커버 | ✅ 해결 | [`tests/integration/test_pipeline.py`](../../tests/integration/test_pipeline.py) | `test_finish_ok_reprocess_dedup` 추가 — 같은 잡 2회 처리 시 prescriptions 1건 단언 |
| C5-2 | 배포 워크플로 SERVICE 분기 | ✅ 해결 | [`deploy-built-service.yml`](../../.github/workflows/deploy-built-service.yml), [`build-and-deploy-engine.yml`](../../.github/workflows/build-and-deploy-engine.yml) | `dorny/paths-filter` + matrix 로 변경 경로 감지 → 해당 서비스만 빌드/배포. `packages/**` 변경 시 양쪽 모두 배포. `workflow_dispatch` 는 전체 배포 |

## 미해결(후속 작업)

| # | 항목 | 이유 |
|---|---|---|
| P1-3 | presigned E2E·RLS 검증 테스트 | 1~2일 공수. Phase 4 완료 조건 |
| D4 | 실제 믹스 config(`config/mixes.json`) | 도메인 의존. prod fail-fast **배포 블로커** |
| N3·N5 | placeholder·인메모리 레이트리밋 | N3 조치 불필요, N5 는 Phase 5 로드맵 |
| P2-3·P2-4 | docs 옛 경로·제거 예정 자산 | 진행 중 |

## 검증

- `python -m pytest tests -q --ignore=tests/integration` → **96건 통과**.
- `cd apps/webapp-next && npx tsc --noEmit` → **에러 0건**.
- `node --check apps/webapp-next/next.config.mjs` → **통과**.
- 통합 테스트(P1-3·N4 의 DB 경로)는 `DATABASE_URL` 주입 환경(CI postgres 서비스)에서 실행.
