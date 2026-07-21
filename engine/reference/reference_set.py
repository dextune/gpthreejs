"""ReferenceSet manifest and provenance contract."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path
from typing import Any

from engine.shared.artifacts import content_hash
from engine.shared.jsonutil import dump_json, load_json

REFERENCE_SET_SCHEMA_VERSION = 1
EVIDENCE_CLASSES = (
    "observed",
    "design-intent",
    "design-hypothesis",
    "inferred",
)
REFERENCE_REQUIRED_FIELDS = (
    "id",
    "path",
    "assetHash",
    "declaredView",
    "evidenceClass",
)
REFERENCE_SET_REQUIRED_FIELDS = ("schemaVersion", "references")


class ReferenceSetError(ValueError):
    """Raised when a ReferenceSet cannot be parsed or validated."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


def reference_set_schema() -> dict[str, Any]:
    return deepcopy(_REFERENCE_SET_SCHEMA)


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_reference_set(
    reference_set: dict[str, Any],
    *,
    base_dir: str | Path | None = None,
    check_files: bool = False,
) -> list[str]:
    errors: list[str] = []
    for field in REFERENCE_SET_REQUIRED_FIELDS:
        if field not in reference_set:
            errors.append(f"$.{field}: missing required field")

    if reference_set.get("schemaVersion") != REFERENCE_SET_SCHEMA_VERSION:
        errors.append("$.schemaVersion: expected 1")

    refs = reference_set.get("references")
    if refs is None:
        return errors
    if not isinstance(refs, list):
        errors.append("$.references: expected array")
        return errors
    if not refs:
        errors.append("$.references: at least one reference is required")

    seen_ids: set[str] = set()
    base = Path(base_dir) if base_dir else None
    for index, ref in enumerate(refs):
        path = f"$.references[{index}]"
        if not isinstance(ref, dict):
            errors.append(f"{path}: expected object")
            continue
        for field in REFERENCE_REQUIRED_FIELDS:
            if field not in ref:
                errors.append(f"{path}.{field}: missing required field")

        ref_id = ref.get("id")
        if isinstance(ref_id, str) and ref_id:
            if ref_id in seen_ids:
                errors.append(f"{path}.id: duplicate reference id {ref_id!r}")
            seen_ids.add(ref_id)
        elif "id" in ref:
            errors.append(f"{path}.id: expected non-empty string")

        evidence = ref.get("evidenceClass")
        if evidence is not None and evidence not in EVIDENCE_CLASSES:
            errors.append(f"{path}.evidenceClass: unsupported class {evidence!r}")

        # Generated/hypothesized views may never be promoted to observed.
        if evidence == "observed":
            origin = ref.get("origin") or ref.get("generationOrigin")
            if origin in ("generated", "edited", "provider"):
                errors.append(
                    f"{path}.evidenceClass: generated/edited assets cannot be classed as observed"
                )

        if check_files and ref.get("path"):
            asset_path = Path(str(ref["path"]))
            if not asset_path.is_absolute() and base is not None:
                asset_path = base / asset_path
            if not asset_path.exists():
                errors.append(f"{path}.path: file not found {asset_path}")
            elif ref.get("assetHash"):
                actual = file_sha256(asset_path)
                if actual != ref["assetHash"]:
                    errors.append(
                        f"{path}.assetHash: mismatch expected {ref['assetHash']}, got {actual}"
                    )

        visible = ref.get("visibleFeatures")
        if visible is not None and not isinstance(visible, list):
            errors.append(f"{path}.visibleFeatures: expected array")

    return errors


def parse_reference_set(
    path: str | Path,
    *,
    check_files: bool = False,
) -> dict[str, Any]:
    data = load_json(path)
    if not isinstance(data, dict):
        raise ReferenceSetError(["$: expected object"])
    errors = validate_reference_set(
        data,
        base_dir=Path(path).parent,
        check_files=check_files,
    )
    if errors:
        raise ReferenceSetError(errors)
    return data


def build_reference_entry(
    *,
    ref_id: str,
    path: str | Path,
    declared_view: str,
    evidence_class: str = "observed",
    detected_view: str | None = None,
    visible_features: list[str] | None = None,
    sense_pack: str | None = None,
    origin: str | None = None,
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
    asset = Path(path)
    hash_path = asset
    if not asset.is_absolute() and base_dir is not None:
        hash_path = Path(base_dir) / asset
    entry: dict[str, Any] = {
        "id": ref_id,
        "path": str(path),
        "assetHash": file_sha256(hash_path) if hash_path.exists() else "",
        "declaredView": declared_view,
        "detectedView": detected_view or declared_view,
        "evidenceClass": evidence_class,
        "visibleFeatures": list(visible_features or []),
    }
    if sense_pack:
        entry["sensePack"] = sense_pack
    if origin:
        entry["origin"] = origin
    return entry


def build_reference_set(references: list[dict[str, Any]]) -> dict[str, Any]:
    payload = {
        "schemaVersion": REFERENCE_SET_SCHEMA_VERSION,
        "references": references,
        "contentHash": "",
    }
    payload["contentHash"] = content_hash(payload, ignored_paths=(("contentHash",),))
    return payload


def write_reference_set(path: str | Path, reference_set: dict[str, Any]) -> dict[str, Any]:
    errors = validate_reference_set(reference_set)
    if errors:
        raise ReferenceSetError(errors)
    dump_json(path, reference_set)
    return reference_set


_REFERENCE_SET_SCHEMA = {
    "title": "gpthreejs ReferenceSet",
    "type": "object",
    "required": list(REFERENCE_SET_REQUIRED_FIELDS),
    "properties": {
        "schemaVersion": {"const": REFERENCE_SET_SCHEMA_VERSION},
        "references": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": list(REFERENCE_REQUIRED_FIELDS),
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "path": {"type": "string", "minLength": 1},
                    "assetHash": {"type": "string"},
                    "declaredView": {"type": "string"},
                    "detectedView": {"type": "string"},
                    "evidenceClass": {"type": "string", "enum": list(EVIDENCE_CLASSES)},
                    "visibleFeatures": {"type": "array", "items": {"type": "string"}},
                    "sensePack": {"type": "string"},
                    "origin": {"type": "string"},
                },
            },
        },
        "contentHash": {"type": "string"},
    },
}
