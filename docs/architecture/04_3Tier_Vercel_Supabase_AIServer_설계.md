# SkinLens 3-Tier 재설계 — Vercel · Supabase · AI Server

> 목적: 현재 monorepo(자체 nginx 엣지 + 로컬/자체호스팅 Supabase 혼용)를
> **Vercel(웹/PWA) + Supabase(데이터/인증/스토리지) + AI Server(FastAPI·Docker·GPU)** 의
> 명확한 3분할로 재편하는 설계 정본.
>
> 이 문서는 "왜/무엇을"을 담는다. 실제 배선(compose·env·마이그레이션)은 별도 패치 노트로 내린다.
>
> 관련 문서:
> - 현재 운영 아키텍처 감사: [`01_SkinLens_운영아키텍처_최종리뷰.md`](./01_SkinLens_운영아키텍처_최종리뷰.md)
> - Phase 로드맵(현재 위치): [`../roadmap/00_PHASE_ROADMAP.md`](../roadmap/00_PHASE_ROADMAP.md)
> - DB 마이그레이션/롤백 런북: [`03_DB_MIGRATION_ROLLBACK.md`](./03_DB_MIGRATION_ROLLBACK.md)
> - 엔진 교체 seam: [`엔진_baseline_교체_가이드.md`](./엔진_baseline_교체_가이드.md)

---

## 0. 한눈에 보는 목표 구조

```
사용자
  │
  ▼
┌─────────────┐      (정적/PWA·엣지 캐시·Web API 라우트)
│   Vercel    │  ── Next.js PWA ── 서비스워커는 앱셸만 precache, /api·Supabase NetworkOnly
└──────┬──────┘
       │  (1) 인증·DB·스토리지 = Supabase SDK (브라우저, anon key + RLS)
       │  (2) AI 작업 요청    = HTTPS → AI Server
       ▼                     ▼
┌───────────┐          ┌──────────────┐
│ Supabase  │          │  AI Server   │
│ Postgres  │◀─service│  (전용 호스트)│
│ Auth      │  role   │  FastAPI     │
│ Storage   │  (서버만)│  PyTorch     │
│ (RLS 강제) │          │  OpenCV      │
└───────────┘          │  Docker·GPU  │
                       └──────────────┘
```

**역할 한 줄**
- **Vercel** — SkinLens 웹서비스(PWA)를 빠르고 안전하게 전역 배포/운영. 서버리스 Route Handler는 *가벼운 BFF* 용도로만.
- **Supabase** — 데이터(Postgres)·인증(Auth)·파일(Storage)의 단일 진실원본. RLS로 "사용자 A는 B 것 불가"를 DB가 강제.
- **AI Server** — 분석/처방 엔진 + 잡 큐/워커 + (필요시) 게이트웨이를 싣는 **전용 GPU 호스트**(Docker Compose). 외부엔 HTTPS 1개만 연다.

---

## 1. 왜 바꾸나 — 현재 대비 변화 요약

| 축 | 지금(monorepo 운영) | 목표(3-Tier) | 핵심 이유 |
|---|---|---|---|
| 웹 표면 | nginx 컨테이너가 `homepage`/`webapp`/`devpage` 정적 서빙 | **Vercel**이 Next.js PWA를 엣지에서 서빙 | 배포 속도·CDN·프리뷰·TLS 자동. nginx 정적 3종 제거 |
| 엣지/TLS | 자체 nginx 80 + Caddy TLS(예정) | Vercel(웹) + AI Server 앞단 TLS(Caddy)만 | 인증서·보안헤더·HSTS를 Vercel에 위임, 서버 노출 최소화 |
| 데이터 | dev=로컬 pg, staging=로컬 pg(Supabase 대역), prod=Supabase | **전 환경 Supabase**(프로젝트 dev/prod 분리) | 로컬/운영 스키마 드리프트 제거, RLS·백업·관측을 Supabase에 일원화 |
| 스토리지 | 로컬 볼륨 `storage:`(운영은 Supabase 예정) | **Supabase Storage**(presigned 업로드) | PIPA·보존·서명 URL을 한 곳에서. 게이트웨이 경유 업로드 제거 |
| 인증 | Supabase JWT를 gateway가 검증(`AUTH_MODE=strict`) | 동일 — 다만 **브라우저→Supabase 직결 인증**, AI Server는 JWT 검증만 | 게이트웨이가 인증을 '대행'하지 않고 '검증'만 → 단순화 |
| 엔진 | 동일 호스트 compose 内 `enginenet(internal)` | **AI Server 남되**, 네트워크 경계는 동일 원칙 유지 | GPU·폐쇄망·무자격증명(Case A) 원칙은 그대로 계승 |
| CI/CD | GH Actions → self-hosted runner → deploy.sh | 웹=**Vercel 자동**, AI Server=GH Actions→(runner) compose 배포 | 웹 배포와 서버 배포 분리로 실패 반경 축소 |

> **무엇이 빠지나**: `deploy/nginx/{app,www,dev}.conf` + `homepage/devpage/webapp` nginx 컨테이너 + `80:80` 엣지 프록시.
> **무엇이 남나**: AI Server 안의 `gateway/worker/engine-*`(필요 시), 그리고 `deploy/compose`는 **AI Server 전용**으로 슬림화.

---

## 2. 구성요소별 설계

### 2.1 Vercel — 웹/PWA
- **앱**: `apps/webapp`을 **Next.js(App Router) + PWA**로 이전(현재 Vite SPA). 정적 앱셸 + `/api/*`는 NetworkOnly(PIPA: 사진·결과·토큰 미캐시).
- **호스팅 경계**:
  - 정적/앱셸/설문·결과 화면 → Vercel.
  - 민감 API 호출은 브라우저가 **Supabase**(인증/DB/스토리지) 또는 **AI Server**(AI 작업)로 직접. Vercel 서버리스는 *토큰 교환·웹훅·소량 BFF*에 한정.
- **환경변수(큰 틀)**:
  - 공개: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_AI_API_BASE`.
  - 비공개(서버리스 전용, 필요 시): `SUPABASE_SERVICE_ROLE_KEY`(절대 브라우저 노출 금지).
- **CORS/오리진**: 앱과 API가 오리진을 달리하므로, AI Server는 **명시적 CORS 허용 목록**(Vercel 도메인)만 연다. 지금의 "같은 오리진이라 CORS 불필요" 전제는 사라진다 → 서버측 CORS 하드닝 필요.

### 2.2 Supabase — 데이터·인증·스토리지(단일 진실원본)
- **프로젝트 분리**: `skinlens-dev` / `skinlens-prod` (스키마 동일, 데이터 분리). 로컬 개발도 `supabase start`로 동일 스키마 사용 → **로컬 postgres 제거**.
- **DB/RLS**: `jobs`·`job_events`·`prescriptions` 테이블은 유지하되, **RLS가 최종 경계**. "사용자 A가 B의 job/photo 접근 불가"를 SQL 정책으로 강제(현재 문서상 과제 G를 해소).
  - 브라우저는 `anon key` + RLS로 **읽기/제한적 쓰기**.
  - 무거운 쓰기(잡 상태 전이·결과 기록)는 **AI Server가 service role**로 수행 → RLS 우회는 서버에서만.
- **Auth**: Supabase Auth(이메일/소셜). AI Server는 기존처럼 **HS256 JWT(`aud=authenticated`) 검증**만 한다(검증 로직 재사용).
- **Storage**: 버킷 `skin-images` + object-key `{user_id}/{job_id}/original.<ext>`. **presigned 업로드**를 도입해 브라우저가 곧장 업로드(게이트웨이 업로드 제거). 다운로드는 서명 URL.
  - 정책 SQL은 기존 [`deploy/supabase/policies/0001_rls_and_storage.sql`](../../deploy/supabase/policies/0001_rls_and_storage.sql)을 **Supabase 프로젝트에 실제 적용**하는 것으로.

### 2.3 AI Server — 전용 호스트(Docker Compose, GPU)
현재 `services/`의 자산을 **거의 그대로** 옮긴다. 바뀌는 건 "누가 붙고, 어디서 인증하고, 어디에 쓰는가"뿐.

- **구성(권장안 A: 얇은 게이트웨이 유지)**
  - `gateway` — 외부에 여는 유일한 HTTP 표면. 업로드는 받지 않고(=presigned로 대체) **작업 생성/조회/이벤트 스트림**만.
  - `worker` — `FOR UPDATE SKIP LOCKED`로 잡 클레임 → 엔진 호출 → Supabase에 결과 기록(service role).
  - `engine-analysis` / `engine-prescription` — `enginenet(internal: true)` 폐쇄망, 무자격증명, 포트 미발행. GPU는 `compose.gpu.yml` 오버레이로 배선 + **동시성=1 직렬화**(VRAM OOM 방지, ①-A/③-C 계승).
- **구성(대안 B: 게이트웨리스)** — 웹이 Supabase에 잡 row를 INSERT(RLS)하면, AI Server는 **워커+엔진만** 두고 DB 폴 LISTEN/NOTIFY로 소비. 표면이 더 작아지나 이벤트 스트림/권한 설계가 복잡해지므로 **기본은 A**.
- **네트워크/보안 경계**
  - 외부 노출은 AI Server의 **443 하나**(Caddy 자동 TLS). 엔진은 외부 egress 없음.
  - **신뢰 경계**: Vercel/브라우저 → (Supabase JWT) → AI Server. AI Server → Supabase는 service role.
  - **비밀**: `SUPABASE_SERVICE_ROLE_KEY`, 엔진 모델 경로 등은 AI Server의 `.env`에만. Vercel엔 anon key만.

> GPU 미사용 시(초기): `compose.gpu.yml` 없이 CPU로 운용하되, 문서상 "GPU 엔진" 표기와 실제 배선이 어긋나지 않도록 명시(리뷰 ①-A 교훈).

---

## 3. 데이터/요청 흐름

### 3.1 분석 요청(권장안 A)
1. 브라우저(Vercel PWA) → Supabase Auth 로그인 → 세션 토큰 획득.
2. 브라우저 → AI Server `POST /analyze` : `survey`만 본문, 이미지는 `image_key`(= presigned로 먼저 업로드한 키) 또는 직접 multipart(소규모/초기 호환).
   - *presigned 플로우*: AI Server가 `image_key`를 발급 → 브라우저가 Supabase Storage에 직접 PUT → 완료 후 `POST /analyze { image_key }`.
3. AI Server(gateway) → Supabase `jobs` INSERT(service role) → `job_id` 즉시 반환. `job_events`에 `upload→queued` 기록.
4. `worker` → 잡 클레임 → Storage에서 서명 URL로 원본 fetch → `engine-analysis` → `engine-prescription` → 결과를 `jobs.result`, `prescriptions`에 기록, 이벤트 스트림 갱신.
5. 브라우저 → `GET /jobs/{id}` 또는 `/jobs/{id}/events` 폴/SSE로 진행·결과 표시. 결과 데이터 자체는 RLS로 본인 것만.

### 3.2 환경별 차이
| 환경 | 웹 | DB/Auth/Storage | AI Server | 엔진 |
|---|---|---|---|---|
| dev(로컬) | `next dev`(또는 Vercel dev) | `supabase start`(로컬) | 로컬 compose(CPU) | baseline OpenCV/규칙 |
| staging | Vercel Preview | Supabase `skinlens-dev` | AI Server compose(staging 오버레이) | baseline |
| prod | Vercel Production | Supabase `skinlens-prod` | AI Server compose(prod+gpu+tls) | baseline→ML 교체 seam |

---

## 4. 저장소(모노레포)에 미치는 영향 — What moves / What stays / What goes

- **Moves**
  - `apps/webapp` → **Next.js PWA**로 포팅(`app/` 라우터, `next-pwa`). `VITE_*` → `NEXT_PUBLIC_*`.
  - `deploy/compose` → **AI Server 전용**으로 슬림화: `nginx/homepage/devpage/webapp` 서비스·`frontnet` 제거, `gateway/worker/engine-*`만.
  - `deploy/caddy` → AI Server 앞단 TLS만 담당(웹 정적 라우팅 삭제).
- **Stays (그대로 가치 유지)**
  - `services/gateway`·`services/worker`·`services/engine-*`(엔진 HTTP 계약 `/score`·`/prescribe` 불변).
  - `packages/common/skinlens_contract`(계약 버전·10지표·STAGES 단일 진실원본).
  - `deploy/db/migrations` + `deploy/supabase/policies`(이제 실제 Supabase에 적용).
  - `deploy/ops-jobs`(보존·로그 스크럽·복구 리허설) — 대상이 Supabase로 바뀌므로 스크립트의 연결 문자엧만 교체.
- **Goes (제거)**
  - `deploy/nginx/conf.d/{app,www,dev}.conf` + `homepage/devpage/webapp` 정적 nginx 컨테이너.
  - "같은 오리진" 전제의 CORS-프리 설계 주석(실제로는 CORS 설정 추가).

> 상세 매핑은 [`../../MIGRATION.md`](../../MIGRATION.md)에 3-Tier 대응표를 추가한다.

---

## 5. 보안/컴플라이언스(PIPA) 메모
- **TLS**: Vercel(웹) + Caddy(AI Server) 자동. HSTS·보안헤더·CSP는 Vercel `headers()`와 AI Server Caddy에 이중으로(기존 `security-headers.conf` 재활용).
- **PIPA**: 사진·분석결과·토큰은 서비스워커/응답 캐시 금지(기존 원칙 유지). Storage object는 서명 URL로만, 보존·삭제 잡(`retention.py`) 대상을 Supabase로 전환.
- **RLS가 최종 경계**: 앱이 아니라 DB가 소유권을 강제. "코드로 담당"에서 "정책으로 강제"로 이동(리뷰 ②-G 해소).
- **비밀 분리**: anon key(공개) / service role(AI Server만) / 모델 가중치 경로. self-hosted runner는 production 환경 승인 게이트 필수(기존 권고 계승).

---

## 6. 리스크와 완화
| 리스크 | 내용 | 완화 |
|---|---|---|
| CORS 회귀 | 오리진 분리로 기존 "CORS 불필요" 전제 붕괴 | AI Server에 허용 오리진 명시 + 프리플라이트 캐시 + 헤더 화이트리스트 |
| presigned 남용 | 서명 URL 유출·대용량 업로드 | 만료 짧게·MIME/크기 서버 검증·업로드 전용 레이트리밋·버킷 정책 |
| service role 남용 | AI Server 키 유출 시 전체 우회 | 키 로테이션·최소 권한 커스텀 role 검토·출구 IP 제한·감사 로그 |
| 스키마 드리프트 | 로컬↔Supabase 불일치 | 마이그레이션 단일 원천(`deploy/db/migrations`) + CI에 `alembic upgrade head` + expand-contract 규칙(03 런북) |
| GPU 미배선 | CPU로 조용히 운영 | compose.gpu 오버레이 + `ENGINE_MAX_CONCURRENCY=1` + 헬스/메트릭으로 VRAM 감시 |
| 웹/서버 배포 타이밍 | 계약 불일치 | `ENGINE_CONTRACT_VERSION` 게이트 + Vercel/AI Server 배포 순서 런북 |

---

## 7. 마이그레이션 단계(권장 순서)
1. **Supabase 정렬**: 프로젝트 dev/prod 생성 → `deploy/db/migrations` + RLS/Storage 정책 적용 → `storage.py`의 Supabase 백엔드 **실구현**(현재 seam).
2. **웹 포팅**: `apps/webapp` → Next.js PWA. Vercel 프로젝트 연결, 환경변수 세팅, 서비스워커 캐시 규칙(앱셸만 precache) 적용.
3. **AI Server 슬림화**: compose에서 정적/nginx 제거, `gateway`를 "잡 생성/조회"로 축소 + presigned 발급 추가. Caddy TLS.
4. **presigned 업로드 전환**: 브라우저 직접 업로드 플로우로 전환(구 multipart는 feature flag로 유지→제거).
5. **CD 분리**: 웹=Vercel 자동 / AI Server=GH Actions→compose(기존 `deploy.sh` 재사용, `.env.images` flock 유지).
6. **관측/DR 이관**: `ops-jobs`의 대상을 Supabase로 전환, 복구 리허설 스케줄 고정.

각 단계는 독립 배포 가능(웹과 서버를 따로). 계약(`skinlens_contract`) 버전이 호환 게이트.

---

## 8. 명시적 미결정(다음 설계에서 확정)
- **게이트웨이 유지(A) vs 게이트웨리스(B)** — 기본 A. B는 이벤트 스트림/권한 설계가 커지므로 트래픽 증가 후 재평가.
- **엔진 동시성/스케줄링** — GPU 1장 전제 직렬화. 다중 GPU/큐(Redis) 도입은 Phase 3/5에서.
- **결과 조회 채널** — 폴 `/jobs/{id}` vs SSE `/jobs/{id}/events` vs Supabase Realtime 구독. 초기엔 폴, 이후 Realtime 검토.
- **presigned 다운로드 범위** — 결과 리포트(HTML/이미지)도 서명 URL로 갈지, DB JSON만으로 충분한지.

---

## 9. 성공 기준(Definition of Done)
- [ ] Vercel에서 PWA 설치·오프라인 앱셸 동작, `/api`·Supabase는 캐시 없음(PIPA).
- [ ] Supabase RLS로 타 사용자 job/사진 접근 차단이 SQL 정책으로 검증(테스트 포함).
- [ ] AI Server는 443만 노출, 엔진은 `enginenet` 폐쇄망·무자격증명·포트 미발행.
- [ ] presigned 업로드 → 잡 생성 → 워커 처리 → 결과 조회의 E2E가 통과.
- [ ] CI에서 `alembic upgrade head` + 스키마 드리프트 테스트(`tests/common/test_schema_drift.py`) 통과.
- [ ] GPU 오버레이 적용 시 동시성=1로 VRAM OOM 없이 엔진 헬스 유지.
