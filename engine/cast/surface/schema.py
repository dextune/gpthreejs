"""Surface stack schema helpers (domain-agnostic)."""

from __future__ import annotations

from typing import Any

from engine.cast.surface.presets import SURFACE_ROLES
from engine.contracts.modes import (
    DETAIL_LEVELS,
    DETAIL_RIVET_LIMITS,
    detail_resolution,
    normalize_detail_level,
    quality_mode_to_detail_level,
)


def default_surface_stack(
    *,
    detail_level: str = "high",
    resolution: int = 512,
    seed: int = 42,
) -> dict[str, Any]:
    detail_level = normalize_detail_level(detail_level)
    res = detail_resolution(detail_level, resolution)
    return {
        "version": 1,
        "detailLevel": detail_level,
        "resolution": res,
        "seed": seed,
        "bands": {
            "macro": True,
            "meso": detail_level in ("medium", "high", "ultra"),
            "micro": detail_level in ("high", "ultra"),
        },
        "maps": {
            "normal": True,
            "roughness": True,
            "ao": detail_level in ("high", "ultra"),
            "metalness": detail_level == "ultra",
        },
        "meso": {
            "instancedRivets": detail_level in ("high", "ultra"),
            "edgeTrim": detail_level in ("medium", "high", "ultra"),
            "panelLines": detail_level in ("high", "ultra"),
        },
        "roles": {role: {"preset": role} for role in SURFACE_ROLES},
        "budget": {
            "maxMapResolution": res,
            "maxRivetInstances": DETAIL_RIVET_LIMITS[detail_level],
            "preferMapsOverGeometry": True,
        },
    }


def merge_surface_into_blueprint(blueprint: dict[str, Any], stack: dict[str, Any] | None = None) -> dict[str, Any]:
    """Attach a surfaceStack and ensure materials reference a surfaceRole."""
    stack = stack or default_surface_stack(
        detail_level=quality_mode_to_detail_level(blueprint.get("qualityMode")),
        seed=int(blueprint.get("seed") or 42),
    )
    # qualityMode may not map cleanly — normalize
    dl = stack.get("detailLevel", "high")
    if dl not in DETAIL_LEVELS:
        stack = default_surface_stack(seed=int(blueprint.get("seed") or 42))

    blueprint["surfaceStack"] = stack

    role_guess = {
        "steel": "metal",
        "metal": "metal",
        "iron": "metal",
        "brass": "brass",
        "gold": "brass",
        "copper": "brass",
        "cloth": "cloth",
        "fabric": "cloth",
        "crimson": "cloth",
        "leather": "leather",
        "wood": "wood",
        "stone": "stone",
        "plastic": "plastic",
        "rubber": "rubber",
        "skin": "skin",
        "paint": "painted_metal",
    }

    for mat in blueprint.get("materials") or []:
        if mat.get("surfaceRole"):
            continue
        mid = str(mat.get("id") or "").lower()
        base = str(mat.get("baseColor") or "")
        metal = float(mat.get("metalness") or 0)
        rough = float(mat.get("roughness") or 0.5)
        role = "default"
        for key, r in role_guess.items():
            if key in mid:
                role = r
                break
        else:
            if metal >= 0.7:
                role = "brass" if "a" in base.lower() or "c" in mid else "metal"
            elif rough >= 0.7:
                role = "cloth"
            elif rough >= 0.55:
                role = "leather"
            else:
                role = "plastic"
        mat["surfaceRole"] = role
        mat.setdefault("surface", {"useNormal": True, "useRoughness": True, "useAo": stack["maps"].get("ao", False)})

    return blueprint
