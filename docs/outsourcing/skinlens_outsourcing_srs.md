# [요구사양 명세서] SkinLens AI 피부분석 · 처방 플랫폼 외주개발

본 문서는 **SkinLens (AI 피부분석 · 처방 플랫폼)** 프로젝트를 외부 전문 개발사에 외주 개발 위탁하기 위해 작성된 **요구사양 명세서 (Software Requirements Specification - SRS)** 입니다. 

현재 SkinLens 프로젝트는 **인프라 환경 구축, 컨테이너 오케스트레이션, 3망 분리 네트워크 설계 및 CI/CD 자동화 파이프라인(배포/롤백)**의 골격이 완비된 상태입니다. 개발사는 본 문서에 명시된 아키텍처 규칙과 인터페이스 계약을 준수하여 **실제 비즈니스 로직 구현, 엔진 알고리즘 고도화, 데이터베이스 마이그레이션 및 신뢰성/보안성 강화** 과업을 완료해야 합니다.

---

## 1. 프로젝트 개요 및 아키텍처

SkinLens는 사용자의 피부 사진 및 설문 데이터를 분석하여, 개인 맞춤형 처방 믹스를 추천하는 AI 기반 플랫폼입니다. 본 프로젝트는 코드, 인프라 설정, 문서를 단일 Monorepo로 관리합니다.

### 1.1 전체 시스템 구조 (Monorepo)
```
skinlens/
├── apps/              # 프론트 표면 (Vite+React PWA 앱 셸, 홈페이지, 개발자 콘솔)
├── services/          # 백엔드 마이크로서비스 (gateway, worker, engine-analysis, engine-prescription)
├── packages/          # 서비스 간 공유 계약 및 공용 라이브러리
├── deploy/            # Docker Compose, Nginx, Caddy, DB 스키마, 백업/모니터링 스크립트
├── tests/             # pytest 기반 통합/스모크 테스트 코드
└── docs/              # 시스템 설계 및 아키텍처 가이드 문서
```

### 1.2 네트워크 3분할 및 보안 아키텍처 (Case A 격리 원칙)
개발사는 아래 명시된 **네트워크 분리 규칙**을 절대적으로 유지해야 합니다.
*   **frontnet (외부망)**: Nginx 엣지 프록시와 프론트엔드 표면 앱 간의 통신망.
*   **appnet (내부망)**: 외부와 직접 단절된 영역으로 Gateway, Worker, DB(PostgreSQL/Supabase)가 존재함.
*   **enginenet (폐쇄망)**: `internal: true`로 설정된 완전 격리망. `engine-analysis` 및 `engine-prescription` 엔진 컨테이너만 이 망에 소속되며, 포트 발행 금지, 자격 증명(Credential) 사용 불가, 외부 인터넷 Egress가 원천 금지됩니다.
    > [!IMPORTANT]
    > 모든 AI 분석 및 처방 엔진은 인터넷 연결 없이 로컬 컨테이너 내에서 독립적으로 실행되어야 하며, Gateway 또는 Worker의 프록시 요청을 통해서만 접근해야 합니다.

---

## 2. 현재 개발 현황 (Baseline)

현재 프로젝트는 아래와 같이 **Phase 1 및 Phase 2의 기본 구조가 설계 및 검증**되어 있습니다.
*   **비동기 Job 처리 흐름 완비**: Gateway가 사진/설문을 수신하면 데이터베이스에 Job을 생성하고 즉시 `job_id`를 반환합니다. Worker는 DB에서 대기 상태(`queued`)의 Job을 순차적으로 가져와(`FOR UPDATE SKIP LOCKED`) 각 엔진을 호출한 후 최종 결과를 기록합니다.
*   **환경 오버레이 배포 구조**: 개발(`dev`), 스테이징(`staging`), 운영(`production`) 환경이 Docker Compose 오버레이 스택으로 구성되어 있으며, `deploy/scripts/deploy.sh`를 통해 **원자적 교체, 헬스체크 게이트 점검, 실패 시 자동 롤백**이 가동됩니다.
*   **인프라 하드닝**: WSL2 Ubuntu 및 클라우드 서버 대상 방화벽(UFW), 컨테이너 비루트 권한 실행(`cap_drop`, `no-new-privileges`), Nginx 보안 헤더 및 Rate Limit이 스캐폴딩 상태로 반영되어 있습니다.
*   **원격 모니터링·제어 레이어**: 외부 Windows 환경에서 SSH 단일 회선(신규 포트·데몬 없음)으로 리눅스 서버 상태를 조회·제어하는 채널이 구축되어 있습니다. 서버 측 읽기 전용 스냅샷 에이전트(`deploy/ops/remote-status.sh`, 1왕복 수집)와 Windows 클라이언트(`deploy/scripts/remote.ps1`·`remote.cmd`)가 서버 측 기존 CLI(`sl`, `deploy.sh`)를 원격 구동합니다(런북: [`docs/operations/11_원격_모니터링_제어.md`](../operations/11_원격_모니터링_제어.md)).
*   **관측성·개인정보 운영 잡**: 구조적 JSON 로깅 + `job_id` 상관ID(`observability/logging_config.py`), 디스크/VRAM/큐 임계 알림(`observability/alert.sh`), PII/토큰 로그 마스킹(`log-scrub.py`), 완료 원본 삭제 보존 잡(`retention.py`), 백업 복구 리허설(`restore-rehearsal.*`)이 `deploy/ops-jobs/`에 파일로 반영되어 있습니다.

---

## 3. 외주 개발 범위 및 상세 기술 규격 (Scope of Work)

개발사는 아래의 5가지 핵심 영역에 대한 상세 기능을 구현하고 검증해야 합니다.

### 3.1 [API Gateway] 입력 데이터 검증 및 예외 처리 고도화
*   **업로드 이미지 보안 검증**:
    *   `services/gateway` API 진입점에서 멀티파트 업로드 이미지의 **최대 크기를 25MB로 엄격히 제한**합니다. (Nginx 단과 Gateway 애플리케이션 단의 2중 방어선 구축)
    *   단순 파일 확장자 검사(`.png`, `.jpg`)에 의존하지 않고, 파일의 첫 8바이트 바이너리를 분석하는 **매직 바이트(Magic Byte) 시그니처 검증**을 필수 구현하여 웹셸 및 임베디드 악성 스크립트 실행 파일의 우회 업로드를 차단합니다.
        *   허용 형식: `image/jpeg` (`FF D8 FF`), `image/png` (`89 50 4E 47 0D 0A 1A 0A`), `image/webp` (`52 49 46 46 ... 57 45 42 50`)
*   **설문 및 PCR 데이터 검증**:
    *   요청 본문에 포함된 `survey` 및 `pcr` JSON 문자열을 `packages/common/skinlens_contract`에 정의된 Pydantic 모델 스키마와 정합성 검증을 거친 후 DB에 저장합니다.
    *   정의되지 않은 필드 유입, 필수 필드 누락, 허용 수치 범위를 초과하는 악의적 페이로드에 대해 `400 Bad Request`로 즉시 거부해야 합니다.
*   **안전한 임시 파일 영속화 및 가비지 컬렉션**:
    *   대용량 이미지 유입 시 메모리 고갈을 방지하기 위해 파일 스트림 형태로 로컬 버퍼에 임시 기록한 후 Supabase Storage로 전송해야 합니다.
    *   네트워크 단절, 클라이언트 업로드 취소, 비즈니스 에러 발생 등 모든 예외 경로에서 임시 버퍼 파일이 로컬 스토리지에 잔류하지 않도록 `finally` 블록 혹은 컨텍스트 매니저(`with` 문)를 사용해 확실히 가비지 컬렉션(삭제)해야 합니다.

### 3.2 [Worker] 비동기 처리 정합성 및 장애 대응
*   **동시성 제어 및 멱등성 보장**:
    *   복수 워커 인스턴스 환경에서 큐 스케일 아웃 시 발생할 수 있는 동일 Job 중복 소비 방지를 위해, PostgreSQL의 로우 단위 락(`SELECT FOR UPDATE SKIP LOCKED`)을 적용합니다.
    *   Job 상태 전이(`queued` ➔ `processing` ➔ `done`/`error`)는 데이터베이스 트랜잭션 범위 내에서 원자적으로 처리되어야 합니다.
*   **재시도 및 백오프 아키텍처**:
    *   폐쇄망 엔진 호출 시 임시적인 네트워크 타임아웃이나 컨테이너 리부팅 등의 일시적 장애가 발생할 경우를 대비하여, **지수 백오프(Exponential Backoff) 기반의 재시도**를 구현합니다.
    *   환경 변수(`ENGINE_RETRIES`, 기본값: 3회)를 준수하며, 백오프 수식은 $2^{\text{retry\_count}} \times \text{base\_delay}$ (예: 2초, 4초, 8초 대기)을 기본으로 하고 지터(Jitter)를 가미하여 데이터베이스 병목을 분산시킵니다.
*   **에러 전파 및 Dead-Letter 처리**:
    *   최대 재시도 횟수를 초과하거나 치명적 예외 발생 시, 해당 작업 상태를 `error`로 마킹합니다.
    *   이때 데이터베이스 `jobs` 테이블의 `error_reason`, `failed_step`, `error_details` 필드에 예외 스택 및 구체적인 실패 원인(예: `ANALYSIS_ENGINE_TIMEOUT`, `PRESCRIPTION_RULE_VIOLATION`)을 규격화된 JSON 포맷으로 세밀히 기록하여 프론트엔드 폴링 단에서 에러 사유를 명확히 안내할 수 있도록 합니다.

### 3.3 [AI & 처방 엔진] 실측 알고리즘 및 도메인 규칙 연동
*   **피부분석 엔진 (`engine-analysis` 고도화)**:
    *   **얼굴 ROI 세부 분할 및 마스킹**: 전통적인 Haar Cascade 사각형 검출을 전면 제거하고, **MediaPipe FaceMesh** 또는 **RetinaFace**를 탑재하여 얼굴의 랜드마크를 468개 이상 추출합니다. 이를 통해 이마, 코, 양 볼, 턱 등 5대 관심 영역(ROI)을 픽셀 마스크 단위로 정확히 분할 크롭하고, 눈, 눈썹, 입술, 치아 등 비피부 노이즈 영역은 마스킹하여 분석 대상에서 완벽히 배제해야 합니다.
    *   **입력 화질 및 조명 정규화**: 촬영 기기, 화이트 밸런스, 환경광(형광등 vs 자연광)의 영향을 억제하기 위해 **그레이 카드 캘리브레이션** 및 색상 오토 밸런싱 필터를 선행 적용하여 10개 지표 분석의 일관성을 확보합니다.
    *   **화질 복원 모듈 탑재**: 저조도/흐림 이미지 복원을 위해 **CodeFormer** 모델을 탑재하되, 복원으로 인한 미세 주름/트러블 왜곡을 방지하기 위해 이미지 품질 평가(IQA) 임계치를 기준으로 복원 적용을 분기하는 온/오프 정책(Toggle Policy)을 구현해야 합니다.
    *   **MLScorer 추론 파이프라인**: 향후 전통 CV 기반 Baseline 알고리즘에서 딥러닝 추론 모델(PyTorch/ONNX Runtime)로의 전환이 원활하도록 `services/engine-analysis/app/model.py` 내의 `MLScorer` Seam 인터페이스를 완벽하게 유지해야 합니다.
*   **처방 엔진 (`engine-prescription` 고도화)**:
    *   **다차원 의사결정 처방 매트릭스**: 단순 개별 점수 합산 매핑을 폐기하고, **[CV 분석 지표(10종) × 설문 응답(민감도, 복합성 등) × PCR 유전적 요인]**의 다차원 연산 매트릭스를 기반으로 최종 처방 믹스(M01~M11, PM01~PM03)를 도출하는 규칙 엔진을 개발해야 합니다.
    *   **안전성 교차 금기 검증 (Safety Filter)**: 여러 개의 처방 믹스가 중복 배정될 시 발생할 수 있는 성분 간 상호작용 부작용(예: 레티놀과 고농도 비타민C 복용 중첩 제한, 과도한 AHA/BHA 병용 차단 등)을 필터링하는 **안전성 룰 엔진**을 최종 파이프라인 단계에 탑재해야 합니다.
    *   **동적 함량 최적화 (INCI Level)**: 고정된 화장품 믹스 번호 제공을 넘어, 피부 민감도 및 장벽 점수에 따라 각 활성 성분의 **동적 최적 배합 비율(%)**을 정밀 계산하여 제조 장치 규격에 맞게 산출하는 정밀 연산 로직을 구현합니다.
    *   **피드백 루프 피팅 설계 (RLUF)**: 사용자의 4주 사용 만족도 데이터 및 재촬영 델타 값을 수집하여 처방 기준(Threshold) 점수 분포 및 가중치를 역전파 미세 조정하는 학습 데이터 파이프라인을 설계해야 합니다.
*   **엔진 공통 인터페이스 및 가중치 오프라인 로딩 규격 (중요)**:
    *   **오프라인 가중치(Weights) 번들링**: 두 엔진 모두 외부 인터넷 Egress가 원천 금지된 완전 폐쇄망(`enginenet`) 내에서 동작해야 합니다. 따라서 MediaPipe FaceMesh, RetinaFace, CodeFormer 등의 모든 AI/ML 모델 가중치 파일(`.pth`, `.onnx` 등)은 컨테이너 실행 중 동적으로 다운로드할 수 없으며, Docker 이미지 빌드 단계에서 레이어 내에 직접 포함하여 오프라인으로 즉시 로드될 수 있도록 패키징해야 합니다.
    *   **표준 헬스체크 API (`GET /healthz`)**: Gateway 및 Worker의 헬스체크 게이트 점검과 런타임 관측성(Observability) 확보를 위해 각 엔진은 모델 로딩 및 준비 상태를 검증하여 성공 시 `200 OK`를 반환하는 `/healthz` 엔드포인트를 필수로 제공해야 합니다.


### 3.4 [Supabase] 데이터 계층 마이그레이션 및 RLS 보안 강화
*   **클라우드 DB 이관 설계**: `staging`의 로컬 DB 구조를 `production` 환경에서 관리형 **Supabase DB** 인프라로 원활히 연결할 수 있도록 DB 연결 팩토리 및 마이그레이션 파이프라인을 정비합니다.
*   **행 단위 보안 정책 (RLS) 적용 및 검증**:
    *   `deploy/supabase/policies/0001_rls_and_storage.sql`에 기술된 RLS 설정을 데이터베이스에 온전히 배선하고 작동을 검증해야 합니다.
    *   로그인한 사용자의 JWT 클레임(`auth.uid()`)과 해당 데이터 행의 소유자 ID(`jobs.user_id`)가 일치할 때만 `SELECT` 및 `INSERT`를 허용하며, 비정상적 교차 접근 시 `404 Not Found` 또는 `403 Forbidden`을 반환해야 합니다.
*   **비공개 스토리지 버킷 및 서명된 URL 제공**:
    *   Supabase Storage 내의 피부 사진 및 분석 결과 리포트 리소스 버킷을 **Private**으로 고정합니다.
    *   클라이언트는 해당 사진에 직접 링크할 수 없으며, API Gateway가 발급한 제한된 유효 시간(예: 15분)의 **서명된 URL(Presigned URL)**을 통해서만 한시적으로 렌더링되도록 구현해야 합니다.
    *   **Presigned URL 캐싱**: 조회 성능 개선 및 Supabase Storage API 호출 오버헤드를 방지하기 위해, 발급된 Presigned URL을 Redis 분산 캐시 레이어에 유효시간보다 약간 짧게(예: 10~12분) 캐싱하여 서빙하도록 구현해야 합니다.


### 3.5 [비기능 및 운영 자동화] 신뢰성 · 성능 · 관측성 개선

> 현재 Baseline에 이미 반영된 항목(구조적 로깅·임계 알림·로그 스크러빙·복구 리허설 파일, 원격 모니터링·제어 레이어)은 개발사가 **확장·완성**하는 대상이며, 신규 착수가 아닙니다.
*   **성능 개선**:
    *   **커넥션 풀 최적화**: DB 동시 커넥션 누수를 방지하기 위해 SQLAlchemy의 `QueuePool` 커넥션 풀링을 사용하되, Gateway와 Worker의 풀 크기(`pool_size`) 및 최대 오버플로우(`max_overflow`) 설정 합산치(동시 최대 커넥션 수)가 Supabase DB 인프라의 최대 커넥션 임계치를 초과하지 않도록 조율해야 합니다.
    *   **조회 캐시 레이어**: 잦은 조회성 결과 요청에 대응하기 위해 Redis 기반 분산 캐시 레이어 진입점 설정을 배선합니다.

*   **개인정보보호 및 로그 마스킹**:
    *   수집된 로그 및 컨테이너 출력 파일 내의 PII(주소, 전화번호 등)와 Bearer JWT 토큰 등의 보안 민감 데이터를 실시간 감지하여 은닉 처리하는 **`log-scrub.py` 필터**를 구현하고 배포 스택에 통합합니다.
    *   Nginx 엣지 프록시 로그에서 쿼리스트링 및 Authorization 헤더 값을 무조건 배제하는 정책을 `nginx-log-privacy.conf`로 완성합니다.
*   **재해 복구(DR) 리허설 자동화**:
    *   `deploy/ops-jobs/restore-rehearsal.sh`를 완성하여 매주 1회 백업 파일 압축 해제, 스테이징 DB 스키마 복원, 데이터 무결성 체크 및 RPO(복구시점목표)/RTO(복구시간목표) 수치를 측정하는 모의 훈련 작업을 크론탭 잡에 정식 배선합니다.
    *   스테이징에서 1회 실행하여 RPO/RTO를 `restore-rehearsal.md` 기록표에 실제 기록합니다.

> [!NOTE]
> 원격 모니터링·제어 이외에 남은 보완 항목(관측성 심화, 테스트·품질 게이트, DR·용량, 개인정보·보안, 미결 결정사항, 문서)과 권장 우선순위는 [`docs/roadmap/05_보완항목_정리.md`](../roadmap/05_보완항목_정리.md)에 도메인별로 정리되어 있습니다.

---

## 4. 모바일 앱(Flutter) ↔ 서버 API 연동 계약

모바일 클라이언트와의 연동을 위해 다음 API 명세 및 오류 처리 규칙을 완벽하게 충족해야 합니다.

### 4.1 비동기 피부분석 요청 (`POST /analyze`)
*   **프로토콜**: `HTTP/1.1`, `multipart/form-data`
*   **인증 헤더**: `Authorization: Bearer <supabase-jwt>`
*   **Payload 구성**:
    *   `image`: 바이너리 파일 (JPEG/PNG/WEBP, ≤25MB, 매직 바이트 검증 대상)
    *   `survey`: JSON string (Pydantic 스키마 검증 대상, Optional)
    *   `pcr`: JSON string (Pydantic 스키마 검증 대상, Optional)
*   **응답 (HTTP 202 Accepted)**:
    ```json
    {
      "job_id": "8f8b50f7-64df-4161-b586-7a91176b6a0a",
      "status": "queued"
    }
    ```

### 4.2 분석 결과 폴링 조회 (`GET /jobs/{job_id}`)
*   **인증 헤더**: `Authorization: Bearer <supabase-jwt>` (본인의 작업만 조회 가능)
*   **응답 예시 (HTTP 200 OK - 작업 완료 시)**:
    ```json
    {
      "job_id": "8f8b50f7-64df-4161-b586-7a91176b6a0a",
      "status": "done",
      "result": {
        "analysis": {
          "score": 72.4,
          "metrics": {
            "redness": { "value": 15.2, "source": "cv" },
            "sebum": { "value": 65.0, "source": "survey" }
          }
        },
        "prescription": {
          "grade": "경미",
          "prescription_ratio_pct": 0.5,
          "selected_mixes": [
            { "mix": "M06", "reason": "sensitivity=위험/심각" }
          ],
          "concerns": ["redness", "dryness"]
        }
      }
    }
    ```

### 4.3 오류 대응 표준 (RFC 7807 구현)
모든 에러 응답은 일관된 예외 디버깅을 위해 RFC 7807 규격을 따릅니다.
*   **400 Bad Request**: 필수 파일 누락, JSON 파싱 실패 또는 Pydantic 스키마 검증 실패
*   **413 Payload Too Large**: 이미지 파일 크기가 25MB를 초과한 경우
*   **415 Unsupported Media Type**: 이미지 실제 매직 바이트 형식이 규격 외인 경우
*   **404 Not Found**: 요청한 `job_id`가 존재하지 않거나, 조회자의 JWT `uid`와 작업 소유자가 일치하지 않는 경우
*   **500 Internal Server Error**: 내부 엔진 실행 실패 등 서버 장애 발생 시

---

## 5. 산출물 및 인도 조건

외주 계약 완료 시 인도해야 할 필수 산출물 및 품질 검증 기준은 다음과 같습니다.

### 5.1 필수 인도 산출물
1.  **소스 코드**: Gateway, Worker, Engine-Analysis, Engine-Prescription 서비스 내 완료된 전체 파이썬 소스 코드 (Monorepo 형식 유지)
2.  **테스트 스위트**: 주요 로직(이미지 유효성 검사, 분석/처방 알고리즘, 에러 처리 백오프)을 검증하는 `pytest` 단위 및 통합 테스트 코드 (테스트 커버리지 85% 이상 달성 필수)
3.  **인프라 설정 코드**: 배포에 즉시 활용할 수 있는 `compose.prod.yml`, Nginx/Caddy 설정 파일 및 Supabase 정책 SQL 스크립트 정본
4.  **결과 보고서**: `pytest` 커버리지 리포트, 부하 테스트 결과표 및 Supabase RLS 취약점 검증 테스트 결과 보고서

### 5.2 검증 및 통과 기준 (Acceptance Criteria)
*   **자동화 테스트 통과**: 개발자가 작성한 `tests/` 디렉토리 하위의 모든 테스트 코드가 에러 없이 **100% 성공** 통과해야 합니다. 외주 개발사는 기존 `tests/`의 통합 테스트 Baseline을 확장하여 **교차 사용자 권한 접근 차단(404/403)** 및 **25MB 초과 대용량 이미지 업로드 거부(413)** 시나리오를 검증하는 테스트 코드를 필수로 작성하고 이를 통과해야 합니다.
*   **배포 스크립트 무중단 검증**: 변경된 코드를 반영하고 `deploy/scripts/deploy.sh`를 실행 시, **자동 헬스체크 게이트 점검을 정상적으로 완료**하고 무중단(또는 롤백 프로세스) 상태를 온전히 검증해야 합니다.
*   **하드닝 규격 준수**: 실행 환경에서 임의의 컨테이너를 강제 감사할 시, 비루트(Non-root) 계정 실행 및 파일 시스템 쓰기 금지(Read-only rootfs) 등의 하드닝 요건이 깨지지 않아야 합니다.
*   **보안 검증**: 타 사용자의 Access Token으로 다른 사용자의 피부분석 결과 조회를 시도할 때 반드시 HTTP 404 또는 403 오류가 반환되어야 합니다.

