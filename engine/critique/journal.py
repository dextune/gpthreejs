"""Append critique journal entries to a blueprint."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from engine.blueprint.schema import DECISIONS
from engine.critique.metrics import floors_pass
from engine.shared.jsonutil import dump_json, load_json


def load_metrics_file(path: str | Path | None) -> dict:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    return load_json(p)


def append_journal(
    blueprint_path: str | Path,
    *,
    layer: str,
    fidelity: float,
    decision: str,
    vision: float,
    summary: str,
    metrics_path: str | Path | None = None,
    render: str | None = None,
    sheet: str | None = None,
    feature_scores: dict | None = None,
    in_place: bool = True,
) -> dict[str, Any]:
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of {DECISIONS}")
    bp = load_json(blueprint_path)
    metrics = load_metrics_file(metrics_path)
    floors = (bp.get("fidelityPact") or {}).get("metricFloors") or {}
    ok_m, fails = floors_pass(metrics, floors) if metrics else (True, [])

    # vision / feature floors
    if decision == "accept":
        thr = floors.get("vision", 0.7)
        if vision < thr:
            raise SystemExit(f"cannot accept: vision {vision} < {thr}")
        mode = bp.get("qualityMode", "sharp")
        if mode in ("solid", "sharp", "razor", "hybrid") and metrics and not ok_m:
            raise SystemExit(f"cannot accept: metric floors failed: {fails}")
        for feat in bp.get("criticalFeatures") or []:
            if feat.get("layer") != layer:
                continue
            fs = (feature_scores or {}).get(feat["id"])
            if fs is not None and fs < feat.get("floor", 0.7):
                raise SystemExit(
                    f"cannot accept: feature {feat['id']} score {fs} < {feat.get('floor')}"
                )

    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "layer": layer,
        "fidelity": fidelity,
        "vision": vision,
        "decision": decision,
        "summary": summary,
        "metrics": metrics,
        "metricFloorFails": fails,
        "render": render,
        "sheet": sheet,
        "featureScores": feature_scores or {},
    }
    bp.setdefault("journal", []).append(entry)
    if layer in (bp.get("layers") or {}):
        bp["layers"][layer].setdefault("reviews", []).append(entry)
    if in_place:
        dump_json(blueprint_path, bp)
    return entry
