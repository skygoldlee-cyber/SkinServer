import numpy as np
from tests._util import load
roi = load("engine-analysis", "app.roi")


def test_crop_returns_image_and_info():
    img = np.random.default_rng(1).integers(0, 255, (200, 200, 3), dtype=np.uint8)
    out, info = roi.crop_roi(img)
    assert out.ndim == 3 and out.shape[2] == 3
    assert info["roi"] in ("face", "center-fallback")
    x0, y0, x1, y1 = info["box"]
    assert 0 <= x0 < x1 <= 200 and 0 <= y0 < y1 <= 200


def test_noise_image_falls_back():
    img = np.random.default_rng(2).integers(0, 255, (128, 128, 3), dtype=np.uint8)
    _, info = roi.crop_roi(img)
    assert info["roi"] == "center-fallback"   # 노이즈엔 얼굴 없음
