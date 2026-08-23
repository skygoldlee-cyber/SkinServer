# 엔진 baseline · 교체 지점 가이드

스텁을 **실측 baseline** 으로 바꾸되, SkinLens 고유 과학(점수식·배합/선택 규칙)은
발명하지 않고 **끼우는 자리(seam)** 로 남겼다. HTTP 계약(`/score`, `/prescribe`)과
단계 이벤트는 그대로라 파이프라인·콘솔은 수정 없이 동작한다.

공용 규격(단일 진실원본): [`../../packages/common/skinlens_contract`](../../packages/common/skinlens_contract) —
`ENGINE_CONTRACT_VERSION`, `STAGES`, 10지표 키/라벨, 확정 등급표.

---

## engine-analysis (분석)

이제 더미(해시)가 아니라 **OpenCV 실측**이다.

- `app/metrics.py` — 이미지에서 실제 피처 계산(LAB a* 붉은기, b*/L 편차=색소·톤,
  Laplacian 분산=모공/피부결, Canny 에지=주름, 하이라이트=지성, 국소 붉은반점=트러블 등),
  그리고 피처 → 10지표 점수(0~100, 높을수록 양호).
  ⚠ **정규화 경계·매핑은 placeholder 상수**다(튜닝 대상). survey 로만 신뢰 가능한
  민감성/복합성은 중립값 + `source:"placeholder"` 로 표시.
- `app/model.py` — **교체 seam**:
  - `Restorer.restore()` : 지금은 항등 통과. 여기 **GAN/Diffusion 복원**(CodeFormer,
    RestoreFormer++) 삽입. GPU 는 `compose.gpu.yml` + CUDA base 이미지로.
  - `BaselineScorer` / `MLScorer` : `ENGINE_MODEL=baseline|ml` 로 전환. `MLScorer` 에
    학습 모델 로딩·추론을 넣으면 baseline 을 대체.
- 응답: `{ score, metrics{10지표}, features(원시), engine, model, contract_version }`.
  `score`(종합)는 처방 진입점이 참조하므로 유지.

## engine-prescription (처방)

- 확정 규칙 고정: 점수→등급→비율(76 양호 0% / 60 경미 0.5% / 40 보통 1.0% / <40 3.0%).
- `app/rules.py` — 지표별 등급 산정 + **믹스 선택**. 선택 규칙은 코드가 아니라
  **설정 주입**: `app/config/mixes.json`(없으면 `mixes.example.json`).
  - `metric_to_mixes` : 지표 → 활성 믹스 코드(M01~M11) 후보
  - `trigger_grades` : 이 등급 이하일 때 해당 믹스 채택(기본 보통·위험/심각)
  - `base_mixes` : 항상 포함(베이스)
  - `pcr_to_mixes` : PCR 마커 → PM01~PM03
  - `source:"placeholder"` 지표(survey 미제공)는 트리거에서 제외(노이즈 방지).
- 응답에 `per_metric`(지표별 등급/비율), `selected_mixes`(코드+사유), `pcr_mixes` 추가.
  최상위 `score/grade/prescription_ratio_pct` 는 콘솔·결과 호환 위해 유지.

> ⚠ **실제 배합**(INCI·한글명·함량비)은 여기 없다. `mixes.json` 의 코드 슬롯에
> '꼬뜨리브 맞춤형 13품목' 엑셀 값을 채워 넣는다(운영에선 config 를 커밋/마운트).

---

## 남은 결정 포인트 (당신의 과학)

1. **종합 vs 지표별 비율** — 지금은 종합 점수로 대표 등급/비율을 내고, 지표별 비율은
   `per_metric` 으로 병렬 제공한다. 최종 처방을 '종합 1개'로 낼지 '지표별 다중'으로 낼지 규칙 필요.
2. **지표 정규화 경계** — `metrics.py` 의 `_norm(...)` 상수는 실제 촬영 조건/기기 기준으로 교정.
3. **점수 합성 가중치** — `model.py` `BaselineScorer.WEIGHTS`(현재 placeholder).
4. **믹스 선택 로직** — 단일 지표 트리거를 넘어 조합/우선순위/상한이 필요하면 `rules.py`+config 확장.
5. **복원 필요 여부** — 저품질 입력에 한해 `Restorer` 활성화(전면 적용 시 비용/왜곡 검토).

로컬 검증(합성 이미지)에서 확인된 흐름: `analysis:result` 에 10지표 실측값,
`prescription:result` 에 지표별 등급 + `selected_mixes`(예: 붉은기·건성 트리거 → M11/M04 + 베이스 M01/M02).
