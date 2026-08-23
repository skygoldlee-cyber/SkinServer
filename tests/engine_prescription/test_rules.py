import pytest
from tests._util import load
rules = load("engine-prescription", "app.rules")

CFG = {"trigger_grades": ["보통", "위험/심각"],
       "metric_to_mixes": {"redness": ["M12"], "dryness": ["M04"], "sensitivity": ["M06"]},
       "base_mixes": ["M01"], "pcr_to_mixes": {"malassezia_high": ["PM02"]}}


def test_grade_boundaries():
    assert rules.grade_and_ratio(76) == ("양호", 0.0)
    assert rules.grade_and_ratio(75.9) == ("경미", 0.5)
    assert rules.grade_and_ratio(59.9) == ("보통", 1.0)
    assert rules.grade_and_ratio(39.9) == ("위험/심각", 3.0)


def test_triggers_and_base():
    metrics = {"redness": {"value": 20, "source": "cv"}, "dryness": {"value": 90, "source": "cv"}}
    per, sel = rules.select_mixes(metrics, CFG)
    codes = {m["mix"] for m in sel}
    assert "M12" in codes and "M01" in codes and "M04" not in codes


def test_placeholder_excluded():
    metrics = {"sensitivity": {"value": 10, "source": "placeholder"}}
    per, sel = rules.select_mixes(metrics, CFG)
    assert all(m["mix"] != "M06" for m in sel)
    assert per["sensitivity"]["grade"] == "위험/심각"


def test_pcr_mixes():
    out = rules.select_pcr_mixes({"malassezia_high": True, "x": True}, CFG)
    assert out and out[0]["mix"] == "PM02"


def test_default_config_loads():
    cfg = rules.load_config()
    assert "metric_to_mixes" in cfg and cfg.get("_source_file")


# ---------------------------------------------------------------------------
# P0-5: load_config() ENV=prod fail-fast
# ---------------------------------------------------------------------------

def test_load_config_prod_rejects_example(monkeypatch, tmp_path):
    """ENV=prod 에서 mixes.example.json 로드 시 RuntimeError."""
    monkeypatch.setenv("ENV", "prod")
    # mixes.json 은 없고 example 만 있는 상황을 시뮬레이션
    monkeypatch.setattr(rules.os.path, "exists", lambda p: "example" in p)
    with pytest.raises(RuntimeError, match="mixes.example.json 사용 금지"):
        rules.load_config()


def test_load_config_dev_allows_example(monkeypatch):
    """ENV=dev 에서는 mixes.example.json 로드 허용."""
    monkeypatch.setenv("ENV", "dev")
    monkeypatch.setattr(rules.os.path, "exists", lambda p: "example" in p)
    cfg = rules.load_config()
    assert cfg["_source_file"] == "mixes.example.json"


def test_load_config_prefers_real_over_example(monkeypatch, tmp_path):
    """mixes.json 이 존재하면 example 보다 우선 로드한다."""
    monkeypatch.setenv("ENV", "dev")
    real = tmp_path / "mixes.json"
    real.write_text('{"trigger_grades": [], "metric_to_mixes": {}, "base_mixes": [], "pcr_to_mixes": {}}')
    example = tmp_path / "mixes.example.json"
    example.write_text('{"trigger_grades": ["X"], "metric_to_mixes": {}, "base_mixes": [], "pcr_to_mixes": {}}')
    monkeypatch.setattr(rules.os.path, "exists", lambda p: str(p) in (str(real), str(example)))
    monkeypatch.setattr(rules.os.path, "join", lambda *a: str(real) if "mixes.json" in a[-1] and "example" not in a[-1] else str(example))
    cfg = rules.load_config()
    assert cfg["_source_file"] == "mixes.json"


def test_load_config_returns_default_when_no_files(monkeypatch):
    """config 파일이 모두 없으면 기본값을 반환한다."""
    monkeypatch.setenv("ENV", "dev")
    monkeypatch.setattr(rules.os.path, "exists", lambda p: False)
    cfg = rules.load_config()
    assert cfg == {"trigger_grades": [], "metric_to_mixes": {}, "base_mixes": [], "pcr_to_mixes": {}}
    assert "_source_file" not in cfg


# ---------------------------------------------------------------------------
# P1-10: select_mixes() 비정상 지표값 방어 테스트
# ---------------------------------------------------------------------------

def test_select_mixes_skips_none_value():
    """value 가 None 이면 해당 지표를 건너뛴다."""
    metrics = {"redness": {"value": None, "source": "cv"},
               "dryness": {"value": 90, "source": "cv"}}
    per, sel = rules.select_mixes(metrics, CFG)
    assert "redness" not in per
    assert "dryness" in per


def test_select_mixes_skips_non_numeric_string():
    """value 가 숫자로 변환 불가능한 문자열이면 건어뛴다."""
    metrics = {"redness": {"value": "not-a-number", "source": "cv"},
               "dryness": {"value": 90, "source": "cv"}}
    per, sel = rules.select_mixes(metrics, CFG)
    assert "redness" not in per
    assert "dryness" in per


def test_select_mixes_skips_non_numeric_object():
    """value 가 dict 등 숫자 변환 불가능한 객체이면 건어뛴다."""
    metrics = {"redness": {"value": {"nested": 1}, "source": "cv"},
               "dryness": {"value": 90, "source": "cv"}}
    per, sel = rules.select_mixes(metrics, CFG)
    assert "redness" not in per
    assert "dryness" in per


def test_select_mixes_accepts_numeric_string():
    """value 가 숫자 문자열이면 float 으로 변환하여 처리한다."""
    metrics = {"redness": {"value": "20", "source": "cv"}}
    per, sel = rules.select_mixes(metrics, CFG)
    assert per["redness"]["score"] == 20.0
    assert per["redness"]["grade"] == "위험/심각"


def test_select_mixes_handles_bare_value_not_dict():
    """지표값이 dict 가 아니라 bare number 면 source='unknown' 으로 처리한다."""
    metrics = {"redness": 20}
    per, sel = rules.select_mixes(metrics, CFG)
    assert per["redness"]["score"] == 20.0
    assert per["redness"]["source"] == "unknown"
    assert per["redness"]["grade"] == "위험/심각"


def test_select_mixes_metrics_none_returns_empty():
    """metrics 가 None 이면 빈 결과를 반환한다."""
    per, sel = rules.select_mixes(None, CFG)
    assert per == {}
    assert sel == [{"mix": "M01", "reason": "base"}]


def test_select_mixes_metrics_empty_dict_returns_empty():
    """metrics 가 빈 dict 이면 per_metric 만 비고 base_mixes 는 포함한다."""
    per, sel = rules.select_mixes({}, CFG)
    assert per == {}
    assert sel == [{"mix": "M01", "reason": "base"}]


def test_select_pcr_mixes_pcr_none_returns_empty():
    """pcr 가 None 이면 빈 리스트를 반환한다."""
    assert rules.select_pcr_mixes(None, CFG) == []


def test_select_pcr_mixes_pcr_empty_returns_empty():
    """pcr 가 빈 dict 이면 빈 리스트를 반환한다."""
    assert rules.select_pcr_mixes({}, CFG) == []


def test_select_pcr_mixes_skips_false_marker():
    """marker 값이 False 면 해당 믹스를 선택하지 않는다."""
    out = rules.select_pcr_mixes({"malassezia_high": False}, CFG)
    assert out == []
