"""
(P3 #9) 스키마 드리프트 가드 — gateway auto-DDL(dev)과 deploy/db/migrations(운영)이
같은 DDL 을 정의하는지 CI 에서 강제한다. 둘이 벌어지면 dev/prod 스키마가 달라지는
사고가 생기므로, 어느 한쪽만 고쳐도 이 테스트가 실패해 drift 를 조기에 잡는다.

비교 방식: 정규화(공백/주석/후행 콤마·세미콜론 정리) 후 CREATE 문 단위 집합 비교.
인덱스의 컬럼 간 공백 차이(정렬용 스페이스) 같은 표면적 차이는 무시하고 의미만 본다.
"""
import re
import pathlib

from tests._util import load

ROOT = pathlib.Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "deploy" / "db" / "migrations" / "0001_init.sql"


def _normalize(sql: str) -> str:
    """주석 제거 + 공백/콤마 정규화로 '의미 있는' DDL 만 남긴다."""
    sql = re.sub(r"--[^\n]*", "", sql)          # 한 줄 주석 제거
    sql = sql.lower()
    sql = re.sub(r"\s+", " ", sql)               # 연속 공백 → 단일 공백
    sql = re.sub(r"\s*,\s*", ",", sql)           # 콤마 주변 공백 제거
    sql = re.sub(r"\(\s+", "(", sql)
    sql = re.sub(r"\s+\)", ")", sql)
    return sql.strip()


def _statements(sql: str) -> set[str]:
    """세미콜론으로 문을 나누고 정규화해 비어있지 않은 문 집합을 반환."""
    return {s for s in (_normalize(x) for x in sql.split(";")) if s}


def test_auto_ddl_matches_migration():
    gateway = load("gateway", "app.main")
    auto = _statements(gateway.DDL)
    mig = _statements(MIGRATION.read_text(encoding="utf-8"))

    only_in_auto = auto - mig
    only_in_mig = mig - auto
    assert not only_in_auto, f"auto-DDL 에만 있는 문:\n" + "\n".join(sorted(only_in_auto))
    assert not only_in_mig, f"migration 에만 있는 문:\n" + "\n".join(sorted(only_in_mig))
