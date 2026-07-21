"""Reference Prep handoff from sufficiency reports (RP-003).

Keeps GenerationBrief attach logic out of the thin sufficiency orchestrator.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.sense.sufficiency_messages import next_steps, user_message


def maybe_attach_generation_brief(
    report: dict[str, Any],
    *,
    domain: str,
    intent: str,
    image: str | Path,
    out: str | Path | None,
) -> None:
    """On abort/ask, emit GenerationBrief path/inline."""
    action = report.get("agentAction")
    if action not in ("abort", "ask"):
        return
    try:
        from engine.reference.generation_brief import (
            build_generation_brief_from_issues,
            write_generation_brief,
        )
    except Exception:
        return

    request = {
        "subject": Path(str(image)).stem if image else "subject",
        "intent": intent,
        "modelingProfile": "stylized-character" if domain == "character" else "generic-prop",
        "domain": domain,
        "targetViews": ["front", "side"] if domain == "character" else ["front"],
        "mustHave": [],
        "route": "redesign-from-ref" if Path(str(image)).exists() else "concept-first",
    }
    brief = build_generation_brief_from_issues(
        list(report.get("issues") or []),
        request=request,
        subject=request["subject"],
        seed_image=str(image) if Path(str(image)).exists() else None,
    )
    report["generationBrief"] = brief
    if out:
        brief_path = Path(out).with_name("generation-brief.json")
        write_generation_brief(brief_path, brief)
        report["generationBriefPath"] = str(brief_path)
        report["userMessage"] = user_message(
            report["verdict"],
            report["issues"],
            domain=str(domain),
            image=str(image),
            generation_brief_path=str(brief_path),
        )
        report["nextSteps"] = next_steps(
            str(action),
            report["issues"],
            generation_brief_path=str(brief_path),
        )
    else:
        report["userMessage"] = user_message(
            report["verdict"],
            report["issues"],
            domain=str(domain),
            image=str(image),
        )
        report["nextSteps"] = next_steps(str(action), report["issues"])
