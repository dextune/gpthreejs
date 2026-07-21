"""Dominant color clusters via simple binning (stdlib)."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from engine.shared.pngio import read_png


def extract_palette(image_path: str | Path, k: int = 6, step: int = 4) -> dict:
    img = read_png(image_path)
    counter: Counter[tuple[int, int, int]] = Counter()
    for y in range(0, img.height, step):
        for x in range(0, img.width, step):
            r, g, b, a = img.pixel(x, y)
            if a < 16:
                continue
            # quantize to 32 levels
            key = (r // 32 * 32 + 16, g // 32 * 32 + 16, b // 32 * 32 + 16)
            counter[key] += 1
    total = sum(counter.values()) or 1
    top = counter.most_common(k)
    colors = [
        {
            "rgb": list(rgb),
            "hex": f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}",
            "weight": round(c / total, 4),
        }
        for rgb, c in top
    ]
    return {"colors": colors, "method": "quantized-histogram", "sample_step": step}
