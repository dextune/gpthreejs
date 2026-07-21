"""Build a Sense Pack (maps + metadata) from a reference PNG."""

from __future__ import annotations

from pathlib import Path

from engine.sense.depth_proxy import build_depth_proxy
from engine.sense.edges import build_edges
from engine.sense.matte import build_matte
from engine.sense.palette import extract_palette
from engine.sense.probe import probe_image, probe_loaded_png
from engine.contracts.modes import QUALITY_MODES
from engine.shared.jsonutil import dump_json
from engine.shared.pngio import Image, read_png, resize_nearest, write_png


def _ensure_png_workcopy(image_path: Path, out_dir: Path, max_side: int = 1024) -> tuple[Path, Image, dict]:
    """If PNG, optionally downscale for CPU work. Non-PNG: raise with clear message."""
    if image_path.suffix.lower() != ".png":
        raise SystemExit(
            f"Sense Pack currently requires PNG. Convert {image_path} to PNG first."
        )
    img = read_png(image_path)
    meta = probe_loaded_png(image_path, img)
    work = out_dir / "reference_work.png"
    m = max(img.width, img.height)
    if m > max_side:
        scale = max_side / m
        img = resize_nearest(img, max(1, int(img.width * scale)), max(1, int(img.height * scale)))
    write_png(work, img)
    return work, img, meta


def build_sense_pack(image_path: str | Path, out_dir: str | Path, mode: str = "sharp") -> dict:
    if mode not in QUALITY_MODES:
        raise ValueError(f"mode must be one of {QUALITY_MODES}")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    src = Path(image_path)
    if mode == "draft":
        meta = probe_image(src)
        pack = {
            "version": 1,
            "mode": mode,
            "source": meta,
            "maps": {},
            "palette": {},
            "part_grid": [],
        }
        dump_json(out / "sense_pack.json", pack)
        return pack

    work, work_img, meta = _ensure_png_workcopy(src, out)
    maps: dict = {}
    maps["matte"] = build_matte(work, out / "matte.png", source_image=work_img)
    maps["edges"] = build_edges(work, out / "edges.png", source_image=work_img)
    if mode in ("sharp", "razor", "hybrid"):
        maps["depth_proxy"] = build_depth_proxy(work, out / "depth_proxy.png", source_image=work_img)
    palette = extract_palette(work, source_image=work_img)
    # 3x3 part grid proposals from matte bbox
    bbox = maps["matte"]["bbox"]
    part_grid = []
    for gy in range(3):
        for gx in range(3):
            part_grid.append(
                {
                    "id": f"z{gy}{gx}",
                    "region": {
                        "x": bbox["x"] + bbox["w"] * gx / 3,
                        "y": bbox["y"] + bbox["h"] * gy / 3,
                        "w": bbox["w"] / 3,
                        "h": bbox["h"] / 3,
                        "units": "normalized",
                    },
                }
            )
    pack = {
        "version": 1,
        "mode": mode,
        "source": meta,
        "work_reference": str(work),
        "maps": maps,
        "palette": palette,
        "part_grid": part_grid,
        "advice": [
            "Author proportions from matte bbox aspect before freehand guesses.",
            "Use edge density to decide bevel/panel-line budget.",
            "Map palette colors to materials.baseColor and localOverrides.",
        ],
    }
    dump_json(out / "sense_pack.json", pack)
    return pack
