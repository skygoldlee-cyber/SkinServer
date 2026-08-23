# Phase 5.4 실행 런북 — Vercel / AI Server 배포 순서 (계약 버전 게이트)

> 목적: 3-Tier 분리 이후 **웹(Vercel)** 과 **AI Server(GH Actions→self-hosted)** 의
> 배포 채널이 갈라졌으므로, 두 축이 **엔진 계약(`ENGINE_CONTRACT_VERSION`)** 을 기준으로
> 어긋나지 않도록 배포 순서와 게이트 절차를 고정한다.
>
> 상위 계획: [`05_3Tier_이전_작업계획.md`](../architecture/05_3Tier_이전_작업계획.md) Phase 5
> 계약 단일 진실원본: [`packages/common/skinlens_contract/__init__.py`](../../packages/common/skinlens_contract/__init__.py)

---

## 0. 배포 축 정리 (현재 상태)

| 축 | 소스 | 트리거 | 배포 대상 | 책임자 |
|----|------|--------|-----------|--------|
| **웹 (Next.js PWA)** | [`apps/webapp-next`](../../apps/webapp-next) | `main` push → Vercel 자동 빌드/배포 | Vercel (정적+SSR 엣지) | Vercel |
| **AI Server — gateway/worker** | [`services/gateway`](../../services/gateway), [`services/worker`](../../services/worker) | `main`/`develop` push → [`.github/workflows/deploy-built-service.yml`](../../.github/workflows/deploy-built-service.yml) | self-hosted 러너가 서버에서 직접 빌드 → `deploy.sh` | GH Actions |
| **AI Server — engine-*** | [`services/engine-analysis`](../../services/engine-analysis), [`services/engine-prescription`](../../services/engine-prescription) | `main`/`develop` push → [`.github/workflows/build-and-deploy-engine.yml`](../../.github/workflows/build-and-deploy-engine.yml) | GHCR 빌드 → 서버 pull → `deploy.sh` | GH Actions |
| **테스트** | 전체 | push/PR → [`.github/workflows/tests.yml`](../../.github/workflows/tests.yml) | unit + integration (postgres:16 서비스) | GH Actions |

> 웹은 더 이상 이 리포지토리에서 빌드/배포하지 않는다.
> (`deploy-static.yml` / `deploy-webapp.yml` 제거됨 — Phase 5.1)

---

## 1. 어느 축이 무엇에 의존하는가

```
웹 (Vercel)
  │  analyze() → gateway /analyze, /uploads/presign, /jobs/*  (REST 계약)
  │  survey/job 스키마 → gateway 가 DB 에 쓰는 모양
  ▼
AI Server — gateway
  │  엔진 호출 → engine-analysis /score, engine-prescription /prescribe
  │  응답 스키마 → packages/common/skinlens_contract
  ▼
AI Server — engine-*
```

- **웹↔gateway** 계약: REST 경로·필드·`image_key` 플로우. 깨지면 4xx/5xx.
- **gateway↔engine** 계약: [`skinlens_contract`](../../packages/common/skinlens_contract/__init__.py) 의
  `AnalysisResult` / `PrescribeResult` / `MetricScore` / `STAGES` / `METRIC_KEYS`.
  응답에 `contract_version` 필드로 실려 나간다.
- **계약 버전 단일 진실원본**: `ENGINE_CONTRACT_VERSION = "1.0.0"` (동일 파일 14번째 줄).
  스키마 필드가 바뀌면 **여기 값을 올린다**.

---

## 2. 계약 버전 게이트 (핵심 규칙)

> **규칙**: `packages/common/skinlens_contract/**` 를 건드리는 변경은
> **웹과 AI Server 를 같은 배포 단위로 취급** 하고, 아래 순서를 강제한다.

### 2.1 트리거 조건

다음 중 하나라도 해당하면 "계약 변경" 으로 간주:

- `packages/common/skinlens_contract/__init__.py` 의
  `AnalysisResult` / `PrescribeResult` / `PrescribeRequest` / `MetricScore` 필드 추가·삭제·이름변경
- `METRIC_KEYS` / `STAGES` / `GRADE_TABLE` 변경
- `ENGINE_CONTRACT_VERSION` 값 자체를 올리는 커밋

### 2.2 게이트 절차 (계약 변경이 포함된 배포)

```
①  ENGINE_CONTRACT_VERSION 을 올린다 (예: 1.0.0 → 1.1.0)
        │
②  AI Server 배포를 먼저 한다 (gateway + worker + engine-*)
        │  → gateway 가 새 계약을 말할 수 있게 된다
        │  → worker/engine 도 같은 버전으로 맞춘다
        │
③  헬스 게이트 확인 (deploy.sh 가 자동 수행)
        │  → /health/db, /debug/engines 정상
        │  → 엔진 응답에 새 contract_version 이 실려 나오는지 확인
        │
④  (선택) 통합 테스트로 계약 일치 확인
        │  → pytest -m integration (postgres:16 필요)
        │  → worker 가 실제 엔진을 호출해 결과 스키마 검증
        │
⑤  웹 (Vercel) 배포
        │  → apps/webapp-next 를 main 에 merge → Vercel 자동 배포
        │  → 웹이 새 계약(또는 하위호환 계약)을 소비한다
        │
⑥  사후 확인
           → /jobs/{id} 폴로우로 실제 파이프라인 1건 완주 확인
```

**왜 AI Server 먼저인가**: 웹이 새 계약을 기대하는 순간 구 엔진이 응답하면
웹이 깨진다. 반대로 AI Server 가 새 계약을 먼저 말하기 시작하면,
웹은 하위호환 범위 내에서는 계속 동작한다(필드 추가는 무시, 필드 삭제는
웹이 아직 안 쓰면 무해). 따라서 **서버를 먼저 올리고 웹을 따라가게** 한다.

### 2.3 하위호환 판정

| 변경 종류 | 하위호환? | 배포 순서 |
|-----------|-----------|-----------|
| 필드 **추가** (선택적) | ✅ 하위호환 | AI Server → 웹 (순서 무관에 가까움, 그래도 서버 우선 권장) |
| 필드 **삭제** / **이름변경** | ❌ 파괴적 | AI Server 먼저, 웹은 같은 창(window) 내 배포. 다운타임 창 필요 |
| `ENGINE_CONTRACT_VERSION` 만 올림 (스키마 동일) | ✅ | 순서 무관. 단 엔진/워커/게이트웨이는 같은 버전으로 맞출 것 |

> **파괴적 변경**이 필요하면: 구 필드를 deprecate 로 남겨두고(읽기만)
> 웹이 새 필드로 이행한 뒤 다음 배포에서 구 필드를 제거하는 **expand-contract** 를 따른다.
> (DB 마이그레이션과 같은 원칙 — [`03_DB_MIGRATION_ROLLBACK.md`](../architecture/03_DB_MIGRATION_ROLLBACK.md) 참조)

---

## 3. 일반 배포 (계약 변경 없음) 순서

대부분의 배포는 계약을 건드리지 않는다. 이 경우 순서 제약이 느슨하다.

### 3.1 웹만 바뀐 경우

1. `apps/webapp-next` 변경을 `main` 에 merge.
2. Vercel 이 자동 빌드/배포.
3. 사후 확인: `/` 로드, `analyze()` 1건 완주.

### 3.2 AI Server 만 바뀐 경우

1. `services/gateway` / `services/worker` / `services/engine-*` 변경을 `main` 에 merge.
2. 해당 워크플로가 자동 트리거 (paths 필터로 변경된 서비스만 빌드).
3. `deploy.sh` 가 헬스 게이트 + 롤백을 수행.
4. 사후 확인: `/health/db`, `/debug/engines`, `/jobs/{id}` 1건 완주.

### 3.3 둘 다 바뀐 경우 (계약은 그대로)

1. AI Server 먼저 배포 (3.2).
2. 헬스 게이트 통과 확인 후 웹 배포 (3.1).
3. 이유: 웹이 새 필드/경로를 기대할 수 있으므로, 서버가 먼저 그 표면을 제공해야 한다.

---

## 4. 롤백

### 4.1 AI Server 롤백

- `deploy.sh` 는 헬스 게이트 실패 시 **자동으로 이전 태그로 롤백** 한다.
- 수동 롤백이 필요하면: `deploy.sh --service <svc> --image <이전태그> --env <env>` 를
  이전 성공 태그로 재실행.
- **주의**: gateway 롤백 시 DB 마이그레이션은 이미 expand-only 로 적용된 상태.
  구 코드가 새 스키마에서 동작하도록 마이그레이션은 항상 하위호환이어야 한다(expand-contract).

### 4.2 웹 롤백

- Vercel 대시보드 → 해당 프로젝트 → **Deployments** → 이전 배포의 **Promote to Production**.
- Git 으로는 `git revert` 후 `main` push.

### 4.3 계약 불일치로 인한 롤백

- 웹이 새 계약을 기대하는데 서버가 구 계약이면 → 서버를 새 버전으로 올린다(웹 롤백 불필요).
- 서버가 새 계약인데 웹이 깨지면 → 웹을 이전 버전으로 롤백(Vercel Promote) 후 원인 분석.

---

## 5. 체크리스트

### 5.1 배포 전

- [ ] `packages/common/skinlens_contract/**` 변경 여부 확인 → 변경이면 **계약 변경** 절차(§2.2)
- [ ] `ENGINE_CONTRACT_VERSION` 을 올렸는가 (계약 변경 시)
- [ ] 엔진 / gateway / worker 가 같은 계약 버전을 참조하는가
- [ ] unit tests 통과 (`pytest -m "not integration"`)
- [ ] (계약 변경 시) integration tests 통과 (`pytest -m integration`)

### 5.2 AI Server 배포 후

- [ ] `deploy.sh` 헬스 게이트 통과 (자동)
- [ ] `GET /health/db` 200
- [ ] `GET /debug/engines` 정상 (엔진 연결 확인)
- [ ] 엔진 응답의 `contract_version` 이 새 버전인지 확인
- [ ] 실제 job 1건 완주 (`/jobs/{id}` 의 `done`)

### 5.3 웹 배포 후

- [ ] Vercel 빌드 성공
- [ ] `/` 로드, 로그인 동작
- [ ] `analyze()` 1건 완주 (presign → PUT → analyze → done)
- [ ] 결과 리포트(`/jobs/{id}/report`) 렌더링 확인

---

## 6. 참고 — 남아있는 정리 대상 (Phase 5 범위 밖)

다음은 Phase 5 가 아니라 **Phase 2/6 정리 대상** 이므로, 본 런북에서는 건드리지 않는다:

- [`deploy/nginx/conf.d/dev.conf`](../../deploy/nginx/conf.d/dev.conf), [`www.conf`](../../deploy/nginx/conf.d/www.conf)
  — `devpage` / `homepage` 프록시가 남아있으나, nginx 스택 전체 제거는
  계획 §2 "제거 대상 요약" 의 책임 이주 확정(rate limit→Caddy/gateway,
  security headers→Caddy, body-size→gateway) 후 진행.
- `apps/homepage/public/index.html` — Vercel 이관 또는 제거.

---

## 7. 관련 문서

- [`05_3Tier_이전_작업계획.md`](../architecture/05_3Tier_이전_작업계획.md) — Phase 5 본문
- [`04_3Tier_Vercel_Supabase_AIServer_설계.md`](../architecture/04_3Tier_Vercel_Supabase_AIServer_설계.md) — §리스크 표의 "웹/서버 배포 타이밍 → 계약 불일치" 항목
- [`packages/common/skinlens_contract/__init__.py`](../../packages/common/skinlens_contract/__init__.py) — 계약 단일 진실원본
- [`deploy/scripts/deploy.sh`](../../deploy/scripts/deploy.sh) — 헬스 게이트 + 롤백 로직
- [`09_Phase1_Supabase_실행런북.md`](./09_Phase1_Supabase_실행런북.md) — Supabase 측 런북
