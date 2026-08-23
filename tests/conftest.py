"""공용 계약(packages/common)은 충돌이 없어 path 에 상시 추가."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "common"))
