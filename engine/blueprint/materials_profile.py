"""Neutral environment and material role profiles with readability checks."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

MATERIAL_ROLES = (
    "steel",
    "brass",
    "cloth",
    "leather",
    "paint",
    "emissive",
    "skin",
    "generic",
)

DEFAULT_ROLE_PROFILES: dict[str, dict[str, Any]] = {
    "steel": {
        "baseColor": "#8a939c",
        "roughness": 0.35,
        "metalness": 0.85,
        "clearcoat": 0.1,
        "aoIntensity": 0.35,
    },
    "brass": {
        "baseColor": "#b08d57",
        "roughness": 0.4,
        "metalness": 0.8,
        "clearcoat": 0.05,
        "aoIntensity": 0.3,
    },
    "cloth": {
        "baseColor": "#3a4a6b",
        "roughness": 0.85,
        "metalness": 0.0,
        "clearcoat": 0.0,
        "aoIntensity": 0.25,
    },
    "leather": {
        "baseColor": "#5a3a28",
        "roughness": 0.75,
        "metalness": 0.05,
        "clearcoat": 0.0,
        "aoIntensity": 0.3,
    },
    "paint": {
        "baseColor": "#4a6fa5",
        "roughness": 0.55,
        "metalness": 0.1,
        "clearcoat": 0.15,
        "aoIntensity": 0.2,
    },
    "emissive": {
        "baseColor": "#203040",
        "roughness": 0.5,
        "metalness": 0.0,
        "emissive": "#4060ff",
        "emissiveIntensity": 0.4,
        "aoIntensity": 0.1,
    },
    "skin": {
        "baseColor": "#c garnet",
        "roughness": 0.65,
        "metalness": 0.0,
        "aoIntensity": 0.15,
    },
    "generic": {
        "baseColor": "#888888",
        "roughness": 0.5,
        "metalness": 0.0,
        "aoIntensity": 0.25,
    },
}

# fix accidental space in skin color
DEFAULT_ROLE_PROFILES["skin"]["baseColor"] = "#c49a7c"

NEUTRAL_ENVIRONMENT = {
    "id": "neutral-studio",
    "exposure": 1.0,
    "ambientIntensity": 0.45,
    "keyIntensity": 1.1,
    "fillIntensity": 0.4,
    "rimIntensity": 0.25,
    "background": "#2a2a2e",
    "envMapIntensity": 0.55,
}


def material_role_profile(role: str) -> dict[str, Any]:
    if role not in DEFAULT_ROLE_PROFILES:
        raise ValueError(f"unsupported material role {role!r}")
    return deepcopy(DEFAULT_ROLE_PROFILES[role])


def neutral_environment_profile() -> dict[str, Any]:
    return deepcopy(NEUTRAL_ENVIRONMENT)


def apply_role_to_material(material: dict[str, Any], role: str | None = None) -> dict[str, Any]:
    resolved_role = role or material.get("role") or "generic"
    profile = material_role_profile(resolved_role if resolved_role in DEFAULT_ROLE_PROFILES else "generic")
    merged = deepcopy(material)
    merged["role"] = resolved_role if resolved_role in DEFAULT_ROLE_PROFILES else "generic"
    for key, value in profile.items():
        merged.setdefault(key, value)
    return merged


def assess_material_readability(
    materials: list[dict[str, Any]],
    *,
    high_detail_scores: dict[str, float] | None = None,
    no_detail_scores: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Detect black crush / clipping / AO that reduces readability.

    When high-detail readability is worse than no-detail, fail closed.
    """

    issues: list[dict[str, Any]] = []
    for material in materials:
        mid = material.get("id")
        color = str(material.get("baseColor") or "#888888").lstrip("#")
        if len(color) >= 6:
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
            luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
        else:
            luminance = 0.5
        ao = float(material.get("aoIntensity") or 0.0)
        metal = float(material.get("metalness") or 0.0)
        if luminance < 0.08 and metal > 0.5:
            issues.append(
                {
                    "code": "BLACK_CRUSH",
                    "materialId": mid,
                    "message": "metal baseColor too dark under neutral exposure",
                    "severity": "error",
                }
            )
        if ao > 0.7 and metal > 0.5:
            issues.append(
                {
                    "code": "AO_OVERDRIVE",
                    "materialId": mid,
                    "message": "AO intensity likely crushes metal form read",
                    "severity": "error",
                }
            )
        if float(material.get("emissiveIntensity") or 0) > 2.0:
            issues.append(
                {
                    "code": "CLIPPING_RISK",
                    "materialId": mid,
                    "message": "emissive intensity may clip highlights",
                    "severity": "warning",
                }
            )

    high = high_detail_scores or {}
    none = no_detail_scores or {}
    if high and none:
        for key, high_score in high.items():
            base = none.get(key)
            if base is not None and high_score + 1e-6 < base:
                issues.append(
                    {
                        "code": "DETAIL_REDUCES_READABILITY",
                        "metric": key,
                        "highDetail": high_score,
                        "noDetail": base,
                        "severity": "error",
                        "message": f"high detail {key}={high_score} worse than no-detail {base}",
                    }
                )

    return {
        "schemaVersion": 1,
        "passed": not any(i.get("severity") == "error" for i in issues),
        "issues": issues,
        "environment": neutral_environment_profile(),
    }
