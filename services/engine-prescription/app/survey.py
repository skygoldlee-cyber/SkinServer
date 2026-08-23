"""
설문 해석 (baseline, tunable) — 고객 설문 → 설문 기반 지표 점수(0~100, 높을수록 양호).
CV 로는 신뢰가 어려운 민감성/복합성 등을 설문으로 채운다. 실제 문항·척도·가중은
도메인 결정이므로 아래 상수/규칙은 placeholder 로 명시(교체 대상).
"""
from __future__ import annotations


def survey_to_metrics(survey: dict | None) -> dict:
    """인식하는 필드만 사용해 일부 지표를 산출. 없으면 빈 dict."""
    if not survey:
        return {}
    out: dict[str, dict] = {}
    st = (survey.get("skin_type") or "").lower()
    sens = survey.get("sensitivity") or {}
    flags = sum(1 for v in sens.values() if v) if isinstance(sens, dict) else 0

    # 민감성: 자가보고 'sensitive' + 플래그 개수 → 낮을수록 민감(=나쁨). (placeholder 계수)
    if st == "sensitive" or flags:
        val = 70 - 15 * flags - (20 if st == "sensitive" else 0)
        out["sensitivity"] = {"value": float(max(0, min(100, val))), "source": "survey"}
    else:
        out["sensitivity"] = {"value": 85.0, "source": "survey"}

    # 복합성: 자가보고 skin_type 로만 판단(placeholder). combination 이면 경향 반영.
    if st == "combination":
        out["combination"] = {"value": 55.0, "source": "survey"}
    elif st in ("oily", "dry", "normal", "sensitive"):
        out["combination"] = {"value": 80.0, "source": "survey"}

    return out


def survey_concerns(survey: dict | None) -> list[str]:
    """고객이 고른 관심 지표(기록/후속 가중용)."""
    if not survey:
        return []
    c = survey.get("concerns") or []
    return [str(x) for x in c] if isinstance(c, list) else []
