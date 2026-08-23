# architecture/ — 다리(적합성) + 감사 계층

이 폴더는 **왜/무엇을**을 담습니다(SkinLens 관점의 적합성 판단 + 운영 아키텍처 감사).
실제 배선된 **설정/코드**는 `docs/` 밖의 실물에 있습니다 — `deploy/`(compose·nginx·caddy·scripts·supabase·ops-jobs)·`.github/workflows/`(CD)·`services/`·`apps/`.

> 저장소 전체 구조는 루트 [`../../README.md`](../../README.md), 문서 인덱스는 [`../README.md`](../README.md),
> 옛 문서세트(`SkinServer`) → 현재 경로의 정본 대응표는 [`../../MIGRATION.md`](../../MIGRATION.md) 참고.

## 이 폴더의 문서

| 파일 | 무엇 |
|---|---|
| `SkinLens_서버구성_적합성_검토.md` | 다리: 범용 서버 가이드가 4표면(홈·개발자·앱(PWA)·API)+엔진 2개+Supabase에 맞는지 §0~9 + 부록 A/B/C |
| `00_README.md` | 이 문서 — 감사 계층 안내 + 배선 반영 요약 |
| `01_SkinLens_운영아키텍처_최종리뷰.md` | 실제 설정/코드 기준 감사 — ①구조 ②보안 ③장애 ④개선 ⑤P0/P1/P2 |
| `02_PATCH_NOTES_P0_P1.md` | 리뷰에서 도출한 **P0 4건 + P1(flock)**을 어디에·어떻게 반영했나 + 검증 스모크 |
| `03_DB_MIGRATION_ROLLBACK.md` | 런북 — "코드 롤백 ≠ 스키마 롤백" · expand-contract 규칙 |
| `04_3Tier_Vercel_Supabase_AIServer_설계.md` | ⭐ 목표 구조 — Vercel(웹/PWA) + Supabase(데이터·인증·스토리지) + AI Server(FastAPI·Docker·GPU) 3분할 재설계 정본 |
| `05_3Tier_이전_작업계획.md` | 04 설계를 실행 단위로 분해한 작업계획 — Phase 1~6·상태 스냅샷 |
| `SkinLens_서버구축_아키텍처_장단점_비교.md` | 3-Tier 선택 근거 — 단일 서버 vs 전통적 3-Tier vs Vercel+Supabase+AI Server 등 5개 구조 비교 |
| `엔진_baseline_교체_가이드.md` | 엔진 baseline(OpenCV/규칙) → ML/GAN 교체 지점 가이드 |

> 후속 백로그(우선 3개 반영 위치 포함)는 이 폴더가 아니라 [`../roadmap/04_후속보완_로드맵.md`](../roadmap/04_후속보완_로드맵.md)로 이동했습니다.

## 이 리뷰가 실물 배선에 남긴 변경(요약)

문서(여기 `architecture/`)와 배선(`deploy/`·`.github/workflows/`)의 분리:

- **`deploy/compose/`·`deploy/caddy/`** — `compose.gpu.yml`·`compose.tls.yml`·`Caddyfile`(신규)
- **`deploy/scripts/`·`deploy/nginx/`·(루트)`.gitignore`** — `deploy.sh`·`nginx/*`(교체)
- **`deploy/supabase/policies/`** — `0001_rls_and_storage.sql`(신규)
- **`.github/workflows/`** — `deploy-built-service.yml`(마이그레이션 스텝 추가)

적용 순서·검증은 `02_PATCH_NOTES_P0_P1.md` 참고.
