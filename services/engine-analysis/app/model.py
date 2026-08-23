"""
모델 seam — GAN 복원 + ML 스코어러가 끼는 자리. ROI 크롭 후 실측.
ENGINE_MODEL=baseline|ml.
"""
from __future__ import annotations
import os
import numpy as np
from . import metrics
from .roi import crop_roi


class Restorer:
    def restore(self, bgr: np.ndarray) -> np.ndarray:
        return bgr  # TODO: CodeFormer/RestoreFormer++ 복원 지점


class BaselineScorer:
    name = "baseline"
    WEIGHTS = {"redness": 1.0, "pigmentation_tone": 1.0, "pores": 1.0, "texture": 1.0,
               "wrinkle_elasticity": 1.0, "oiliness": 0.8, "trouble": 1.2, "dryness": 0.8}

    def score(self, bgr: np.ndarray) -> dict:
        roi_img, roi_info = crop_roi(bgr)          # ★ 얼굴/ROI 크롭 후 지표 산출
        feats = metrics.raw_features(roi_img)
        mets = metrics.metrics_from_features(feats)
        num = sum(self.WEIGHTS[k] * mets[k]["value"] for k in self.WEIGHTS)
        overall = round(num / sum(self.WEIGHTS.values()), 1)
        return {"score": overall, "metrics": mets,
                "features": {k: round(v, 4) for k, v in feats.items()}, "roi": roi_info}


class MLScorer(BaselineScorer):
    name = "ml"
    # def __init__(self): self.net = load_weights(os.environ["MODEL_PATH"])  # TODO


def load():
    scorer = MLScorer() if os.environ.get("ENGINE_MODEL") == "ml" else BaselineScorer()
    return Restorer(), scorer
