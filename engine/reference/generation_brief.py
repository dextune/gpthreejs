"""GenerationBrief contract: schema, validation, and pure builders (RP-001)."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from engine.reference.capture_defaults import (
    CHARACTER_RECOMMENDED_VIEW_IDS,
    CHARACTER_REQUIRED_VIEW_IDS,
    EVIDENCE_CLASS_GENERATED,
    INTAKE_ROUTES,
    MIN_SHORT_SIDE_RECOMMENDED_PX,
    RECOMMENDED_SHORT_SIDE_PX,
    VIEW_CAMERA_MAP,
    frame_defaults,
    pose_defaults,
)
from engine.shared.jsonutil import dump_json, load_json

GENERATION_BRIEF_SCHEMA_VERSION = 1
GENERATION_BRIEF_REQUIRED_FIELDS = (
    "schemaVersion",
    "subject",
    "route",
    "evidenceClassDefault",
    "views",
    "frame",
    "pose",
)

# Issue codes that drive view / frame requirements in the brief.
ISSUE_VIEW_SIDE_CODES = frozenset(
    {
        "CHAR_SINGLE_VIEW",
        "CHAR_NO_SIDE",
        "DELIVERY_VIEW_INSUFFICIENT",
        "VIEW_COVERAGE_THIN",
    }
)
ISSUE_RES_CODES = frozenset({"RES_TOO_LOW", "RES_MARGINAL"})
ISSUE_BACK_CODES = frozenset({"CHAR_NO_BACK"})


class GenerationBriefError(ValueError):
    """Raised when a GenerationBrief cannot be parsed."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


def generation_brief_schema() -> dict[str, Any]:
    return deepcopy(_GENERATION_BRIEF_SCHEMA)


def validate_generation_brief(brief: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in GENERATION_BRIEF_REQUIRED_FIELDS:
        if field not in brief:
            errors.append(f"$.{field}: missing required field")

    if brief.get("schemaVersion") != GENERATION_BRIEF_SCHEMA_VERSION:
        errors.append("$.schemaVersion: expected 1")

    subject = brief.get("subject")
    if subject is not None and (not isinstance(subject, str) or not subject.strip()):
        errors.append("$.subject: expected non-empty string")

    route = brief.get("route")
    if route is not None and route not in INTAKE_ROUTES:
        errors.append(f"$.route: unsupported route {route!r}")

    evidence = brief.get("evidenceClassDefault")
    if evidence is not None and evidence not in (
        "design-intent",
        "design-hypothesis",
        "observed",
        "inferred",
    ):
        errors.append(f"$.evidenceClassDefault: unsupported class {evidence!r}")
    # Generated default must never be silent observed.
    if evidence == "observed" and brief.get("route") in (
        "concept-first",
        "redesign-from-ref",
    ):
        errors.append(
            "$.evidenceClassDefault: concept-first/redesign-from-ref cannot default to observed"
        )

    views = brief.get("views")
    if views is not None:
        if not isinstance(views, list) or not views:
            errors.append("$.views: expected non-empty array")
        else:
            for index, view in enumerate(views):
                path = f"$.views[{index}]"
                if not isinstance(view, dict):
                    errors.append(f"{path}: expected object")
                    continue
                if not view.get("id"):
                    errors.append(f"{path}.id: missing")
                if "required" not in view:
                    errors.append(f"{path}.required: missing")

    frame = brief.get("frame")
    if frame is not None:
        if not isinstance(frame, dict):
            errors.append("$.frame: expected object")
        else:
            min_side = frame.get("minShortSidePx")
            if min_side is not None and (
                not isinstance(min_side, (int, float)) or int(min_side) < 256
            ):
                errors.append("$.frame.minShortSidePx: expected number >= 256")

    return errors


def parse_generation_brief(path: str | Path) -> dict[str, Any]:
    data = load_json(path)
    if not isinstance(data, dict):
        raise GenerationBriefError(["$: expected object"])
    errors = validate_generation_brief(data)
    if errors:
        raise GenerationBriefError(errors)
    return data


def write_generation_brief(path: str | Path, brief: dict[str, Any]) -> dict[str, Any]:
    errors = validate_generation_brief(brief)
    if errors:
        raise GenerationBriefError(errors)
    dump_json(path, brief)
    return brief


def _issue_codes(issues: list[dict[str, Any]] | None) -> set[str]:
    if not issues:
        return set()
    return {str(item.get("code") or "") for item in issues if item.get("code")}


def _domain_from_request(request: dict[str, Any] | None) -> str:
    if not request:
        return "character"
    profile = str(request.get("modelingProfile") or "")
    if profile == "stylized-character":
        return "character"
    if request.get("domain"):
        return str(request["domain"])
    return "object" if profile == "generic-prop" else "character"


def _resolve_route(
    *,
    route: str | None,
    request: dict[str, Any] | None,
    has_seed_image: bool,
    issue_codes: set[str] | None = None,
) -> str:
    if route and route in INTAKE_ROUTES:
        return route
    if request and request.get("route") in INTAKE_ROUTES:
        return str(request["route"])
    if request and request.get("redesignPolicy"):
        return "redesign-from-ref"
    if request and request.get("redesign"):
        return "redesign-from-ref"
    if not has_seed_image:
        return "concept-first"
    codes = issue_codes or set()
    # Seed present but sufficiency issues → redesign prep, not photo-lock.
    if codes & (ISSUE_VIEW_SIDE_CODES | ISSUE_RES_CODES | ISSUE_BACK_CODES):
        return "redesign-from-ref"
    return "photo-lock"


def _build_views(
    *,
    domain: str,
    codes: set[str],
    request: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    required_ids: set[str] = set()
    optional_ids: set[str] = set()

    target = list((request or {}).get("targetViews") or [])
    for view_id in target:
        normalized = "side" if view_id in ("left", "right", "side") else view_id
        if normalized in ("front", "side", "back", "source-34"):
            required_ids.add(normalized if normalized != "source-34" else "front")

    if domain == "character":
        required_ids.update(CHARACTER_REQUIRED_VIEW_IDS)
        optional_ids.update(CHARACTER_RECOMMENDED_VIEW_IDS)
        if codes & ISSUE_VIEW_SIDE_CODES:
            required_ids.add("side")
            required_ids.add("front")
        if codes & ISSUE_BACK_CODES:
            required_ids.add("back")
    else:
        if not required_ids:
            required_ids.add("front")
        if codes & ISSUE_VIEW_SIDE_CODES:
            optional_ids.add("side")

    # Prefer front then side then back order.
    order = ["front", "side", "back", "source-34"]
    seen: set[str] = set()
    views: list[dict[str, Any]] = []
    for view_id in order:
        if view_id in required_ids or view_id in optional_ids:
            if view_id in seen:
                continue
            seen.add(view_id)
            views.append(
                {
                    "id": view_id,
                    "camera": VIEW_CAMERA_MAP.get(view_id, f"orthographic-{view_id}"),
                    "required": view_id in required_ids,
                }
            )
    for view_id in sorted(required_ids | optional_ids):
        if view_id in seen:
            continue
        seen.add(view_id)
        views.append(
            {
                "id": view_id,
                "camera": VIEW_CAMERA_MAP.get(view_id, f"orthographic-{view_id}"),
                "required": view_id in required_ids,
            }
        )
    return views


def _host_prompt(
    subject: str,
    *,
    route: str,
    views: list[dict[str, Any]],
    frame: dict[str, Any],
    pose: dict[str, Any],
    style_direction: str | None,
) -> str:
    view_list = ", ".join(
        f"{v['id']}({'required' if v.get('required') else 'optional'})" for v in views
    )
    style = style_direction or "modern hard-surface fantasy, clean readable silhouette"
    return (
        f"Create casting-favorable reference views for: {subject}. "
        f"Route={route}. Views: {view_list}. "
        f"Each view: separate PNG, short side ≥ {frame.get('minShortSidePx')}px "
        f"(prefer {frame.get('recommendedShortSidePx')}px), "
        f"aspect {frame.get('aspect')}, background {frame.get('background')} "
        f"(hex {frame.get('backgroundHex')}, alpha preferred={frame.get('alphaPreferred')}). "
        f"Pose: {pose.get('preset')}, {pose.get('facing')}, no heavy occlusion. "
        f"Style: {style}. One subject centered, soft studio lighting, no harsh rim."
    )


def build_generation_brief(
    *,
    subject: str | None = None,
    request: dict[str, Any] | None = None,
    issues: list[dict[str, Any]] | None = None,
    route: str | None = None,
    has_seed_image: bool = False,
    identity_locks: list[str] | None = None,
    style: dict[str, Any] | None = None,
    seed_image: str | None = None,
) -> dict[str, Any]:
    """Pure builder: issue codes + RequestSpec → GenerationBrief dict."""

    req = request or {}
    codes = _issue_codes(issues)
    domain = _domain_from_request(req)
    resolved_route = _resolve_route(
        route=route,
        request=req,
        has_seed_image=has_seed_image or bool(seed_image),
        issue_codes=codes,
    )
    subject_text = (
        (subject or req.get("subject") or "unspecified subject").strip()
        or "unspecified subject"
    )

    min_side = MIN_SHORT_SIDE_RECOMMENDED_PX
    rec_side = RECOMMENDED_SHORT_SIDE_PX
    if codes & ISSUE_RES_CODES:
        # Always recommend above hard floor when resolution was the problem.
        min_side = MIN_SHORT_SIDE_RECOMMENDED_PX
        rec_side = RECOMMENDED_SHORT_SIDE_PX

    frame = frame_defaults(
        min_short_side_px=min_side,
        recommended_short_side_px=rec_side,
    )
    pose = pose_defaults()
    views = _build_views(domain=domain, codes=codes, request=req)

    evidence_default = EVIDENCE_CLASS_GENERATED
    if resolved_route == "photo-lock":
        evidence_default = "observed"

    locks = list(identity_locks or [])
    if not locks and req.get("mustHave"):
        locks = [str(item.get("id")) for item in req["mustHave"] if item.get("id")]

    style_payload = style or {
        "direction": "modern hard-surface fantasy",
        "not": ["photoreal human skin pores", "illegible micro deco"],
    }

    brief: dict[str, Any] = {
        "schemaVersion": GENERATION_BRIEF_SCHEMA_VERSION,
        "subject": subject_text,
        "route": resolved_route,
        "domain": domain,
        "evidenceClassDefault": evidence_default,
        "views": views,
        "frame": frame,
        "pose": pose,
        "identityLocks": locks,
        "style": style_payload,
        "remediesFromIssues": sorted(c for c in codes if c),
        "hostPrompt": "",
        "perViewPrompts": {},
    }
    if seed_image:
        brief["seedImage"] = seed_image
        if resolved_route == "redesign-from-ref":
            brief["seedEvidenceClass"] = "observed"
            brief["seedRole"] = "identity-seed"
    if req.get("redesignPolicy"):
        brief["redesignPolicy"] = req["redesignPolicy"]
    elif resolved_route == "redesign-from-ref":
        brief["redesignPolicy"] = {
            "redesign": True,
            "likenessFloor": "stylized",
            "matchSourcePixels": False,
        }
    elif resolved_route == "concept-first":
        brief["redesignPolicy"] = {
            "redesign": True,
            "likenessFloor": "stylized",
            "matchSourcePixels": False,
            "source": "text-only",
        }

    brief["hostPrompt"] = _host_prompt(
        subject_text,
        route=resolved_route,
        views=views,
        frame=frame,
        pose=pose,
        style_direction=str(style_payload.get("direction") or ""),
    )
    for view in views:
        brief["perViewPrompts"][view["id"]] = (
            f"{brief['hostPrompt']} Focus: single {view['id']} view only, "
            f"camera {view.get('camera')}."
        )

    errors = validate_generation_brief(brief)
    if errors:
        raise GenerationBriefError(errors)
    return brief


def build_generation_brief_from_issues(
    issues: list[dict[str, Any]],
    *,
    request: dict[str, Any] | None = None,
    subject: str | None = None,
    route: str | None = None,
    seed_image: str | None = None,
) -> dict[str, Any]:
    """Map sufficiency issue list → GenerationBrief (unit-test entry point)."""
    return build_generation_brief(
        subject=subject,
        request=request,
        issues=issues,
        route=route,
        has_seed_image=bool(seed_image),
        seed_image=seed_image,
    )


def prep_checklist_message(*, language: str = "ko") -> str:
    """Human checklist for capture/gen (UX-002 / SK-002)."""
    if language == "en":
        return (
            "Capture/gen checklist before cast:\n"
            f"1) Resolution: short side ≥ {MIN_SHORT_SIDE_RECOMMENDED_PX}px "
            f"(prefer {RECOMMENDED_SHORT_SIDE_PX}px; hard floor 256px).\n"
            "2) Background: transparent PNG or solid neutral gray.\n"
            "3) Views (character): front + side required; back recommended.\n"
            "4) Pose: A-pose or T-pose, facing camera-relative, no heavy occlusion.\n"
            "5) One view per file, PNG format.\n"
            "Options: (A) host generates under GenerationBrief (B) user uploads "
            "(C) explicit limited-info stylization waiver (not recommended)."
        )
    return (
        "캐스팅 전 생성/촬영 체크리스트:\n"
        f"1) 해상도: 짧은 변 ≥ {MIN_SHORT_SIDE_RECOMMENDED_PX}px "
        f"(권장 {RECOMMENDED_SHORT_SIDE_PX}px; 절대 하한 256px).\n"
        "2) 배경: 투명 PNG 또는 중성 단색(solid neutral).\n"
        "3) 뷰(캐릭터): 정면(front) + 측면(side) 필수, 후면(back) 권장.\n"
        "4) 포즈: A-pose/T-pose, 카메라 기준 정면, 심한 가림 금지.\n"
        "5) 파일 하나당 한 뷰, PNG.\n"
        "선택: (A) 호스트가 GenerationBrief로 생성 (B) 사용자 업로드 "
        "(C) 정보 부족 스타일라이즈드 waiver 명시(기본 비권장)."
    )


_GENERATION_BRIEF_SCHEMA = {
    "title": "gpthreejs GenerationBrief",
    "type": "object",
    "required": list(GENERATION_BRIEF_REQUIRED_FIELDS),
    "properties": {
        "schemaVersion": {"const": GENERATION_BRIEF_SCHEMA_VERSION},
        "subject": {"type": "string", "minLength": 1},
        "route": {"type": "string", "enum": list(INTAKE_ROUTES)},
        "evidenceClassDefault": {
            "type": "string",
            "enum": [
                "observed",
                "design-intent",
                "design-hypothesis",
                "inferred",
            ],
        },
        "views": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "required"],
                "properties": {
                    "id": {"type": "string"},
                    "camera": {"type": "string"},
                    "required": {"type": "boolean"},
                },
            },
        },
        "frame": {"type": "object"},
        "pose": {"type": "object"},
        "identityLocks": {"type": "array"},
        "style": {"type": "object"},
        "hostPrompt": {"type": "string"},
        "perViewPrompts": {"type": "object"},
        "remediesFromIssues": {"type": "array", "items": {"type": "string"}},
    },
}
