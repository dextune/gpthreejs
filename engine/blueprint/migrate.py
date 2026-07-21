"""Blueprint migration and compatibility helpers."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from engine.contracts.blueprint_v2 import BLUEPRINT_V2_SCHEMA_VERSION
from engine.shared.artifacts import blueprint_revision_content_hash
from engine.shared.jsonutil import dump_json, load_json


def is_blueprint_v2(blueprint: dict[str, Any]) -> bool:
    return blueprint.get("schemaVersion") == BLUEPRINT_V2_SCHEMA_VERSION


def _modeling_profile(domain: str | None) -> str:
    if domain in ("character", "hybrid"):
        return "stylized-character"
    return "generic-prop"


def _v2_transform(transform: dict[str, Any] | None) -> dict[str, Any]:
    transform = transform or {}
    position = transform.get("position") or transform.get("translation") or [0, 0, 0]
    return {
        "translation": list(position),
        "position": list(position),
        "rotation": list(transform.get("rotation") or [0, 0, 0]),
        "scale": list(transform.get("scale") or [1, 1, 1]),
    }


def _migrate_part(part: dict[str, Any]) -> dict[str, Any]:
    migrated = deepcopy(part)
    migrated["name"] = migrated.get("name") or migrated.get("id") or "part"
    migrated["role"] = migrated.get("role") or "primary"
    migrated["geometry"] = migrated.get("geometry") or {"kind": "box", "size": [1, 1, 1]}
    migrated["materialId"] = migrated.get("materialId") or "mat_primary"
    migrated["transform"] = _v2_transform(migrated.get("transform"))
    migrated["children"] = [_migrate_part(child) for child in migrated.get("children") or []]
    return migrated


def _migrate_material(material: dict[str, Any]) -> dict[str, Any]:
    channels = dict(material.get("channels") or {})
    channels.setdefault("baseColor", material.get("baseColor", "#888888"))
    channels.setdefault("roughness", material.get("roughness", 0.5))
    channels.setdefault("metalness", material.get("metalness", 0.0))
    migrated = deepcopy(material)
    migrated["name"] = migrated.get("name") or migrated.get("id") or "material"
    migrated["role"] = migrated.get("role") or migrated.get("surfaceRole") or migrated.get("type") or "surface"
    migrated["channels"] = channels
    return migrated


def _migrate_handles(handles: dict[str, Any]) -> dict[str, Any]:
    migrated: dict[str, Any] = {}
    for group, entries in handles.items():
        if not isinstance(entries, list):
            continue
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            handle_id = entry.get("id") or f"{group}-{index}"
            part_id = entry.get("partId") or entry.get("part") or entry.get("parent") or "root_mass"
            local = entry.get("local") or entry.get("position") or [0, 0, 0]
            migrated[handle_id] = {
                "id": handle_id,
                "partId": part_id,
                "type": entry.get("type") or group.rstrip("s") or "handle",
                "transform": {
                    "translation": list(local),
                    "position": list(local),
                    "rotation": list(entry.get("rotation") or [0, 0, 0]),
                    "scale": list(entry.get("scale") or [1, 1, 1]),
                },
            }
    return migrated


def _migrate_critical_feature(feature: dict[str, Any]) -> dict[str, Any]:
    migrated = deepcopy(feature)
    migrated["description"] = migrated.get("description") or migrated.get("id") or "critical feature"
    migrated["partIds"] = list(migrated.get("partIds") or [])
    migrated["targetViews"] = list(migrated.get("targetViews") or [])
    return migrated


def migrate_v1_to_v2(blueprint: dict[str, Any]) -> dict[str, Any]:
    """Convert a v1 Blueprint dictionary into the v2 contract shape."""

    if is_blueprint_v2(blueprint):
        return deepcopy(blueprint)

    domain = str(blueprint.get("domain") or "object")
    layers = blueprint.get("layers") or {}
    migrated: dict[str, Any] = {
        "schemaVersion": BLUEPRINT_V2_SCHEMA_VERSION,
        "name": blueprint.get("name") or "Blueprint",
        "qualityMode": blueprint.get("qualityMode") or "sharp",
        "modelingProfile": _modeling_profile(domain),
        "intent": "inspection",
        "revision": {
            "id": "rev-0001",
            "parent": None,
            "contentHash": "",
        },
        "proportionProfile": {
            "headUnits": 4.0 if domain in ("character", "hybrid") else 1.0,
            "headHeightRatio": 0.25 if domain in ("character", "hybrid") else 1.0,
            "shoulderWidthRatio": 0.4 if domain in ("character", "hybrid") else 1.0,
            "limbThickness": "standard",
        },
        "poseProfile": {
            "id": "source",
            "mirrored": False,
            "joints": {},
        },
        "landmarks": list(blueprint.get("landmarks") or []),
        "parts": [_migrate_part(part) for part in blueprint.get("parts") or []],
        "materials": [_migrate_material(material) for material in blueprint.get("materials") or []],
        "handles": _migrate_handles(blueprint.get("handles") or {}),
        "renderProfiles": list(
            blueprint.get("renderProfiles")
            or [
                {
                    "id": "source",
                    "view": "source",
                    "camera": {},
                    "purpose": "source-aligned",
                }
            ]
        ),
        "criticalFeatures": [
            _migrate_critical_feature(feature) for feature in blueprint.get("criticalFeatures") or []
        ],
        "compatibility": {
            "sourceSchemaVersion": blueprint.get("version", 1),
            "sourceDomain": domain,
            "sourceLayers": list(layers.keys()),
        },
    }
    migrated["revision"]["contentHash"] = blueprint_revision_content_hash(migrated)
    return migrated


def _cast_material(material: dict[str, Any]) -> dict[str, Any]:
    converted = deepcopy(material)
    channels = converted.get("channels") or {}
    converted.setdefault("baseColor", channels.get("baseColor", "#888888"))
    converted.setdefault("roughness", channels.get("roughness", 0.5))
    converted.setdefault("metalness", channels.get("metalness", 0.0))
    return converted


def _cast_part(part: dict[str, Any]) -> dict[str, Any]:
    converted = deepcopy(part)
    transform = converted.get("transform") or {}
    if "position" not in transform and "translation" in transform:
        transform = dict(transform)
        transform["position"] = transform["translation"]
        converted["transform"] = transform
    converted["children"] = [_cast_part(child) for child in converted.get("children") or []]
    return converted


def blueprint_for_v1_cast(blueprint: dict[str, Any]) -> dict[str, Any]:
    """Return a v1-emitter-compatible view of a Blueprint."""

    if not is_blueprint_v2(blueprint):
        return deepcopy(blueprint)

    converted = deepcopy(blueprint)
    converted.setdefault("version", 1)
    converted.setdefault("bodySource", "procedural")
    converted["parts"] = [_cast_part(part) for part in converted.get("parts") or []]
    converted["materials"] = [_cast_material(material) for material in converted.get("materials") or []]
    return converted


def migrate_v1_to_v2_file(source: str | Path, out: str | Path) -> dict[str, Any]:
    migrated = migrate_v1_to_v2(load_json(source))
    dump_json(out, migrated)
    return migrated
