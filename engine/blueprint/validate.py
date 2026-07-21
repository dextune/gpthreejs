"""Validate Form Blueprint structure and strict fidelity rules."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.blueprint.schema import COMPLEXITY_LEDGER_MIN
from engine.shared.jsonutil import load_json


class ValidationResult:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {"ok": self.ok, "errors": self.errors, "warnings": self.warnings}


def _walk_parts(parts: list[dict], acc: list[dict] | None = None) -> list[dict]:
    acc = acc if acc is not None else []
    for p in parts:
        acc.append(p)
        _walk_parts(p.get("children") or [], acc)
    return acc


def validate_blueprint(path: str | Path, *, strict: bool = False) -> ValidationResult:
    res = ValidationResult()
    try:
        bp = load_json(path)
    except Exception as e:  # noqa: BLE001
        res.errors.append(f"cannot load: {e}")
        return res

    if bp.get("version") != 1:
        res.warnings.append("version != 1")
    if not bp.get("name"):
        res.errors.append("missing name")
    if not bp.get("parts"):
        res.errors.append("parts[] empty")
    if not bp.get("materials"):
        res.errors.append("materials[] empty")

    mat_ids = {m.get("id") for m in bp.get("materials") or []}
    parts = _walk_parts(bp.get("parts") or [])
    part_ids = {p.get("id") for p in parts}

    for p in parts:
        mid = p.get("materialId")
        if mid and mid not in mat_ids:
            res.errors.append(f"part {p.get('id')} materialId {mid} missing")
        if not p.get("geometry"):
            res.errors.append(f"part {p.get('id')} missing geometry")
        att = p.get("attachment")
        if att and att.get("parent") and att["parent"] not in part_ids:
            res.errors.append(f"part {p.get('id')} attachment parent missing")

    layers = bp.get("layers") or {}
    if not layers:
        res.errors.append("layers state missing")

    if not strict:
        return res

    # strict fidelity
    complexity = bp.get("complexity", "moderate")
    pact = bp.get("fidelityPact") or {}
    ledger_min = pact.get("ledgerMin") or COMPLEXITY_LEDGER_MIN.get(complexity, 6)
    ledger = bp.get("ledger") or {}
    entries = [e for e in ledger.get("entries") or [] if e.get("status") != "todo"]
    todos = [e for e in ledger.get("entries") or [] if e.get("status") == "todo"]
    if todos:
        res.errors.append(f"ledger still has {len(todos)} todo entries")
    if len(entries) < ledger_min:
        res.errors.append(f"ledger filled entries {len(entries)} < min {ledger_min}")

    # mapsTo linkage
    feature_ids = set()
    override_ids = set()
    for p in parts:
        for f in p.get("features") or []:
            if f.get("id"):
                feature_ids.add(f["id"])
    for m in bp.get("materials") or []:
        for o in m.get("overrides") or []:
            if o.get("id"):
                override_ids.add(o["id"])

    for e in entries:
        mt = e.get("mapsTo")
        if not mt:
            res.errors.append(f"ledger {e.get('id')} missing mapsTo")
            continue
        ref = mt.get("ref") if isinstance(mt, dict) else None
        kind = mt.get("type") if isinstance(mt, dict) else None
        if kind == "feature" and ref not in feature_ids:
            res.errors.append(f"ledger {e.get('id')} mapsTo feature {ref} not found")
        if kind == "override" and ref not in override_ids:
            res.errors.append(f"ledger {e.get('id')} mapsTo override {ref} not found")

    if complexity in ("complex", "ultra") and len(parts) < 2:
        res.errors.append("complex object needs more than one part")

    if bp.get("domain") in ("character", "hybrid"):
        if "proportion" not in layers and "landmarks" not in layers:
            res.warnings.append("character domain without proportion/landmarks layers")

    body = bp.get("bodySource", "procedural")
    if body not in ("procedural", "hybrid-glb"):
        res.errors.append(f"invalid bodySource {body}")
    if body == "hybrid-glb" and bp.get("qualityMode") != "hybrid":
        res.warnings.append("hybrid body without qualityMode=hybrid")

    return res


def summarize_layers(bp: dict[str, Any]) -> dict[str, Any]:
    layers = bp.get("layers") or {}
    open_layers = [k for k, v in layers.items() if v.get("status") == "open"]
    done = [k for k, v in layers.items() if v.get("status") == "done"]
    locked = [k for k, v in layers.items() if v.get("status") == "locked"]
    return {"open": open_layers, "done": done, "locked": locked, "order": list(layers.keys())}
