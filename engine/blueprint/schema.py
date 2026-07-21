"""Blueprint constants and layer order."""

from __future__ import annotations

LAYERS = (
    "mass",
    "skeleton",
    "contour",
    "skin",
    "light",
    "handle",
    "polish",
)

CHARACTER_INSERT = ("proportion", "landmarks")  # before skin

LEDGER_KINDS = (
    "gloss",
    "bevel",
    "fastener",
    "linework",
    "contour",
    "seam",
    "stitch",
    "stain",
    "scratch",
    "chip",
    "decal",
    "emissive",
    "hole",
    "groove",
    "ridge",
)

COMPLEXITY_LEDGER_MIN = {
    "simple": 3,
    "moderate": 6,
    "complex": 10,
    "ultra": 16,
}

DEFAULT_METRIC_FLOORS = {
    "maskIoU_front": 0.85,
    "ssim_front": 0.50,
    "edgeF1": 0.25,
    "vision": 0.70,
}

DECISIONS = ("accept", "replan", "recode", "ask", "abort")
