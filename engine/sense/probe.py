"""Image metadata probe + host capability report."""

from __future__ import annotations

import importlib.util
import os
import platform
from pathlib import Path

from engine.shared.pngio import read_png


def probe_image(path: str | Path) -> dict:
    p = Path(path)
    info: dict = {
        "path": str(p.resolve()),
        "exists": p.exists(),
        "bytes": p.stat().st_size if p.exists() else 0,
        "suffix": p.suffix.lower(),
    }
    if not p.exists():
        info["error"] = "missing"
        return info
    if p.suffix.lower() != ".png":
        info["note"] = "non-PNG: host image tools may still open it; engine PNG codecs need conversion first"
        return info
    try:
        img = read_png(p)
        info.update(
            {
                "width": img.width,
                "height": img.height,
                "aspect": round(img.width / max(1, img.height), 4),
                "megapixels": round(img.width * img.height / 1e6, 3),
            }
        )
        # rough exposure stats
        s = n = 0
        step = max(1, (img.width * img.height) // 5000)
        for i in range(0, len(img.rgba), 4 * step):
            s += img.rgba[i] + img.rgba[i + 1] + img.rgba[i + 2]
            n += 3
        mean = s / max(1, n)
        info["mean_luma_approx"] = round(mean, 1)
        if mean < 25:
            info["flags"] = ["very-dark"]
        elif mean > 230:
            info["flags"] = ["very-bright"]
        else:
            info["flags"] = []
    except Exception as e:  # noqa: BLE001
        info["error"] = str(e)
    return info


def probe_capabilities() -> dict:
    def has(mod: str) -> bool:
        return importlib.util.find_spec(mod) is not None

    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "modules": {
            "opencv": has("cv2"),
            "numpy": has("numpy"),
            "onnxruntime": has("onnxruntime"),
            "rembg": has("rembg"),
            "pillow": has("PIL"),
        },
        "recommended_workers": max(1, (os.cpu_count() or 2) - 1),
        "core_mode": "stdlib-only (always available)",
        "optional": "pip install -r engine/extras/requirements-cpu.txt for OpenCV/onnx",
    }
