"""Sufficiency checks for image, sense pack, views, and spec artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.sense.probe import probe_image
from engine.sense.sufficiency_policy import (
    IDEAL_FOREGROUND,
    MAX_EDGE_DENSITY,
    MAX_FOREGROUND_RATIO,
    MIN_EDGE_DENSITY,
    MIN_FOREGROUND_RATIO,
    MIN_LEDGER_FILLED_FRAC,
    MIN_MEGAPIXELS,
    MIN_MEGAPIXELS_SHARP,
    MIN_SHORT_SIDE,
    MIN_SHORT_SIDE_SHARP,
    VERY_BRIGHT,
    VERY_DARK,
    issue,
)


def assess_image_file(image_path: str | Path) -> tuple[list[dict], dict]:
    """Technical file / raster checks."""
    issues: list[dict] = []
    probe = probe_image(image_path)
    meta: dict[str, Any] = {"probe": probe}

    if probe.get("error") == "missing" or not probe.get("exists"):
        issues.append(
            issue(
                "FILE_MISSING",
                "blocker",
                "The image file is missing or the path cannot be read.",
                "Provide a valid image path.",
                field="image",
                evidence=probe.get("path"),
            )
        )
        return issues, meta

    if probe.get("error"):
        issues.append(
            issue(
                "FILE_UNREADABLE",
                "blocker",
                f"The image could not be decoded: {probe.get('error')}",
                "Save or convert the source again as an intact PNG.",
                field="image",
            )
        )
        return issues, meta

    suffix = str(probe.get("suffix") or "").lower()
    if suffix and suffix not in (".png", ".jpg", ".jpeg", ".webp"):
        issues.append(
            issue(
                "FORMAT_UNUSUAL",
                "major",
                f"The engine Sense Pack path is PNG-first (current suffix: {suffix}).",
                "Convert the image to PNG, then run `engine sense`.",
                field="format",
                evidence=suffix,
            )
        )
    elif suffix in (".jpg", ".jpeg", ".webp"):
        issues.append(
            issue(
                "FORMAT_CONVERT",
                "minor",
                "JPEG/WebP can only be metadata-probed; Sense map generation requires PNG conversion.",
                "Save the image as PNG with `convert` or PIL before running sense.",
                field="format",
            )
        )

    w = probe.get("width")
    h = probe.get("height")
    if w and h:
        short = min(int(w), int(h))
        mp = float(probe.get("megapixels") or (w * h / 1e6))
        meta["shortSide"] = short
        meta["megapixels"] = mp
        if short < MIN_SHORT_SIDE:
            issues.append(
                issue(
                    "RES_TOO_LOW",
                    "blocker",
                    f"Resolution is too low (short side {short}px < {MIN_SHORT_SIDE}px).",
                    "Provide an image with a short side of at least 256px; 512px+ is recommended for sharp mode.",
                    field="resolution",
                    evidence={"width": w, "height": h},
                )
            )
        elif short < MIN_SHORT_SIDE_SHARP:
            issues.append(
                issue(
                    "RES_MARGINAL",
                    "major",
                    f"Resolution is marginal (short side {short}px). It may be insufficient for sharp or razor quality.",
                    f"Retake or upscale to a short side of at least {MIN_SHORT_SIDE_SHARP}px; a sharp source is preferred.",
                    field="resolution",
                    evidence={"width": w, "height": h},
                )
            )
        if mp < MIN_MEGAPIXELS:
            issues.append(
                issue(
                    "MP_TOO_LOW",
                    "blocker",
                    f"Total pixel count is too low ({mp} MP).",
                    "Provide a larger image.",
                    field="resolution",
                )
            )
        elif mp < MIN_MEGAPIXELS_SHARP:
            issues.append(
                issue(
                    "MP_MARGINAL",
                    "minor",
                    f"Total pixel count is somewhat low ({mp} MP).",
                    "Use a larger source if detail reconstruction matters.",
                    field="resolution",
                )
            )

        aspect = float(probe.get("aspect") or (w / max(1, h)))
        if aspect > 3.5 or aspect < 0.28:
            issues.append(
                issue(
                    "ASPECT_EXTREME",
                    "major",
                    f"Aspect ratio is extreme (aspect={aspect:.2f}). The subject may be cropped or too small.",
                    "Crop or reframe so the full subject is visible and close to a front-facing view.",
                    field="composition",
                    evidence={"aspect": aspect},
                )
            )

    flags = list(probe.get("flags") or [])
    luma = probe.get("mean_luma_approx")
    if luma is not None:
        if luma < VERY_DARK or "very-dark" in flags:
            issues.append(
                issue(
                    "EXPOSURE_DARK",
                    "major",
                    f"The image is very dark (mean luminance about {luma}).",
                    "Provide a better-exposed photo or a reference with clearer lighting.",
                    field="exposure",
                    evidence={"meanLuma": luma},
                )
            )
        elif luma > VERY_BRIGHT or "very-bright" in flags:
            issues.append(
                issue(
                    "EXPOSURE_BRIGHT",
                    "major",
                    f"The image is close to overexposed (mean luminance about {luma}).",
                    "Provide a reference without clipped highlights.",
                    field="exposure",
                    evidence={"meanLuma": luma},
                )
            )

    return issues, meta


def assess_sense_pack(sense: dict[str, Any] | None) -> tuple[list[dict], dict]:
    """Checks that need a Sense Pack (matte / edges)."""
    issues: list[dict] = []
    meta: dict[str, Any] = {}
    if not sense:
        issues.append(
            issue(
                "SENSE_MISSING",
                "info",
                "No Sense Pack is available, so silhouette and edge sufficiency checks are skipped.",
                "Run `python3 -m engine sense <img> --out work/sense --mode sharp`.",
                field="sense",
            )
        )
        return issues, meta

    maps = sense.get("maps") or {}
    matte = maps.get("matte") or {}
    edges = maps.get("edges") or {}
    fg = matte.get("foreground_ratio")
    edge_d = edges.get("edge_density")
    bbox = matte.get("bbox")
    meta["foregroundRatio"] = fg
    meta["edgeDensity"] = edge_d
    meta["bbox"] = bbox

    if fg is not None:
        fg = float(fg)
        if fg < MIN_FOREGROUND_RATIO:
            issues.append(
                issue(
                    "SUBJECT_TOO_SMALL",
                    "blocker",
                    f"The foreground subject is too small in the frame (foreground about {fg:.1%}).",
                    "Provide a tighter crop of the subject. A plain background is preferred.",
                    field="composition",
                    evidence={"foregroundRatio": fg},
                )
            )
        elif fg < IDEAL_FOREGROUND[0]:
            issues.append(
                issue(
                    "SUBJECT_SMALL",
                    "major",
                    f"The foreground ratio is low (foreground about {fg:.1%}). Silhouette locking may be unstable.",
                    "Use a subject-centered crop or simplify the background.",
                    field="composition",
                    evidence={"foregroundRatio": fg},
                )
            )
        elif fg > MAX_FOREGROUND_RATIO:
            issues.append(
                issue(
                    "SUBJECT_FILLS_FRAME",
                    "major",
                    f"The foreground fills almost the entire frame (foreground about {fg:.1%}). Silhouette and matte extraction may be unstable.",
                    "Provide a shot with margin around the subject or a clean alpha cutout.",
                    field="composition",
                    evidence={"foregroundRatio": fg},
                )
            )

    if edge_d is not None:
        edge_d = float(edge_d)
        if edge_d < MIN_EDGE_DENSITY:
            issues.append(
                issue(
                    "EDGE_TOO_FEW",
                    "major",
                    f"Very few contour or detail edges were detected (edgeDensity about {edge_d:.4f}). Shape information may be insufficient.",
                    "Use a reference with clearer object structure or higher contrast. Texture swatches alone are unsuitable.",
                    field="structure",
                    evidence={"edgeDensity": edge_d},
                )
            )
        elif edge_d > MAX_EDGE_DENSITY:
            issues.append(
                issue(
                    "EDGE_TOO_BUSY",
                    "minor",
                    f"Edge density is very high (edgeDensity about {edge_d:.4f}). This may be background noise or excessive patterning.",
                    "Crop to a plain background or constrain the agent to the subject ROI.",
                    field="composition",
                    evidence={"edgeDensity": edge_d},
                )
            )

    method = matte.get("method")
    if method == "corner-distance":
        issues.append(
            issue(
                "MATTE_HEURISTIC",
                "info",
                "The foreground matte uses a corner-background heuristic and may be inaccurate on complex backgrounds.",
                "Use a plain-background shot or a higher-quality cutout such as rembg.",
                field="sense",
                evidence={"matteMethod": method},
            )
        )

    return issues, meta


def assess_intent_and_views(
    *,
    domain: str | None,
    intent: str | None,
    view_count: int,
    has_side: bool,
    has_back: bool,
) -> list[dict]:
    issues: list[dict] = []
    domain = (domain or "object").lower()
    intent = (intent or "realtime-prop").lower()

    if domain in ("character", "hybrid") and view_count < 2:
        issues.append(
            issue(
                "CHAR_SINGLE_VIEW",
                "major",
                "The domain is character or hybrid, but the reference is effectively single-view. Side/back proportions and volume are uncertain.",
                "Add front and side turnaround references. Without them, proceed only with stylized symmetry assumptions and lower confidence.",
                field="views",
                evidence={"viewCount": view_count, "domain": domain},
            )
        )
    if domain in ("character", "hybrid") and not has_side:
        issues.append(
            issue(
                "CHAR_NO_SIDE",
                "major",
                "No character side reference is available. Thickness, helmet depth, nose projection, and similar features are underspecified.",
                "Add a `side` or orthographic side image.",
                field="views",
            )
        )
    if intent in ("game", "playable", "animation", "rig") and view_count < 2:
        issues.append(
            issue(
                "GAME_VIEWS_THIN",
                "minor",
                "The intended use is game or animation, but multiview coverage is thin. Rig and silhouette validation will be weaker.",
                "Provide at least front and side views, and a back view when possible.",
                field="views",
            )
        )
    if intent in ("hero", "hero-render", "likeness", "maximum-likeness") and not (has_side and view_count >= 2):
        issues.append(
            issue(
                "LIKENESS_VIEWS",
                "major",
                "The requested likeness or hero quality needs more view information.",
                "Add front, side, optional back, and detail crops. A single image cannot support a 100% likeness claim.",
                field="views",
            )
        )
    return issues


def assess_spec(
    *,
    brief: dict | None,
    ledger: dict | None,
    blueprint: dict | None,
    domain: str | None,
) -> list[dict]:
    """Specification completeness (when artifacts exist)."""
    issues: list[dict] = []
    domain = (domain or (brief or {}).get("domain") or (blueprint or {}).get("domain") or "object").lower()

    if brief is None and blueprint is None and ledger is None:
        return issues

    if brief is not None:
        if not brief.get("fidelityPact"):
            issues.append(
                issue(
                    "BRIEF_NO_PACT",
                    "major",
                    "The Intake Brief is missing a Fidelity Pact.",
                    "Regenerate with `engine brief` or fill the fidelityPact block.",
                    field="brief",
                )
            )
        if not brief.get("complexity"):
            issues.append(
                issue(
                    "BRIEF_NO_COMPLEXITY",
                    "minor",
                    "complexity is missing, so the Ledger minimum is ambiguous.",
                    "Set one of simple|moderate|complex|ultra.",
                    field="brief",
                )
            )

    if ledger is not None:
        entries = ledger.get("entries") or []
        todos = [entry for entry in entries if entry.get("status") == "todo"]
        filled = [entry for entry in entries if entry.get("status") != "todo"]
        target = int(ledger.get("targetMin") or 0)
        unmapped = [entry for entry in filled if not entry.get("mapsTo")]
        if todos and len(todos) == len(entries):
            issues.append(
                issue(
                    "LEDGER_ALL_TODO",
                    "blocker",
                    "Every Feature Ledger entry is still todo. The detail inventory is empty.",
                    "Fill real zone-level details, set status=filled, and connect mapsTo.",
                    field="ledger",
                    evidence={"todo": len(todos)},
                )
            )
        elif target and len(filled) < max(1, int(target * MIN_LEDGER_FILLED_FRAC)):
            issues.append(
                issue(
                    "LEDGER_SPARSE",
                    "major",
                    f"Filled Ledger entries are below target (filled={len(filled)}, targetMin={target}).",
                    f"Enter at least about {max(1, int(target * MIN_LEDGER_FILLED_FRAC))} identity details.",
                    field="ledger",
                    evidence={"filled": len(filled), "targetMin": target},
                )
            )
        if unmapped:
            issues.append(
                issue(
                    "LEDGER_UNMAPPED",
                    "major",
                    f"{len(unmapped)} Ledger entries are missing mapsTo and are not linked to implementation targets.",
                    "Connect each entry to a component feature or material override id.",
                    field="ledger",
                )
            )

    if blueprint is not None:
        parts = blueprint.get("parts") or []
        if not parts:
            issues.append(
                issue(
                    "BP_NO_PARTS",
                    "blocker",
                    "The Form Blueprint has no parts.",
                    "Create the part tree, then validate.",
                    field="blueprint",
                )
            )
        mats = blueprint.get("materials") or []
        if not mats:
            issues.append(
                issue(
                    "BP_NO_MATERIALS",
                    "blocker",
                    "materials is empty.",
                    "Define at least one PBR material.",
                    field="blueprint",
                )
            )
        if domain in ("character", "hybrid") and not blueprint.get("anatomy"):
            issues.append(
                issue(
                    "BP_NO_ANATOMY",
                    "major",
                    "The domain is character or hybrid, but the anatomy block is missing.",
                    "Fill head units, proportions, pose, and landmarks, or request a side view.",
                    field="blueprint",
                )
            )
        complexity = str(blueprint.get("complexity") or "").lower()
        if complexity in ("complex", "ultra") and len(parts) < 2:
            issues.append(
                issue(
                    "BP_SHALLOW_TREE",
                    "major",
                    "complexity is high, but the part tree is too shallow.",
                    "Split major subparts to deepen the parts hierarchy.",
                    field="blueprint",
                )
            )
        if not blueprint.get("surfaceStack") and str(blueprint.get("qualityMode") or "") in (
            "sharp",
            "razor",
            "hybrid",
        ):
            issues.append(
                issue(
                    "BP_NO_SURFACE",
                    "minor",
                    "High-quality mode is set, but surfaceStack is missing.",
                    "Run `engine surface-annotate`.",
                    field="blueprint",
                )
            )

    return issues
