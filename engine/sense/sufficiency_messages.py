"""User-facing sufficiency report messages."""

from __future__ import annotations


def user_message(
    verdict: str,
    issues: list[dict],
    *,
    domain: str,
    image: str,
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
        if item["severity"] == "info" and verdict != "reject":
            continue
        lines.append(f"{index}. [{item['severity'].upper()}] {item['code']}: {item['message']}")
        lines.append(f"   Action: {item['remedy']}")
    blockers = [item for item in issues if item["severity"] == "blocker"]
    majors = [item for item in issues if item["severity"] == "major"]
    lines.append("")
    if blockers:
        lines.append("Recommended agent action: abort or ask. Do not start cast until blockers are resolved.")
    elif majors:
        lines.append("Recommended agent action: ask for more images or specification before conditional progress.")
    else:
        lines.append("Recommended agent action: continue after recording minor issues.")
    return "\n".join(lines)


def next_steps(action: str, issues: list[dict]) -> list[str]:
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
    if "CHAR_SINGLE_VIEW" in codes or "CHAR_NO_SIDE" in codes:
        steps.append("Request side (and optionally back) turnaround images.")
    if "RES_TOO_LOW" in codes or "RES_MARGINAL" in codes:
        steps.append("Request higher-resolution source.")
    if action == "continue" and not steps:
        steps.append("Proceed to brief/ledger/blueprint or next open cast layer.")
    return steps
