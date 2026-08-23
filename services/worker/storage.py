"""
Worker 스토리지 접근 — gateway/storage.py 와 대칭(빌드 컨텍스트가 분리돼 별도 사본).
STORAGE_BACKEND=local|supabase.
  local    : STORAGE_DIR 하위에서 안전 경로로 원본 읽기(경로 탈출 차단).
  supabase : 서명 URL 로 fetch → 임시 파일 (운영 구현 자리). 미구현 시 조용히 skip 하지 않고
             명시적으로 예외를 던져 'prod 미배선'이 무증상으로 넘어가지 않게 한다.
반환 계약: resolve_local(image_key) 는 로컬에서 열 수 있는 경로 또는 None(파일 없음).
"""
from __future__ import annotations
import os

# (2-3) 다운로드 상한 — presign 의 MAX_UPLOAD_BYTES 와 동일 상한을 워커도 적용.
# 버킷 file_size_limit 이 1차 방어선이고, 이 값은 워커 측 심층 방어다.
# Supabase 가 차단하지 못한 과대 파일(또는 프록시 우회)이 tmpfs(RAM)를 고갈시키는 것을 막는다.
MAX_DOWNLOAD_BYTES = int(os.environ.get("MAX_DOWNLOAD_BYTES", str(25 * 1024 * 1024)))
_DOWNLOAD_CHUNK = 1 * 1024 * 1024  # 1MB 청크 스트리밍(메모리 상주 방지)


class _Local:
    name = "local"
    # 로컬 백엔드는 실제 볼륨의 원본을 가리키므로 호출자가 삭제하면 안 된다.
    is_temp = False

    def __init__(self, root: str):
        self.root = os.path.realpath(root)

    def resolve_local(self, key: str) -> str | None:
        dest = os.path.realpath(os.path.join(self.root, key))
        # 서버 생성 키만 오지만, 심층 방어로 루트 밖 경로는 차단.
        if os.path.commonpath([self.root, dest]) != self.root:
            raise ValueError("잘못된 저장 경로")
        return dest if os.path.exists(dest) else None


class _Supabase:
    name = "supabase"
    # resolve_local() 이 돌려주는 경로는 mkstemp 로 만든 임시파일 — 호출자가 반드시 정리한다(1-1).
    is_temp = True

    def __init__(self):
        self.url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        self.bucket = os.environ.get("STORAGE_BUCKET", "skin-images")
        self.key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not (self.url and self.key):
            raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_KEY 미설정")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.key}",
            "apikey": self.key,
        }

    def _signed_url(self, key: str, expires_in: int = 900) -> str:
        import httpx
        with httpx.Client(timeout=30) as c:
            r = c.post(
                f"{self.url}/storage/v1/object/sign/{self.bucket}/{key}",
                headers={**self._headers(), "Content-Type": "application/json"},
                json={"expiresIn": expires_in},
            )
            r.raise_for_status()
            data = r.json()
            return f"{self.url}{data['signedURL']}"

    def resolve_local(self, key: str) -> str | None:
        """
        서명 URL 로 원본을 날라 임시파일로 저장하고 경로를 돌려준다.
        - (2-3) 스트리밍 + MAX_DOWNLOAD_BYTES 상한: r.content 로 전량을 메모리에 올리지 않는다.
        - (1-1) 반환된 경로는 호출자(worker.process)가 사용 후 반드시 삭제해야 한다.
        """
        import tempfile
        import httpx

        url = self._signed_url(key)

        suffix = os.path.splitext(key)[1] or ".bin"
        # Windows 에서는 mkstemp 로 만든 파일이 os.fdopen 으로 열린 채 있으면 unlink 가 실패한다.
        # NamedTemporaryFile(delete=False) 는 핸들을 즉시 닫아 경로만 확보하므로 안전하다.
        with tempfile.NamedTemporaryFile(prefix="sl_", suffix=suffix, delete=False) as tmp:
            path = tmp.name
        try:
            with open(path, "wb") as f:
                with httpx.Client(timeout=60) as c:
                    with c.stream("GET", url) as r:
                        if r.status_code == 404:
                            return None
                        r.raise_for_status()
                        written = 0
                        for chunk in r.iter_bytes(_DOWNLOAD_CHUNK):
                            written += len(chunk)
                            if written > MAX_DOWNLOAD_BYTES:
                                raise ValueError(
                                    f"다운로드 상한 초과(최대 {MAX_DOWNLOAD_BYTES // (1024 * 1024)}MB)"
                                )
                            f.write(chunk)
        except Exception:
            # 실패 시 고아 임시파일이 tmpfs(RAM)에 남지 않도록 즉시 정리한다.
            try:
                os.unlink(path)
            except OSError:
                pass
            raise
        return path


def get_storage():
    if os.environ.get("STORAGE_BACKEND") == "supabase":
        return _Supabase()
    return _Local(os.environ.get("STORAGE_DIR", "/data/storage"))
