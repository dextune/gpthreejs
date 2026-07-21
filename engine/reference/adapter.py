"""Adapters that wrap single-image CLI inputs as a ReferenceSet."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.reference.reference_set import (
    build_reference_entry,
    build_reference_set,
    write_reference_set,
)
from engine.sense.sufficiency import assess_sufficiency


def single_image_to_reference_set(
    image: str | Path,
    *,
    declared_view: str = "source-34",
    evidence_class: str = "observed",
    ref_id: str = "ref-source",
    visible_features: list[str] | None = None,
    sense_pack: str | None = None,
    out: str | Path | None = None,
) -> dict[str, Any]:
    """Wrap a single reference image into a one-entry ReferenceSet."""

    image_path = Path(image)
    entry = build_reference_entry(
        ref_id=ref_id,
        path=image_path.name if out else str(image_path),
        declared_view=declared_view,
        evidence_class=evidence_class,
        visible_features=visible_features,
        sense_pack=sense_pack,
        base_dir=image_path.parent if out else None,
    )
    if out is None:
        # Keep absolute path so hash and later consumers can open the file.
        entry["path"] = str(image_path.resolve())
        entry["assetHash"] = build_reference_entry(
            ref_id=ref_id,
            path=image_path.resolve(),
            declared_view=declared_view,
            evidence_class=evidence_class,
        )["assetHash"]
    else:
        # When writing beside the image, re-hash using the image path.
        entry = build_reference_entry(
            ref_id=ref_id,
            path=image_path.name,
            declared_view=declared_view,
            evidence_class=evidence_class,
            visible_features=visible_features,
            sense_pack=sense_pack,
            base_dir=image_path.parent,
        )
        # Prefer absolute path for portability of the written set.
        entry["path"] = str(image_path.resolve())

    reference_set = build_reference_set([entry])
    if out is not None:
        write_reference_set(out, reference_set)
    return reference_set


def assess_sufficiency_from_reference_set(
    reference_set: dict[str, Any],
    *,
    primary_index: int = 0,
    domain: str | None = None,
    intent: str | None = None,
    view_count: int | None = None,
    has_side: bool | None = None,
    has_back: bool | None = None,
    sense_path: str | Path | None = None,
    ledger_path: str | Path | None = None,
    blueprint_path: str | Path | None = None,
    brief_path: str | Path | None = None,
    out: str | Path | None = None,
) -> dict[str, Any]:
    """Run the existing single-image sufficiency gate using ReferenceSet metadata."""

    refs = reference_set.get("references") or []
    if not refs:
        raise ValueError("ReferenceSet has no references")
    primary = refs[primary_index]
    image = primary["path"]

    views = [str(r.get("detectedView") or r.get("declaredView") or "") for r in refs]
    derived_view_count = len({v for v in views if v})
    side_tokens = ("left", "right", "side")
    derived_has_side = any(any(token in v for token in side_tokens) for v in views)
    derived_has_back = any("back" in v for v in views)

    report = assess_sufficiency(
        image,
        sense_path=sense_path or primary.get("sensePack"),
        brief_path=brief_path,
        ledger_path=ledger_path,
        blueprint_path=blueprint_path,
        domain=domain,
        intent=intent,
        view_count=view_count if view_count is not None else max(1, derived_view_count),
        has_side=has_side if has_side is not None else derived_has_side,
        has_back=has_back if has_back is not None else derived_has_back,
        out=out,
    )
    report["referenceSet"] = {
        "referenceCount": len(refs),
        "views": views,
        "primaryId": primary.get("id"),
    }
    return report
