"""Reversible canvas padding / normalization for reference images."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from engine.reference.matte_confidence import assess_matte_confidence
from engine.sense.matte import matte_heuristic
from engine.shared.pngio import Image, read_png, write_png


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_hash(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pad_image(
    image: Image,
    *,
    pad_ratio: float = 0.15,
    background: tuple[int, int, int, int] | None = None,
) -> tuple[Image, dict[str, Any]]:
    """Pad an image with a constant background, returning the padded image and transform."""

    pad_x = max(1, int(round(image.width * pad_ratio)))
    pad_y = max(1, int(round(image.height * pad_ratio)))
    new_w = image.width + 2 * pad_x
    new_h = image.height + 2 * pad_y

    if background is None:
        # Estimate from corners of the source.
        corners = [
            image.pixel(0, 0),
            image.pixel(image.width - 1, 0),
            image.pixel(0, image.height - 1),
            image.pixel(image.width - 1, image.height - 1),
        ]
        r = sum(c[0] for c in corners) // 4
        g = sum(c[1] for c in corners) // 4
        b = sum(c[2] for c in corners) // 4
        background = (r, g, b, 255)

    dst = Image(new_w, new_h, bytearray([0] * (new_w * new_h * 4)))
    for y in range(new_h):
        for x in range(new_w):
            dst.set_pixel(x, y, background)

    for y in range(image.height):
        for x in range(image.width):
            dst.set_pixel(x + pad_x, y + pad_y, image.pixel(x, y))

    transform = {
        "operation": "pad",
        "canvas": [new_w, new_h],
        "offset": [pad_x, pad_y],
        "sourceSize": [image.width, image.height],
        "background": list(background),
        "backgroundMode": "estimated",
        "reversible": True,
        "padRatio": pad_ratio,
    }
    return dst, transform


def normalize_reference(
    image_path: str | Path,
    *,
    out_path: str | Path | None = None,
    pad_ratio: float = 0.15,
    force: bool = False,
) -> dict[str, Any]:
    """
    Normalize a frame-filling subject via reversible padding when needed.

    Always records source hash and transform metadata. Does not mutate the
    original file; writes a new PNG when padding is applied.
    """

    path = Path(image_path)
    src = read_png(path)
    source_hash = _source_hash(path)
    before = assess_matte_confidence(src)

    applied = False
    transform: dict[str, Any] | None = None
    result_image = src
    if force or before.get("normalizationCandidate") or before.get("agentAction") == "normalize":
        result_image, transform = pad_image(src, pad_ratio=pad_ratio)
        transform["sourceHash"] = source_hash
        applied = True
    else:
        transform = {
            "operation": "identity",
            "sourceHash": source_hash,
            "canvas": [src.width, src.height],
            "offset": [0, 0],
            "sourceSize": [src.width, src.height],
            "reversible": True,
        }

    written: str | None = None
    if applied:
        target = Path(out_path) if out_path else path.with_name(f"{path.stem}.normalized{path.suffix}")
        write_png(target, result_image)
        written = str(target)

    after = assess_matte_confidence(result_image)
    return {
        "schemaVersion": 1,
        "sourcePath": str(path),
        "sourceHash": source_hash,
        "normalizedPath": written,
        "applied": applied,
        "normalization": transform,
        "confidenceBefore": before,
        "confidenceAfter": after,
        "agentAction": after.get("agentAction", "continue"),
    }


def reverse_pad_point(
    x: float,
    y: float,
    normalization: dict[str, Any],
    *,
    normalized_space: bool = True,
) -> tuple[float, float]:
    """Map a point from normalized canvas space back to source space."""

    if normalization.get("operation") != "pad":
        return x, y
    ox, oy = normalization["offset"]
    sw, sh = normalization["sourceSize"]
    if normalized_space:
        # Inputs are in [0,1] on the padded canvas.
        cw, ch = normalization["canvas"]
        px, py = x * cw, y * ch
    else:
        px, py = x, y
    sx = (px - ox) / max(1, sw)
    sy = (py - oy) / max(1, sh)
    return sx, sy
