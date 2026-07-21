"""Central sufficiency thresholds and verdict policy."""

from __future__ import annotations

from typing import Any

MIN_SHORT_SIDE = 256
MIN_SHORT_SIDE_SHARP = 512
MIN_MEGAPIXELS = 0.05
MIN_MEGAPIXELS_SHARP = 0.15
MIN_FOREGROUND_RATIO = 0.04
MAX_FOREGROUND_RATIO = 0.97
IDEAL_FOREGROUND = (0.12, 0.85)
VERY_DARK = 28
VERY_BRIGHT = 235
MIN_EDGE_DENSITY = 0.008
MAX_EDGE_DENSITY = 0.55
MIN_LEDGER_FILLED_FRAC = 0.5

Severity = str

SEVERITY_SCORE_PENALTY = {
    "blocker": 0.45,
    "major": 0.18,
    "minor": 0.06,
    "info": 0.02,
}


def issue(
    code: str,
    severity: Severity,
    message: str,
    remedy: str,
    *,
    field: str | None = None,
    evidence: Any = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "code": code,
        "severity": severity,
        "message": message,
        "remedy": remedy,
    }
    if field:
        out["field"] = field
    if evidence is not None:
        out["evidence"] = evidence
    return out


def verdict_and_action(issues: list[dict]) -> tuple[str, str, bool]:
    sevs = {item["severity"] for item in issues}
    if "blocker" in sevs:
        return "reject", "abort", False
    majors = [item for item in issues if item["severity"] == "major"]
    if majors:
        return "conditional", "ask", False
    if issues:
        return "conditional", "continue", True
    return "pass", "continue", True


def sufficiency_score(issues: list[dict]) -> float:
    score = 1.0
    for item in issues:
        score -= SEVERITY_SCORE_PENALTY.get(item["severity"], 0.05)
    return round(max(0.0, min(1.0, score)), 3)
