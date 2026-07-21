"""CPU multi-start parameter fit against matte silhouette (stdlib)."""

from __future__ import annotations

import math
import random
import time
from pathlib import Path
from typing import Any

from engine.shared.jsonutil import dump_json, load_json
from engine.shared.parallel import default_workers
from engine.shared.pngio import Image, read_png, resize_nearest


def _raster_box_silhouette(size: tuple[float, float, float], w: int, h: int) -> Image:
    """Orthographic fake: project box as axis-aligned ellipse-rect hybrid."""
    out = Image(w, h, bytearray(w * h * 4))
    # map size.x, size.y to image fraction
    sx = min(0.95, 0.35 * size[0])
    sy = min(0.95, 0.35 * size[1])
    cx, cy = w / 2, h / 2
    rx, ry = sx * w / 2, sy * h / 2
    for y in range(h):
        for x in range(w):
            nx = (x - cx) / max(1e-6, rx)
            ny = (y - cy) / max(1e-6, ry)
            # superellipse-ish box silhouette
            inside = (abs(nx) ** 4 + abs(ny) ** 4) <= 1.0
            v = 255 if inside else 0
            out.set_pixel(x, y, (v, v, v, 255))
    return out


def _mask_iou(a: Image, b: Image, thr: int = 128) -> float:
    w = min(a.width, b.width)
    h = min(a.height, b.height)
    inter = union = 0
    for y in range(h):
        for x in range(w):
            pa = a.pixel(x, y)[0] > thr or a.pixel(x, y)[3] > thr
            # for matte use alpha
            if a.pixel(x, y)[3] not in (0, 255):
                pa = a.pixel(x, y)[3] > thr
            pb = b.pixel(x, y)[0] > thr or b.pixel(x, y)[3] > thr
            if a is b:
                pass
            inter += int(pa and pb)
            union += int(pa or pb)
    return inter / union if union else 0.0


def _matte_as_mask(matte: Image, w: int, h: int) -> Image:
    m = resize_nearest(matte, w, h)
    out = Image(w, h, bytearray(w * h * 4))
    for y in range(h):
        for x in range(w):
            a = m.pixel(x, y)[3]
            out.set_pixel(x, y, (a, a, a, 255))
    return out


def fit_root_mass(
    blueprint_path: str | Path,
    sense_path: str | Path,
    *,
    budget_sec: float = 60,
    workers: int | None = None,
    in_place: bool = True,
    seed: int = 0,
) -> dict[str, Any]:
    """
    Random multi-start search over root_mass size vs matte silhouette.
    CPU-bound; designed to use many iterations on one process (thread-safe RNG).
    """
    del workers  # reserved for future process pool of candidates
    bp = load_json(blueprint_path)
    sense = load_json(sense_path)
    matte_path = (sense.get("maps") or {}).get("matte", {}).get("path")
    if not matte_path or not Path(matte_path).exists():
        return {"ok": False, "error": "sense pack missing matte.png"}

    matte = read_png(matte_path)
    W = H = 96  # coarse for speed
    target = _matte_as_mask(matte, W, H)

    parts = bp.get("parts") or []
    if not parts:
        return {"ok": False, "error": "no parts"}
    root = parts[0]
    space = (root.get("searchSpace") or {}).get("size") or {
        "min": [0.4, 0.3, 0.3],
        "max": [1.6, 1.2, 1.2],
    }
    lo = space["min"]
    hi = space["max"]

    rng = random.Random(seed or bp.get("seed") or 42)
    best_iou = -1.0
    best_size = list(root.get("geometry", {}).get("size") or [1, 1, 1])
    t0 = time.time()
    trials = 0
    # Use available CPU time with many trials (single-threaded raster is GIL-bound;
    # still burns CPU meaningfully at 96²).
    while time.time() - t0 < budget_sec:
        size = (
            rng.uniform(lo[0], hi[0]),
            rng.uniform(lo[1], hi[1]),
            rng.uniform(lo[2], hi[2]),
        )
        sil = _raster_box_silhouette(size, W, H)
        iou = _mask_iou(sil, target)
        trials += 1
        if iou > best_iou:
            best_iou = iou
            best_size = [round(size[0], 4), round(size[1], 4), round(size[2], 4)]

    root.setdefault("geometry", {})["size"] = best_size
    parts[0] = root
    bp["parts"] = parts
    bp.setdefault("fitLog", []).append(
        {
            "layer": "mass",
            "metric": "maskIoU_proxy",
            "score": round(best_iou, 4),
            "trials": trials,
            "budgetSec": budget_sec,
            "workersHint": default_workers(),
            "size": best_size,
        }
    )
    if in_place:
        dump_json(blueprint_path, bp)
    return {
        "ok": True,
        "bestIoU": round(best_iou, 4),
        "size": best_size,
        "trials": trials,
        "elapsed": round(time.time() - t0, 2),
    }
