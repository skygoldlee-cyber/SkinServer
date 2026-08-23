# [가이드] SkinLens 통합 배포 스택 (`deploy/`) 폴더 구성 및 역할 상세

`deploy/` 폴더는 SkinLens 플랫폼의 **인프라 설정, 데이터베이스 설계, 보안 정책, 배포/운영 자동화 스크립트** 등을 통합 관리하는 핵심 인프라 영역입니다. 단일 **Monorepo** 구조 내에서 코드와 환경 설정을 동기화하여 버전 관리를 보장합니다.

아래는 `deploy/` 하위 8개 폴더의 세부 구성 요소와 각각의 역할 및 기능 설명입니다.

---

## 1. `deploy/compose/` (Docker 컨테이너 오케스트레이션)
Docker Compose를 사용하여 마이크로서비스 및 인프라 컨테이너 스택을 환경별로 정의하고 오버레이합니다.

*   [`compose.base.yml`](../deploy/compose/compose.base.yml):
    *   **역할**: 전체 서비스의 표준 뼈대를 정의하는 **단일 진실 원본(Single Source of Truth)**.
    *   **기능**:
        *   네트워크 3분할(`frontnet`, `appnet`, `enginenet`) 설계.
        *   컨테이너 수준 보안 하드닝 적용(비루트 계정 실행, `no-new-privileges`, `cap_drop`으로 시스템 권한 최소화, 리소스 사용 상한선 제어).
        *   Gateway, Worker, Nginx, AI/처방 엔진 등 핵심 서비스 정의.
*   [`compose.dev.yml`](../deploy/compose/compose.dev.yml):
    *   **역할**: 로컬 개발(Development) 환경용 오버레이.
    *   **기능**: 소스 코드의 실시간 마운트(Volume Bind) 및 로컬 데이터베이스 띄우기용 설정 포함.
*   [`compose.staging.yml`](../deploy/compose/compose.staging.yml):
    *   **역할**: 스테이징(Staging) 환경용 오버레이.
    *   **기능**: 로컬 DB 대역(Supabase 대리) 및 사전에 빌드된 GHCR 이미지 태그 로드.
*   [`compose.prod.yml`](../deploy/compose/compose.prod.yml):
    *   **역할**: 운영(Production) 환경용 오버레이.
    *   **기능**: 자체 DB 컨테이너 없이 클라우드 관리형 Supabase DB를 바로 사용하도록 배선.
*   [`compose.gpu.yml`](../deploy/compose/compose.gpu.yml):
    *   **역할**: AI 엔진용 GPU 지원 및 동시성 제어 오버레이.
    *   **기능**: NVIDIA GPU 런타임 배선 및 엔진 컨테이너 동시성 제한 설정.
*   [`compose.tls.yml`](../deploy/compose/compose.tls.yml):
    *   **역할**: TLS(HTTPS) 강제화 설정.
    *   **기능**: Caddy 프록시를 활성화하여 자동 SSL/TLS 인증서 발급 및 HSTS 헤더 주입.

---

## 2. `deploy/nginx/` (엣지 웹 프록시 및 외부 라우팅)
외부 요청을 받아 내부 서비스로 라우팅하고, 1차 보안 방어선 역할을 수행하는 Nginx 설정 파일 그룹입니다.

*   `conf.d/` (호스트별 라우팅):
    *   `www.conf`: 사용자 웹사이트(홈페이지) 서빙 설정.
    *   `dev.conf`: 개발자 전용 관리 콘솔 라우팅 및 Basic Auth(기본 인증) 설정.
    *   `app.conf`: **Vite+React PWA 웹앱 표면** 서빙 및 동일 오리진(`/api/` ➔ Gateway) 프록시 라우팅.
    *   `api.conf`: **API Gateway 라우팅** 및 대용량 업로드 제한(25MB), 레이트 리밋(Rate Limiting)을 통한 DDoS 차단.
    *   [`00-hardening.conf`](../deploy/nginx/conf.d/00-hardening.conf): http 전역 설정 하드닝(버전 비공개, 레이트 리밋 존 설정).
*   `snippets/` (공통 재사용 설정):
    *   `security-headers.conf`: 클릭재킹/XSS 등을 방지하는 HTTP 보안 헤더 설정.
    *   `proxy-common.conf`: 백엔드로 클라이언트의 실 IP 및 프로토콜을 전달하는 프록시 헤더 템플릿.
    *   `csp-app.conf`: 앱 PWA 전용 **콘텐츠 보안 정책(CSP)** (Supabase 및 자체 도메인 오리진만 통신 허용).
*   `.htpasswd.example`: 개발자 페이지 접근 제어를 위한 Basic Auth Bcrypt 해시 샘플.

---

## 3. `deploy/caddy/` (자동 TLS 엣지 Caddy)
*   [`Caddyfile`](../deploy/caddy/Caddyfile):
    *   **역할**: Caddy 리버스 프록시 설정 파일.
    *   **기능**: 도메인 지정 시 Let's Encrypt를 통해 인증서를 자동으로 생성·갱신하고 HTTPS/HSTS 적용을 간소화.

---

## 4. `deploy/env/` (환경 정보 템플릿)
*   [`.env.example`](../deploy/env/.env.example):
    *   **역할**: 각 서비스 및 인프라의 비밀 키, 포트, URL 등의 설정 목록 정의서. (실제 환경에서는 `.env`로 파일 생성 후 수정사용)
*   [`.env.images.example`](../deploy/env/.env.images.example):
    *   **역할**: 컨테이너 이미지 태그 관리.
    *   **기능**: GitHub Actions CI/CD 파이프라인에서 배포 시 태그 버전을 기록하여, 배포 스크립트 실행 및 롤백 시 단일 참조점이 됨.

---

## 5. `deploy/scripts/` (인프라 자동화 스크립트)
서버의 구축, 배포, 모니터링, 이관, 백업 등을 자동화하는 핵심 실행 스크립트 모음입니다.

*   [`deploy.sh`](../deploy/scripts/deploy.sh):
    *   **기능**: 무중단 배포 및 롤백 스크립트. GHCR에서 이미지를 당겨온 뒤 순차적으로 컨테이너를 구동하고, 헬스 게이트 체크 실패 시 이전 `.env.images` 상태로 즉시 롤백을 처리(Atomic deployment).
*   `verify_*.sh / verify_client.ps1`:
    *   **기능**: 환경 검증용 자가 진단 스크립트. 서버 방화벽 규격, 컨테이너 하드닝 설정 위반 여부, 클라이언트 통신 포트 상태 등을 모듈형 테스트로 검증.
*   `pg_backup.sh`:
    *   **기능**: PostgreSQL DB 백업 스크립트. 오프사이트 복사, 암호화, 보존 연한 관리 및 데드맨 스위치 알림(성공 시 핑 전송) 기능 내장.
*   `migrate_export.sh / migrate_import.sh`:
    *   **기능**: 서버 이관 런북 자동화 스크립트. 쓰기를 잠시 차단(ReadOnly)하고 최종 DB 및 스토리지 델타 데이터를 암호화하여 타겟 서버로 이관 및 복구.

---

## 6. `deploy/supabase/` (클라우드 DB 보안 정책)
*   [`0001_rls_and_storage.sql`](../deploy/supabase/policies/0001_rls_and_storage.sql):
    *   **역할**: Supabase DB 및 스토리지의 접근 제어.
    *   **기능**: 행 단위 보안(RLS)을 적용하여 로그인한 사용자의 JWT UID가 자신의 행(`jobs.user_id`)과 일치할 때만 데이터 접근을 허용하고, 스토리지 버킷을 비공개로 유지하여 Presigned URL 방식으로만 접근을 통제.

---

## 7. `deploy/db/` (스키마 마이그레이션)
*   [`migrations/0001_init.sql`](../deploy/db/migrations/0001_init.sql):
    *   **역할**: 서비스 가동을 위한 최초/기본 DB 스키마.
    *   **기능**: 테이블 구조(jobs, users, reports 등) 및 제약 조건을 정의하며 운영 환경에서 자동 DDL 대신 명시적으로 실행되는 원본 스키마.
*   [`README.md`](../deploy/db/README.md):
    *   **역할**: 스키마의 롤백 및 적용 가이드.
    *   **기능**: 마이그레이션 적용 및 expand-contract(확장-축소) 기법을 통한 데이터 무결성 보존 롤백 런북 수록.

---

## 8. `deploy/ops-jobs/` (운영 배치 및 관측성 개선)
서비스 가동 이후 백그라운드에서 주기적으로 돌아가는 배치 작업 및 모니터링 모듈입니다.

*   `retention.py`:
    *   **기능**: 개인정보 보호 정책(PIPA) 및 스토리지 효율화를 위해, 분석이 완료된 지 일정 기한이 지난 원본 이미지 및 미완료된 폐기 대상 Job 데이터를 Supabase Storage/DB에서 삭제하는 배치 스크립트.
*   `log-scrub.py`:
    *   **기능**: PII(개인 식별 정보) 보안 필터. 어플리케이션 로그 스트림에서 전화번호, 주소, JWT 토큰 등을 정규식으로 실시간 감지하여 마스킹(`[SCRUBBED]`) 처리.
*   `nginx-log-privacy.conf`:
    *   **기능**: Nginx 로그 프라이버시 설정. 접근 로그에서 쿼리 스트링이나 인증 정보를 포함하는 URI 필드를 저장소에서 물리적으로 배제.
*   `observability/`:
    *   **기능**: 통합 로깅 및 모니터링. 크론탭을 활용하여 비정상 예외 또는 리소스 한계 도달 시 Webhook 알림(`alert.sh`)을 연동.
*   `restore-rehearsal.sh`:
    *   **기능**: 백업 무결성 모의 훈련. 백업 파일을 자동으로 복원하여 스테이징 환경에서 무결성 검사를 실행하고 RPO/RTO 메트릭을 기록.
