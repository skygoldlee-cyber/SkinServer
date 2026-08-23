"""통합 테스트 픽스처 — 임시 Postgres 스키마 + 엔진 서브프로세스.

DATABASE_URL 이 없으면 통합 테스트를 건너뛴다(단위 전용 환경 보호).
CI 는 postgres 서비스 컨테이너로 DATABASE_URL 을 주입한다.
"""
import os, sys, time, socket, subprocess, pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _free_port() -> int:
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


@pytest.fixture(scope="module")
def database_url():
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL 미설정 — 통합 테스트 건너뜀")
    return url


@pytest.fixture(scope="module")
def schema(database_url):
    """마이그레이션으로 스키마를 새로 만든다(드롭 후 재적용)."""
    import psycopg
    sql = (ROOT / "deploy/db/migrations/0001_init.sql").read_text(encoding="utf-8")
    with psycopg.connect(database_url) as c, c.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS prescriptions, job_events, jobs CASCADE;")
        cur.execute(sql)
        c.commit()
    return True


@pytest.fixture(scope="module")
def engines():
    """engine-analysis / engine-prescription 를 서브프로세스로 띄우고 URL 반환."""
    import httpx
    procs, urls = [], {}
    for name, svc in (("analysis", "engine-analysis"), ("prescription", "engine-prescription")):
        port = _free_port()
        p = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app",
             "--app-dir", str(ROOT / "services" / svc),
             "--host", "127.0.0.1", "--port", str(port)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        procs.append(p); urls[name] = f"http://127.0.0.1:{port}"
    # health 대기
    deadline = time.time() + 40
    for name, base in urls.items():
        while time.time() < deadline:
            try:
                if httpx.get(f"{base}/health", timeout=2).status_code == 200:
                    break
            except Exception:
                time.sleep(0.5)
        else:
            for p in procs: p.terminate()
            pytest.fail(f"engine {name} 기동 실패")
    yield urls
    for p in procs:
        p.terminate()
        try: p.wait(timeout=5)
        except Exception: p.kill()


@pytest.fixture()
def storage_dir(tmp_path):
    d = tmp_path / "storage"; d.mkdir()
    return str(d)
