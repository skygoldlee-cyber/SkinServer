"""
(1-1) 워커 임시파일 누수 회귀 테스트.

presigned 잡이 하나 돌 때마다 _Supabase.resolve_local() 이 남기는 임시파일이
process() 에서 반드시 정리되는지 검증한다. 로컬 백엔드(원본)는 삭제되면 안 된다.
"""
import os
from unittest.mock import patch

import pytest

from tests._util import load

# worker.py 는 임포트 시 storage = get_storage() 를 실행한다. STORAGE_BACKEND 미설정이면
# local(STORAGE_DIR, _util 이 /tmp/sl_test_storage 로 setdefault) 이라 부작용 없이 로드된다.
wk = load("worker", "worker")


def _png_bytes():
    import struct, zlib
    def ch(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n"
            + ch(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + ch(b"IDAT", zlib.compress(b"\x00\x00\x00\x00"))
            + ch(b"IEND", b""))


def _make_job(tmp_path, image_name="original.png"):
    """로컬 스토리지에 이미지를 두고, 그것을 가리키는 job dict 를 만든다."""
    img = tmp_path / "u" / "j"
    img.mkdir(parents=True)
    (img / image_name).write_bytes(_png_bytes())
    key = f"u/j/{image_name}"
    return {
        "id": "job-1",
        "user_id": "user-1",
        "image_key": key,
        "inputs": {"survey": {"skin_type": "sensitive"}},
    }


def test_process_cleans_up_temp_file_on_success(monkeypatch, tmp_path):
    """is_temp=True 백엔드가 돌려준 경로는 process() 성공 후 삭제돼야 한다(1-1)."""
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    # storage 를 is_temp=True 인 가짜로 교체 — 실제 _Local 은 is_temp=False 라 이 테스트만의 격리.
    class _FakeTempStorage:
        name = "supabase"
        is_temp = True

        def resolve_local(self, key):
            return os.path.join(str(tmp_path), key)

    monkeypatch.setattr(wk, "storage", _FakeTempStorage())
    monkeypatch.setattr(wk, "call_engine", lambda fn, **kw: {"ok": True})
    monkeypatch.setattr(wk, "event", lambda *a, **k: None)

    job = _make_job(tmp_path)
    image_path = os.path.join(str(tmp_path), job["image_key"])
    assert os.path.exists(image_path)

    wk.process(job)
    assert not os.path.exists(image_path), "임시파일이 process() 이후에도 남아 있다"


def test_process_cleans_up_temp_file_on_failure(monkeypatch, tmp_path):
    """분석 중 예외가 나도 finally 로 임시파일이 정리돼야 한다(1-1)."""
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))

    class _FakeTempStorage:
        name = "supabase"
        is_temp = True

        def resolve_local(self, key):
            return os.path.join(str(tmp_path), key)

    monkeypatch.setattr(wk, "storage", _FakeTempStorage())
    monkeypatch.setattr(wk, "event", lambda *a, **k: None)

    def _boom(*a, **kw):
        raise RuntimeError("engine down")

    monkeypatch.setattr(wk, "call_engine", _boom)

    job = _make_job(tmp_path)
    image_path = os.path.join(str(tmp_path), job["image_key"])
    assert os.path.exists(image_path)

    with pytest.raises(RuntimeError, match="engine down"):
        wk.process(job)
    assert not os.path.exists(image_path), "실패 시에도 임시파일이 정리되지 않았다"


def test_process_keeps_local_original(monkeypatch, tmp_path):
    """로컬 백엔드(is_temp=False)의 원본은 process() 가 삭제하면 안 된다(1-1 구분)."""
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    # 기본 로컬 스토리지를 쓰되, DB 이벤트만 무시한다.
    monkeypatch.setattr(wk, "event", lambda *a, **k: None)
    monkeypatch.setattr(wk, "call_engine", lambda fn, **kw: {"ok": True})

    job = _make_job(tmp_path)
    image_path = os.path.join(str(tmp_path), job["image_key"])
    assert os.path.exists(image_path)

    wk.process(job)
    assert os.path.exists(image_path), "로컬 원본이 process() 에 의해 삭제됐다"
