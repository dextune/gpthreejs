"""Quality and detail mode contracts."""

from __future__ import annotations

QUALITY_MODES = ("draft", "solid", "sharp", "razor", "hybrid")
DETAIL_LEVELS = ("low", "medium", "high", "ultra")

QUALITY_TO_DETAIL = {
    "draft": "low",
    "solid": "medium",
    "sharp": "high",
    "razor": "ultra",
    "hybrid": "high",
}

DETAIL_RESOLUTIONS = {
    "low": 256,
    "medium": 512,
    "high": 512,
    "ultra": 1024,
}

DETAIL_RIVET_LIMITS = {
    "low": 0,
    "medium": 64,
    "high": 256,
    "ultra": 512,
}


def normalize_detail_level(detail_level: str | None, *, default: str = "high") -> str:
    if detail_level in DETAIL_LEVELS:
        return str(detail_level)
    return default


def quality_mode_to_detail_level(mode: str | None) -> str:
    return QUALITY_TO_DETAIL.get(str(mode or "sharp"), "high")


def detail_resolution(detail_level: str, override: int = 0) -> int:
    if override:
        return override
    return DETAIL_RESOLUTIONS[normalize_detail_level(detail_level)]
