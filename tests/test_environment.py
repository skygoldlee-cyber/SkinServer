"""
test_environment.py
환경 검증 pytest 스위트 — 로컬 PC / 서버 양쪽에서 실행.

의존성:
    pip install pytest requests

전체 실행:
    pytest test_environment.py -v                                  # localhost(서버 자체)
    TARGET_HOST=192.168.0.50 SSH_USER=coteleaf pytest -v           # 로컬 → 원격

이관 후(외부 호스팅·HTTPS) 검증:  MODE=prod
    TARGET_HOST=your.domain.com SSH_USER=ubuntu MODE=prod pytest -v
    → 22/80/443 만 확인하고 HTTPS 로 응답을 봅니다.
      8000(API)·5432(DB)는 방화벽으로 외부 차단이 '정상'이라(런북 §7-1) 검사에서 제외됩니다.

부분 실행 (-k 이름 매칭, 구축 단계 직후 확인용):
    pytest -k ssh        -v    # SSH 포트 + SSH 로그인만
    pytest -k nginx      -v    # Nginx 포트 + 응답만        (구축 9장 후)
    pytest -k fastapi    -v    # FastAPI 포트 + /docs 만     (구축 9장 후)
    pytest -k postgresql -v    # PostgreSQL 포트만           (구축 9장 후)
    pytest -k port       -v    # 포트 개방만

환경 변수 (모두 선택):
    TARGET_HOST(기본 localhost), SSH_USER, SSH_PORT(22),
    HTTP_PORT(80), HTTPS_PORT(443), API_PORT(8000), PG_PORT(5432),
    MODE(lan|prod, 기본 lan), SCHEME(http|https, 기본 prod=https/lan=http),
    WEB_PORT(웹 검사 포트, 기본 prod=443/lan=80)
"""
import os
import socket
import subprocess

import pytest

try:
    import requests
except ImportError:
    requests = None

HOST      = os.environ.get("TARGET_HOST", "localhost")
MODE      = os.environ.get("MODE", "lan").lower()          # lan | prod
SSH_USER  = os.environ.get("SSH_USER", "")
SSH_PORT  = int(os.environ.get("SSH_PORT", "22"))
HTTP_PORT = int(os.environ.get("HTTP_PORT", "80"))
HTTPS_PORT = int(os.environ.get("HTTPS_PORT", "443"))
API_PORT  = int(os.environ.get("API_PORT", "8000"))
PG_PORT   = int(os.environ.get("PG_PORT", "5432"))

# prod = 외부 호스팅+HTTPS, lan = WSL2/LAN 검증 환경. SCHEME/WEB_PORT 로 개별 override 가능.
IS_PROD   = MODE == "prod"
SCHEME    = os.environ.get("SCHEME", "https" if IS_PROD else "http")
WEB_PORT  = int(os.environ.get("WEB_PORT", str(HTTPS_PORT if IS_PROD else HTTP_PORT)))


def _web_base() -> str:
    # 표준 포트(80/443)면 URL 에서 포트 생략
    if (SCHEME, WEB_PORT) in (("http", 80), ("https", 443)):
        return f"{SCHEME}://{HOST}"
    return f"{SCHEME}://{HOST}:{WEB_PORT}"


# 검사할 포트 목록: prod 는 8000(API)/5432(DB) 외부 차단이 정상 → 제외(런북 §7-1)
if IS_PROD:
    _PORTS = [(SSH_PORT, "SSH"), (HTTP_PORT, "HTTP"), (HTTPS_PORT, "HTTPS")]
else:
    _PORTS = [(SSH_PORT, "SSH"), (HTTP_PORT, "Nginx"),
              (API_PORT, "FastAPI"), (PG_PORT, "PostgreSQL")]
_PORT_IDS = [name for _, name in _PORTS]


def _port_open(host: str, port: int, timeout: float = 5.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# 파라미터 id(SSH/Nginx/FastAPI/PostgreSQL/HTTP/HTTPS)로 -k 부분 선택이 가능하도록 ids 지정
@pytest.mark.parametrize("port,name", _PORTS, ids=_PORT_IDS)
def test_port_open(port, name):
    assert _port_open(HOST, port), f"{name} 포트 {port} 연결 실패 (host={HOST})"


@pytest.mark.skipif(requests is None, reason="requests 미설치")
def test_nginx_responds():
    # lan: http://HOST:80 / prod: https://도메인 (http→https 리다이렉트는 requests 가 자동으로 따라감)
    r = requests.get(_web_base(), timeout=8)
    assert r.status_code < 500, f"프런트({_web_base()}) 5xx 응답: {r.status_code}"


@pytest.mark.skipif(requests is None, reason="requests 미설치")
@pytest.mark.skipif(IS_PROD, reason="prod: 8000(FastAPI)은 외부 차단이 정상 → 서버 내부에서 확인")
def test_fastapi_docs():
    r = requests.get(f"http://{HOST}:{API_PORT}/docs", timeout=8)
    assert r.status_code == 200, f"FastAPI /docs 비정상: {r.status_code}"


@pytest.mark.skipif(not SSH_USER, reason="SSH_USER 미지정 → 원격 SSH 로그인 검사 스킵")
def test_ssh_login():
    result = subprocess.run(
        [
            "ssh", "-p", str(SSH_PORT),
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=8",
            "-o", "StrictHostKeyChecking=accept-new",
            f"{SSH_USER}@{HOST}", "echo OK",
        ],
        capture_output=True, text=True, timeout=20,
    )
    assert "OK" in result.stdout, f"SSH 로그인 실패: {result.stderr.strip()}"
