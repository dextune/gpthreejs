"""Feature Ledger validation shared by Blueprint versions."""

from __future__ import annotations

from typing import Any

CHARACTER_LEDGER_CATEGORIES = (
    "silhouette-proportion",
    "head-face-helmet",
    "torso-layering",
    "limb-asymmetry",
    "held-worn-equipment",
    "lower-body-feet",
    "material-roles",
    "attachment-relationships",
)


def _feature_ids(parts: list[dict[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for part in parts:
        for feature in part.get("features") or []:
            if feature.get("id"):
                ids.add(feature["id"])
    return ids


def _override_ids(materials: list[dict[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for material in materials:
        for override in material.get("overrides") or []:
            if override.get("id"):
                ids.add(override["id"])
    return ids


def _entry_category(entry: dict[str, Any]) -> str | None:
    raw = entry.get("category") or entry.get("coverageCategory")
    if raw:
        return str(raw)
    return None


def validate_character_ledger_coverage(
    entries: list[dict[str, Any]],
    *,
    path: str = "$.ledger",
) -> list[str]:
    """Return errors when stylized-character category coverage is incomplete."""

    filled = [entry for entry in entries if entry.get("status") != "todo"]
    present = {_entry_category(entry) for entry in filled}
    missing = [category for category in CHARACTER_LEDGER_CATEGORIES if category not in present]
    if missing:
        return [f"{path}.entries[].category: missing character coverage categories {missing}"]
    return []


def validate_ledger_production_gate(
    ledger: dict[str, Any],
    *,
    path: str = "$",
    modeling_profile: str | None = None,
) -> list[str]:
    """
    Production ledger gate (REF-130/131):

    - no TODO entries in production mode
    - entry count >= targetMin
    - character profiles require global/meso/micro category coverage
    """

    errors: list[str] = []
    entries = ledger.get("entries") or []
    target_min = int(ledger.get("targetMin") or 0)
    mode = ledger.get("mode") or "production"
    profile = modeling_profile or ledger.get("modelingProfile") or "generic-prop"

    if mode == "production":
        todos = [e for e in entries if e.get("status") == "todo"]
        if todos:
            errors.append(f"{path}.entries: production ledger forbids TODO stubs ({len(todos)} found)")
        filled = [e for e in entries if e.get("status") != "todo"]
        if len(filled) < target_min:
            errors.append(
                f"{path}.entries: expected at least targetMin={target_min} real entries, got {len(filled)}"
            )
        for index, entry in enumerate(entries):
            entry_path = f"{path}.entries[{index}]"
            for field in ("id", "kind", "description", "region", "scale", "affects", "confidence", "status"):
                if field not in entry:
                    errors.append(f"{entry_path}.{field}: missing required field")
            if "evidenceRefs" not in entry:
                errors.append(f"{entry_path}.evidenceRefs: missing required field")

    if profile == "stylized-character" or ledger.get("requireCharacterCoverage"):
        errors.extend(validate_character_ledger_coverage(entries, path=path))

    return errors


def validate_ledger_contract(
    blueprint: dict[str, Any],
    parts: list[dict[str, Any]],
    errors: list[str],
    *,
    path: str = "$.ledger",
    require_character_coverage: bool = False,
) -> None:
    """Validate strict ledger linkage and optional character coverage."""

    ledger = blueprint.get("ledger") or {}
    entries = ledger.get("entries") or []
    feature_ids = _feature_ids(parts)
    override_ids = _override_ids(blueprint.get("materials") or [])
    part_ids = {part.get("id") for part in parts if part.get("id")}
    filled_entries = [entry for entry in entries if entry.get("status") != "todo"]

    for index, entry in enumerate(filled_entries):
        entry_path = f"{path}.entries[{index}]"
        maps_to = entry.get("mapsTo")
        if maps_to in (None, "unresolved"):
            errors.append(f"{entry_path}.mapsTo: unresolved ledger mapping")
            continue
        if not isinstance(maps_to, dict):
            errors.append(f"{entry_path}.mapsTo: expected object mapping")
            continue

        ref = maps_to.get("ref")
        target_type = maps_to.get("type")
        if target_type == "feature":
            if ref not in feature_ids:
                errors.append(f"{entry_path}.mapsTo.ref: feature {ref!r} not found")
        elif target_type == "override":
            if ref not in override_ids:
                errors.append(f"{entry_path}.mapsTo.ref: override {ref!r} not found")
        elif target_type == "part":
            if ref not in part_ids:
                errors.append(f"{entry_path}.mapsTo.ref: part {ref!r} not found")
        else:
            errors.append(f"{entry_path}.mapsTo.type: unsupported target type {target_type!r}")

    if not require_character_coverage:
        return

    errors.extend(validate_character_ledger_coverage(filled_entries, path=path))
