"""Foreground matte via chroma/luma heuristics (stdlib). Optional rembg if installed."""

from __future__ import annotations

from pathlib import Path

from engine.shared.pngio import Image, read_png, write_png


def _corner_bg_color(img: Image) -> tuple[int, int, int]:
    samples = [
        img.pixel(0, 0),
        img.pixel(img.width - 1, 0),
        img.pixel(0, img.height - 1),
        img.pixel(img.width - 1, img.height - 1),
        img.pixel(img.width // 2, 0),
        img.pixel(0, img.height // 2),
    ]
    rs = sum(s[0] for s in samples) // len(samples)
    gs = sum(s[1] for s in samples) // len(samples)
    bs = sum(s[2] for s in samples) // len(samples)
    return rs, gs, bs


def matte_heuristic(img: Image, threshold: int = 42) -> Image:
    """Simple distance-to-corner-background matte. Good enough for product shots."""
    br, bg, bb = _corner_bg_color(img)
    src = img.rgba
    dst = bytearray(len(src))
    soft_min = threshold - 12
    for i in range(0, len(src), 4):
        r, g, b, a = src[i], src[i + 1], src[i + 2], src[i + 3]
        dist = abs(r - br) + abs(g - bg) + abs(b - bb)
        alpha = 255 if dist >= threshold else 0
        if soft_min <= dist < threshold:
            alpha = int(255 * (dist - soft_min) / 12)
        dst[i] = r
        dst[i + 1] = g
        dst[i + 2] = b
        dst[i + 3] = alpha if a > 0 else 0
    return Image(img.width, img.height, dst)


def matte_optional_rembg(path: Path) -> Image | None:
    try:
        from rembg import remove  # type: ignore
    except Exception:
        return None
    try:
        from engine.shared.pngio import read_png, write_png
        import tempfile

        raw = path.read_bytes()
        cut = remove(raw)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(cut)
            tmp_path = Path(tmp.name)
        img = read_png(tmp_path)
        tmp_path.unlink(missing_ok=True)
        return img
    except Exception:
        return None


def build_matte(
    image_path: str | Path,
    out_path: str | Path,
    *,
    source_image: Image | None = None,
) -> dict:
    path = Path(image_path)
    img = source_image or (read_png(path) if path.suffix.lower() == ".png" else None)
    if img is None:
        raise ValueError("matte builder requires PNG input (convert first)")
    rem = matte_optional_rembg(path)
    method = "rembg" if rem is not None else "corner-distance"
    result = rem if rem is not None else matte_heuristic(img)
    write_png(out_path, result)
    # bbox of opaque
    minx, miny, maxx, maxy = result.width, result.height, 0, 0
    opaque = 0
    rgba = result.rgba
    for y in range(result.height):
        row = y * result.width
        for x in range(result.width):
            if rgba[(row + x) * 4 + 3] > 128:
                opaque += 1
                minx, miny = min(minx, x), min(miny, y)
                maxx, maxy = max(maxx, x), max(maxy, y)
    area = result.width * result.height
    if opaque == 0:
        bbox = {"x": 0, "y": 0, "w": 1, "h": 1, "units": "normalized"}
    else:
        bbox = {
            "x": minx / result.width,
            "y": miny / result.height,
            "w": (maxx - minx + 1) / result.width,
            "h": (maxy - miny + 1) / result.height,
            "units": "normalized",
        }
    return {
        "method": method,
        "path": str(out_path),
        "foreground_ratio": round(opaque / max(1, area), 4),
        "bbox": bbox,
    }
