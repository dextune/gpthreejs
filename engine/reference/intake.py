"""Intake routing: text-only / concept-first RequestSpec builders (RP-004)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.reference.capture_defaults import INTAKE_ROUTES
from engine.reference.generation_brief import build_generation_brief, write_generation_brief
from engine.reference.request import REQUEST_SPEC_SCHEMA_VERSION, validate_request_spec
from engine.shared.jsonutil import dump_json


def build_request_spec_from_intent(
    subject: str,
    *,
    domain: str = "character",
    intent: str = "game",
    quality_mode: str = "sharp",
    route: str = "concept-first",
    delivery_grade: str = "standard",
    must_have: list[dict[str, Any]] | None = None,
    redesign: bool = False,
) -> dict[str, Any]:
    """Build a RequestSpec suitable for concept-first or redesign intake."""

    if route not in INTAKE_ROUTES:
        raise ValueError(f"unsupported intake route: {route!r}")

    if domain == "character":
        modeling_profile = "stylized-character"
        target_views = ["front", "side", "back"]
        required_views = ["front", "side"]
    elif domain == "hybrid":
        modeling_profile = "stylized-character"
        target_views = ["front", "side"]
        required_views = ["front", "side"]
    else:
        modeling_profile = "generic-prop"
        target_views = ["front"]
        required_views = ["front"]

    is_redesign = redesign or route in ("concept-first", "redesign-from-ref")
    spec: dict[str, Any] = {
        "schemaVersion": REQUEST_SPEC_SCHEMA_VERSION,
        "subject": subject.strip(),
        "intent": intent,
        "modelingProfile": modeling_profile,
        "qualityMode": quality_mode,
        "mustHave": list(must_have or []),
        "mustNotHave": [],
        "targetViews": target_views,
        "requiredViews": required_views,
        "deliveryGrade": delivery_grade,
        "domain": domain,
        "route": route,
    }
    if is_redesign:
        spec["redesign"] = True
        spec["redesignPolicy"] = {
            "redesign": True,
            "likenessFloor": "stylized",
            "matchSourcePixels": False,
        }
    errors = validate_request_spec(spec)
    if errors:
        raise ValueError("; ".join(errors))
    return spec


def run_intake(
    subject: str,
    *,
    domain: str = "character",
    intent: str = "game",
    quality_mode: str = "sharp",
    route: str = "concept-first",
    out: str | Path | None = None,
    brief_out: str | Path | None = None,
) -> dict[str, Any]:
    """Text-only intake: RequestSpec + GenerationBrief (no cast)."""

    has_seed = route in ("photo-lock", "redesign-from-ref")
    # concept-first is the text-only path; no seed assumed.
    if route == "concept-first":
        has_seed = False

    request = build_request_spec_from_intent(
        subject,
        domain=domain,
        intent=intent,
        quality_mode=quality_mode,
        route=route,
        redesign=route in ("concept-first", "redesign-from-ref"),
    )
    brief = build_generation_brief(
        subject=subject,
        request=request,
        route=route,
        has_seed_image=has_seed,
        issues=[
            {
                "code": "CHAR_NO_SIDE",
                "severity": "major",
                "message": "concept-first requires planned multi-view references",
                "remedy": "generate front+side under GenerationBrief",
            }
        ]
        if domain == "character"
        else None,
    )

    result: dict[str, Any] = {
        "schemaVersion": 1,
        "request": request,
        "generationBrief": brief,
        "agentAction": "ask",
        "nextSteps": [
            "Review GenerationBrief frame/views/pose defaults.",
            "Generate or capture views under the brief (host or user).",
            "Register views with evidenceClass design-intent (not observed).",
            "Re-run sufficiency-set; only then cast.",
        ],
    }
    if out:
        dump_json(out, request)
        result["requestPath"] = str(out)
    if brief_out:
        write_generation_brief(brief_out, brief)
        result["generationBriefPath"] = str(brief_out)
    return result
