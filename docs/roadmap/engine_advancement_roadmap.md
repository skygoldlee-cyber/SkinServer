# SkinLens 피부분석 및 처방전 엔진 고도화 로드맵

피부분석 엔진(`engine-analysis`)과 처방전 엔진(`engine-prescription`)은 SkinLens 플랫폼의 핵심 IP(지식재산)이자 비즈니스 경쟁력의 원천입니다. 현재 구현된 Baseline(OpenCV 실측 Heuristics + Rule-based Mapping)을 넘어 지속적으로 AI 고도화를 이루기 위한 기술적 방향성과 구체적인 코드 내 교체 지점(Seam)을 제안합니다.

---

## 1. 엔진별 현재 상태 및 한계점

### 📊 피부분석 엔진 (`engine-analysis`)
*   **현재 구현 ([metrics.py](../../services/engine-analysis/app/metrics.py), [roi.py](../../services/engine-analysis/app/roi.py))**:
    *   **얼굴 검출**: Haar Cascade 기반 사각형 크롭(검출 실패 시 중앙 60% 폴백).
    *   **지표 추출**: LAB 색공간(a* 평균)으로 붉은기 추출, Laplacian 분산으로 피부결/모공 추출, Canny Edge로 주름 추출 등 전통적 컴퓨터 비전(CV) 지표에 의존.
    *   **점수 정규화**: 임의로 세팅된 임계값 상수(`_norm`)를 기준으로 선형 매핑.
*   **한계**: 
    *   배경이나 옷이 검출 영역에 섞여 지표 오염 발생 가능.
    *   조명, 촬영 기기, 화이트 밸런스에 따라 지표 변동성이 매우 큼(환경 표준화 부재).
    *   복잡한 주름 깊이나 미세 모공, 여드름 등급 구분이 정교하지 못함.

### 📝 처방전 엔진 (`engine-prescription`)
*   **현재 구현 ([rules.py](../../services/engine-prescription/app/rules.py), [survey.py](../../services/engine-prescription/app/survey.py))**:
    *   **점수-등급 매핑**: 종합 점수를 기준으로 일차원 등급(양호/경미/보통/위험) 및 처방 비율 결정.
    *   **믹스 매핑**: [mixes.json](../../services/engine-prescription/app/config/mixes.json)(또는 example) 설정을 바탕으로, 특정 지표가 트리거 등급 이하일 때 매핑된 믹스 코드(M01~M11)를 단순 합집합 형태로 수집.
    *   **설문 보완**: 설문 응답을 기반으로 민감성/복합성 지표를 보완 대입.
*   **한계**:
    *   피부 상태는 여러 지표가 복합 작용함에도 일차원적인 점수 기반의 단순 합집합 처방에 의존.
    *   동시에 여러 믹스가 처방될 때 원료 간 상호작용(부작용 발생 우려 성분 조합 등)을 걸러내는 안전 장치 부족.
    *   사용자 반응(피드백 루프)을 통한 규칙 자동 교정(Calibration) 모델 부재.

---

## 2. 엔진 고도화 기술 로드맵

```mermaid
graph TD
    subgraph Phase 1: Heuristic Tuning
        H1[MediaPipe FaceMesh ROI 분할]
        H2[색상/조명 정규화]
        H3[mixes.json 배합 규칙 정교화]
    end
    subgraph Phase 2: Deep Learning Integration
        D1[CodeFormer 이미지 복원 탑재]
        D2[지표별 전문 MLScorer 학습]
        D3[설문-CV-PCR 다차원 의사결정 모델]
    end
    subgraph Phase 3: AI Platform & Feedback Loop
        F1[성분 안전성 & 교차 금기 검증 엔진]
        F2[사용자 피드백 루프 구축 RLUF]
        F3[개인화 함량 동적 최적화]
    end
    Phase 1 --> Phase 2
    Phase 2 --> Phase 3
```

### ① 피부분석 엔진 고도화 세부 전략

#### 1) 얼굴 세부 영역(ROI) 정밀 분할 및 마스킹
*   **방향**: Haar Cascade의 대략적인 사각형 검출을 탈피하고, **MediaPipe FaceMesh** 또는 **RetinaFace**를 활용하여 얼굴의 주요 랜드마크를 추출합니다.
*   **효과**: 이마, 양 볼, 코, 턱 등 세부 영역을 정확히 마스킹하고, 눈썹·입술·눈 등 피부 분석 대상이 아닌 영역을 마스킹하여 분석 정확도를 비약적으로 향상시킵니다.
*   **코드 교체 지점**: [roi.py](../../services/engine-analysis/app/roi.py)의 `crop_roi` 함수.

#### 2) 입력 이미지 화질 복원 (GAN/Diffusion)
*   **방향**: 저조도 또는 초점이 흐려진 사용자 업로드 이미지를 개선하기 위해 **CodeFormer** 또는 **RestoreFormer++** 모델을 도입합니다.
*   **주의점**: 과도한 복원으로 인해 실제 트러블이나 주름이 지워지는(왜곡) 현상을 막기 위해, 이미지 품질 평가(IQA, Image Quality Assessment) 모듈을 선행 적용하고 품질 이하 이미지에 한해서만 복원을 부분 적용하는 정책(Toggle Policy)이 필요합니다.
*   **코드 교체 지점**: [model.py](../../services/engine-analysis/app/model.py)의 `Restorer.restore` 메서드.

#### 3) 조명 및 색상 정규화 (Calibration)
*   **방향**: 환경(형광등, 백열등, 자연광)에 따른 지표 왜곡을 막기 위해 이미지 내의 화이트 밸런스 오토 캘리브레이션 및 그레이 카드/참조 패치 기준의 색 복원 알고리즘을 추가합니다.

#### 4) Deep Learning 기반 피부 지표 추론 (`MLScorer`)
*   **방향**: 전통적 CV(에지 밀도, 단순 분산) 대신 피부 임상 데이터로 학습된 딥러닝 모델(ResNet/ViT 기반의 다중 작업 학습 모델)을 활용하여 여드름 등급(KAGS 기준), 주름 깊이, 색소 침착 면적을 추론합니다.
*   **코드 교체 지점**: [model.py](../../services/engine-analysis/app/model.py)의 `MLScorer.score` 및 `load()` 함수에서 `ENGINE_MODEL=ml` 활성화.

---

### ② 처방전 엔진 고도화 세부 전략

#### 1) 다차원 처방 결정 트리 (Multi-Criteria Decision Making)
*   **방향**: 단순 점수 합산 처방이 아닌, **[분석 지표 × 고객 관심사(설문) × PCR 유전 마커]**를 종합 변수로 갖는 다차원 행렬 처방 로직으로 전환합니다.
    *   *예시*: CV 분석 결과 모공 지표는 양호하나, 유전적(PCR) 요인으로 피지 분비 가능성이 높고, 설문에서 지성을 호소하는 경우 예방 차원의 믹스를 선제 배정.
*   **코드 교체 지점**: [rules.py](../../services/engine-prescription/app/rules.py)의 `select_mixes` 및 `select_pcr_mixes`.

#### 2) 성분 상호작용(교차 부작용) 검증 및 안전 필터링
*   **방향**: 여러 믹스 성분이 혼합될 때 발생할 수 있는 성분 충돌(예: 레티놀과 고농도 비타민C의 동시 처방 제한, AHA/BHA 과도 중첩 차단)을 방지하는 **피부 안전성 룰 엔진**을 하단에 탑재합니다.
*   **코드 교체 지점**: [rules.py](../../services/engine-prescription/app/rules.py)의 믹스 선택 프로세스 마지막 단계에 `Filter` 레이어 추가.

#### 3) 동적 배합 농도/함량 최적화 (INCI Level)
*   **방향**: 단순히 완성된 믹스(M01~M11)의 목록만 제공하는 대신, 개인의 피부 두께나 장벽 민감도에 맞추어 활성 성분의 **최적 함량 비중(%)**을 동적으로 연산하여 제조 장비로 전송하는 INCI(국제화장품성분) 레벨의 정밀 계산을 도입합니다.

#### 4) 피드백 루프 기반 규칙 자가 조정 (RLUF)
*   **방향**: 처방된 제품을 2~4주 사용한 후 사용자가 보고하는 피부 개선 만족도 및 재촬영 데이터를 수집하여, `mixes.json`의 가중치 및 트리거 경계를 역전파 형태로 미세 조정(Fine-tuning)하는 기계학습 루프를 설계합니다.

---

## 3. 실행을 위한 단기/중기 액션 플랜

### 🏃 단기 과제 (Quick Wins - 인프라 유지하며 고도화 시작)
1.  **얼굴 ROI 검출 고도화**: Haar Cascade 필터를 제거하고 `mediapipe` 패키지를 추가하여 이마/양 볼 중심의 마스크 기반 크롭 적용.
2.  **`mixes.json` 과학화**: 화장품 원료 배합 전문가(BM)와의 협업을 통해 `trigger_grades` 설정 및 지표별 배합 믹스 매핑을 정밀 설계하여 `config/mixes.json` 업데이트.
3.  **지표 가중치 현실화**: [model.py](../../services/engine-analysis/app/model.py) `BaselineScorer.WEIGHTS` 상수를 임상 피드백 기준으로 수정.

### 📅 중/장기 과제 (인프라 고도화 수반)
1.  **GPU 배선 완료**: `deploy/compose/compose.base.yml` 내 엔진 컨테이너에 NVIDIA GPU 런타임 및 디바이스 예약 블록 배선.
2.  **MLScorer 추론 코드 작성**: PyTorch/ONNX 런타임을 임베딩하여 딥러닝 기반 지표 추출 가동.
3.  **안전 필터 룰 엔진 구현**: 화학적/피부과학적 궁합을 필터링하는 룰셋 로직 구축.
