"""Comparison overlay / silhouette-diff PNG generation (REV-170)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.shared.pngio import Image, read_png, write_png


def silhouette_diff_png(
    reference_alpha: str | Path,
    candidate_alpha: str | Path,
    out_path: str | Path,
) -> dict[str, Any]:
    """
    Write RGB overlay:
      green = true positive (both opaque)
      red = false positive (candidate only)
      blue = false negative (reference only)
    """

    ref = read_png(reference_alpha)
    cand = read_png(candidate_alpha)
    w = min(ref.width, cand.width)
    h = min(ref.height, cand.height)
    out = Image(w, h, bytearray([20, 20, 24, 255] * (w * h)))
    tp = fp = fn = 0
    for y in range(h):
        for x in range(w):
            ra = ref.pixel(x, y)[3] > 128
            ca = cand.pixel(x, y)[3] > 128
            if ra and ca:
                out.set_pixel(x, y, (40, 200, 80, 255))
                tp += 1
            elif ca and not ra:
                out.set_pixel(x, y, (220, 60, 60, 255))
                fp += 1
            elif ra and not ca:
                out.set_pixel(x, y, (60, 100, 220, 255))
                fn += 1
    write_png(out_path, out)
    return {
        "path": str(out_path),
        "truePositive": tp,
        "falsePositive": fp,
        "falseNegative": fn,
        "width": w,
        "height": h,
    }


def part_label_overlay(
    beauty_path: str | Path,
    part_id_path: str | Path,
    out_path: str | Path,
    *,
    blend: float = 0.45,
) -> dict[str, Any]:
    """Blend beauty with part-id colors for part-label annotation."""

    beauty = read_png(beauty_path)
    part = read_png(part_id_path)
    w = min(beauty.width, part.width)
    h = min(beauty.height, part.height)
    out = Image(w, h, bytearray(w * h * 4))
    t = max(0.0, min(1.0, blend))
    for y in range(h):
        for x in range(w):
            br, bg, bb, ba = beauty.pixel(x, y)
            pr, pg, pb, pa = part.pixel(x, y)
            if pa < 16:
                out.set_pixel(x, y, (br, bg, bb, ba))
            else:
                r = int(br * (1 - t) + pr * t)
                g = int(bg * (1 - t) + pg * t)
                b = int(bb * (1 - t) + pb * t)
                out.set_pixel(x, y, (r, g, b, 255))
    write_png(out_path, out)
    return {"path": str(out_path), "blend": t}


def build_gate_comparison_artifacts(
    *,
    render_set: dict[str, Any],
    out_dir: str | Path,
    view_id: str = "source-34",
    reference_alpha: str | Path | None = None,
) -> dict[str, Any]:
    """Produce overlay PNGs for Gate A–E review."""

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    view = next((v for v in render_set.get("views") or [] if v.get("id") == view_id), None)
    if not view:
        raise ValueError(f"view {view_id} missing from render set")
    passes = view.get("passes") or {}
    alpha = passes["alpha"]["path"]
    beauty = passes["beauty"]["path"]
    part_id = passes["partId"]["path"]

    artifacts: dict[str, Any] = {"viewId": view_id}
    if reference_alpha and Path(reference_alpha).is_file():
        artifacts["silhouetteDiff"] = silhouette_diff_png(
            reference_alpha,
            alpha,
            out / f"{view_id}-silhouette-diff.png",
        )
    else:
        # self-diff baseline (should be mostly green)
        artifacts["silhouetteDiff"] = silhouette_diff_png(
            alpha,
            alpha,
            out / f"{view_id}-silhouette-diff.png",
        )
    artifacts["partLabels"] = part_label_overlay(
        beauty,
        part_id,
        out / f"{view_id}-part-labels.png",
    )
    artifacts["annotations"] = [
        {"type": "silhouette-diff", "path": artifacts["silhouetteDiff"]["path"]},
        {"type": "part-labels", "path": artifacts["partLabels"]["path"]},
    ]
    return artifacts
