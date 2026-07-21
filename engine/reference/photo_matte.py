"""Build external reference alpha mattes from photos (not blueprint self-render)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.sense.matte import build_matte, matte_heuristic
from engine.shared.pngio import Image, read_png, resize_nearest, write_png


def matte_alpha_from_image(
    image_path: str | Path,
    out_path: str | Path,
    *,
    width: int | None = None,
    height: int | None = None,
) -> dict[str, Any]:
    """
    Write an alpha PNG derived from a reference photo matte.

    This is the delivery-grade silhouette target: never a re-render of the Blueprint.
    """

    image_path = Path(image_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Prefer build_matte (may use rembg); falls back to corner heuristic.
    tmp = out_path.with_suffix(".raw-matte.png")
    meta = build_matte(image_path, tmp)
    matte = read_png(tmp)
    if width and height and (matte.width != width or matte.height != height):
        matte = resize_nearest(matte, width, height)
    # Ensure output is alpha silhouette (opaque where subject)
    alpha_only = Image(matte.width, matte.height, bytearray(matte.width * matte.height * 4))
    for y in range(matte.height):
        for x in range(matte.width):
            a = matte.pixel(x, y)[3]
            if a > 128:
                alpha_only.set_pixel(x, y, (255, 255, 255, 255))
            else:
                alpha_only.set_pixel(x, y, (0, 0, 0, 0))
    write_png(out_path, alpha_only)
    tmp.unlink(missing_ok=True)
    return {
        "path": str(out_path),
        "sourceImage": str(image_path),
        "method": meta.get("method") or "matte",
        "width": alpha_only.width,
        "height": alpha_only.height,
        "external": True,
        "selfBaseline": False,
    }


def resolve_reference_alpha_map(
    *,
    project: dict[str, Any],
    project_dir: Path,
    out_dir: Path,
    reference_set_path: Path | None = None,
    view_id: str = "source-34",
    width: int = 128,
    height: int = 128,
) -> dict[str, Any]:
    """
    Resolve EXTERNAL reference alpha paths for metrics.

    Priority:
      1. project.referenceAlphaPath (file)
      2. project.referenceAlphaMap[view]
      3. ReferenceSet primary image → photo matte
      4. sense pack matte.png next to reference if present

    Does NOT synthesize blueprint self-render. Returns empty map if none found.
    """

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, str] = {}
    meta: dict[str, Any] = {"external": False, "sources": {}}

    # 1) explicit path
    raw = project.get("referenceAlphaPath")
    if raw:
        p = Path(str(raw))
        if not p.is_absolute():
            p = project_dir / p
        if p.is_file():
            dest = out_dir / f"{view_id}-ref-alpha.png"
            # copy/normalize size
            img = read_png(p)
            if img.width != width or img.height != height:
                img = resize_nearest(img, width, height)
            write_png(dest, img)
            result[view_id] = str(dest)
            meta["external"] = True
            meta["sources"][view_id] = {"kind": "project.referenceAlphaPath", "path": str(p)}
            return {"map": result, "meta": meta}

    # 2) map of views
    amap = project.get("referenceAlphaMap") or {}
    if isinstance(amap, dict) and amap:
        for vid, path in amap.items():
            p = Path(str(path))
            if not p.is_absolute():
                p = project_dir / p
            if p.is_file():
                dest = out_dir / f"{vid}-ref-alpha.png"
                img = read_png(p)
                if img.width != width or img.height != height:
                    img = resize_nearest(img, width, height)
                write_png(dest, img)
                result[str(vid)] = str(dest)
                meta["sources"][str(vid)] = {"kind": "project.referenceAlphaMap", "path": str(p)}
        if result:
            meta["external"] = True
            return {"map": result, "meta": meta}

    # 3) ReferenceSet images → photo mattes
    if reference_set_path and Path(reference_set_path).is_file():
        from engine.reference.reference_set import parse_reference_set
        from engine.reference.views import normalize_view_token

        refset = parse_reference_set(reference_set_path, check_files=False)
        base = Path(reference_set_path).parent
        for ref in refset.get("references") or []:
            view = normalize_view_token(ref.get("detectedView") or ref.get("declaredView")) or "unknown"
            img_path = Path(str(ref.get("path") or ""))
            if not img_path.is_absolute():
                img_path = base / img_path
            if not img_path.is_file():
                continue
            # prefer sense matte if linked
            sense = ref.get("sensePack")
            matte_candidate = None
            if sense:
                sp = Path(str(sense))
                if sp.is_file():
                    cand = sp.parent / "matte.png"
                    if cand.is_file():
                        matte_candidate = cand
                elif sp.is_dir() and (sp / "matte.png").is_file():
                    matte_candidate = sp / "matte.png"
            dest = out_dir / f"{view}-ref-alpha.png"
            if matte_candidate:
                img = read_png(matte_candidate)
                if img.width != width or img.height != height:
                    img = resize_nearest(img, width, height)
                # force alpha-only
                alpha_only = Image(img.width, img.height, bytearray(img.width * img.height * 4))
                for y in range(img.height):
                    for x in range(img.width):
                        a = img.pixel(x, y)[3]
                        alpha_only.set_pixel(
                            x, y, (255, 255, 255, 255) if a > 128 else (0, 0, 0, 0)
                        )
                write_png(dest, alpha_only)
                meta["sources"][view] = {
                    "kind": "sense.matte",
                    "path": str(matte_candidate),
                }
            else:
                info = matte_alpha_from_image(img_path, dest, width=width, height=height)
                meta["sources"][view] = {
                    "kind": "photo.matte",
                    "path": str(img_path),
                    "method": info.get("method"),
                }
            result[view] = str(dest)
        # alias source-aligned
        if "source-34" not in result and "front" in result:
            result["source-34"] = result["front"]
        if result:
            meta["external"] = True
            return {"map": result, "meta": meta}

    return {"map": {}, "meta": meta}
