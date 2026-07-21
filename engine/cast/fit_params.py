"""CPU multi-start parameter fit against matte silhouette (stdlib)."""

from __future__ import annotations

import math
import random
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from engine.shared.jsonutil import dump_json, load_json
from engine.shared.parallel import default_workers
from engine.shared.pngio import Image, read_png, resize_nearest


Candidate = tuple[float, float, float]
CandidateResult = tuple[float, Candidate, int]


def _mask_iou_from_candidate(size: Candidate, target: bytes | bytearray, w: int, h: int) -> float:
    """Evaluate box silhouette IoU against a compact matte mask without Image allocation."""
    sx = min(0.95, 0.35 * size[0])
    sy = min(0.95, 0.35 * size[1])
    cx, cy = w / 2, h / 2
    rx = max(1e-6, sx * w / 2)
    ry = max(1e-6, sy * h / 2)
    inter = union = 0
    for y in range(h):
        ny4 = abs((y - cy) / ry) ** 4
        row = y * w
        for x in range(w):
            nx = abs((x - cx) / rx)
            pa = (nx * nx * nx * nx + ny4) <= 1.0
            pb = target[row + x] > 0
            inter += int(pa and pb)
            union += int(pa or pb)
    return inter / union if union else 0.0


def _matte_as_mask(matte: Image, w: int, h: int) -> bytearray:
    m = resize_nearest(matte, w, h)
    mask = bytearray(w * h)
    rgba = m.rgba
    for i, j in enumerate(range(3, len(rgba), 4)):
        mask[i] = 1 if rgba[j] > 128 else 0
    return mask


def _evaluate_candidate_batch(args: tuple[list[Candidate], bytes | bytearray, int, int]) -> CandidateResult:
    candidates, target, w, h = args
    best_iou = -1.0
    best_size: Candidate = (1.0, 1.0, 1.0)
    for size in candidates:
        iou = _mask_iou_from_candidate(size, target, w, h)
        if iou > best_iou:
            best_iou = iou
            best_size = size
    return best_iou, best_size, len(candidates)


def _candidate_batches(
    rng: random.Random,
    lo: list[float],
    hi: list[float],
    *,
    batch_size: int,
    max_trials: int | None,
    deadline: float,
):
    produced = 0
    while max_trials is None or produced < max_trials:
        if max_trials is None and produced > 0 and time.time() >= deadline:
            break
        remaining = batch_size if max_trials is None else min(batch_size, max_trials - produced)
        batch: list[Candidate] = []
        for _ in range(remaining):
            batch.append(
                (
                    rng.uniform(lo[0], hi[0]),
                    rng.uniform(lo[1], hi[1]),
                    rng.uniform(lo[2], hi[2]),
                )
            )
        produced += len(batch)
        if batch:
            yield batch


def fit_root_mass(
    blueprint_path: str | Path,
    sense_path: str | Path,
    *,
    budget_sec: float = 60,
    workers: int | None = None,
    in_place: bool = True,
    seed: int = 0,
    max_trials: int | None = None,
) -> dict[str, Any]:
    """
    Random multi-start search over root_mass size vs matte silhouette.
    CPU-bound; designed to use many iterations on one process (thread-safe RNG).
    """
    requested_workers = max(1, int(workers or default_workers()))
    workers_used = max(1, min(requested_workers, default_workers()))
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
    deadline = t0 + max(0.0, budget_sec)
    trials = 0
    batch_size = max(16, workers_used * 16)
    batches = _candidate_batches(
        rng,
        lo,
        hi,
        batch_size=batch_size,
        max_trials=max_trials,
        deadline=deadline,
    )

    if workers_used == 1:
        result_iter = (_evaluate_candidate_batch((batch, target, W, H)) for batch in batches)
        for iou, size, count in result_iter:
            trials += count
            if iou > best_iou:
                best_iou = iou
                best_size = [round(size[0], 4), round(size[1], 4), round(size[2], 4)]
    else:
        with ProcessPoolExecutor(max_workers=workers_used) as executor:
            pending: list[list[Candidate]] = []
            for batch in batches:
                pending.append(batch)
                if len(pending) < workers_used:
                    continue
                for iou, size, count in executor.map(
                    _evaluate_candidate_batch,
                    [(chunk, target, W, H) for chunk in pending],
                ):
                    trials += count
                    if iou > best_iou:
                        best_iou = iou
                        best_size = [round(size[0], 4), round(size[1], 4), round(size[2], 4)]
                pending.clear()
            if pending:
                for iou, size, count in executor.map(
                    _evaluate_candidate_batch,
                    [(chunk, target, W, H) for chunk in pending],
                ):
                    trials += count
                    if iou > best_iou:
                        best_iou = iou
                        best_size = [round(size[0], 4), round(size[1], 4), round(size[2], 4)]

    if trials == 0:
        size = tuple(float(v) for v in best_size[:3])
        best_iou = _mask_iou_from_candidate(size, target, W, H)
        trials = 1

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
            "maxTrials": max_trials,
            "workersRequested": requested_workers,
            "workersUsed": workers_used,
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
        "workersRequested": requested_workers,
        "workersUsed": workers_used,
        "elapsed": round(time.time() - t0, 2),
    }
