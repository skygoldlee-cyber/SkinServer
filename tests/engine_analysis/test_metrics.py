import numpy as np
import pytest
from tests._util import load
model = load("engine-analysis", "app.model")

KEYS = {"oiliness","dryness","combination","sensitivity","trouble",
        "pigmentation_tone","pores","texture","wrinkle_elasticity","redness"}


def _img():
    rng = np.random.default_rng(0)
    return rng.integers(0, 255, (256, 256, 3), dtype=np.uint8)


def test_metrics_keys_and_range():
    out = model.BaselineScorer().score(_img())
    assert set(out["metrics"]) == KEYS
    for v in out["metrics"].values():
        assert 0.0 <= v["value"] <= 100.0
        assert v["source"] in ("cv", "placeholder")


def test_overall_and_roi():
    out = model.BaselineScorer().score(_img())
    assert 0.0 <= out["score"] <= 100.0
    assert "roi" in out and "box" in out["roi"]


# ---------------------------------------------------------------------------
# P1-7: _norm() 경계값 테스트
# ---------------------------------------------------------------------------

def test_norm_lo_equals_hi_returns_zero():
    """hi <= lo 이면 0.0 을 반환한다."""
    assert model.metrics._norm(5.0, 10.0, 10.0) == 0.0
    assert model.metrics._norm(5.0, 10.0, 5.0) == 0.0


def test_norm_clamps_below_lo():
    """x < lo 이면 0.0 으로 클램핑된다."""
    assert model.metrics._norm(-5.0, 0.0, 10.0) == 0.0
    assert model.metrics._norm(0.0, 1.0, 10.0) == 0.0


def test_norm_clamps_above_hi():
    """x > hi 이면 1.0 으로 클램핑된다."""
    assert model.metrics._norm(15.0, 0.0, 10.0) == 1.0
    assert model.metrics._norm(10.0, 0.0, 10.0) == 1.0


def test_norm_midpoint():
    """정확한 중간값은 0.5."""
    assert model.metrics._norm(5.0, 0.0, 10.0) == 0.5
    assert model.metrics._norm(0.0, -10.0, 10.0) == 0.5


def test_norm_quarter_and_three_quarters():
    """0.25, 0.75 지점도 정확하다."""
    assert model.metrics._norm(2.5, 0.0, 10.0) == 0.25
    assert model.metrics._norm(7.5, 0.0, 10.0) == 0.75


# ---------------------------------------------------------------------------
# P1-8: raw_features() 개별 피처 테스트
# ---------------------------------------------------------------------------

def test_raw_features_returns_all_keys():
    """raw_features 가 7개 피처 키를 모두 반환한다."""
    f = model.metrics.raw_features(_img())
    expected = {"redness_a", "pigment_var", "lap_var", "edge_density",
                "spec_ratio", "trouble_ratio", "dryness_proxy"}
    assert set(f.keys()) == expected


def test_raw_features_values_are_numeric():
    """모든 피처 값이 float 이다."""
    f = model.metrics.raw_features(_img())
    for v in f.values():
        assert isinstance(v, float)


def test_raw_features_deterministic_for_same_input():
    """같은 입력에 대해 같은 피처값이 나온다."""
    img = _img()
    f1 = model.metrics.raw_features(img)
    f2 = model.metrics.raw_features(img)
    for k in f1:
        assert f1[k] == pytest.approx(f2[k])


def test_raw_features_solid_color_image():
    """단색 이미지는 variance 가 0 에 가깝다."""
    solid = np.full((64, 64, 3), 128, dtype=np.uint8)
    f = model.metrics.raw_features(solid)
    assert f["lap_var"] == pytest.approx(0.0, abs=1e-6)
    assert f["pigment_var"] == pytest.approx(0.0, abs=1e-6)
    assert f["edge_density"] == pytest.approx(0.0, abs=1e-6)
    assert f["spec_ratio"] == pytest.approx(0.0, abs=1e-6)


def test_raw_features_bright_image_has_high_spec_ratio():
    """아주 밝은 이미지는 spec_ratio 가 높다."""
    bright = np.full((64, 64, 3), 255, dtype=np.uint8)
    f = model.metrics.raw_features(bright)
    assert f["spec_ratio"] > 0.9


def test_raw_features_dark_image_has_high_dryness_proxy():
    """어두운 이미지는 dryness_proxy 가 높다."""
    dark = np.full((64, 64, 3), 30, dtype=np.uint8)
    f = model.metrics.raw_features(dark)
    assert f["dryness_proxy"] > 0.9


# ---------------------------------------------------------------------------
# P1-8: metrics_from_features() 경계값 테스트
# ---------------------------------------------------------------------------

def test_metrics_from_features_all_zero_badness_gives_100():
    """모든 badness 가 0 이면 cv 지표는 100.0 이고 placeholder 는 50.0."""
    f = {k: 0.0 for k in ("redness_a", "pigment_var", "lap_var",
                          "edge_density", "spec_ratio", "trouble_ratio", "dryness_proxy")}
    m = model.metrics.metrics_from_features(f)
    cv_keys = ("redness", "pigmentation_tone", "pores", "texture",
               "wrinkle_elasticity", "oiliness", "trouble", "dryness")
    for k in cv_keys:
        assert m[k]["value"] == 100.0, f"{k} should be 100.0"
    assert m["combination"]["value"] == 50.0
    assert m["sensitivity"]["value"] == 50.0


def test_metrics_from_features_all_max_badness_gives_0():
    """모든 badness 가 1 이면 cv 지표가 0.0."""
    f = {"redness_a": 25.0, "pigment_var": 40.0, "lap_var": 800.0,
         "edge_density": 0.20, "spec_ratio": 0.08, "trouble_ratio": 0.05,
         "dryness_proxy": 0.6}
    m = model.metrics.metrics_from_features(f)
    cv_keys = ("redness", "pigmentation_tone", "pores", "texture",
               "wrinkle_elasticity", "oiliness", "trouble", "dryness")
    for k in cv_keys:
        assert m[k]["value"] == 0.0, f"{k} should be 0.0"


def test_metrics_from_features_placeholder_neutral_50():
    """placeholder 지표(민감성/복합성)는 항상 50.0."""
    f = {k: 0.0 for k in ("redness_a", "pigment_var", "lap_var",
                          "edge_density", "spec_ratio", "trouble_ratio", "dryness_proxy")}
    m = model.metrics.metrics_from_features(f)
    assert m["combination"]["value"] == 50.0
    assert m["sensitivity"]["value"] == 50.0
    assert m["combination"]["source"] == "placeholder"
    assert m["sensitivity"]["source"] == "placeholder"


def test_metrics_from_features_half_badness_gives_50():
    """badness 가 정확히 0.5 이면 50.0."""
    f = {"redness_a": 12.5, "pigment_var": 24.0, "lap_var": 425.0,
         "edge_density": 0.115, "spec_ratio": 0.04, "trouble_ratio": 0.025,
         "dryness_proxy": 0.35}
    m = model.metrics.metrics_from_features(f)
    cv_keys = ("redness", "pigmentation_tone", "pores", "texture",
               "wrinkle_elasticity", "oiliness", "trouble", "dryness")
    for k in cv_keys:
        assert m[k]["value"] == pytest.approx(50.0, abs=0.1), f"{k} should be ~50.0"
