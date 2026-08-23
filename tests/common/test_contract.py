from skinlens_contract import (ENGINE_CONTRACT_VERSION, STAGES, METRIC_KEYS,
    METRIC_LABELS, GRADE_TABLE, grade_and_ratio, Survey, AnalysisResult,
    PrescribeRequest, PrescribeResult)

from tests._util import load


def test_metric_keys_are_ten_and_labeled():
    assert len(METRIC_KEYS) == 10
    assert set(METRIC_LABELS) == set(METRIC_KEYS)


def test_stages_cover_pipeline():
    for s in ("uploaded", "queued", "claimed", "analysis:result", "prescription:result", "done", "error"):
        assert s in STAGES


def test_grade_boundaries():
    assert grade_and_ratio(76) == ("양호", 0.0)
    assert grade_and_ratio(60) == ("경미", 0.5)
    assert grade_and_ratio(40) == ("보통", 1.0)
    assert grade_and_ratio(39.9) == ("위험/심각", 3.0)


def test_survey_allows_extra_fields():
    s = Survey(skin_type="oily", unknown_q="keep me")
    assert s.model_dump().get("unknown_q") == "keep me"


def test_schemas_instantiate():
    assert ENGINE_CONTRACT_VERSION
    PrescribeRequest(analysis={"score": 50})
    PrescribeResult(score=50, grade="보통", prescription_ratio_pct=1.0, score_source="analysis",
                    engine="x")


# ── 드리프트 가드(fix): 엔진의 로컬 사본이 공용 계약과 어긋나지 않게 CI 에서 강제 ──
# 엔진은 빌드 컨텍스트 분리 때문에 계약을 import 하지 않고 값을 손으로 복사한다.
# 그 사본(등급표·지표키·응답 필드)이 조용히 벌어지는 걸 아래 테스트가 막는다.

def test_prescription_grade_table_matches_contract():
    """처방 엔진 rules.py 의 확정 등급표가 계약과 완전히 일치해야 한다(비즈니스 규칙 중복)."""
    rules = load("engine-prescription", "app.rules")
    assert rules.GRADE_TABLE == GRADE_TABLE
    # 경계값도 동일 결과인지 재확인(표 파싱 로직 포함)
    for lo, grade, ratio in GRADE_TABLE:
        assert rules.grade_and_ratio(lo) == (grade, ratio)


def test_analysis_metric_keys_match_contract():
    """분석 엔진이 내는 10지표 키 집합이 계약 METRIC_KEYS 와 정확히 일치해야 한다."""
    metrics = load("engine-analysis", "app.metrics")
    # raw_features 가 만드는 키만 있으면 되므로 0 으로 채운 피처로 지표 산출.
    zero_feats = {k: 0.0 for k in
                  ("redness_a", "pigment_var", "lap_var", "edge_density",
                   "spec_ratio", "trouble_ratio", "dryness_proxy")}
    produced = set(metrics.metrics_from_features(zero_feats).keys())
    assert produced == set(METRIC_KEYS)


def test_engine_response_models_superset_contract():
    """
    엔진 응답 모델(AnalysisOut/PrescribeOut)이 계약이 약속한 필드를 모두 포함해야 한다.
    (추가 필드는 허용 — 계약은 최소 보장. 계약 필드가 빠지면 소비자 계약 위반.)
    """
    ea = load("engine-analysis", "app.main")
    assert set(AnalysisResult.model_fields) <= set(ea.AnalysisOut.model_fields), \
        set(AnalysisResult.model_fields) - set(ea.AnalysisOut.model_fields)

    ep = load("engine-prescription", "app.main")
    assert set(PrescribeResult.model_fields) <= set(ep.PrescribeOut.model_fields), \
        set(PrescribeResult.model_fields) - set(ep.PrescribeOut.model_fields)


def test_requeued_stage_registered():
    """worker 가 내보내는 requeued 단계가 계약 STAGES 에 등록돼 있어야 한다."""
    assert "requeued" in STAGES
