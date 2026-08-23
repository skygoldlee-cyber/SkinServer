# SkinLens 3-Tier Migration Plan (SkinLens_3Tier_Migration.md) 검토 보고서

본 검토 보고서는 [SkinLens_3Tier_Migration.md](file:///c:/Project/SkinServer/SkinLens_3Tier_Migration.md)에 기술된 로컬 서버호스팅에서 **Vercel + Render + Supabase** 관리형 3-Tier 인프라로의 이관 계획을 아키텍처, CD 자동화, 데이터 설계, 비용 및 안정성 측면에서 종합적으로 검토한 결과입니다.

---

## 1. 아키텍처 및 설계 타당성 검토

### 1.1 GPU 제거 및 CPU 추론 전환 (타당성: 매우 높음 ✅)
- **판단**: 기존 `06_CI_CD_Vercel_Render_검토.md`에서 Render의 GPU 미지원을 가장 치명적인 제약으로 보았으나, 최종 본문에서 **"16MB 경량 CV 모델을 통한 CPU 추론 적용"**이 확정되면서 이 제약이 완전히 해소되었습니다.
- **결과**: 비싼 GPU 서버 운영 부담이 제거되었으며, Render의 일반 Standard 컨테이너 컴퓨트만으로도 성능 요건을 충족할 수 있어 비용/관리 효율성이 극대화됩니다.

### 1.2 presigned 업로드 구조 (타당성: 매우 높음 ✅)
- **판단**: 클라이언트가 gateway를 거치지 않고 Supabase Storage에 직접 PUT하고, gateway/worker는 `image_key`만 받아 처리하는 흐름은 클라우드 환경에서 대역폭 비용과 네트워크 지연을 줄이기 위한 모범 사례(Best Practice)입니다.
- **결과**: Render의 대역폭 요금(Egress GB당 $0.15)을 최소화하고 gateway 서비스의 메모리/네트워크 병목을 방지합니다.

### 1.3 Case A 보안 모델 (타당성: 높음 ✅)
- **판단**: 피부분석 및 처방 엔진이 완전한 무자격증명(No DB Credentials, No Supabase Key) 상태로 동작하고, gateway/worker가 프록시 및 권한 검증 주체가 되는 설계는 보안상 매우 안전합니다.
- **결과**: 만에 하나 엔진 서비스가 외부 침입을 당하거나 코드 취약점이 발생하더라도 DB 자격증명이 유출될 우려가 원천 차단됩니다.

---

## 2. 기술적 보완이 필요한 Gap 및 해결 방안

검토 과정에서 발견된 주요 기술적 Gap과 이를 해결하기 위한 구체적인 가이드는 다음과 같습니다.

### 2.1 Render Blueprint (`render.yaml`) 플레이스홀더 오류
- **문제점**: `render.yaml` 내 `image.url`에 작성된 `ghcr.io/<org>/engine-analysis:<sha>`는 초기 블루프린트 싱크 시점에 Render가 이미지를 찾지 못해 **싱크 실패 및 서비스 생성 실패**를 유발합니다. Render는 변수 보간이나 플레이스홀더를 파싱하지 못하기 때문입니다.
- **해결 방안**: 블루프린트 파일에는 최초 싱크가 가능한 고정된 태그(예: `ghcr.io/my-org/engine-analysis:latest` 또는 `ghcr.io/my-org/engine-analysis:main`)를 디폴트로 명시합니다. 이후 실제 버전 배포는 GitHub Actions CD 파이프라인에서 **Render Deploy Hook URL** 뒤에 `&imgURL=<image_tag>`를 덧붙여 호출(URL 인코딩 필수)함으로써 특정 커밋 SHA 버전으로 배포하도록 구성합니다.

### 2.2 데이터베이스 마이그레이션 타이밍 및 자동화
- **문제점**: 이관 계획서의 `render.yaml`에는 DB 마이그레이션(`alembic upgrade head`) 실행 지점 및 명령어가 누락되어 있습니다. 새 백엔드가 Vercel/Supabase와 연동될 때 스키마 불일치로 장애가 발생할 수 있습니다.
- **해결 방안**: Render의 `preDeployCommand` 기능을 활용합니다. `gateway` 서비스 정의에 `preDeployCommand`를 주입하여, 새 컨테이너 배포 전에 스키마 마이그레이션이 먼저 완수되도록 강제해야 합니다.
```yaml
  - type: web
    name: skinlens-gateway
    runtime: docker
    rootDir: services/gateway
    dockerfilePath: ./Dockerfile
    # preDeployCommand 추가
    preDeployCommand: alembic upgrade head
```

### 2.3 콜드 스타트 및 서비스 요금제(Plan) 명시
- **문제점**: Render의 기본 요금제는 `Free` 티어이며, 15분간 트래픽이 없으면 컨테이너가 내려갑니다(스핀다운). 이는 30초 이상의 콜드스타트 지연을 유발하여 상업 서비스에 치명적입니다. 블루프린트에는 Redis만 `plan: starter`로 되어 있고 gateway/worker/engine은 요금제가 누락되어 있습니다.
- **해결 방안**: 운영 환경용 `render.yaml`에는 `plan: starter` 또는 `plan: standard`를 각 서비스에 명시하여 상시 가동(Always-On) 상태를 보장해야 합니다.

---

## 3. 핵심 파일 구현 검토 및 적용

이관 계획서 §5.6에서 언급되었으나 실제 레포에 존재하지 않았던 핵심 파일들을 설계 요건에 맞춰 구현 및 검증 완료하였습니다.

### 3.1 회귀 게이트용 테스트 파일 생성
- **생성 경로**: [`tests/test_scoring_regression.py`](file:///c:/Project/SkinServer/tests/test_scoring_regression.py)
- **검증 내용**: 
  - **점수 허용오차(Tolerance)**: 난수 시드로 생성한 결정론적 테스트 이미지에 대해 BaselineScorer의 점수가 기준치(41.7점) 대비 허용오차(±2.0점) 범위 내에 있는지 검증.
  - **처방 비율 정확일치**: 점수 등급별 처방 비율 매핑이 계약 규칙(양호: 0.0%, 경미: 0.5%, 보통: 1.0%, 위험/심각: 3.0%)에 부합하는지 엣지 케이스 확인.
  - **계약 스키마 고정**: 출력 데이터의 10개 메트릭 필드가 변경되거나 누락되지 않았는지 데이터 타입 및 스키마 검증.
- **결과**: `pytest tests/test_scoring_regression.py -v` 실행 결과, 3개 테스트 케이스가 성공적으로 통과(Passed)하는 것을 확인했습니다.

### 3.2 GitHub Actions Render CD 워크플로 구현
- **생성 경로**: [`.github/workflows/engine-cd.yml`](file:///c:/Project/SkinServer/.github/workflows/engine-cd.yml)
- **검증 내용**:
  - **독립 배포**: `paths-filter`를 적용하여 `engine-analysis`나 `engine-prescription` 중 변경이 발생한 엔진만 빌드/배포되도록 최적화.
  - **회귀 게이트**: 이미지 빌드 및 배포 전에 `tests/test_scoring_regression.py`와 일반 단위 테스트가 먼저 통과해야만 이미지 푸시 및 배포 단계로 진입하도록 설계.
  - **안전한 배포 트리거**: Render Deploy Hook을 호출할 때 이미지 태그를 URL 인코딩(`python3 -c "import urllib.parse..."`)하여 전송하도록 보완함으로써 배포 실패 리스크를 방지.
  - **Docker Context 조정**: 각 서비스 Dockerfile 빌드 시 context를 `services/${{ matrix.service }}`로 올바르게 설정하여, Dockerfile 내 `requirements.txt`와 `app` 파일 복사 레이아웃이 정확히 일치하도록 조치.

---

## 4. 최종 의견 및 액션 아이템

본 이관 계획서는 기존 self-hosted 배포 구조의 무중단/롤백 로직을 Render의 관리형 클라우드 배포 주기로 성공적으로 녹여냈습니다. 특히 비용 예측($70) 및 egress 방어용 presigned 설계가 매우 탄탄합니다.

### 🚀 후속 진행을 위한 액션 아이템
1. **GitHub Secrets 설정**:
   - `RENDER_DEPLOY_HOOK_ANALYSIS_STAGING` / `_PROD`
   - `RENDER_DEPLOY_HOOK_PRESCRIPTION_STAGING` / `_PROD`
   위 CD 트리거용 4개 Deploy Hook URL을 GitHub 레포지토리 Settings -> Secrets에 등록해 주십시오.
2. **`render.yaml` 보완**:
   - `engine-analysis`, `engine-prescription`의 `image.url`을 임시 플레이스홀더 `<sha>` 대신 초기 구동이 가능한 stable 이미지명(예: `ghcr.io/my-org/engine-analysis:latest`)으로 수정해 주십시오.
   - 각 서비스에 `plan: starter`를 추가하여 콜드스타트 현상을 방지해 주십시오.
3. **Supabase CORS/Storage 설정**:
   - Supabase Storage 버킷 생성 및 RLS 정책을 활성화한 후, Vercel 프론트엔드 도메인을 Supabase와 Render Gateway CORS 허용 목록(`CORS_ORIGINS`)에 추가해야 합니다.
