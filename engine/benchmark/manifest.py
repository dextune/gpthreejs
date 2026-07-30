"""Benchmark manifest schema and validation.

A benchmark manifest declares a set of fixtures with provenance, expected
routes, and pass/fail criteria. It is the contract for repeatable quality
measurement.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


MANIFEST_SCHEMA_VERSION = 1

FIXTURE_REQUIRED_FIELDS = (
    "id",
    "category",
    "profile",
    "source",
    "views",
    "heldOutViews",
    "requiredPasses",
    "expectedRoute",
)

SOURCE_REQUIRED_FIELDS = (
    "type",
    "license",
    "provenance",
)

SOURCE_TYPES = (
    "repo-local-sample",
    "repo-generated",
    "external-permissive",
    "external-restricted",
    "synthetic-known-scene",
)

CATEGORIES = (
    "character",
    "hard-surface",
    "generic-prop",
    "camera-calibration",
    "appearance-isolation",
)

PROFILES = (
    "stylized-character",
    "hard-surface-hero",
    "generic-prop",
)

VIEW_REQUIRED_FIELDS = (
    "id",
    "role",
)

VIEW_ROLES = (
    "primary",
    "held-out",
    "detail",
    "turnaround",
)


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    """Validate a benchmark manifest. Returns a list of error strings (empty = valid)."""
    errors: list[str] = []

    if not isinstance(manifest, dict):
        return ["$: expected object"]

    # Top-level fields
    if "schemaVersion" not in manifest:
        errors.append("$.schemaVersion: missing required field")
    elif manifest["schemaVersion"] != MANIFEST_SCHEMA_VERSION:
        errors.append(
            f"$.schemaVersion: expected {MANIFEST_SCHEMA_VERSION}, "
            f"got {manifest['schemaVersion']!r}"
        )

    if "fixtures" not in manifest:
        errors.append("$.fixtures: missing required field")
        return errors

    fixtures = manifest["fixtures"]
    if not isinstance(fixtures, list):
        errors.append("$.fixtures: expected array")
        return errors

    if not fixtures:
        errors.append("$.fixtures: at least one fixture is required")
        return errors

    # Duplicate ID check
    seen_ids: set[str] = set()
    for index, fixture in enumerate(fixtures):
        path = f"$.fixtures[{index}]"
        if not isinstance(fixture, dict):
            errors.append(f"{path}: expected object")
            continue

        fid = fixture.get("id")
        if fid is None:
            errors.append(f"{path}.id: missing required field")
        elif not isinstance(fid, str) or not fid.strip():
            errors.append(f"{path}.id: expected non-empty string")
        else:
            if fid in seen_ids:
                errors.append(f"{path}.id: duplicate fixture id {fid!r}")
            seen_ids.add(fid)

        errors.extend(_validate_fixture(fixture, path))

    return errors


def _validate_fixture(fixture: dict[str, Any], path: str) -> list[str]:
    """Validate a single fixture entry."""
    errors: list[str] = []

    for field in FIXTURE_REQUIRED_FIELDS:
        if field not in fixture:
            errors.append(f"{path}.{field}: missing required field")

    # Category
    category = fixture.get("category")
    if category is not None and category not in CATEGORIES:
        errors.append(
            f"{path}.category: unsupported category {category!r}; "
            f"expected one of {CATEGORIES}"
        )

    # Profile
    profile = fixture.get("profile")
    if profile is not None and profile not in PROFILES:
        errors.append(
            f"{path}.profile: unsupported profile {profile!r}; "
            f"expected one of {PROFILES}"
        )

    # Source validation
    source = fixture.get("source")
    if source is not None:
        errors.extend(_validate_source(source, f"{path}.source"))

    # Views validation
    views = fixture.get("views")
    if views is not None:
        if not isinstance(views, list):
            errors.append(f"{path}.views: expected array")
        elif not views:
            errors.append(f"{path}.views: at least one view is required")
        else:
            for vi, view in enumerate(views):
                errors.extend(_validate_view(view, f"{path}.views[{vi}]"))

    # Held-out views (optional but validated if present)
    held_out = fixture.get("heldOutViews")
    if held_out is not None:
        if not isinstance(held_out, list):
            errors.append(f"{path}.heldOutViews: expected array")
        else:
            for vi, view in enumerate(held_out):
                errors.extend(_validate_view(view, f"{path}.heldOutViews[{vi}]"))

    # Expected route (optional but validated if present)
    route = fixture.get("expectedRoute")
    if route is not None and not isinstance(route, str):
        errors.append(f"{path}.expectedRoute: expected string")

    # Required passes (optional but validated if present)
    passes = fixture.get("requiredPasses")
    if passes is not None:
        if not isinstance(passes, list):
            errors.append(f"{path}.requiredPasses: expected array")
        elif not all(isinstance(p, str) for p in passes):
            errors.append(f"{path}.requiredPasses: expected array of strings")

    return errors


def _validate_source(source: dict[str, Any], path: str) -> list[str]:
    """Validate a fixture source block."""
    errors: list[str] = []

    if not isinstance(source, dict):
        errors.append(f"{path}: expected object")
        return errors

    for field in SOURCE_REQUIRED_FIELDS:
        if field not in source:
            errors.append(f"{path}.{field}: missing required field")

    source_type = source.get("type")
    if source_type is not None and source_type not in SOURCE_TYPES:
        errors.append(
            f"{path}.type: unsupported source type {source_type!r}; "
            f"expected one of {SOURCE_TYPES}"
        )

    license_val = source.get("license")
    if license_val is not None and not isinstance(license_val, str):
        errors.append(f"{path}.license: expected string")

    provenance = source.get("provenance")
    if provenance is not None and not isinstance(provenance, str):
        errors.append(f"{path}.provenance: expected string")

    return errors


def _validate_view(view: dict[str, Any], path: str) -> list[str]:
    """Validate a view entry."""
    errors: list[str] = []

    if not isinstance(view, dict):
        errors.append(f"{path}: expected object")
        return errors

    for field in VIEW_REQUIRED_FIELDS:
        if field not in view:
            errors.append(f"{path}.{field}: missing required field")

    role = view.get("role")
    if role is not None and role not in VIEW_ROLES:
        errors.append(
            f"{path}.role: unsupported view role {role!r}; "
            f"expected one of {VIEW_ROLES}"
        )

    return errors


def parse_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate and return a normalized manifest. Raises ValueError on errors."""
    errors = validate_manifest(manifest)
    if errors:
        raise ValueError(
            f"Benchmark manifest validation failed with {len(errors)} error(s):\n"
            + "\n".join(f"  - {e}" for e in errors)
        )
    return deepcopy(manifest)


def manifest_schema() -> dict[str, Any]:
    """Return a JSON-schema-shaped descriptor for documentation."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://gpthreejs.local/contracts/benchmark-manifest.schema.json",
        "title": "gpthreejs Benchmark Manifest",
        "type": "object",
        "required": ["schemaVersion", "fixtures"],
        "properties": {
            "schemaVersion": {"const": MANIFEST_SCHEMA_VERSION},
            "fixtures": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": list(FIXTURE_REQUIRED_FIELDS),
                },
            },
        },
    }
