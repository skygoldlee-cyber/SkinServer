# packages/common — 엔진 공용 계약 (source of truth)

`skinlens_contract` 는 두 엔진과 worker/gateway 가 공유하는 **규격(모양)** 을 고정한다.
세부 과학(점수식·믹스 배합/선택)은 여기 두지 않는다 — 필드명·단계명·버전·등급규칙만.

- `ENGINE_CONTRACT_VERSION` — 응답에 실어 호환성 추적
- `STAGES` — job_events 단계명(콘솔/worker 공유)
- `METRIC_KEYS` / `METRIC_LABELS` — 확정된 10지표
- `GRADE_TABLE` / `grade_and_ratio()` — 확정된 점수→등급→비율(76/60/40 경계)
- 스키마: `AnalysisResult` · `PrescribeRequest` · `PrescribeResult`

> 컨테이너 빌드 컨텍스트가 서비스별로 분리돼 있어, 현재 각 엔진은 이 규격에 맞춘
> 로컬 구현을 둔다. CI 에서 이 패키지를 각 이미지에 vendoring(복사)하거나, 빌드 컨텍스트를
> 레포 루트로 올려 공유 설치하는 방식으로 단일화할 수 있다(운영 전환 시 택1).
