"""Phase 4.6 (P0) — worker magic-byte 재검증 단위 테스트.

presigned 전환 후 브라우저가 Supabase Storage 에 직접 PUT 하고 gateway 는 image_key 만 받으므로,
gateway 의 validate_image() 가 하던 시그니처 검사가 서버에서 증발한다. worker 가 원본 fetch 직후·
엔진 호출 전에 실제 바이트를 재검증하는 것이 실질 방어선이다.
"""
import struct
import zlib
import pytest

from tests._util import load

# worker.py 는 임포트 시 storage = get_storage() 를 실행한다. STORAGE_BACKEND 미설정이면
# local(STORAGE_DIR, _util 이 /tmp/sl_test_storage 로 setdefault) 이라 부작용 없이 로드된다.
wk = load("worker", "worker")


def _png_bytes():
    def ch(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n"
            + ch(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + ch(b"IDAT", zlib.compress(b"\x00\x00\x00\x00"))
            + ch(b"IEND", b""))


def _write(tmp_path, name, data):
    p = tmp_path / name
    p.write_bytes(data)
    return str(p)


# ---------------------------------------------------------------------------
# validate_image_bytes — 확장자 ↔ 실제 매직 바이트 일치 검증
# ---------------------------------------------------------------------------

def test_accepts_real_png(tmp_path):
    path = _write(tmp_path, "original.png", _png_bytes())
    assert wk.validate_image_bytes(path) == ".png"


def test_accepts_real_jpeg(tmp_path):
    path = _write(tmp_path, "original.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 12)
    assert wk.validate_image_bytes(path) == ".jpg"


def test_accepts_real_webp(tmp_path):
    data = b"RIFF" + struct.pack("<I", 4) + b"WEBP" + b"VP8 " + b"\x00" * 4
    path = _write(tmp_path, "original.webp", data)
    assert wk.validate_image_bytes(path) == ".webp"


def test_rejects_forged_png_with_text_body(tmp_path):
    """확장자만 .png 이고 내용은 텍스트인 위조 파일 → ValueError (데드레터)."""
    path = _write(tmp_path, "original.png", b"not-a-real-png, definitely forged")
    with pytest.raises(ValueError, match="불일치"):
        wk.validate_image_bytes(path)


def test_rejects_extension_content_mismatch(tmp_path):
    """jpeg 바이트를 .png 확장자로 올린 경우(혼동) → 불일치."""
    path = _write(tmp_path, "original.png", b"\xff\xd8\xff\xe0" + b"\x00" * 12)
    with pytest.raises(ValueError, match="불일치"):
        wk.validate_image_bytes(path)


def test_rejects_unsupported_extension(tmp_path):
    path = _write(tmp_path, "original.gif", b"GIF89a" + b"\x00" * 10)
    with pytest.raises(ValueError, match="지원하지 않는"):
        wk.validate_image_bytes(path)


def test_rejects_empty_file(tmp_path):
    path = _write(tmp_path, "original.png", b"")
    with pytest.raises(ValueError):
        wk.validate_image_bytes(path)


# ---------------------------------------------------------------------------
# P0-6: _is_webp() 매직바이트 검증
# ---------------------------------------------------------------------------

def test_is_webp_accepts_valid():
    """RIFF + WEBP 매직이 있으면 True."""
    data = b"RIFF" + b"\x00" * 4 + b"WEBP" + b"\x00" * 4
    assert wk._is_webp(data) is True


def test_is_webp_rejects_short():
    """12바이트 미만은 False."""
    assert wk._is_webp(b"RIFF") is False
    assert wk._is_webp(b"RIFF" + b"\x00" * 7) is False


def test_is_webp_rejects_no_riff():
    """RIFF 헤더가 없으면 False."""
    data = b"NOPE" + b"\x00" * 4 + b"WEBP" + b"\x00" * 4
    assert wk._is_webp(data) is False


def test_is_webp_rejects_no_webp():
    """WEBP 시그니처가 없으면 False."""
    data = b"RIFF" + b"\x00" * 4 + b"NOPE" + b"\x00" * 4
    assert wk._is_webp(data) is False
