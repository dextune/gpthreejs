"""Sobel-like edge map in pure Python."""

from __future__ import annotations

from pathlib import Path

from engine.shared.pngio import Image, grayscale, read_png, write_png


def sobel_edges(img: Image) -> Image:
    g = grayscale(img)
    w, h = img.width, img.height
    out = Image(w, h, bytearray(w * h * 4))
    # Sobel kernels
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            def at(xx: int, yy: int) -> int:
                return g[yy * w + xx]

            gx = (
                -at(x - 1, y - 1)
                + at(x + 1, y - 1)
                - 2 * at(x - 1, y)
                + 2 * at(x + 1, y)
                - at(x - 1, y + 1)
                + at(x + 1, y + 1)
            )
            gy = (
                -at(x - 1, y - 1)
                - 2 * at(x, y - 1)
                - at(x + 1, y - 1)
                + at(x - 1, y + 1)
                + 2 * at(x, y + 1)
                + at(x + 1, y + 1)
            )
            mag = min(255, int((gx * gx + gy * gy) ** 0.5))
            out.set_pixel(x, y, (mag, mag, mag, 255))
    return out


def build_edges(image_path: str | Path, out_path: str | Path) -> dict:
    img = read_png(image_path)
    edges = sobel_edges(img)
    write_png(out_path, edges)
    # edge density
    strong = 0
    total = edges.width * edges.height
    for i in range(0, len(edges.rgba), 4):
        if edges.rgba[i] > 64:
            strong += 1
    return {
        "path": str(out_path),
        "edge_density": round(strong / max(1, total), 4),
        "method": "sobel-stdlib",
    }
