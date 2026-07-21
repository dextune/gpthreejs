"""Deterministic image metrics (stdlib). Agent still owns narrative scores."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from engine.shared.jsonutil import dump_json
from engine.shared.pngio import Image, grayscale, read_png, resize_nearest


def _to_mask(img: Image, use_alpha: bool = True) -> list[bool]:
    m: list[bool] = []
    for i in range(0, len(img.rgba), 4):
        if use_alpha and img.rgba[i + 3] < 255:
            m.append(img.rgba[i + 3] > 128)
        else:
            m.append(img.rgba[i] > 128)
    return m


def mask_iou(ref_matte: Image, render: Image) -> float:
    w = min(ref_matte.width, render.width)
    h = min(ref_matte.height, render.height)
    a = resize_nearest(ref_matte, w, h)
    rendered = resize_nearest(render, w, h)
    matte_rgba = a.rgba
    render_rgba = rendered.rgba
    # render: luma threshold as proxy if no alpha
    inter = union = 0
    for i in range(0, len(matte_rgba), 4):
        pa = matte_rgba[i + 3] > 128
        r, g, bch, al = render_rgba[i], render_rgba[i + 1], render_rgba[i + 2], render_rgba[i + 3]
        # dark-background heuristic when render lacks cutout alpha
        lum = (r + g + bch) / 3.0
        pb = (al > 128) and (lum > 18)
        inter += int(pa and pb)
        union += int(pa or pb)
    return inter / union if union else 0.0


def ssim_approx(a: Image, b: Image) -> float:
    """Lightweight luminance SSIM-ish score on downscaled gray."""
    W = H = 64
    ga = grayscale(resize_nearest(a, W, H))
    gb = grayscale(resize_nearest(b, W, H))
    n = W * H
    ma = sum(ga) / n
    mb = sum(gb) / n
    va = sum((x - ma) ** 2 for x in ga) / n
    vb = sum((x - mb) ** 2 for x in gb) / n
    cov = sum((ga[i] - ma) * (gb[i] - mb) for i in range(n)) / n
    c1, c2 = 6.5025, 58.5225  # (0.01*255)^2, (0.03*255)^2
    num = (2 * ma * mb + c1) * (2 * cov + c2)
    den = (ma * ma + mb * mb + c1) * (va + vb + c2)
    return max(0.0, min(1.0, num / den if den else 0.0))


def edge_f1(ref_edges: Image, render: Image) -> float:
    """F1 between ref edge map and sobel of render."""
    from engine.sense.edges import sobel_edges

    W = H = 96
    re = resize_nearest(ref_edges, W, H)
    se = sobel_edges(resize_nearest(render, W, H))
    ref_rgba = re.rgba
    sobel_rgba = se.rgba
    tp = fp = fn = 0
    for i in range(0, len(ref_rgba), 4):
        rt = ref_rgba[i] > 64
        pt = sobel_rgba[i] > 64
        tp += int(rt and pt)
        fp += int(pt and not rt)
        fn += int(rt and not pt)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    if prec + rec == 0:
        return 0.0
    return 2 * prec * rec / (prec + rec)


def compute_metrics(
    reference: str | Path,
    render: str | Path,
    *,
    matte: str | Path | None = None,
    edges: str | Path | None = None,
    out: str | Path | None = None,
) -> dict[str, Any]:
    ref = read_png(reference)
    ren = read_png(render)
    result: dict[str, Any] = {
        "reference": str(reference),
        "render": str(render),
        "ssim": round(ssim_approx(ref, ren), 4),
    }
    if matte and Path(matte).exists():
        result["maskIoU"] = round(mask_iou(read_png(matte), ren), 4)
    if edges and Path(edges).exists():
        result["edgeF1"] = round(edge_f1(read_png(edges), ren), 4)
    if out:
        dump_json(out, result)
    return result


def floors_pass(metrics: dict, floors: dict) -> tuple[bool, list[str]]:
    fails = []
    mapping = {
        "maskIoU_front": "maskIoU",
        "ssim_front": "ssim",
        "edgeF1": "edgeF1",
    }
    for floor_key, metric_key in mapping.items():
        if floor_key in floors and metric_key in metrics:
            if metrics[metric_key] < floors[floor_key]:
                fails.append(f"{metric_key}={metrics[metric_key]} < {floors[floor_key]}")
    return (len(fails) == 0, fails)
