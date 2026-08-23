"""
처방 규칙 — 확정된 등급/비율(계약)은 고정, 믹스 선택은 config(JSON)에서 주입.
세부 배합(INCI·함량)은 여기 없다 — 코드 슬롯(활성 M01~M11 / PCR PM01~PM03)만 매핑한다.
"""
from __future__ import annotations
import json
import os

_HERE = os.path.dirname(__file__)

# 확정 규칙: 점수(높을수록 양호) → 등급 → 처방 비율
GRADE_TABLE = [(76.0, "양호", 0.0), (60.0, "경미", 0.5), (40.0, "보통", 1.0), (0.0, "위험/심각", 3.0)]


def grade_and_ratio(score: float):
    for lo, g, r in GRADE_TABLE:
        if score >= lo:
            return g, r
    return "위험/심각", 3.0


def load_config() -> dict:
    """
    config/mixes.json 우선, 없으면 example. 운영에선 실제 config 를 마운트/커밋.
    (P1 #5) ENV=prod 에서는 mixes.example.json fallback 을 금지한다 —
    실제 믹스 대신 예시가 조용히 배포되는 사고를 막기 위해 fail-fast.
    dev/staging 은 example 허용(개발 편의).
    """
    env = os.environ.get("ENV", "dev").lower()
    for name in ("mixes.json", "mixes.example.json"):
        p = os.path.join(_HERE, "config", name)
        if os.path.exists(p):
            if env == "prod" and name == "mixes.example.json":
                raise RuntimeError(
                    "ENV=prod 에서는 mixes.example.json 사용 금지 — "
                    "실제 config/mixes.json 을 마운트/커밋하세요."
                )
            with open(p, encoding="utf-8") as f:
                cfg = json.load(f)
            cfg["_source_file"] = name
            return cfg
    return {"trigger_grades": [], "metric_to_mixes": {}, "base_mixes": [], "pcr_to_mixes": {}}


def select_mixes(metrics: dict, cfg: dict):
    """
    지표별 등급을 매기고, trigger 등급 이하인 지표의 믹스 코드를 모은다(중복 제거).
    반환: (per_metric, selected_mixes)
    """
    triggers = set(cfg.get("trigger_grades", []))
    m2m = cfg.get("metric_to_mixes", {})
    per_metric = {}
    selected: list[dict] = []
    seen: set[str] = set()

    for key, ms in (metrics or {}).items():
        val = ms.get("value") if isinstance(ms, dict) else ms
        if val is None:
            continue
        try:
            val = float(val)
        except (TypeError, ValueError):
            continue   # 비정상 지표값은 500 대신 조용히 건너뜀(계약 밖 입력 방어)
        src = ms.get("source") if isinstance(ms, dict) else "unknown"
        g, r = grade_and_ratio(val)
        per_metric[key] = {"score": val, "grade": g, "ratio_pct": r, "source": src}
        # placeholder(예: survey 미제공 민감성/복합성)는 믹스 트리거에서 제외 — 노이즈 방지.
        if src == "placeholder":
            continue
        if g in triggers:
            for code in m2m.get(key, []):
                if code not in seen:
                    seen.add(code)
                    selected.append({"mix": code, "reason": f"{key}={g}"})

    # 베이스 믹스는 항상 포함(placeholder 규칙).
    for code in cfg.get("base_mixes", []):
        if code not in seen:
            seen.add(code)
            selected.append({"mix": code, "reason": "base"})
    return per_metric, selected


def select_pcr_mixes(pcr: dict, cfg: dict):
    """PCR 마커 → PM 코드(placeholder 매핑). pcr 예: {'cutibacterium_high': true}."""
    out = []
    p2m = cfg.get("pcr_to_mixes", {})
    for marker, on in (pcr or {}).items():
        if on and marker in p2m:
            for code in p2m[marker]:
                out.append({"mix": code, "reason": f"pcr:{marker}"})
    return out
