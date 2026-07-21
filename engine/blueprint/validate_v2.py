"""Blueprint v2 structural validation."""

from __future__ import annotations

import math
from typing import Any

from engine.blueprint.ledger_validation import validate_ledger_contract
from engine.blueprint.validate import ValidationResult
from engine.contracts.blueprint_v2 import (
    BLUEPRINT_V2_SCHEMA_VERSION,
    TOP_LEVEL_REQUIRED_FIELDS,
    blueprint_v2_required_fields,
)
from engine.geometry.schema import validate_geometry_required_fields


VECTOR3_FIELDS = {"position", "translation", "rotation", "scale", "size"}


def _walk_parts(parts: list[dict[str, Any]], path: str = "$.parts") -> list[tuple[dict[str, Any], str]]:
    found: list[tuple[dict[str, Any], str]] = []
    for index, part in enumerate(parts):
        part_path = f"{path}[{index}]"
        found.append((part, part_path))
        found.extend(_walk_parts(part.get("children") or [], f"{part_path}.children"))
    return found


def _add_missing(result: ValidationResult, value: dict[str, Any], fields: tuple[str, ...], path: str) -> None:
    for field in fields:
        if field not in value:
            result.errors.append(f"{path}.{field}: missing required field")


def _collect_id(
    result: ValidationResult,
    seen: dict[str, str],
    value: dict[str, Any],
    path: str,
    namespace: str,
) -> None:
    item_id = value.get("id")
    if not item_id:
        result.errors.append(f"{path}.id: missing id")
        return
    scoped = f"{namespace}:{item_id}"
    if scoped in seen:
        result.errors.append(f"{path}.id: duplicate id {item_id!r}; first seen at {seen[scoped]}")
        return
    seen[scoped] = f"{path}.id"


def _check_finite_numbers(result: ValidationResult, value: Any, path: str = "$") -> None:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            result.errors.append(f"{path}: non-finite number")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _check_finite_numbers(result, item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _check_finite_numbers(result, item, f"{path}.{key}")


def _check_vector_lengths(result: ValidationResult, value: Any, path: str = "$") -> None:
    if isinstance(value, list):
        for index, item in enumerate(value):
            _check_vector_lengths(result, item, f"{path}[{index}]")
        return
    if not isinstance(value, dict):
        return
    for key, item in value.items():
        item_path = f"{path}.{key}"
        if (
            key in VECTOR3_FIELDS
            and isinstance(item, list)
            and len(item) != 3
            and not (key == "position" and path.startswith("$.landmarks["))
        ):
            result.errors.append(f"{item_path}: expected vector length 3, got {len(item)}")
        _check_vector_lengths(result, item, item_path)


def _check_landmark_positions(result: ValidationResult, landmarks: list[dict[str, Any]]) -> None:
    for index, landmark in enumerate(landmarks):
        position = landmark.get("position")
        if isinstance(position, list) and len(position) not in (2, 3):
            result.errors.append(f"$.landmarks[{index}].position: expected vector length 2 or 3, got {len(position)}")


def _check_parent_cycles(result: ValidationResult, parts: list[tuple[dict[str, Any], str]]) -> None:
    parents = {
        part["id"]: part.get("parentId")
        for part, _path in parts
        if part.get("id") and part.get("parentId")
    }
    paths = {part.get("id"): path for part, path in parts if part.get("id")}
    for part_id in parents:
        visiting: set[str] = set()
        current: str | None = part_id
        while current in parents:
            if current in visiting:
                result.errors.append(f"{paths.get(part_id, '$.parts')}.parentId: parent cycle includes {current!r}")
                break
            visiting.add(current)
            current = parents.get(current)


def validate_blueprint_v2(blueprint: dict[str, Any], *, strict: bool = False) -> ValidationResult:
    result = ValidationResult()
    required = blueprint_v2_required_fields()

    if blueprint.get("schemaVersion") != BLUEPRINT_V2_SCHEMA_VERSION:
        result.errors.append("$.schemaVersion: expected 2")
    _add_missing(result, blueprint, TOP_LEVEL_REQUIRED_FIELDS, "$")
    _check_finite_numbers(result, blueprint)
    _check_vector_lengths(result, blueprint)

    parts = _walk_parts(blueprint.get("parts") or [])
    material_ids = {material.get("id") for material in blueprint.get("materials") or []}
    part_ids = {part.get("id") for part, _path in parts}
    handle_ids = set((blueprint.get("handles") or {}).keys())
    render_profile_ids = {profile.get("id") for profile in blueprint.get("renderProfiles") or []}

    seen: dict[str, str] = {}
    for part, path in parts:
        _add_missing(result, part, required["part"], path)
        _collect_id(result, seen, part, path, "part")
        material_id = part.get("materialId")
        if material_id and material_id not in material_ids:
            result.errors.append(f"{path}.materialId: dangling material reference {material_id!r}")
        geometry = part.get("geometry")
        if isinstance(geometry, dict):
            result.errors.extend(validate_geometry_required_fields(geometry, path=f"{path}.geometry"))
        attachment = part.get("attachment")
        if isinstance(attachment, dict):
            _add_missing(result, attachment, required["attachment"], f"{path}.attachment")
            for socket_key in ("parentSocket", "childSocket"):
                socket = attachment.get(socket_key)
                if socket and socket not in handle_ids:
                    result.errors.append(f"{path}.attachment.{socket_key}: dangling socket reference {socket!r}")

    for index, material in enumerate(blueprint.get("materials") or []):
        path = f"$.materials[{index}]"
        _add_missing(result, material, required["material"], path)
        _collect_id(result, seen, material, path, "material")

    handles = blueprint.get("handles") or {}
    for handle_id, handle in handles.items():
        path = f"$.handles.{handle_id}"
        if isinstance(handle, dict):
            _add_missing(result, handle, required["handle"], path)
            part_id = handle.get("partId")
            if part_id and part_id not in part_ids:
                result.errors.append(f"{path}.partId: dangling part reference {part_id!r}")
            if handle.get("id") != handle_id:
                result.errors.append(f"{path}.id: must match handles key {handle_id!r}")

    for index, landmark in enumerate(blueprint.get("landmarks") or []):
        path = f"$.landmarks[{index}]"
        _add_missing(result, landmark, required["landmark"], path)
        _collect_id(result, seen, landmark, path, "landmark")
    _check_landmark_positions(result, blueprint.get("landmarks") or [])

    for index, profile in enumerate(blueprint.get("renderProfiles") or []):
        path = f"$.renderProfiles[{index}]"
        _add_missing(result, profile, required["renderProfile"], path)
        _collect_id(result, seen, profile, path, "renderProfile")

    for index, feature in enumerate(blueprint.get("criticalFeatures") or []):
        path = f"$.criticalFeatures[{index}]"
        _add_missing(result, feature, required["criticalFeature"], path)
        _collect_id(result, seen, feature, path, "criticalFeature")
        for part_id in feature.get("partIds") or []:
            if part_id not in part_ids:
                result.errors.append(f"{path}.partIds: dangling part reference {part_id!r}")
        for view_id in feature.get("targetViews") or []:
            if view_id not in render_profile_ids:
                result.errors.append(f"{path}.targetViews: dangling render profile reference {view_id!r}")

    _check_parent_cycles(result, parts)

    if strict and blueprint.get("ledger"):
        validate_ledger_contract(
            blueprint,
            [part for part, _path in parts],
            result.errors,
            require_character_coverage=blueprint.get("modelingProfile") == "stylized-character",
        )

    if strict and not parts:
        result.errors.append("$.parts: strict Blueprint v2 requires at least one part")

    # PD-2 delivery depth: full character rules when delivery-grade or explicit flag.
    # Minimal schema fixtures stay on structural checks only.
    if strict and blueprint.get("modelingProfile") == "stylized-character":
        if blueprint.get("deliveryGrade") in ("delivery", "strict") or blueprint.get(
            "enforceCharacterDepth"
        ):
            _check_character_delivery_depth(blueprint, parts, result)

    return result


def _check_character_delivery_depth(
    blueprint: dict[str, Any],
    parts: list[tuple[dict[str, Any], str]],
    result: ValidationResult,
) -> None:
    """PD-2: profile rules + semantic depth for stylized-character strict."""

    try:
        from engine.blueprint.profiles import (
            modeling_profile_rules,
            validate_landmarks,
            validate_proportion_profile,
        )
    except Exception:
        return

    profile = str(blueprint.get("modelingProfile") or "stylized-character")
    try:
        rules = modeling_profile_rules(profile)
    except ValueError as exc:
        result.errors.append(f"$.modelingProfile: {exc}")
        return

    result.errors.extend(validate_proportion_profile(blueprint.get("proportionProfile") or {}))
    if rules.get("requireLandmarks"):
        result.errors.extend(
            validate_landmarks(
                blueprint.get("landmarks") or [],
                required=tuple(rules.get("requiredLandmarks") or ()),
            )
        )
    if rules.get("requirePose") and not (blueprint.get("poseProfile") or {}).get("joints"):
        result.errors.append("$.poseProfile.joints: stylized-character requires joint hierarchy")

    roles = {part.get("role") for part, _ in parts}
    for role in rules.get("requiredRoles") or ():
        if role not in roles:
            result.errors.append(f"$.parts: missing required role {role!r}")

    # hierarchy depth from roots
    def depth(part: dict[str, Any], d: int = 1) -> int:
        kids = part.get("children") or []
        if not kids:
            return d
        return max(depth(ch, d + 1) for ch in kids)

    roots = blueprint.get("parts") or []
    max_depth = max((depth(p) for p in roots), default=0) if roots else 0
    min_depth = int(rules.get("minHierarchyDepth") or 1)
    if max_depth < min_depth:
        result.errors.append(
            f"$.parts: hierarchy depth {max_depth} below minimum {min_depth}"
        )

    min_parts = int(rules.get("minParts") or 1)
    if len(parts) < min_parts:
        result.errors.append(f"$.parts: part count {len(parts)} below minimum {min_parts}")

    # critical features must link parts and views
    render_ids = {p.get("id") for p in blueprint.get("renderProfiles") or []}
    part_ids = {p.get("id") for p, _ in parts}
    for index, feat in enumerate(blueprint.get("criticalFeatures") or []):
        path = f"$.criticalFeatures[{index}]"
        if not feat.get("partIds"):
            result.errors.append(f"{path}.partIds: required for delivery-grade character")
        if not feat.get("targetViews"):
            result.errors.append(f"{path}.targetViews: required for delivery-grade character")
