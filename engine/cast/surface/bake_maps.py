"""
Bake procedural surface maps (normal, roughness, AO) as PNG — stdlib only.

Domain-agnostic presets: metal, brass, cloth, leather, plastic, wood, stone, skin, ...
Used by CLI `surface-bake` and any factory that prefers offline maps over canvas.
"""

from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Any

from engine.shared.jsonutil import dump_json
from engine.shared.pngio import Image, write_png


SURFACE_PRESETS: dict[str, dict[str, Any]] = {
    "metal": {
        "base_rough": 0.32,
        "rough_var": 0.12,
        "scratch": 0.55,
        "panel": 0.7,
        "grain": 0.25,
        "ao_edge": 0.35,
        "normal_strength": 1.0,
    },
    "painted_metal": {
        "base_rough": 0.42,
        "rough_var": 0.1,
        "scratch": 0.4,
        "panel": 0.5,
        "grain": 0.15,
        "ao_edge": 0.3,
        "normal_strength": 0.7,
    },
    "brass": {
        "base_rough": 0.28,
        "rough_var": 0.08,
        "scratch": 0.35,
        "panel": 0.25,
        "grain": 0.2,
        "ao_edge": 0.2,
        "normal_strength": 0.6,
    },
    "cloth": {
        "base_rough": 0.78,
        "rough_var": 0.06,
        "scratch": 0.05,
        "panel": 0.1,
        "grain": 0.85,
        "ao_edge": 0.25,
        "normal_strength": 0.9,
        "weave": True,
    },
    "leather": {
        "base_rough": 0.82,
        "rough_var": 0.1,
        "scratch": 0.15,
        "panel": 0.15,
        "grain": 0.7,
        "ao_edge": 0.35,
        "normal_strength": 0.85,
    },
    "rubber": {
        "base_rough": 0.9,
        "rough_var": 0.04,
        "scratch": 0.1,
        "panel": 0.05,
        "grain": 0.4,
        "ao_edge": 0.2,
        "normal_strength": 0.4,
    },
    "plastic": {
        "base_rough": 0.45,
        "rough_var": 0.08,
        "scratch": 0.2,
        "panel": 0.2,
        "grain": 0.15,
        "ao_edge": 0.15,
        "normal_strength": 0.35,
    },
    "wood": {
        "base_rough": 0.7,
        "rough_var": 0.12,
        "scratch": 0.2,
        "panel": 0.1,
        "grain": 0.9,
        "ao_edge": 0.3,
        "normal_strength": 0.75,
        "aniso_grain": True,
    },
    "stone": {
        "base_rough": 0.85,
        "rough_var": 0.15,
        "scratch": 0.1,
        "panel": 0.2,
        "grain": 0.8,
        "ao_edge": 0.4,
        "normal_strength": 1.0,
    },
    "skin": {
        "base_rough": 0.55,
        "rough_var": 0.08,
        "scratch": 0.05,
        "panel": 0.0,
        "grain": 0.45,
        "ao_edge": 0.15,
        "normal_strength": 0.4,
    },
    "emissive": {
        "base_rough": 0.35,
        "rough_var": 0.05,
        "scratch": 0.0,
        "panel": 0.1,
        "grain": 0.1,
        "ao_edge": 0.1,
        "normal_strength": 0.2,
    },
    "default": {
        "base_rough": 0.5,
        "rough_var": 0.1,
        "scratch": 0.2,
        "panel": 0.3,
        "grain": 0.3,
        "ao_edge": 0.25,
        "normal_strength": 0.6,
    },
}


def _hash2(x: int, y: int, seed: int) -> float:
    n = (x * 374761393 + y * 668265263 + seed * 362437) & 0x7FFFFFFF
    n = (n ^ (n >> 13)) * 1274126177
    return ((n ^ (n >> 16)) & 0x7FFFFFFF) / 0x7FFFFFFF


def _value_noise(x: float, y: float, seed: int) -> float:
    x0, y0 = int(math.floor(x)), int(math.floor(y))
    fx, fy = x - x0, y - y0
    fx = fx * fx * (3 - 2 * fx)
    fy = fy * fy * (3 - 2 * fy)
    v00 = _hash2(x0, y0, seed)
    v10 = _hash2(x0 + 1, y0, seed)
    v01 = _hash2(x0, y0 + 1, seed)
    v11 = _hash2(x0 + 1, y0 + 1, seed)
    return (
        v00 * (1 - fx) * (1 - fy)
        + v10 * fx * (1 - fy)
        + v01 * (1 - fx) * fy
        + v11 * fx * fy
    )


def _fbm(x: float, y: float, seed: int, octaves: int = 4) -> float:
    a, f, s, m = 0.0, 1.0, 0.0, 0.0
    for i in range(octaves):
        s += a * _value_noise(x * f, y * f, seed + i * 19)
        m += a
        a *= 0.5
        f *= 2.0
    return s / m if m else 0.0


def _height_field(
    size: int,
    preset: dict[str, Any],
    seed: int,
) -> list[list[float]]:
    """Return height in roughly [-1, 1] for normal derivation."""
    h = [[0.0] * size for _ in range(size)]
    strength = float(preset.get("normal_strength", 0.6))
    weave = bool(preset.get("weave"))
    aniso = bool(preset.get("aniso_grain"))
    panel = float(preset.get("panel", 0.3))
    grain = float(preset.get("grain", 0.3))
    scratch = float(preset.get("scratch", 0.2))

    for y in range(size):
        for x in range(size):
            u, v = x / size, y / size
            n = _fbm(u * 8, v * 8, seed) * 2 - 1
            g = _fbm(u * 32, v * 32, seed + 3) * 2 - 1
            height = n * 0.35 * grain + g * 0.2 * grain

            if weave:
                height += 0.15 * math.sin(u * math.pi * 64) * math.sin(v * math.pi * 64)

            if aniso:
                height += 0.2 * math.sin(v * math.pi * 40 + n)

            # panel grid (meso)
            if panel > 0:
                px = abs((u * 4) % 1 - 0.5)
                py = abs((v * 4) % 1 - 0.5)
                edge = max(0.0, 0.04 - min(px, py)) * 25
                height -= edge * panel * 0.5

            # sparse scratches
            if scratch > 0 and _hash2(x // 3, y, seed + 7) > 1.0 - scratch * 0.02:
                height += ( _hash2(x, y, seed + 9) - 0.5) * scratch * 0.4

            # edge AO-ish darken as negative height near border
            border = min(u, v, 1 - u, 1 - v)
            if border < 0.08:
                height -= (0.08 - border) * 2.0 * float(preset.get("ao_edge", 0.25))

            h[y][x] = height * strength
    return h


def _normal_from_height(h: list[list[float]], size: int) -> Image:
    img = Image(size, size, bytearray(size * size * 4))
    for y in range(size):
        for x in range(size):
            x0 = h[y][x - 1 if x else x]
            x1 = h[y][x + 1 if x + 1 < size else x]
            y0 = h[y - 1 if y else y][x]
            y1 = h[y + 1 if y + 1 < size else y][x]
            dx = (x1 - x0) * 0.5
            dy = (y1 - y0) * 0.5
            # normal = normalize(-dx, -dy, 1)
            nx, ny, nz = -dx * 2.5, -dy * 2.5, 1.0
            inv = 1.0 / math.sqrt(nx * nx + ny * ny + nz * nz)
            nx, ny, nz = nx * inv, ny * inv, nz * inv
            r = int((nx * 0.5 + 0.5) * 255)
            g = int((ny * 0.5 + 0.5) * 255)
            b = int((nz * 0.5 + 0.5) * 255)
            img.set_pixel(x, y, (r, g, b, 255))
    return img


def _roughness_map(size: int, preset: dict[str, Any], seed: int, h: list[list[float]]) -> Image:
    base = float(preset.get("base_rough", 0.5))
    var = float(preset.get("rough_var", 0.1))
    img = Image(size, size, bytearray(size * size * 4))
    for y in range(size):
        for x in range(size):
            n = _fbm(x / size * 10, y / size * 10, seed + 11)
            # higher height variation → slightly rougher (edge wear proxy)
            wear = min(1.0, abs(h[y][x]) * 0.8)
            rough = base + (n - 0.5) * 2 * var + wear * 0.15
            rough = max(0.0, min(1.0, rough))
            v = int(rough * 255)
            img.set_pixel(x, y, (v, v, v, 255))
    return img


def _ao_map(size: int, h: list[list[float]]) -> Image:
    img = Image(size, size, bytearray(size * size * 4))
    for y in range(size):
        for x in range(size):
            # lower height → more occlusion
            v = h[y][x]
            ao = max(0.0, min(1.0, 0.65 + v * 0.5))
            c = int(ao * 255)
            img.set_pixel(x, y, (c, c, c, 255))
    return img


def bake_role(
    role: str,
    out_dir: str | Path,
    *,
    size: int = 512,
    seed: int = 42,
    maps: dict[str, bool] | None = None,
) -> dict[str, Any]:
    maps = maps or {"normal": True, "roughness": True, "ao": True}
    preset = SURFACE_PRESETS.get(role, SURFACE_PRESETS["default"])
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    h = _height_field(size, preset, seed + hash(role) % 10000)
    paths: dict[str, str] = {}
    if maps.get("normal", True):
        p = out / f"{role}_normal.png"
        write_png(p, _normal_from_height(h, size))
        paths["normal"] = str(p)
    if maps.get("roughness", True):
        p = out / f"{role}_roughness.png"
        write_png(p, _roughness_map(size, preset, seed, h))
        paths["roughness"] = str(p)
    if maps.get("ao", False):
        p = out / f"{role}_ao.png"
        write_png(p, _ao_map(size, h))
        paths["ao"] = str(p)
    return {"role": role, "preset": preset, "paths": paths, "resolution": size}


def bake_surface_stack(
    out_dir: str | Path,
    *,
    roles: list[str] | None = None,
    detail_level: str = "high",
    resolution: int | None = None,
    seed: int = 42,
) -> dict[str, Any]:
    from engine.cast.surface.schema import default_surface_stack

    stack = default_surface_stack(detail_level=detail_level, resolution=resolution or 0, seed=seed)
    res = int(stack["resolution"])
    roles = roles or ["metal", "brass", "cloth", "leather", "plastic", "default"]
    baked = {}
    for role in roles:
        baked[role] = bake_role(
            role,
            Path(out_dir) / "maps",
            size=res,
            seed=seed,
            maps=stack["maps"],
        )
    manifest = {
        "surfaceStack": stack,
        "baked": baked,
        "outDir": str(out_dir),
    }
    dump_json(Path(out_dir) / "surface_manifest.json", manifest)
    return manifest
