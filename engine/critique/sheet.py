"""Comparison sheets and multi-view grids."""

from __future__ import annotations

from pathlib import Path

from engine.shared.pngio import hstack, read_png, resize_nearest, side_by_side, write_png


def make_sheet(reference: str | Path, render: str | Path, out: str | Path, max_side: int = 512) -> str:
    ref = read_png(reference)
    ren = read_png(render)
    m = max(ref.width, ref.height, ren.width, ren.height)
    if m > max_side:
        s = max_side / m
        ref = resize_nearest(ref, max(1, int(ref.width * s)), max(1, int(ref.height * s)))
        ren = resize_nearest(ren, max(1, int(ren.width * s)), max(1, int(ren.height * s)))
    # match heights
    h = max(ref.height, ren.height)
    if ref.height != h:
        ref = resize_nearest(ref, ref.width, h)
    if ren.height != h:
        ren = resize_nearest(ren, ren.width, h)
    sheet = side_by_side(ref, ren)
    write_png(out, sheet)
    return str(out)


def make_grid(
    reference: str | Path,
    renders_dir: str | Path,
    out: str | Path,
    max_each: int = 256,
) -> str:
    ref = read_png(reference)
    m = max(ref.width, ref.height)
    if m > max_each:
        s = max_each / m
        ref = resize_nearest(ref, max(1, int(ref.width * s)), max(1, int(ref.height * s)))
    paths = sorted(Path(renders_dir).glob("*.png"))[:8]
    imgs = [ref]
    for p in paths:
        im = read_png(p)
        m = max(im.width, im.height)
        if m > max_each:
            s = max_each / m
            im = resize_nearest(im, max(1, int(im.width * s)), max(1, int(im.height * s)))
        imgs.append(im)
    grid = hstack(imgs)
    write_png(out, grid)
    return str(out)
