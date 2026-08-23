"""
engine-prescription — 폐쇄망·독립 진입점. 입력 3원(분석/설문/PCR) 중 ≥1 이면 동작.
설문은 CV 로 못 얻는 지표(민감성/복합성)를 채우고, 분석 지표와 병합해 등급/믹스를 정한다.
확정 규칙(점수→등급→비율)은 고정, 믹스 선택은 config 주입. 세부 배합은 여기 없음.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Optional

from .rules import grade_and_ratio, load_config, select_mixes, select_pcr_mixes
from .survey import survey_to_metrics, survey_concerns

ENGINE = "prescription-rules"
CONTRACT_VERSION = "1.0.0"

app = FastAPI(title="engine-prescription (rules)")
_cfg = load_config()


class PrescribeIn(BaseModel):
    analysis: Optional[dict[str, Any]] = None
    survey: Optional[dict[str, Any]] = None
    pcr: Optional[dict[str, Any]] = None


class PrescribeOut(BaseModel):
    score: float
    grade: str
    prescription_ratio_pct: float
    score_source: str
    per_metric: dict = {}
    selected_mixes: list = []
    pcr_mixes: list = []
    concerns: list = []
    inputs_present: dict = {}
    engine: str
    contract_version: str
    config: str


@app.get("/health")
def health():
    return {"status": "ok", "engine": ENGINE, "config": _cfg.get("_source_file", "none")}


@app.post("/prescribe")
def prescribe(body: PrescribeIn):
    if body.analysis is None and body.survey is None and body.pcr is None:
        raise HTTPException(400, "분석/설문/PCR 중 최소 1종이 필요합니다")

    # 종합 점수 출처 우선순위: 분석 → 설문(score) → 보수적 기본값
    try:
        if body.analysis and "score" in body.analysis:
            score = float(body.analysis["score"]); source = "analysis"
        elif body.survey and "score" in body.survey:
            score = float(body.survey["score"]); source = "survey"
        else:
            score = 50.0; source = "default"
    except (TypeError, ValueError):
        raise HTTPException(422, "score 는 숫자여야 합니다")

    grade, ratio = grade_and_ratio(score)

    # 지표 병합: 분석(CV) 지표에 설문 기반 지표를 덮어씀(민감성/복합성 등).
    metrics = dict((body.analysis or {}).get("metrics", {}) or {})
    metrics.update(survey_to_metrics(body.survey))

    per_metric, selected = select_mixes(metrics, _cfg)
    pcr_mixes = select_pcr_mixes(body.pcr, _cfg)

    out = {
        "score": score,
        "grade": grade,
        "prescription_ratio_pct": ratio,
        "score_source": source,
        "per_metric": per_metric,
        "selected_mixes": selected,
        "pcr_mixes": pcr_mixes,
        "concerns": survey_concerns(body.survey),
        "inputs_present": {"analysis": body.analysis is not None,
                           "survey": body.survey is not None,
                           "pcr": body.pcr is not None},
        "engine": ENGINE,
        "contract_version": CONTRACT_VERSION,
        "config": _cfg.get("_source_file", "none"),
    }
    return PrescribeOut(**out).model_dump()   # 계약 스키마 검증
