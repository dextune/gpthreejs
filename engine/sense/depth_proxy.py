"""Relative depth proxy from luminance + vertical bias (no ML weights required)."""

from __future__ import annotations

from pathlib import Path

from engine.shared.pngio import Image, grayscale, read_png, write_png


def depth_from_luma(img: Image) -> Image:
    """
    Heuristic: brighter + lower-in-frame often closer for product photos.
    Output: white = near, black = far (relative only).
    """
    g = grayscale(img)
    w, h = img.width, img.height
    out = Image(w, h, bytearray(w * h * 4))
    for y in range(h):
        vbias = int(40 * (y / max(1, h - 1)))  # lower pixels slightly nearer
        for x in range(w):
            lum = g[y * w + x]
            d = min(255, max(0, lum + vbias // 2))
            out.set_pixel(x, y, (d, d, d, 255))
    return out


def build_depth_proxy(image_path: str | Path, out_path: str | Path) -> dict:
    img = read_png(image_path)
    depth = depth_from_luma(img)
    write_png(out_path, depth)
    return {
        "path": str(out_path),
        "method": "luma-vertical-proxy",
        "metric": False,
        "note": "Relative only. Optional ONNX Depth Anything may replace this in extras.",
    }
