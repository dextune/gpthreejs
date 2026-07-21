"""Deterministic geometry builders for advanced primitive kinds.

Builders return a normalized geometry descriptor used by validation, snapshots,
and TypeScript emission. They do not require a GPU.
"""

from __future__ import annotations

import math
from typing import Any

from engine.geometry.schema import UnsupportedGeometryError, validate_geometry_required_fields
from engine.shared.artifacts import content_hash


def _finite_numbers(values: list[Any], *, path: str) -> list[str]:
    errors: list[str] = []
    for index, value in enumerate(values):
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
            errors.append(f"{path}[{index}]: expected finite number")
    return errors


def build_geometry(spec: dict[str, Any]) -> dict[str, Any]:
    """Validate and expand a geometry spec into a deterministic descriptor."""

    errors = validate_geometry_required_fields(spec)
    if errors:
        raise ValueError("; ".join(errors))

    kind = spec["kind"]
    builders = {
        "box": _build_box,
        "sphere": _build_sphere,
        "ellipsoid": _build_ellipsoid,
        "capsule": _build_capsule,
        "cylinder": _build_cylinder,
        "cone": _build_cone,
        "torus": _build_torus,
        "rounded-box": _build_rounded_box,
        "shape-extrude": _build_shape_extrude,
        "lathe": _build_lathe,
        "tube": _build_tube,
        "beveled-plate": _build_beveled_plate,
        "curve-blade": _build_curve_blade,
        "feather": _build_feather,
        "cloth-patch": _build_cloth_patch,
        "instance-set": _build_instance_set,
        "shield": _build_shield,
    }
    builder = builders.get(kind)
    if builder is None:
        raise UnsupportedGeometryError(f"unsupported geometry kind {kind!r}")
    descriptor = builder(spec)
    descriptor["kind"] = kind
    descriptor["key"] = content_hash(descriptor, ignored_paths=(("key",),))
    return descriptor


def bounds_of(descriptor: dict[str, Any]) -> dict[str, list[float]]:
    return descriptor["bounds"]


def _bounds_from_size(size: list[float]) -> dict[str, list[float]]:
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    return {"min": [-hx, -hy, -hz], "max": [hx, hy, hz]}


def _build_box(spec: dict[str, Any]) -> dict[str, Any]:
    size = [float(v) for v in spec["size"]]
    if any(v <= 0 for v in size):
        raise ValueError("box.size: expected positive components")
    return {"size": size, "bounds": _bounds_from_size(size), "params": {"segments": spec.get("segments", [1, 1, 1])}}


def _build_sphere(spec: dict[str, Any]) -> dict[str, Any]:
    r = float(spec["radius"])
    if r <= 0:
        raise ValueError("sphere.radius: expected positive")
    return {"radius": r, "bounds": {"min": [-r, -r, -r], "max": [r, r, r]}, "params": {}}


def _build_ellipsoid(spec: dict[str, Any]) -> dict[str, Any]:
    radii = [float(v) for v in spec["radii"]]
    return {
        "radii": radii,
        "bounds": {"min": [-radii[0], -radii[1], -radii[2]], "max": radii},
        "params": {},
    }


def _build_capsule(spec: dict[str, Any]) -> dict[str, Any]:
    r = float(spec["radius"])
    length = float(spec["length"])
    half = length / 2 + r
    return {
        "radius": r,
        "length": length,
        "bounds": {"min": [-r, -half, -r], "max": [r, half, r]},
        "params": {},
    }


def _build_cylinder(spec: dict[str, Any]) -> dict[str, Any]:
    rt = float(spec["radiusTop"])
    rb = float(spec["radiusBottom"])
    h = float(spec["height"])
    r = max(rt, rb)
    return {
        "radiusTop": rt,
        "radiusBottom": rb,
        "height": h,
        "bounds": {"min": [-r, -h / 2, -r], "max": [r, h / 2, r]},
        "params": {},
    }


def _build_cone(spec: dict[str, Any]) -> dict[str, Any]:
    r = float(spec["radius"])
    h = float(spec["height"])
    return {
        "radius": r,
        "height": h,
        "bounds": {"min": [-r, -h / 2, -r], "max": [r, h / 2, r]},
        "params": {},
    }


def _build_torus(spec: dict[str, Any]) -> dict[str, Any]:
    r = float(spec["radius"])
    t = float(spec["tube"])
    ext = r + t
    return {
        "radius": r,
        "tube": t,
        "bounds": {"min": [-ext, -t, -ext], "max": [ext, t, ext]},
        "params": {},
    }


def _build_rounded_box(spec: dict[str, Any]) -> dict[str, Any]:
    size = [float(v) for v in spec["size"]]
    radius = float(spec["radius"])
    if radius < 0:
        raise ValueError("rounded-box.radius: expected non-negative")
    if any(radius * 2 > s + 1e-9 for s in size):
        raise ValueError("rounded-box.radius: exceeds half the smallest size axis")
    return {
        "size": size,
        "radius": radius,
        "bounds": _bounds_from_size(size),
        "params": {"segments": int(spec.get("segments", 4))},
    }


def _build_shape_extrude(spec: dict[str, Any]) -> dict[str, Any]:
    shape = spec["shape"]
    depth = float(spec["depth"])
    if not isinstance(shape, list) or len(shape) < 3:
        raise ValueError("shape-extrude.shape: expected polygon with >= 3 points")
    xs = [float(p[0]) for p in shape]
    ys = [float(p[1]) for p in shape]
    return {
        "shape": [[float(p[0]), float(p[1])] for p in shape],
        "depth": depth,
        "bounds": {
            "min": [min(xs), min(ys), -depth / 2],
            "max": [max(xs), max(ys), depth / 2],
        },
        "params": {"bevel": float(spec.get("bevel", 0.0))},
    }


def _build_lathe(spec: dict[str, Any]) -> dict[str, Any]:
    profile = spec["profile"]
    if not isinstance(profile, list) or len(profile) < 2:
        raise ValueError("lathe.profile: expected >= 2 points")
    xs = [abs(float(p[0])) for p in profile]
    ys = [float(p[1]) for p in profile]
    r = max(xs)
    return {
        "profile": [[float(p[0]), float(p[1])] for p in profile],
        "bounds": {"min": [-r, min(ys), -r], "max": [r, max(ys), r]},
        "params": {"segments": int(spec.get("segments", 24))},
    }


def _build_tube(spec: dict[str, Any]) -> dict[str, Any]:
    path = spec["path"]
    radius = float(spec["radius"])
    if not isinstance(path, list) or len(path) < 2:
        raise ValueError("tube.path: expected >= 2 points")
    pts = [[float(p[0]), float(p[1]), float(p[2])] for p in path]
    xs, ys, zs = zip(*pts)
    return {
        "path": pts,
        "radius": radius,
        "bounds": {
            "min": [min(xs) - radius, min(ys) - radius, min(zs) - radius],
            "max": [max(xs) + radius, max(ys) + radius, max(zs) + radius],
        },
        "params": {"tubularSegments": int(spec.get("tubularSegments", 32))},
    }


def _build_beveled_plate(spec: dict[str, Any]) -> dict[str, Any]:
    outline = spec["outline"]
    thickness = float(spec["thickness"])
    bevel = float(spec["bevel"])
    if not isinstance(outline, list) or len(outline) < 3:
        raise ValueError("beveled-plate.outline: expected polygon with >= 3 points")
    xs = [float(p[0]) for p in outline]
    ys = [float(p[1]) for p in outline]
    return {
        "outline": [[float(p[0]), float(p[1])] for p in outline],
        "thickness": thickness,
        "bevel": bevel,
        "bounds": {
            "min": [min(xs) - bevel, min(ys) - bevel, -thickness / 2],
            "max": [max(xs) + bevel, max(ys) + bevel, thickness / 2],
        },
        "params": {},
    }


def _build_curve_blade(spec: dict[str, Any]) -> dict[str, Any]:
    length = float(spec["length"])
    width = float(spec["width"])
    curve = float(spec["curve"])
    return {
        "length": length,
        "width": width,
        "curve": curve,
        "bounds": {
            "min": [-width / 2, 0.0, -abs(curve) - 0.02],
            "max": [width / 2, length, abs(curve) + 0.02],
        },
        "params": {"tipTaper": float(spec.get("tipTaper", 0.35))},
    }


def _build_shield(spec: dict[str, Any]) -> dict[str, Any]:
    """Convenience builder used by character fixtures (shape-extrude under the hood)."""
    width = float(spec.get("width", 0.55))
    height = float(spec.get("height", 0.7))
    depth = float(spec.get("depth", 0.08))
    shape = [
        [-width / 2, height / 2],
        [width / 2, height / 2],
        [width / 2, -height / 4],
        [0.0, -height / 2],
        [-width / 2, -height / 4],
    ]
    return _build_shape_extrude({"kind": "shape-extrude", "shape": shape, "depth": depth, "bevel": 0.02})


def _build_feather(spec: dict[str, Any]) -> dict[str, Any]:
    length = float(spec["length"])
    width = float(spec["width"])
    barb_count = int(spec["barbCount"])
    if barb_count < 1:
        raise ValueError("feather.barbCount: expected >= 1")
    return {
        "length": length,
        "width": width,
        "barbCount": barb_count,
        "bounds": {
            "min": [-width / 2, 0.0, -0.02],
            "max": [width / 2, length, 0.02],
        },
        "params": {"curl": float(spec.get("curl", 0.1))},
    }


def _build_cloth_patch(spec: dict[str, Any]) -> dict[str, Any]:
    width = float(spec["width"])
    height = float(spec["height"])
    drape = float(spec["drape"])
    return {
        "width": width,
        "height": height,
        "drape": drape,
        "bounds": {
            "min": [-width / 2, -height, -abs(drape)],
            "max": [width / 2, 0.0, abs(drape)],
        },
        "params": {"segments": int(spec.get("segments", 6))},
    }


def _build_instance_set(spec: dict[str, Any]) -> dict[str, Any]:
    prototype = spec["prototype"]
    count = int(spec["count"])
    distribution = spec["distribution"]
    if count < 1:
        raise ValueError("instance-set.count: expected >= 1")
    proto = build_geometry(prototype)
    return {
        "prototype": proto,
        "count": count,
        "distribution": distribution,
        "bounds": proto["bounds"],
        "params": {},
    }
