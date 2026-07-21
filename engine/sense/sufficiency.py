"""
Image & specification sufficiency gate.

Reports when a reference (and optional sense pack / brief / ledger / blueprint)
lacks enough information for a reliable gpthreejs cast — with codes, severity,
remedies, and a recommended agent action (continue | ask | abort).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.shared.jsonutil import dump_json, load_json
from engine.sense.sufficiency_checks import (
    assess_image_file,
    assess_intent_and_views,
    assess_sense_pack,
    assess_spec,
)
from engine.sense.sufficiency_messages import next_steps, user_message
from engine.sense.sufficiency_policy import (
    sufficiency_score,
    verdict_and_action,
)


def _load_optional(path: str | Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    try:
        data = load_json(p)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def assess_sufficiency(
    image: str | Path,
    *,
    sense_path: str | Path | None = None,
    brief_path: str | Path | None = None,
    ledger_path: str | Path | None = None,
    blueprint_path: str | Path | None = None,
    domain: str | None = None,
    intent: str | None = None,
    view_count: int = 1,
    has_side: bool = False,
    has_back: bool = False,
    out: str | Path | None = None,
) -> dict[str, Any]:
    """
    Full sufficiency report.

    agentAction:
      - continue: proceed (maybe with notes)
      - ask: request more views / cleaner input / fill ledger
      - abort: not feasible with current inputs
    """
    issues, img_meta = assess_image_file(image)

    sense = _load_optional(sense_path)
    # also accept directory containing sense_pack.json
    if sense is None and sense_path:
        sp = Path(sense_path)
        if sp.is_dir() and (sp / "sense_pack.json").exists():
            sense = load_json(sp / "sense_pack.json")

    sense_issues, sense_meta = assess_sense_pack(sense)
    issues.extend(sense_issues)

    brief = _load_optional(brief_path)
    ledger = _load_optional(ledger_path)
    blueprint = _load_optional(blueprint_path)

    dom = domain or (brief or {}).get("domain") or (blueprint or {}).get("domain") or "object"
    intent_v = intent or (brief or {}).get("intent") or "realtime-prop"

    issues.extend(
        assess_intent_and_views(
            domain=str(dom),
            intent=str(intent_v),
            view_count=view_count,
            has_side=has_side,
            has_back=has_back,
        )
    )
    issues.extend(
        assess_spec(
            brief=brief,
            ledger=ledger,
            blueprint=blueprint,
            domain=str(dom),
        )
    )

    verdict, action, sufficient = verdict_and_action(issues)
    # If only SENSE_MISSING info and image ok → still pass-ish
    non_info = [i for i in issues if i["severity"] != "info"]
    if not non_info and verdict == "conditional":
        verdict, action, sufficient = "pass", "continue", True

    report: dict[str, Any] = {
        "version": 1,
        "verdict": verdict,  # pass | conditional | reject
        "sufficient": sufficient,
        "score": sufficiency_score(issues),
        "agentAction": action,  # continue | ask | abort
        "domain": dom,
        "intent": intent_v,
        "image": str(Path(image).resolve()) if Path(image).exists() else str(image),
        "issues": issues,
        "summary": {
            "blockers": sum(1 for i in issues if i["severity"] == "blocker"),
            "majors": sum(1 for i in issues if i["severity"] == "major"),
            "minors": sum(1 for i in issues if i["severity"] == "minor"),
            "infos": sum(1 for i in issues if i["severity"] == "info"),
        },
        "evidence": {
            "image": img_meta,
            "sense": sense_meta,
            "viewCount": view_count,
            "hasSide": has_side,
            "hasBack": has_back,
            "artifacts": {
                "sense": bool(sense),
                "brief": brief is not None,
                "ledger": ledger is not None,
                "blueprint": blueprint is not None,
            },
        },
        "userMessage": user_message(verdict, issues, domain=str(dom), image=str(image)),
        "nextSteps": next_steps(action, issues),
    }

    if out:
        dump_json(out, report)
    return report
