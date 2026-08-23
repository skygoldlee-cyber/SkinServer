"""
P1-9: engine-analysis 모델 seam 테스트 — Restorer, MLScorer, load().
"""
import os
import numpy as np
from tests._util import load

model = load("engine-analysis", "app.model")


def _img():
    rng = np.random.default_rng(0)
    return rng.integers(0, 255, (64, 64, 3), dtype=np.uint8)


def test_restorer_returns_identical_image():
    """Restorer.restore() 는 현재 pass-through (동일 객체 반환)."""
    r = model.Restorer()
    img = _img()
    assert r.restore(img) is img


def test_baseline_scorer_name():
    """BaselineScorer.name 은 'baseline'."""
    assert model.BaselineScorer.name == "baseline"
    assert model.BaselineScorer().name == "baseline"


def test_ml_scorer_name_and_inheritance():
    """MLScorer.name 은 'ml' 이고 BaselineScorer 를 상속한다."""
    assert model.MLScorer.name == "ml"
    assert issubclass(model.MLScorer, model.BaselineScorer)
    assert model.MLScorer().name == "ml"


def test_load_returns_restorer_and_baseline_by_default(monkeypatch):
    """ENGINE_MODEL 미설정 시 BaselineScorer 를 반환한다."""
    monkeypatch.delenv("ENGINE_MODEL", raising=False)
    restorer, scorer = model.load()
    assert isinstance(restorer, model.Restorer)
    assert isinstance(scorer, model.BaselineScorer)
    assert not isinstance(scorer, model.MLScorer)


def test_load_returns_ml_scorer_when_engine_model_ml(monkeypatch):
    """ENGINE_MODEL=ml 일 때 MLScorer 를 반환한다."""
    monkeypatch.setenv("ENGINE_MODEL", "ml")
    restorer, scorer = model.load()
    assert isinstance(restorer, model.Restorer)
    assert isinstance(scorer, model.MLScorer)


def test_load_returns_baseline_for_other_values(monkeypatch):
    """ENGINE_MODEL 이 'ml' 이 아니면 BaselineScorer 를 반환한다."""
    for val in ("baseline", "ML", "", "other"):
        monkeypatch.setenv("ENGINE_MODEL", val)
        _, scorer = model.load()
        assert isinstance(scorer, model.BaselineScorer)
        assert not isinstance(scorer, model.MLScorer)


def test_scorer_output_contract():
    """BaselineScorer.score() 가 계약에 맞는 키를 반환한다."""
    out = model.BaselineScorer().score(_img())
    assert set(out.keys()) == {"score", "metrics", "features", "roi"}
    assert isinstance(out["score"], float)
    assert isinstance(out["metrics"], dict)
    assert isinstance(out["features"], dict)
    assert isinstance(out["roi"], dict)
