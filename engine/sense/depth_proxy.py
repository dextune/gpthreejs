"""Relative depth proxy from luminance + vertical bias (no ML weights required)."""

from __future__ import annotations

from pathlib import Path

from engine.shared.pngio import Image, read_png, write_png


def depth_from_luma(img: Image) -> Image:
    """
    Heuristic: brighter + lower-in-frame often closer for product photos.
    Output: white = near, black = far (relative only).
    """
    w, h = img.width, img.height
    src = img.rgba
    dst = bytearray(w * h * 4)
    for y in range(h):
        vbias = int(40 * (y / max(1, h - 1)))  # lower pixels slightly nearer
        row = y * w
        for x in range(w):
            i = (row + x) * 4
            lum = (src[i] * 299 + src[i + 1] * 587 + src[i + 2] * 114) // 1000
            d = min(255, max(0, lum + vbias // 2))
            dst[i] = d
            dst[i + 1] = d
            dst[i + 2] = d
            dst[i + 3] = 255
    return Image(w, h, dst)


def build_depth_proxy(
    image_path: str | Path,
    out_path: str | Path,
    *,
    source_image: Image | None = None,
) -> dict:
    img = source_image or read_png(image_path)
    depth = depth_from_luma(img)
    write_png(out_path, depth)
    return {
        "path": str(out_path),
        "method": "luma-vertical-proxy",
        "metric": False,
        "note": "Relative only. Optional ONNX Depth Anything may replace this in extras.",
    }
