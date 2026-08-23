"""
SkinLens 엔진 공용 계약 (source of truth).

두 엔진(engine-analysis / engine-prescription)과 worker/gateway 가 공유하는
'말이 통하는 규격'을 한곳에 고정한다. 컨테이너 빌드 컨텍스트 분리 때문에 각 엔진은
이 규격에 맞춘 로컬 사본을 두더라도, 필드명·단계명·버전은 여기 값을 기준으로 맞춘다.

세부 과학(점수 산출식, 믹스 배합/선택 규칙)은 여기서 정의하지 않는다 — 계약(모양)만 고정.
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

# 계약 버전 — 응답에 실어 호환성을 추적. 필드 변경 시 올린다.
ENGINE_CONTRACT_VERSION = "1.0.0"

# 파이프라인 단계명(job_events.stage). worker/gateway 와 콘솔이 공유.
STAGES = [
    "uploaded", "queued", "claimed",
    "analysis:request", "analysis:result",
    "prescription:request", "prescription:result",
    "requeued",                               # 일시적 오류 재큐(worker)
    "done", "error",
]

# 확정된 10개 측정지표 키(표시용 한글명은 라벨로 분리).
METRIC_KEYS = [
    "oiliness", "dryness", "combination", "sensitivity", "trouble",
    "pigmentation_tone", "pores", "texture", "wrinkle_elasticity", "redness",
]
METRIC_LABELS = {
    "oiliness": "지성", "dryness": "건성", "combination": "복합성",
    "sensitivity": "민감성", "trouble": "트러블", "pigmentation_tone": "색소·톤",
    "pores": "모공", "texture": "피부결", "wrinkle_elasticity": "주름·탄력·볼륨",
    "redness": "붉은기",
}

# 확정된 점수→등급→처방비율 규칙(점수는 높을수록 양호).
#   76~100 양호 0% / 60~76 경미 0.5% / 40~60 보통 1.0% / <40 위험·심각 3.0%
GRADE_TABLE = [
    (76.0, "양호", 0.0),
    (60.0, "경미", 0.5),
    (40.0, "보통", 1.0),
    (0.0, "위험/심각", 3.0),
]


def grade_and_ratio(score: float) -> tuple[str, float]:
    for lo, grade, ratio in GRADE_TABLE:
        if score >= lo:
            return grade, ratio
    return "위험/심각", 3.0


# ── 계약 스키마 ──────────────────────────────────────────────────────────
class MetricScore(BaseModel):
    value: float = Field(..., ge=0, le=100)   # 0~100, 높을수록 양호
    source: str = "cv"                         # cv | placeholder | survey


class AnalysisResult(BaseModel):
    score: float                               # 종합 점수(0~100) — 처방 진입점이 참조
    metrics: dict[str, MetricScore]            # 10지표
    features: dict[str, float] = {}            # 원시 CV 피처(디버깅/재현용)
    engine: str
    model: str                                 # baseline | ml
    contract_version: str = ENGINE_CONTRACT_VERSION


class PrescribeRequest(BaseModel):
    analysis: Optional[dict] = None
    survey: Optional[dict] = None
    pcr: Optional[dict] = None


class PrescribeResult(BaseModel):
    score: float
    grade: str
    prescription_ratio_pct: float
    score_source: str
    per_metric: dict = {}                      # 지표별 등급/비율
    selected_mixes: list = []                  # 활성 믹스(M01~M11) 선택 결과
    pcr_mixes: list = []                       # PCR 믹스(PM01~PM03)
    engine: str
    contract_version: str = ENGINE_CONTRACT_VERSION


# ── 고객 설문 (Flutter 앱이 사진과 함께 전송) ────────────────────────────
# 확장 가능한 권장 shape. 앱은 아는 필드만 채워 보내고, 엔진은 아는 필드만 사용한다.
# 실제 문항/척도는 도메인 결정 — 아래는 baseline 해석이 인식하는 최소 권장 필드.
class Survey(BaseModel):
    skin_type: Optional[str] = None          # oily|dry|combination|normal|sensitive (자가보고)
    sensitivity: Optional[dict] = None        # {"stings_easily":bool,"reacts_to_products":bool,"redness_frequent":bool}
    concerns: Optional[list[str]] = None      # ["acne","pigmentation","wrinkles","pores","redness","dryness",...]
    age_band: Optional[str] = None            # 10s|20s|30s|40s|50s+
    sun_exposure: Optional[str] = None        # low|medium|high
    notes: Optional[str] = None
    model_config = ConfigDict(extra="allow")   # 알 수 없는 문항도 그대로 보관

# 업로드 multipart 계약(앱↔gateway): 필드명 고정.
UPLOAD_FIELDS = {"image": "file(jpeg/png/webp)", "survey": "json(Survey)", "pcr": "json(optional)"}
