"""Blueprint v2 schema contract.

This module defines the stable field surface for Blueprint v2 without changing
the legacy v1 authoring or validation path.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from engine.contracts.modes import QUALITY_MODES

BLUEPRINT_V2_SCHEMA_VERSION = 2

MODELING_PROFILES = (
    "generic-prop",
    "hard-surface-hero",
    "stylized-character",
)

INTENTS = (
    "inspection",
    "game",
    "turnaround",
    "production",
)

LIMB_THICKNESS_PROFILES = (
    "slender",
    "standard",
    "chunky",
)

TOP_LEVEL_REQUIRED_FIELDS = (
    "schemaVersion",
    "name",
    "qualityMode",
    "modelingProfile",
    "intent",
    "revision",
    "proportionProfile",
    "poseProfile",
    "landmarks",
    "parts",
    "materials",
    "handles",
    "renderProfiles",
    "criticalFeatures",
)

REVISION_REQUIRED_FIELDS = ("id", "parent", "contentHash")
PROPORTION_REQUIRED_FIELDS = (
    "headUnits",
    "headHeightRatio",
    "shoulderWidthRatio",
    "limbThickness",
)
POSE_REQUIRED_FIELDS = ("id", "mirrored", "joints")
LANDMARK_REQUIRED_FIELDS = ("id", "semantic", "space", "position")
PART_REQUIRED_FIELDS = (
    "id",
    "name",
    "role",
    "geometry",
    "materialId",
    "transform",
    "children",
)
MATERIAL_REQUIRED_FIELDS = ("id", "name", "role", "channels")
HANDLE_REQUIRED_FIELDS = ("id", "partId", "type", "transform")
ATTACHMENT_REQUIRED_FIELDS = (
    "parentSocket",
    "childSocket",
    "contact",
    "maxGap",
    "maxPenetration",
    "required",
)
RENDER_PROFILE_REQUIRED_FIELDS = ("id", "view", "camera", "purpose")
CRITICAL_FEATURE_REQUIRED_FIELDS = ("id", "description", "partIds", "targetViews")


def blueprint_v2_schema() -> dict[str, Any]:
    """Return a JSON-schema-shaped contract for Blueprint v2.

    The project intentionally avoids a schema dependency at this stage; BP-110
    and later tasks can attach strict runtime validation to this shape.
    """

    return deepcopy(_BLUEPRINT_V2_SCHEMA)


def blueprint_v2_required_fields() -> dict[str, tuple[str, ...]]:
    """Return required field groups used by fixtures, docs, and tests."""

    return {
        "topLevel": TOP_LEVEL_REQUIRED_FIELDS,
        "revision": REVISION_REQUIRED_FIELDS,
        "proportionProfile": PROPORTION_REQUIRED_FIELDS,
        "poseProfile": POSE_REQUIRED_FIELDS,
        "landmark": LANDMARK_REQUIRED_FIELDS,
        "part": PART_REQUIRED_FIELDS,
        "material": MATERIAL_REQUIRED_FIELDS,
        "handle": HANDLE_REQUIRED_FIELDS,
        "attachment": ATTACHMENT_REQUIRED_FIELDS,
        "renderProfile": RENDER_PROFILE_REQUIRED_FIELDS,
        "criticalFeature": CRITICAL_FEATURE_REQUIRED_FIELDS,
    }


_BLUEPRINT_V2_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://gpthreejs.local/contracts/blueprint-v2.schema.json",
    "title": "gpthreejs Blueprint v2",
    "type": "object",
    "required": list(TOP_LEVEL_REQUIRED_FIELDS),
    "additionalProperties": True,
    "properties": {
        "schemaVersion": {"const": BLUEPRINT_V2_SCHEMA_VERSION},
        "name": {"type": "string", "minLength": 1},
        "qualityMode": {"type": "string", "enum": list(QUALITY_MODES)},
        "modelingProfile": {"type": "string", "enum": list(MODELING_PROFILES)},
        "intent": {"type": "string", "enum": list(INTENTS)},
        "revision": {
            "type": "object",
            "required": list(REVISION_REQUIRED_FIELDS),
            "additionalProperties": True,
            "properties": {
                "id": {"type": "string", "minLength": 1},
                "parent": {"type": ["string", "null"]},
                "contentHash": {
                    "type": "string",
                    "pattern": "^[a-f0-9]{64}$",
                },
            },
        },
        "proportionProfile": {
            "type": "object",
            "required": list(PROPORTION_REQUIRED_FIELDS),
            "additionalProperties": True,
            "properties": {
                "headUnits": {"type": "number", "exclusiveMinimum": 0},
                "headHeightRatio": {"type": "number", "exclusiveMinimum": 0},
                "shoulderWidthRatio": {"type": "number", "exclusiveMinimum": 0},
                "limbThickness": {
                    "type": "string",
                    "enum": list(LIMB_THICKNESS_PROFILES),
                },
            },
        },
        "poseProfile": {
            "type": "object",
            "required": list(POSE_REQUIRED_FIELDS),
            "additionalProperties": True,
            "properties": {
                "id": {"type": "string", "minLength": 1},
                "mirrored": {"type": "boolean"},
                "joints": {"type": "object"},
            },
        },
        "landmarks": {
            "type": "array",
            "items": {
                "type": "object",
                "required": list(LANDMARK_REQUIRED_FIELDS),
                "additionalProperties": True,
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "semantic": {"type": "string", "minLength": 1},
                    "space": {"type": "string", "enum": ["normalized-2d", "world-3d"]},
                    "position": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 3,
                    },
                },
            },
        },
        "parts": {
            "type": "array",
            "items": {"$ref": "#/$defs/part"},
        },
        "materials": {
            "type": "array",
            "items": {
                "type": "object",
                "required": list(MATERIAL_REQUIRED_FIELDS),
                "additionalProperties": True,
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "name": {"type": "string", "minLength": 1},
                    "role": {"type": "string", "minLength": 1},
                    "channels": {"type": "object"},
                },
            },
        },
        "handles": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": list(HANDLE_REQUIRED_FIELDS),
                "additionalProperties": True,
            },
        },
        "renderProfiles": {
            "type": "array",
            "items": {
                "type": "object",
                "required": list(RENDER_PROFILE_REQUIRED_FIELDS),
                "additionalProperties": True,
            },
        },
        "criticalFeatures": {
            "type": "array",
            "items": {
                "type": "object",
                "required": list(CRITICAL_FEATURE_REQUIRED_FIELDS),
                "additionalProperties": True,
            },
        },
    },
    "$defs": {
        "part": {
            "type": "object",
            "required": list(PART_REQUIRED_FIELDS),
            "additionalProperties": True,
            "properties": {
                "id": {"type": "string", "minLength": 1},
                "name": {"type": "string", "minLength": 1},
                "role": {"type": "string", "minLength": 1},
                "geometry": {"type": "object"},
                "materialId": {"type": "string", "minLength": 1},
                "transform": {"type": "object"},
                "attachment": {
                    "type": "object",
                    "required": list(ATTACHMENT_REQUIRED_FIELDS),
                    "additionalProperties": True,
                },
                "children": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/part"},
                },
            },
        },
    },
}
