# P0×4 + P1(flock) 반영 노트

`01_SkinLens_운영아키텍처_최종리뷰.md`에서 도출한 **P0 4건 + 가장 실용적인 P1**을
실제 파일로 반영했습니다. 문서는 여기(`architecture/`)에, 배선된 설정은 `deploy/`·`.github/workflows/`에 있습니다.

## 무엇을 · 어디에

| 항목 | 우선 | 파일(현재 monorepo 경로) | 종류 |
|---|---|---|---|
| GPU 배선 + 동시성 제한 | P0 | `deploy/compose/compose.gpu.yml` | 신규(오버레이) |
| TLS(Caddy 자동 인증서·HSTS) | P0 | `deploy/compose/compose.tls.yml`, `deploy/caddy/Caddyfile` | 신규 |
| ┗ proto 정규화(뒤단 gateway가 https 인지) | P0 | `deploy/nginx/conf.d/00-hardening.conf`, `deploy/nginx/snippets/proxy-common.conf` | 교체 |
| ┗ 업로드 전용 rate-limit 자리 | P0 | `deploy/nginx/conf.d/api.conf` | 교체(주석 예시) |
| RLS + Storage 정책(교차 사용자 차단) | P0 | `deploy/supabase/policies/0001_rls_and_storage.sql` | 신규 |
| 마이그레이션 expand-only 배선 | P0 | `.github/workflows/deploy-built-service.yml` | 교체 |
| ┗ 코드≠스키마 롤백 런북 | P0 | `03_DB_MIGRATION_ROLLBACK.md` | 신규 |
| deploy 직렬화 락(flock) | P1 | `deploy/scripts/deploy.sh` | 교체 |
| ┗ 락 파일 무시 | P1 | (루트) `.gitignore` | 교체 |

핵심 설계: **오버레이는 "그 호스트의 배포 체크아웃에 파일이 있으면"만 적용**됩니다.
`deploy/scripts/deploy.sh`가 `compose.gpu.yml`/`compose.tls.yml` 존재 여부를 보고 자동으로
`-f`로 얹습니다. → 스테이징 WSL엔 두 파일을 두지 않으면 base(CPU·HTTP) 그대로,
운영 VPS엔 두면 GPU·TLS가 켜집니다. `deploy.sh` 호출부는 바뀌지 않습니다.

> 아래 "적용 순서"의 `~/ops/…` 는 **서버에 체크아웃된 배포 루트**(monorepo의 `deploy/`)를 가리킵니다.
> 저장소에서는 그 파일들이 `deploy/…`·`.github/workflows/…` 에 있습니다.

---

## 적용 순서

### 1) 공통(모든 호스트)
- `deploy/scripts/deploy.sh` 교체 → 실행권한: `chmod +x deploy/scripts/deploy.sh`
- (루트) `.gitignore`, `deploy/nginx/conf.d/00-hardening.conf`, `deploy/nginx/conf.d/api.conf`,
  `deploy/nginx/snippets/proxy-common.conf` 교체
- 정합성: `docker compose config >/dev/null` (에러 없어야 함)

### 2) 운영 VPS — GPU
- 사전: NVIDIA 드라이버 + NVIDIA Container Toolkit(`docs/server-setup/windows11_ubuntu_server_setup.md §26`). `nvidia-smi` 확인.
- `deploy/compose/compose.gpu.yml` 을 **운영 VPS의 배포 체크아웃에만** 두기(스테이징 WSL엔 두지 않음).
- 확인: `docker compose … config` 에 engine-* 의 `devices` 예약이 보이면 OK.
- 처리량 튜닝: 초기엔 `WORKER_CONCURRENCY=1`(Job 단위 순차) → VRAM 여유 보며 상향.

### 3) 운영 VPS — TLS
- DNS A레코드가 VPS를 가리키는지 먼저 확인(ACME 통과 조건).
- `deploy/caddy/Caddyfile` 의 도메인/이메일을 실제 값으로 교체.
- `deploy/compose/compose.tls.yml` 을 **운영 VPS의 배포 체크아웃에만** 두기.
  (이때 nginx의 host 80 포트는 `!reset` 으로 비워지고 Caddy가 80/443 소유)
- ★ Compose는 **v2.24+** 필요(`!reset` 태그). `docker compose version` 확인.
- 기동 후: `curl -I https://api.example.com` 에 `strict-transport-security` 헤더 확인.

### 4) Supabase — RLS/Storage
- `deploy/supabase/policies/0001_rls_and_storage.sql` 실행(SQL Editor 또는 마이그레이션).
- ★ 파일 상단의 테이블/컬럼 가정(`profiles/analyses/prescriptions/jobs`, `user_id`)이
  실제 스키마와 다르면 이름만 교체.
- 검증: 파일 하단 "확인 쿼리"로 RLS 활성·정책 존재 확인.
- 앱: 원본 업로드 경로를 `"{user_id}/{job_id}/..."` 규약으로 맞추고,
  클라이언트엔 서버가 **짧은 TTL presigned** 만 발급.

### 5) 마이그레이션 파이프라인
- `.github/workflows/deploy-built-service.yml` 이 gateway/worker 경로 변경 시 트리거되도록
  `on.push.paths` 필터를 걸고(레포별 분리가 아니라 **monorepo 경로 필터**), `SERVICE` 값으로 대상 지정.
- gateway 경로에서만 `alembic upgrade head` 가 deploy **이전** 실행됨(단일 마이그레이터).
- 규칙은 `03_DB_MIGRATION_ROLLBACK.md` — **expand-only·하위호환**만 허용.

---

## 검증 스모크

```bash
# 오버레이 병합 확인(운영 호스트) — deploy/compose 기준
docker compose --env-file deploy/env/.env --env-file deploy/env/.env.images \
  -f deploy/compose/compose.base.yml -f deploy/compose/compose.gpu.yml -f deploy/compose/compose.tls.yml config >/dev/null && echo compose-ok

# GPU 인식(엔진 컨테이너 내부)
docker compose … exec engine-analysis nvidia-smi

# TLS
curl -sI https://api.example.com | grep -i strict-transport-security

# 동시 배포 직렬화(락)
( deploy/scripts/deploy.sh --service engine-analysis     --image ghcr.io/.../analysis:X     --env production --pull & )
( deploy/scripts/deploy.sh --service engine-prescription --image ghcr.io/.../prescription:X --env production --pull & )
wait   # 로그가 섞이지 않고 순서대로 나오면 flock 정상

# RLS: 0001 파일 하단 "확인 쿼리" 를 Supabase SQL Editor 에서 실행
```

---

## 이번 패치에서 의도적으로 뺀 것(후속 P1/P2)

- `.htpasswd` 커밋 중단·bcrypt 재발급·dev IP 화이트리스트 (P1)
- 이미지/PII 보존 잡(cron): 리포트 생성 후 원본 자동 삭제·미완료 정리 (P1)
- 로그 스크러빙(URL/token/PII 미기록) (P1)
- 운영 승인 게이트 필수화·러너 전용 사용자 (P1)
- CSP 헤더, 최초 부팅 이미지 sha 고정, cosign 서명 (P2)

> 위 후속 P1 중 보존 잡·로그 스크러빙·관측성·복구 리허설은 이후 `deploy/ops-jobs/` 로 실제 반영됐습니다(→ `../roadmap/04_후속보완_로드맵.md`).

---

## 참고: compose 통합(옛 `03_webstack_스캐폴드` 흡수)

옛 문서세트는 애플리케이션 스캐폴드(`03_webstack_스캐폴드`, 자체 `docker-compose.yml`/`nginx/` 보유)와
배포 계층(`05_CD_배포/skinlens-ops`)이 **compose를 이중으로** 갖고 있었다. 현재 monorepo에서는
두 compose를 `deploy/compose/compose.base.yml` + 환경 오버레이(`dev`/`staging`/`prod`)로 **단일화**했고,
스캐폴드 코드는 `services/`(gateway·worker·engine-*)·`apps/`(homepage·devpage)로 이동했다.
따라서 "스캐폴드 compose에도 미러링" 같은 이중 관리 항목은 사라졌다.

- GPU 배선은 `deploy/compose/compose.gpu.yml` 오버레이 한 곳에만 있고,
  `compose.base.yml` 엔 엔진에 `mem_limit`(GPU 워크로드용 상향 주석)만 있다.
  실제 모델을 얹을 때 `deploy.resources.reservations.devices` + 엔진 동시성=1 은 오버레이에서 관리.
- nginx proto 정규화(`map $http_x_forwarded_proto`)와 `proxy-common.conf` 는 `deploy/nginx/` 단일 소스에 반영돼 있다.
- 현재 엔진 `services/engine-analysis/requirements.txt` 는 OpenCV baseline(numpy·opencv-headless)만 고정돼 있고
  딥러닝 런타임(torch 등)은 아직 없다(baseline/스텁). 실제 모델을 얹을 때 VRAM 정책(GPU 오버레이 주석)을 함께 확정.
