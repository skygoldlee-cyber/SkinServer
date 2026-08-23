"""
test_scoring_regression.py
회귀 테스트 스위트 — 스코어링 점수 오차 허용범위, 처방 비율 정확일치, 계약 스키마 고정을 검증.
"""
import numpy as np
import pytest
from tests._util import load

# 각 서비스 모듈 로드
analysis_model = load("engine-analysis", "app.model")
prescription_rules = load("engine-prescription", "app.rules")


def _generate_test_image(seed=42):
    """결정론적 테스트용 난수 이미지 생성"""
    rng = np.random.default_rng(seed)
    return rng.integers(0, 255, (256, 256, 3), dtype=np.uint8)


def test_scoring_regression_tolerance():
    """피부분석 엔진 스코어링 점수의 회귀 방지 (허용오차 검증)"""
    img = _generate_test_image(42)
    scorer = analysis_model.BaselineScorer()
    out = scorer.score(img)
    
    # 1. 종합 점수 허용오차 검증 (기존 baseline 점수가 ~41.7점 부근이므로 임계값 설정)
    # 실제 운영 시에는 고정된 픽스처 이미지에 대한 기준 점수를 여기에 명시합니다.
    expected_score = 41.7
    allowed_tolerance = 2.0  # ±2.0점 허용
    assert abs(out["score"] - expected_score) <= allowed_tolerance, (
        f"스코어링 점수가 허용오차를 초과했습니다. 실측: {out['score']}, 기대: {expected_score}"
    )


def test_prescription_ratio_exact_match():
    """처방 엔진의 점수별 처방 비율 매핑이 정확히 일치하는지 검증"""
    # rules.grade_and_ratio 결과가 계약 규칙과 정확히 일치해야 함.
    # 양호 (76점 이상) -> 0.0%
    assert prescription_rules.grade_and_ratio(80) == ("양호", 0.0)
    assert prescription_rules.grade_and_ratio(76) == ("양호", 0.0)
    
    # 경미 (60점 이상 76점 미만) -> 0.5%
    assert prescription_rules.grade_and_ratio(75.9) == ("경미", 0.5)
    assert prescription_rules.grade_and_ratio(60) == ("경미", 0.5)
    
    # 보통 (40점 이상 60점 미만) -> 1.0%
    assert prescription_rules.grade_and_ratio(59.9) == ("보통", 1.0)
    assert prescription_rules.grade_and_ratio(40) == ("보통", 1.0)
    
    # 위험/심각 (40점 미만) -> 3.0%
    assert prescription_rules.grade_and_ratio(39.9) == ("위험/심각", 3.0)
    assert prescription_rules.grade_and_ratio(10) == ("위험/심각", 3.0)


def test_contract_schema_stability():
    """API 계약 스키마 고정 여부 검증 (지표 필드 누락 및 타입 변동 감지)"""
    img = _generate_test_image(42)
    scorer = analysis_model.BaselineScorer()
    out = scorer.score(img)
    
    # 필수 메트릭 키 정의
    required_metrics = {
        "oiliness", "dryness", "combination", "sensitivity", "trouble",
        "pigmentation_tone", "pores", "texture", "wrinkle_elasticity", "redness"
    }
    
    assert "metrics" in out, "분석 결과에 metrics 필드가 누락되었습니다."
    assert set(out["metrics"].keys()) == required_metrics, "API 계약에 정의된 메트릭 필드가 변경되었습니다."
    
    for metric_name, metric_data in out["metrics"].items():
        assert "value" in metric_data, f"{metric_name} 메트릭에 value 필드가 누락되었습니다."
        assert "source" in metric_data, f"{metric_name} 메트릭에 source 필드가 누락되었습니다."
        assert isinstance(metric_data["value"], (int, float)), f"{metric_name} 메트릭의 value는 숫자여야 합니다."
        assert isinstance(metric_data["source"], str), f"{metric_name} 메트릭의 source는 문자열이어야 합니다."
