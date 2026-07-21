"""Canonical artifact serialization and content hashing."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from engine.shared.jsonutil import load_json

CANONICAL_JSON_ALGORITHM = "json-v1:sort-keys,separators,no-nan,utf8,newline"
SHA256_ALGORITHM = "sha256"


def canonical_json_text(value: Any) -> str:
    """Serialize JSON-compatible data with a stable byte representation."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"


def canonical_json_bytes(value: Any) -> bytes:
    """Return canonical UTF-8 bytes for JSON-compatible data."""

    return canonical_json_text(value).encode("utf-8")


def _without_paths(value: Any, ignored_paths: tuple[tuple[str, ...], ...]) -> Any:
    if not ignored_paths:
        return value

    cloned = deepcopy(value)
    for path in ignored_paths:
        current = cloned
        for key in path[:-1]:
            if not isinstance(current, dict) or key not in current:
                current = None
                break
            current = current[key]
        if isinstance(current, dict):
            current.pop(path[-1], None)
    return cloned


def content_hash(value: Any, *, ignored_paths: tuple[tuple[str, ...], ...] = ()) -> str:
    """Hash canonical JSON-compatible data with SHA-256."""

    payload = _without_paths(value, ignored_paths)
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def artifact_content_hash(path: str | Path, *, ignored_paths: tuple[tuple[str, ...], ...] = ()) -> str:
    """Load a JSON artifact and hash its canonical content."""

    return content_hash(load_json(path), ignored_paths=ignored_paths)


def blueprint_revision_content_hash(blueprint: dict[str, Any]) -> str:
    """Hash a Blueprint while excluding the self-referential revision hash field."""

    return content_hash(blueprint, ignored_paths=(("revision", "contentHash"),))
