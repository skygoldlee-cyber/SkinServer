"""
engine-analysis — 폐쇄망. 이미지→ROI 크롭→실측 지표+종합점수. 출력은 계약 스키마로 검증.
baseline: OpenCV 실측. GAN 복원/ML 은 model.py seam.
"""
import numpy as np
import cv2
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel

from .model import load

ENGINE = "analysis-baseline"; CONTRACT_VERSION = "1.0.0"
app = FastAPI(title="engine-analysis (baseline)")
_restorer, _scorer = load()


class MetricScore(BaseModel):
    value: float
    source: str


class AnalysisOut(BaseModel):
    score: float
    metrics: dict[str, MetricScore]
    features: dict[str, float] = {}
    roi: dict = {}
    engine: str
    model: str
    contract_version: str


@app.get("/health")
def health():
    return {"status": "ok", "engine": ENGINE, "model": _scorer.name}


@app.post("/score")
async def score(image: UploadFile = File(...)):
    data = await image.read()
    bgr = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if bgr is None:
        raise HTTPException(400, "이미지 디코드 실패(jpeg/png/webp)")
    out = _scorer.score(_restorer.restore(bgr))
    out.update({"engine": ENGINE, "model": _scorer.name, "contract_version": CONTRACT_VERSION})
    return AnalysisOut(**out).model_dump()   # 계약 스키마 검증(필드 드리프트 차단)
