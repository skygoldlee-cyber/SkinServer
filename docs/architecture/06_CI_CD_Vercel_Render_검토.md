# CI/CD 구조 검토 — Frontend(Vercel) + Backend(Render)

> **검토 일자**: 2026-08-20
> **검토 대상**: 현재 3-Tier(Vercel · Supabase · AI Server) 구조에서 Backend 호스팅을 Render로 변경하는 방안
> **현재 상태**: [`05_3Tier_이전_작업계획.md`](./05_3Tier_이전_작업계획.md) Phase 1~4 코드 완료, Phase 5(CD 분리) 미착수

---

## 1. 한눈에 보는 비교

| 축 | 현재 목표 (3-Tier) | 대안 (Render Backend) | 판정 |
|---|---|---|---|
| **Frontend** | Vercel (Next.js PWA) | Vercel (Next.js PWA) | ✅ 동일 |
| **Backend 호스팅** | self-hosted VPS + Docker Compose | Render (Managed Container) | ⚠️ 구조 변경 |
| **GPU 지원** | `compose.gpu.yml` 오버레이로 nvidia 배선 가능 | **Render는 GPU 미지원** | ❌ 치명적 |
| **네트워크 격리** | `enginenet: internal` (폐쇄망) | Render Private Network (유사하나 완전 폐쇄 아님) | ⚠️ 완화됨 |
| **배포 방식** | GH Actions → self-hosted runner → `deploy.sh` | Git push → Render 자동 빌드/배포 | ✅ 단순화 |
| **헬스 게이트/롤백** | `deploy.sh` flock + 헬스체크 + 자동 롤백 | Render 헬스체크 + 수동/자동 롤백(제한적) | ⚠️ 기능 축소 |
| **DB 마이그레이션** | 워크플로에서 `alembic upgrade head` (deploy 전) | Render 배포 전 훅으로 실행 가능 | ✅ 유지 가능 |
| **비용** | VPS 비용 + 관리 공수 | Render 인스턴스 비용 (스케일에 따라 증가) | ⚠️ 트레이드오프 |
| **PIPA/컴플라이언스** | 서버 위치/접근 제어 가능 | Render 리전 선택에 의존 | ⚠️ 검토 필요 |

**한 줄 결론**: **Frontend → Vercel은 현재 설계와 완전히 일치하나, Backend → Render는 GPU 요구사항과 폐쇄망 엔진 아키텍처(Case A)로 인해 현재 구조에는 적합하지 않다.** 다만 GPU가 필요 없는 경량 서비스(gateway/worker)만 Render로 이전하는 **하이브리드** 방안은 검토 가능하다.

---

## 2. Frontend → Vercel (적합성: ✅ 높음)

현재 설계([`04_3Tier_Vercel_Supabase_AIServer_설계.md`](./04_3Tier_Vercel_Supabase_AIServer_설계.md))와 완전히 일치한다.

- **이미 코드 이전 완료**: [`apps/webapp-next/`](../../apps/webapp-next/) (Next.js 14 + PWA + Supabase)
- **환경변수**: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_AI_API_BASE`
- **PWA 캐시 정책**: `/api` 및 `*.supabase.co`는 NetworkOnly (PIPA 준수) — [`next.config.mjs`](../../apps/webapp-next/next.config.mjs)
- **남은 작업**: Vercel 프로젝트 연결(Phase 2.5) 및 구 `apps/webapp` 제거(Phase 2.7)

**결론**: Frontend를 Vercel에 배포하는 것은 **이미 확정된 방향**이며, Render 도입 여부와 무관하게 유지되어야 한다.

---

## 3. Backend → Render (적합성: ⚠️ 조걶부)

### 3.1 Render로 이전 가능한 것

| 서비스 | 이전 가능성 | 이유 |
|---|---|---|
| `gateway` | ✅ 가능 | 무상태 HTTP 서버, CPU만 사용, 헬스체크 `/health` 존재 |
| `worker` | ✅ 가능 | 백그라운드 워커, Render Background Worker로 배포 가능 |

### 3.2 Render로 이전 불가능/부적합한 것

| 서비스 | 이전 가능성 | 이유 |
|---|---|---|
| `engine-analysis` | ❌ **불가** | OpenCV + 향후 GAN/diffusion 모델은 **GPU 필수**. Render는 GPU 인스턴스를 제공하지 않음. 현재도 `compose.gpu.yml`로 GPU 배선 예정 |
| `engine-prescription` | ❌ **불가** | 동일하게 GPU 바운드 워크로드로 확장 예정 |
| **폐쇄망 구조(Case A)** | ❌ **불가** | 현재 아키텍처의 핵심: `enginenet: internal`로 엔진의 외부 egress를 완전 차단. Render의 Private Network는 서비스 간 통신은 가능하나, 외부 인터넷 접근을 네트워크 레벨에서 완전히 차단하는 "internal" 개념이 없음 |

### 3.3 Render 도입 시 구조 변화

```
[현재 3-Tier]
사용자 → Vercel(웹) → Supabase(DB/Auth/Storage)
                ↘ AI Server(VPS) → Caddy(TLS) → gateway/worker/engine-* (Docker Compose, enginenet internal)

[Render 하이브리드]
사용자 → Vercel(웹) → Supabase(DB/Auth/Storage)
                ↘ Render(gateway/worker) ──(인터넷)──> AI Engine Server(별도 GPU 호스트)
```

**핵심 문제**: gateway/worker와 엔진이 **같은 호스트/네트워크**에 있어야 `enginenet` 폐쇄망이 성립한다. Render에 gateway/worker를 두고 엔진을 별도 GPU 서버에 두면, 엔진 호출이 **공인 인터넷을 경유**하게 되어 Case A 원칙이 붕괴한다.

---

## 4. 상세 리스크 분석

### 4.1 기술적 리스크

| 리스크 | 심각도 | 설명 | 완화 방안 |
|---|---|---|---|
| **GPU 미지원** | 🔴 **치명적** | Render는 GPU 인스턴스를 제공하지 않음. 향후 GAN/diffusion 모델 도입 시 엔진 배포 불가 | GPU는 별도 클라우드(AWS EC2 P/G 인스턴스, GCP Compute Engine) 또는 on-premise 유지. gateway/worker만 Render |
| **폐쇄망 붕괴** | 🔴 **치명적** | Render 서비스 간 통신은 Private Network를 사용하나, 엔진을 외부에 두면 공인망 경유. 엔진에 자격증명이 없는 설계(Case A)와 충돌 | 엔진은 반드시 같은 네트워크 경계 내에 두어야 함. Render Private Network 남용 시에도 외부 egress 차단을 보장할 수 없음 |
| **네트워크 레이턴시** | 🟡 중간 | Render(미국/유럽 리전) ↔ Supabase(싱가포르/도쿄 리전) 간 지연 증가 가능 | Render 리전을 Supabase와 가까운 곳으로 선택(Singapore), 또는 Supabase 리전 이전 |
| **콜드 스타트** | 🟡 중간 | Render의 묵은 인스턴스는 스핀다운 후 콜드 스타트 발생. 사용자 경험 저하 | "Always On" 유료 플랜 사용, 또는 최소 인스턴스 수 1로 설정 |
| **시크릿 관리** | 🟢 낮음 | Render는 환경변수/시크릿 관리 기능 제공 | Render 대시보드에서 `SUPABASE_SERVICE_KEY`, `DATABASE_URL` 등록. `SUPABASE_JWT_SECRET`도 동일 |

### 4.2 운영/배포 리스크

| 리스크 | 심각도 | 설명 | 완화 방안 |
|---|---|---|---|
| **롤백 제한** | 🟡 중간 | Render는 배포 히스토리에서 이전 버전으로 롤백 가능하나, `deploy.sh`의 **헬스 게이트 기반 자동 롤백**보다 단순함 | Render의 헬스체크 경로(`/health`) 설정 + 배포 후 수동 확인 절차 추가 |
| **DB 마이그레이션 타이밍** | 🟡 중간 | Render 배포 전에 `alembic upgrade head`를 실행해야 함. Render는 배포 전 훅(pre-deploy command) 지원 | Render 대시보드에서 pre-deploy command로 `alembic upgrade head` 설정. gateway 서비스에만 적용 |
| **환경별 분리** | 🟢 낮음 | Render는 서비스별로 여러 인스턴스(staging/production) 생성 가능 | Render 서비스를 `skinlens-gateway-staging` / `skinlens-gateway-prod`로 분리 |
| **로그 수집** | 🟡 중간 | Render는 기본 로그 스트림 제공하나, `deploy/ops-jobs/log-scrub.py`와 같은 자체 로그 처리 파이프라인과의 통합 필요 | Render 로그를 외부 로그 수집기(Logtail, Datadog 등)로 스트리밍하거나, 주기적으로 다운로드하여 스크럽 |

### 4.3 보안/컴플라이언스 리스크

| 리스크 | 심각도 | 설명 | 완화 방안 |
|---|---|---|---|
| **PIPA/데이터 주권** | 🟡 중간 | 피부 사진은 민감 개인정보. Render의 서버 위치(미국/유럽)가 한국 데이터 주권 요건과 충돌할 수 있음 | Render Singapore 리전 선택, 또는 한국 클라우드(네이버 클라우드, AWS Seoul) 대안 검토. Supabase는 이미 싱가포르 리전 사용 중 |
| **엔진 접근 제어** | 🔴 **높음** | Render에 gateway/worker를 두면 엔진이 공인망에 노출됨. 현재는 `enginenet: internal`로 완전 차단 중 | 엔진 앞단에 별도 인증 게이트웨이(API Key/mTLS)를 두거나, WireGuard/Tailscale로 프라이빗 네트워크 구성. 복잡성 증가로 비추천 |

---

## 5. 비용 비교 (월간 추정)

| 항목 | 현재 (VPS) | Render (하이브리드) | 비고 |
|---|---|---|---|
| **VPS (AI Server)** | $20~50 (사양에 따라) | $0 (제거) | GPU 서버는 별도 유지 시 $100+ |
| **Render — gateway** | - | $7~25 (Starter/Standard) | 인스턴스 타입에 따라 |
| **Render — worker** | - | $7~25 (Background Worker) | 동일 |
| **GPU 서버 (별도)** | 포함 | $100~500+ | AWS EC2 g4dn.xlarge 등 |
| **Vercel** | $0 (Hobby) / $20 (Pro) | $0 / $20 | 동일 |
| **Supabase** | $0 (Free) / $25 (Pro) | $0 / $25 | 동일 |
| **총계** | **$20~75+** | **$114~570+** | Render + GPU 서버 별도 운영 시 비용 증가 |

> **결론**: Render로 전면 이전하면 **GPU 서버를 별도로 운영**해야 하므로 오히려 비용이 증가하고 관리 포인트가 늘어난다.

---

## 6. 마이그레이션 가이드 (만약 Render를 도입한다면)

> ⚠️ **주의**: 이 가이드는 **gateway/worker만 Render로 이전하고, 엔진은 별도 GPU 호스트에 유지**하는 하이브리드 시나리오를 전제로 한다. 엔진까지 Render로 옮기는 것은 GPU 미지원으로 불가능하다.

### Phase R1: 사전 준비

1. **Render 계정 생성 및 리전 선택**
   - Supabase와 동일 리전(Singapore) 권장 → 레이턴시 최소화
   - `skinlens-gateway-staging`, `skinlens-worker-staging` 서비스 생성

2. **Dockerfile 확인**
   - [`services/gateway/Dockerfile`](../../services/gateway/Dockerfile): `EXPOSE 8000` 확인
   - [`services/worker/Dockerfile`](../../services/worker/Dockerfile): 포트 노출 불필요(Background Worker)

3. **환경변수 매핑**
   - Render 대시보드 → Environment → Secret Files 또는 Environment Variables에 등록:
     - `DATABASE_URL` (Supabase connection string)
     - `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`
     - `AUTH_MODE=strict`, `ENV=prod`
     - `CORS_ORIGINS=https://your-app.vercel.app`
     - `STORAGE_BACKEND=supabase`, `STORAGE_BUCKET=skin-images`

### Phase R2: 배포 설정

1. **Gateway 서비스 (Web Service)**
   - **Build Command**: `docker build -t gateway services/gateway`
   - **Start Command**: `docker run -p $PORT:8000 gateway` (Render는 `$PORT` 환경변수 주입)
   - **Health Check Path**: `/health`
   - **Pre-Deploy Command**: `alembic upgrade head` (DB 마이그레이션)

2. **Worker 서비스 (Background Worker)**
   - **Build Command**: `docker build -t worker services/worker`
   - **Start Command**: `docker run worker`
   - **포트 노출 불필요**

3. **CI/CD 연동**
   - Render는 GitHub 연동 자동 배포 지원
   - `main` 브랜치 push 시 자동 빌드/배포
   - **단, 현재의 `deploy.sh` 헬스 게이트 + flock 롤백은 사용 불가** → Render의 롤백 기능에 의존

### Phase R3: 엔진 서버 분리 (필수)

엔진은 GPU가 필요하므로 별도 호스트 유지:

1. **GPU 서버 준비** (AWS EC2, GCP, 또는 기존 VPS 유지)
   - `engine-analysis`, `engine-prescription`만 Docker Compose로 기동
   - **문제**: gateway/worker(Render)에서 엔진(GPU 서버)으로의 호출이 **공인 인터넷** 경유

2. **보안 강화 (필수)**
   - 엔진 앞단에 **API Gateway** 또는 **mTLS** 설정
   - 또는 **Tailscale/WireGuard**로 Render ↔ GPU 서버 간 프라이빗 네트워크 구성
   - **권장하지 않음**: 복잡성이 현재 Compose 구조보다 크게 증가

### Phase R4: 검증 및 전환

1. **Staging 환경 검증**
   - `https://skinlens-gateway-staging.onrender.com/health` → 200 OK
   - `POST /uploads/presign` → 서명 URL 발급 확인
   - E2E: presign → Supabase PUT → analyze → done

2. **DNS/도메인 전환**
   - Vercel 환경변수 `NEXT_PUBLIC_AI_API_BASE`를 Render 도메인으로 변경
   - `https://skinlens-gateway.onrender.com` → `https://api.yourdomain.com` (CNAME)

3. **모니터링 이관**
   - Render 로그 → 외부 로그 수집기 연동
   - `deploy/ops-jobs/alert.sh`의 대상 URL을 Render 헬스체크로 변경

---

## 7. 최종 권고안

### 권고 1: **현재 3-Tier 구조 유지 (가장 권장)**

현재 설계(Vercel + Supabase + self-hosted AI Server)는 **이미 매우 성숙**하다:

- ✅ GPU 지원: `compose.gpu.yml`로 nvidia 배선 가능
- ✅ 폐쇄망: `enginenet: internal`로 엔진 완전 격리 (Case A)
- ✅ 헬스 게이트: `deploy.sh` flock + 자동 롤백
- ✅ 비용 효율: 단일 VPS로 gateway/worker/engine 통합 운영 가능

**남은 작업**: Phase 5(CD 분리)에서 웹 워크플로 제거 및 `deploy.sh` 정리만 하면 된다.

### 권고 2: **Render 도입은 "GPU 불필요 시"에만 검토**

만약 **향후에도 GPU가 전혀 필요 없고**, 엔진을 CPU-only로 영구 운영한다면:

- gateway/worker → Render (관리 편의성)
- engine-* → Render (CPU-only)
- **단, 폐쇄망(Case A)은 포기**하거나, Render Private Network + egress 제한 정책으로 최대한 유사하게 구현

이 경우에도 **현재 Compose 구조의 명확한 네트워크 경계**보다는 보안성이 떨어진다.

### 권고 3: **하이브리드는 비추천**

gateway/worker만 Render에 두고 엔진을 별도 GPU 서버에 두는 방식은:
- 네트워크 복잡성 증가 (공인망 경유 또는 VPN 구성 필요)
- 비용 증가 (Render + GPU 서버 이중 비용)
- 보안 경계 모호화

**현재 self-hosted Compose 구조가 더 단순하고 안전하다.**

---

## 8. 요약

| 질문 | 답변 |
|---|---|
| **Frontend → Vercel은 적합한가?** | ✅ **매우 적합**. 이미 코드 이전 완료, Phase 2.5(Vercel 연결)만 남음 |
| **Backend → Render는 적합한가?** | ❌ **현재 구조에는 부적합**. GPU 미지원 + 폐쇄망(Case A) 붕괴가 치명적 |
| **어떤 구조를 선택해야 하나?** | **현재 3-Tier(Vercel + Supabase + self-hosted AI Server) 유지**가 최선. Render는 GPU가 필요 없는 단순 API 서버나, 폐쇄망 요구사항이 없는 경우에만 대안으로 검토 |

---

## 9. 관련 문서

- [`04_3Tier_Vercel_Supabase_AIServer_설계.md`](./04_3Tier_Vercel_Supabase_AIServer_설계.md) — 현재 3-Tier 설계 정본
- [`05_3Tier_이전_작업계획.md`](./05_3Tier_이전_작업계획.md) — Phase별 작업 계획 (Phase 5 CD 분리 미착수)
- [`01_SkinLens_운영아키텍처_최종리뷰.md`](./01_SkinLens_운영아키텍처_최종리뷰.md) — 운영 아키텍처 리뷰 (GPU 미배선 P0 지적)
- [`10_Phase5_배포순서_런북.md`](../operations/10_Phase5_배포순서_런북.md) — Vercel/AI Server 배포 순서 런북
