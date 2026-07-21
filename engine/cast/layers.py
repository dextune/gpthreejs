"""Layer state machine for Form Blueprint."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.blueprint.validate import summarize_layers
from engine.shared.jsonutil import dump_json, load_json


def status(path: str | Path) -> dict[str, Any]:
    bp = load_json(path)
    return summarize_layers(bp)


def check(path: str | Path, layer: str) -> dict[str, Any]:
    bp = load_json(path)
    layers = bp.get("layers") or {}
    if layer not in layers:
        return {"ok": False, "error": f"unknown layer {layer}"}
    st = layers[layer].get("status")
    if st != "open":
        return {"ok": False, "error": f"layer {layer} is {st}, expected open"}
    return {"ok": True, "layer": layer, "status": st}


def sync(path: str | Path, *, in_place: bool = True) -> dict[str, Any]:
    """Advance layers: first open with accept in journal → done; unlock next."""
    bp = load_json(path)
    layers = bp.get("layers") or {}
    order = list(layers.keys())
    journal = bp.get("journal") or []

    accepted = {j["layer"] for j in journal if j.get("decision") == "accept"}

    for i, lid in enumerate(order):
        if lid in accepted:
            layers[lid]["status"] = "done"
            if i + 1 < len(order) and layers[order[i + 1]]["status"] == "locked":
                # unlock next only if all previous done
                if all(layers[order[j]]["status"] == "done" for j in range(i + 1)):
                    layers[order[i + 1]]["status"] = "open"
        elif layers[lid]["status"] == "done":
            continue
        else:
            # first non-done becomes open; rest locked
            if all(layers[order[j]]["status"] == "done" for j in range(i)):
                layers[lid]["status"] = "open"
                for k in range(i + 1, len(order)):
                    if layers[order[k]]["status"] != "done":
                        layers[order[k]]["status"] = "locked"
            break

    bp["layers"] = layers
    if in_place:
        dump_json(path, bp)
    return summarize_layers(bp)
