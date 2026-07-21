"""Shared surface preset loader."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from typing import Any


@lru_cache(maxsize=1)
def load_surface_presets() -> dict[str, dict[str, Any]]:
    data = files("engine.cast.surface").joinpath("presets.json").read_text(encoding="utf-8")
    return json.loads(data)


SURFACE_PRESETS = load_surface_presets()
SURFACE_ROLES = tuple(SURFACE_PRESETS.keys())


def stable_role_seed(role: str) -> int:
    """Return a deterministic small seed offset for a surface role."""
    h = 2166136261
    for byte in role.encode("utf-8"):
        h ^= byte
        h = (h * 16777619) & 0xFFFFFFFF
    return h % 10000
