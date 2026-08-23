"""
얼굴/ROI 검출 (baseline) — 배경 픽셀이 붉은기·색소 지표를 오염시키는 걸 줄인다.
Haar cascade 로 가장 큰 얼굴을 잡아 여유를 두고 크롭. 실패 시 중앙 크롭으로 폴백.
실제로는 landmark/segmentation 기반 피부영역 마스크로 교체(정확도↑).
"""
from __future__ import annotations
import cv2
import numpy as np

_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)


def crop_roi(bgr: np.ndarray) -> tuple[np.ndarray, dict]:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    faces = _cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    h, w = bgr.shape[:2]
    if len(faces) > 0:
        x, y, fw, fh = max(faces, key=lambda r: r[2] * r[3])
        mx, my = int(fw * 0.1), int(fh * 0.1)
        x0, y0 = max(0, x - mx), max(0, y - my)
        x1, y1 = min(w, x + fw + mx), min(h, y + fh + my)
        return bgr[y0:y1, x0:x1], {"roi": "face", "box": [int(x0), int(y0), int(x1), int(y1)]}
    # 폴백: 중앙 60% 크롭(배경 축소)
    cx0, cy0 = int(w * 0.2), int(h * 0.2)
    cx1, cy1 = int(w * 0.8), int(h * 0.8)
    return bgr[cy0:cy1, cx0:cx1], {"roi": "center-fallback", "box": [cx0, cy0, cx1, cy1]}
