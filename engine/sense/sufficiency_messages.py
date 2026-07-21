"""User-facing sufficiency report messages."""

from __future__ import annotations

from engine.reference.capture_defaults import (
    MIN_SHORT_SIDE_RECOMMENDED_PX,
    RECOMMENDED_SHORT_SIDE_PX,
)
from engine.reference.generation_brief import prep_checklist_message


def user_message(
    verdict: str,
    issues: list[dict],
    *,
    domain: str,
    image: str,
    generation_brief_path: str | None = None,
) -> str:
    lines = [
        f"[gpthreejs sufficiency] verdict={verdict} · domain={domain}",
        f"image: {image}",
        "",
    ]
    if verdict == "pass":
        lines.append("The provided image and specifications are sufficient to continue the pipeline.")
        return "\n".join(lines)

    lines.append("The available information or specification is insufficient or risky. Review the items below:")
    lines.append("")
    for index, item in enumerate(issues, 1):
        severity = str(item.get("severity") or "info")
        if severity == "info" and verdict != "reject":
            continue
        code = item.get("code") or "UNKNOWN"
        message = item.get("message") or ""
        remedy = item.get("remedy") or "See GenerationBrief capture/gen checklist."
        lines.append(f"{index}. [{severity.upper()}] {code}: {message}")
        lines.append(f"   Action: {remedy}")
    blockers = [
        item
        for item in issues
        if item.get("severity") in ("blocker", "error")
    ]
    majors = [item for item in issues if item.get("severity") == "major"]
    lines.append("")
    if blockers:
        lines.append("Recommended agent action: abort or ask. Do not start cast until blockers are resolved.")
    elif majors:
        lines.append("Recommended agent action: ask for more images or specification before conditional progress.")
    else:
        lines.append("Recommended agent action: continue after recording minor issues.")

    codes = {item["code"] for item in issues}
    needs_prep = bool(
        codes
        & {
            "RES_TOO_LOW",
            "RES_MARGINAL",
            "CHAR_SINGLE_VIEW",
            "CHAR_NO_SIDE",
            "DELIVERY_VIEW_INSUFFICIENT",
            "VIEW_COVERAGE_THIN",
            "FILE_MISSING",
        }
    ) or verdict in ("reject", "conditional")
    if needs_prep and verdict != "pass":
        lines.append("")
        lines.append(prep_checklist_message(language="ko"))
        lines.append("")
        lines.append(prep_checklist_message(language="en"))
        if generation_brief_path:
            lines.append(f"GenerationBrief: {generation_brief_path}")
        else:
            lines.append(
                "GenerationBrief: emit via `python -m engine reference-prep` "
                "or attach generationBrief on the report."
            )
    return "\n".join(lines)


def next_steps(
    action: str,
    issues: list[dict],
    *,
    generation_brief_path: str | None = None,
) -> list[str]:
    steps: list[str] = []
    codes = {item["code"] for item in issues}
    if action == "abort":
        steps.append("Stop cast/codegen until blockers are resolved.")
    if action == "ask":
        steps.append("Call request-input / ask the user with userMessage remedies.")
    if "FORMAT_CONVERT" in codes or "FORMAT_UNUSUAL" in codes:
        steps.append("Convert reference to PNG.")
    if "SENSE_MISSING" in codes:
        steps.append("Run: python3 -m engine sense <image> --out work/sense --mode sharp")
    if "LEDGER_ALL_TODO" in codes or "LEDGER_SPARSE" in codes:
        steps.append("Fill Feature Ledger before --strict validate.")

    needs_views = bool(
        codes
        & {
            "CHAR_SINGLE_VIEW",
            "CHAR_NO_SIDE",
            "DELIVERY_VIEW_INSUFFICIENT",
            "VIEW_COVERAGE_THIN",
        }
    )
    needs_res = bool(codes & {"RES_TOO_LOW", "RES_MARGINAL"})

    if needs_views or needs_res or action in ("abort", "ask"):
        steps.append(
            "Write GenerationBrief (reference-prep): transparent-or-solid-neutral background, "
            f"resolution short side ≥ {MIN_SHORT_SIDE_RECOMMENDED_PX}px "
            f"(prefer {RECOMMENDED_SHORT_SIDE_PX}px), front+side(+back) views, A-pose/T-pose."
        )
        steps.append(
            "Generate or capture views under the brief, then "
            "`python -m engine reference-register <brief> --images ...` "
            "with evidenceClass design-intent (never silent observed)."
        )
        steps.append("Re-run sufficiency-set; only then cast.")
        if generation_brief_path:
            steps.append(f"Open GenerationBrief at {generation_brief_path}")
    if "CHAR_SINGLE_VIEW" in codes or "CHAR_NO_SIDE" in codes:
        steps.append(
            "Request front and side (and optionally back) turnaround images "
            "with transparent or solid neutral background and clear pose."
        )
    if "RES_TOO_LOW" in codes or "RES_MARGINAL" in codes:
        steps.append(
            f"Request higher-resolution source (short side ≥ {MIN_SHORT_SIDE_RECOMMENDED_PX}px; "
            f"recommended {RECOMMENDED_SHORT_SIDE_PX}px)."
        )
    if action == "continue" and not steps:
        steps.append("Proceed to brief/ledger/blueprint or next open cast layer.")
    return steps
