"""Shared capture / generation defaults for Reference Prep (RP-002).

Playbook prose and GenerationBrief builders must import these constants
instead of duplicating magic numbers.
"""

from __future__ import annotations

from typing import Any

# Hard sufficiency floor (engine.sense.sufficiency_policy.MIN_SHORT_SIDE).
MIN_SHORT_SIDE_HARD_PX = 256
# Casting-favorable recommended floor.
MIN_SHORT_SIDE_RECOMMENDED_PX = 512
# Preferred generation target when RES_TOO_LOW or concept-first.
RECOMMENDED_SHORT_SIDE_PX = 1024

DEFAULT_ASPECT = "1:1"
DEFAULT_BACKGROUND = "transparent-or-solid-neutral"
DEFAULT_BACKGROUND_HEX = "#808080"
DEFAULT_ALPHA_PREFERRED = True
DEFAULT_SUBJECT_FILL = (0.15, 0.80)

DEFAULT_POSE_PRESET = "A-pose"
DEFAULT_POSE_FACING = "camera-relative"
DEFAULT_NO_HEAVY_OCCLUSION = True

DEFAULT_FORMAT = "PNG"
DEFAULT_ONE_VIEW_PER_FILE = True
DEFAULT_LIGHTING = "soft-studio-no-harsh-rim"

# Character domain: front + side required; back recommended.
CHARACTER_REQUIRED_VIEW_IDS = ("front", "side")
CHARACTER_RECOMMENDED_VIEW_IDS = ("back",)

EVIDENCE_CLASS_GENERATED = "design-intent"
EVIDENCE_CLASS_GENERATED_HYPOTHESIS = "design-hypothesis"
EVIDENCE_CLASS_SEED = "observed"

INTAKE_ROUTES = (
    "photo-lock",
    "redesign-from-ref",
    "concept-first",
    "hybrid-body",
)

VIEW_CAMERA_MAP = {
    "front": "orthographic-front",
    "side": "orthographic-left",
    "left": "orthographic-left",
    "right": "orthographic-right",
    "back": "orthographic-back",
    "source-34": "perspective-hero-34",
}


def frame_defaults(
    *,
    min_short_side_px: int | None = None,
    recommended_short_side_px: int | None = None,
) -> dict[str, Any]:
    return {
        "minShortSidePx": min_short_side_px or MIN_SHORT_SIDE_RECOMMENDED_PX,
        "recommendedShortSidePx": recommended_short_side_px or RECOMMENDED_SHORT_SIDE_PX,
        "aspect": DEFAULT_ASPECT,
        "subjectFill": list(DEFAULT_SUBJECT_FILL),
        "background": DEFAULT_BACKGROUND,
        "backgroundHex": DEFAULT_BACKGROUND_HEX,
        "alphaPreferred": DEFAULT_ALPHA_PREFERRED,
        "format": DEFAULT_FORMAT,
        "oneViewPerFile": DEFAULT_ONE_VIEW_PER_FILE,
        "lighting": DEFAULT_LIGHTING,
    }


def pose_defaults() -> dict[str, Any]:
    return {
        "preset": DEFAULT_POSE_PRESET,
        "facing": DEFAULT_POSE_FACING,
        "noHeavyOcclusion": DEFAULT_NO_HEAVY_OCCLUSION,
    }


def capture_checklist_terms() -> list[str]:
    """Terms that must appear in user-facing prep checklists (EN or KO)."""
    return [
        "resolution",
        "512",
        "transparent",
        "background",
        "front",
        "side",
        "pose",
        "해상도",
        "투명",
        "배경",
        "정면",
        "측면",
        "포즈",
    ]
