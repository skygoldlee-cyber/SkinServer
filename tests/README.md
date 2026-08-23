# tests — 파트별 단위 테스트

인프라(DB/도커) 없이 도는 순수 단위/계약 테스트. `make test` 또는 `pytest`.

| 파트 | 파일 | 커버 |
|---|---|---|
| 공용 계약 | `common/test_contract.py` | 10지표·단계·등급경계·Survey·스키마 |
| gateway | `gateway/test_validation.py` | 이미지 검증(415/413/400)·인증(dev/strict 401/UUID) |
| gateway | `gateway/test_storage.py` | 로컬 저장·경로탈출 차단·백엔드 선택·supabase 스텁 |
| gateway | `gateway/test_logging.py` | JSON 로깅 포맷·상관필드 |
| gateway | `gateway/test_health.py` | `/health`·`/`(TestClient, 무DB) |
| worker | `worker/test_retry.py` | 엔진 호출 재시도/소진 |
| engine-analysis | `engine_analysis/test_metrics.py` | 10지표 존재·범위·종합점수 |
| engine-analysis | `engine_analysis/test_roi.py` | ROI 크롭·폴백 |
| engine-analysis | `engine_analysis/test_score_endpoint.py` | `/score` 스키마검증·잘못된 이미지 400 |
| engine-prescription | `engine_prescription/test_rules.py` | 등급·믹스 선택·placeholder 제외·PCR |
| engine-prescription | `engine_prescription/test_survey.py` | 설문→지표 매핑 |
| engine-prescription | `engine_prescription/test_prescribe_endpoint.py` | `/prescribe` 입력조합·400 |

> 세 서비스가 모두 `app` 패키지라 한 세션 임포트 충돌을 피하려고 `tests/_util.py::load`
> 가 서비스별로 격리 로딩한다. DB/도커가 필요한 종단(E2E) 검증은 통합 테스트
> (`tests/test_environment.py`, 서버 실행 후)로 분리.

## 통합 테스트 (DB 필요)

`tests/integration/` — 임시 Postgres + 엔진 서브프로세스로 종단 검증. `integration` 마커.

| 파일 | 커버 |
|---|---|
| `integration/test_pipeline.py` | gateway `/analyze`(사진+설문) → worker(claim→analysis→prescription) → `jobs`/`job_events`/`prescriptions` 기록, 단계 순서, 설문→민감성 반영 |
| `integration/test_pipeline.py::…reaper` | 멈춘 processing 재큐 + attempts 소진 데드레터 |

실행:
```bash
export DATABASE_URL=postgresql://appuser:app_pw@localhost:5432/appdb   # 임시 Postgres
make itest          # = pytest -m integration
```
`DATABASE_URL` 이 없으면 통합 테스트는 자동으로 skip 된다. CI(`.github/workflows/tests.yml`)는
`unit`(파트별) + `integration`(postgres 서비스 컨테이너) 두 잡으로 나눠 돈다.
