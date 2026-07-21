"""Sobel-like edge map in pure Python."""

from __future__ import annotations

from pathlib import Path

from engine.shared.pngio import Image, grayscale, read_png, write_png


def sobel_edges(img: Image) -> Image:
    g = grayscale(img)
    w, h = img.width, img.height
    rgba = bytearray(w * h * 4)
    # Sobel kernels
    for y in range(1, h - 1):
        row = y * w
        prev_row = row - w
        next_row = row + w
        for x in range(1, w - 1):
            gx = (
                -g[prev_row + x - 1]
                + g[prev_row + x + 1]
                - 2 * g[row + x - 1]
                + 2 * g[row + x + 1]
                - g[next_row + x - 1]
                + g[next_row + x + 1]
            )
            gy = (
                -g[prev_row + x - 1]
                - 2 * g[prev_row + x]
                - g[prev_row + x + 1]
                + g[next_row + x - 1]
                + 2 * g[next_row + x]
                + g[next_row + x + 1]
            )
            mag = min(255, int((gx * gx + gy * gy) ** 0.5))
            i = (row + x) * 4
            rgba[i] = mag
            rgba[i + 1] = mag
            rgba[i + 2] = mag
            rgba[i + 3] = 255
    for i in range(3, len(rgba), 4):
        if rgba[i] == 0:
            rgba[i] = 255
    return Image(w, h, rgba)


def build_edges(image_path: str | Path, out_path: str | Path, *, source_image: Image | None = None) -> dict:
    img = source_image or read_png(image_path)
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
