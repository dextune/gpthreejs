"""Canonical multi-view render profiles and pass manifests."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from engine.shared.artifacts import content_hash

VIEW_PROFILE_IDS = ("source-34", "front", "left", "right", "back", "top-34")

DEFAULT_CAMERAS: dict[str, dict[str, Any]] = {
    "source-34": {"position": [0.9, 1.15, 2.2], "lookAt": [0.0, 1.0, 0.0], "fov": 32.0},
    "front": {"position": [0.0, 1.05, 2.4], "lookAt": [0.0, 1.0, 0.0], "fov": 32.0},
    "left": {"position": [-2.4, 1.05, 0.0], "lookAt": [0.0, 1.0, 0.0], "fov": 32.0},
    "right": {"position": [2.4, 1.05, 0.0], "lookAt": [0.0, 1.0, 0.0], "fov": 32.0},
    "back": {"position": [0.0, 1.05, -2.4], "lookAt": [0.0, 1.0, 0.0], "fov": 32.0},
    "top-34": {"position": [1.0, 2.6, 1.4], "lookAt": [0.0, 1.0, 0.0], "fov": 32.0},
}

DEFAULT_LIGHT = {
    "key": {"intensity": 1.1, "position": [2.0, 3.0, 2.0]},
    "fill": {"intensity": 0.4},
    "rim": {"intensity": 0.25, "position": [-1.5, 2.0, -2.0]},
    "ambient": {"intensity": 0.45},
}

REQUIRED_PASSES = (
    "beauty",
    "alpha",
    "partId",
    "albedo",
    "normal",
    "linearDepth",
    "materialDebug",
    "wireframe",
)


def camera_profile(view_id: str) -> dict[str, Any]:
    if view_id not in DEFAULT_CAMERAS:
        raise ValueError(f"unknown view profile {view_id!r}")
    profile = deepcopy(DEFAULT_CAMERAS[view_id])
    profile["id"] = view_id
    profile["hash"] = content_hash(profile, ignored_paths=(("hash",),))
    return profile


def light_profile() -> dict[str, Any]:
    profile = deepcopy(DEFAULT_LIGHT)
    profile["hash"] = content_hash(profile, ignored_paths=(("hash",),))
    return profile


def build_view_manifest(views: tuple[str, ...] = VIEW_PROFILE_IDS) -> dict[str, Any]:
    cameras = {view: camera_profile(view) for view in views}
    lights = light_profile()
    return {
        "schemaVersion": 1,
        "views": list(views),
        "cameras": cameras,
        "light": lights,
        "cameraHashes": {view: cameras[view]["hash"] for view in views},
        "lightHash": lights["hash"],
        "manifestHash": "",
    }


def finalize_view_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    payload = deepcopy(manifest)
    payload["manifestHash"] = content_hash(payload, ignored_paths=(("manifestHash",),))
    return payload


def build_pass_list() -> list[str]:
    return list(REQUIRED_PASSES)


def build_render_set_stub(
    *,
    revision_id: str,
    blueprint_hash: str,
    factory_hash: str,
    renderer_version: str = "gpthreejs-render/0.2",
    views: tuple[str, ...] = VIEW_PROFILE_IDS,
    out_dir: str = "renders",
) -> dict[str, Any]:
    """Build a RenderSet manifest with deterministic metadata (paths may be virtual)."""

    view_manifest = finalize_view_manifest(build_view_manifest(views))
    light_hash = view_manifest["lightHash"]
    render_views = []
    for view in views:
        cam_hash = view_manifest["cameraHashes"][view]
        passes = {
            pass_name: {
                "path": f"{out_dir}/{view}/{pass_name}.png",
                "hash": content_hash({"view": view, "pass": pass_name, "revision": revision_id}),
            }
            for pass_name in REQUIRED_PASSES
        }
        render_views.append(
            {
                "id": view,
                "cameraProfileHash": cam_hash,
                "lightProfileHash": light_hash,
                "passes": passes,
            }
        )
    render_set = {
        "schemaVersion": 1,
        "revisionId": revision_id,
        "blueprintHash": blueprint_hash,
        "factoryHash": factory_hash,
        "rendererVersion": renderer_version,
        "renderProfileHash": view_manifest["manifestHash"],
        "views": render_views,
        "requiredPasses": list(REQUIRED_PASSES),
    }
    return render_set


def validate_partial_render_set(render_set: dict[str, Any], *, require_all_passes: bool = True) -> list[str]:
    from engine.critique.contracts import validate_render_set

    errors = validate_render_set(render_set)
    if require_all_passes:
        for view_index, view in enumerate(render_set.get("views") or []):
            passes = view.get("passes") or {}
            for pass_name in REQUIRED_PASSES:
                if pass_name not in passes:
                    errors.append(f"$.views[{view_index}].passes.{pass_name}: missing required pass")
    if not render_set.get("rendererVersion"):
        errors.append("$.rendererVersion: missing renderer version")
    return errors
