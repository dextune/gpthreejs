"""RequestSpec schema and parser."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from engine.contracts.blueprint_v2 import INTENTS, MODELING_PROFILES
from engine.contracts.modes import QUALITY_MODES
from engine.shared.jsonutil import load_json

REQUEST_SPEC_SCHEMA_VERSION = 1
REQUEST_SPEC_REQUIRED_FIELDS = (
    "schemaVersion",
    "subject",
    "intent",
    "modelingProfile",
    "qualityMode",
    "mustHave",
    "mustNotHave",
    "targetViews",
)
FEATURE_REQUIREMENT_REQUIRED_FIELDS = ("id", "weight")


class RequestSpecError(ValueError):
    """Raised when a RequestSpec cannot be parsed."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


def request_spec_schema() -> dict[str, Any]:
    return deepcopy(_REQUEST_SPEC_SCHEMA)


def validate_request_spec(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in REQUEST_SPEC_REQUIRED_FIELDS:
        if field not in spec:
            errors.append(f"$.{field}: missing required field")

    if spec.get("schemaVersion") != REQUEST_SPEC_SCHEMA_VERSION:
        errors.append("$.schemaVersion: expected 1")
    if spec.get("intent") not in INTENTS:
        errors.append(f"$.intent: unsupported intent {spec.get('intent')!r}")
    if spec.get("modelingProfile") not in MODELING_PROFILES:
        errors.append(f"$.modelingProfile: unsupported profile {spec.get('modelingProfile')!r}")
    if spec.get("qualityMode") not in QUALITY_MODES:
        errors.append(f"$.qualityMode: unsupported quality mode {spec.get('qualityMode')!r}")

    for list_name in ("mustHave", "mustNotHave"):
        items = spec.get(list_name)
        if items is None:
            continue
        if not isinstance(items, list):
            errors.append(f"$.{list_name}: expected array")
            continue
        for index, item in enumerate(items):
            path = f"$.{list_name}[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{path}: expected object")
                continue
            for field in FEATURE_REQUIREMENT_REQUIRED_FIELDS:
                if field not in item:
                    errors.append(f"{path}.{field}: missing required field")
            weight = item.get("weight")
            if not isinstance(weight, (int, float)) or isinstance(weight, bool):
                errors.append(f"{path}.weight: expected number in range 0..1")
            elif not 0 <= float(weight) <= 1:
                errors.append(f"{path}.weight: expected number in range 0..1")

    target_views = spec.get("targetViews")
    if target_views is not None:
        if not isinstance(target_views, list):
            errors.append("$.targetViews: expected array")
        elif not target_views:
            errors.append("$.targetViews: at least one target view is required")
        elif any(not isinstance(view, str) or not view for view in target_views):
            errors.append("$.targetViews: expected non-empty string entries")

    subject = spec.get("subject")
    if subject is not None and (not isinstance(subject, str) or not subject.strip()):
        errors.append("$.subject: expected non-empty string")

    delivery_grade = spec.get("deliveryGrade")
    if delivery_grade is not None and delivery_grade not in ("standard", "delivery", "strict"):
        errors.append(f"$.deliveryGrade: unsupported grade {delivery_grade!r}")

    required_views = spec.get("requiredViews")
    if required_views is not None:
        if not isinstance(required_views, list):
            errors.append("$.requiredViews: expected array")
        elif any(not isinstance(view, str) or not view for view in required_views):
            errors.append("$.requiredViews: expected non-empty string entries")

    return errors


def parse_request_spec(path: str | Path) -> dict[str, Any]:
    spec = load_json(path)
    if not isinstance(spec, dict):
        raise RequestSpecError(["$: expected object"])
    errors = validate_request_spec(spec)
    if errors:
        raise RequestSpecError(errors)
    return spec


_REQUEST_SPEC_SCHEMA = {
    "title": "gpthreejs RequestSpec",
    "type": "object",
    "required": list(REQUEST_SPEC_REQUIRED_FIELDS),
    "properties": {
        "schemaVersion": {"const": REQUEST_SPEC_SCHEMA_VERSION},
        "subject": {"type": "string", "minLength": 1},
        "intent": {"type": "string", "enum": list(INTENTS)},
        "modelingProfile": {"type": "string", "enum": list(MODELING_PROFILES)},
        "qualityMode": {"type": "string", "enum": list(QUALITY_MODES)},
        "mustHave": {"type": "array", "items": {"$ref": "#/$defs/featureRequirement"}},
        "mustNotHave": {"type": "array", "items": {"$ref": "#/$defs/featureRequirement"}},
        "targetViews": {"type": "array", "items": {"type": "string", "minLength": 1}},
        "deliveryGrade": {"type": "string", "enum": ["standard", "delivery", "strict"]},
        "requiredViews": {"type": "array", "items": {"type": "string", "minLength": 1}},
    },
    "$defs": {
        "featureRequirement": {
            "type": "object",
            "required": list(FEATURE_REQUIREMENT_REQUIRED_FIELDS),
            "properties": {
                "id": {"type": "string", "minLength": 1},
                "weight": {"type": "number", "minimum": 0, "maximum": 1},
            },
        }
    },
}
