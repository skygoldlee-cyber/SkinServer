"""
실측 CV 지표 (baseline). 단일 이미지에서 계산 가능한 피처를 OpenCV/numpy 로 뽑는다.
※ 여기 값은 '실제 픽셀 기반 측정'이되, 지표 정의/정규화 상수는 튜닝 대상(placeholder 상수).
   실제 SkinLens 과학(19→10 지표 정의, Self-Ideal 등)으로 교체될 자리다.
"""
from __future__ import annotations
import cv2
import numpy as np


def _norm(x: float, lo: float, hi: float) -> float:
    """[lo,hi] → [0,1] 클립."""
    if hi <= lo:
        return 0.0
    return float(min(1.0, max(0.0, (x - lo) / (hi - lo))))


def raw_features(bgr: np.ndarray) -> dict[str, float]:
    """이미지에서 원시 피처 추출(값의 의미는 아래 주석)."""
    bgr = cv2.resize(bgr, (512, 512), interpolation=cv2.INTER_AREA)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    L, A, B = lab[..., 0], lab[..., 1], lab[..., 2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    # 붉은기: LAB a* 평균(높을수록 붉음). OpenCV a*는 0~255(128 중심).
    redness = float(A.mean() - 128.0)

    # 색소·톤 불균일: b* 표준편차 + L 표준편차(얼룩/톤 편차).
    pigment_var = float(B.std() + 0.5 * L.std())

    # 피부결/모공: 고주파 에너지(Laplacian 분산) — 거칠수록 큼.
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    # 주름: 에지 밀도(Canny 비율).
    edges = cv2.Canny(gray, 50, 150)
    edge_density = float((edges > 0).mean())

    # 지성(유분): 정반사 하이라이트 비율(아주 밝은 픽셀 비율).
    spec_ratio = float((gray > 240).mean())

    # 트러블: 국소 붉은 반점 — a* 상위 임계 초과 픽셀 비율.
    trouble_ratio = float((A > (A.mean() + 2 * A.std())).mean())

    # 건성 프록시: 저휘도·저채도 균일 영역(거칠지 않고 칙칙) — 매우 러프.
    dryness_proxy = float((gray < 90).mean())

    return {
        "redness_a": redness,
        "pigment_var": pigment_var,
        "lap_var": lap_var,
        "edge_density": edge_density,
        "spec_ratio": spec_ratio,
        "trouble_ratio": trouble_ratio,
        "dryness_proxy": dryness_proxy,
    }


def metrics_from_features(f: dict[str, float]) -> dict[str, dict]:
    """
    원시 피처 → 10지표 점수(0~100, 높을수록 양호). 정규화 경계는 placeholder(튜닝 대상).
    survey 로만 신뢰 가능한 지표(민감성/복합성)는 placeholder 중립값 + source 표시.
    """
    good = lambda bad01: round(100.0 * (1.0 - bad01), 1)  # 나쁨(0~1) → 양호점수
    m = {
        "redness":            {"value": good(_norm(f["redness_a"], 0, 25)),      "source": "cv"},
        "pigmentation_tone":  {"value": good(_norm(f["pigment_var"], 8, 40)),    "source": "cv"},
        "pores":              {"value": good(_norm(f["lap_var"], 50, 800)),      "source": "cv"},
        "texture":            {"value": good(_norm(f["lap_var"], 50, 800)),      "source": "cv"},
        "wrinkle_elasticity": {"value": good(_norm(f["edge_density"], 0.03, 0.20)), "source": "cv"},
        "oiliness":           {"value": good(_norm(f["spec_ratio"], 0.0, 0.08)), "source": "cv"},
        "trouble":            {"value": good(_norm(f["trouble_ratio"], 0.0, 0.05)), "source": "cv"},
        "dryness":            {"value": good(_norm(f["dryness_proxy"], 0.1, 0.6)), "source": "cv"},
        # survey 의존 — CV 단독으론 신뢰 불가. 중립값 + placeholder 표시.
        "combination":        {"value": 50.0, "source": "placeholder"},
        "sensitivity":        {"value": 50.0, "source": "placeholder"},
    }
    return m
