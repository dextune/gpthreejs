"""Manifest-derived view classification and coverage."""

from __future__ import annotations

from typing import Any


VIEW_ALIASES = {
    "source": "source-34",
    "source34": "source-34",
    "source-3/4": "source-34",
    "3/4": "source-34",
    "front": "front",
    "fwd": "front",
    "left": "left",
    "right": "right",
    "side": "left",
    "back": "back",
    "rear": "back",
    "top": "top",
    "top-34": "top-34",
    "top34": "top-34",
}


def normalize_view_token(view: str | None) -> str | None:
    if view is None:
        return None
    key = str(view).strip().lower().replace(" ", "-")
    return VIEW_ALIASES.get(key, key)


def classify_reference_views(reference_set: dict[str, Any]) -> dict[str, Any]:
    """Derive view coverage from ReferenceSet entries."""

    refs = reference_set.get("references") or []
    classified: list[dict[str, Any]] = []
    conflicts: list[str] = []
    coverage: dict[str, list[str]] = {}

    for ref in refs:
        declared = normalize_view_token(ref.get("declaredView"))
        detected = normalize_view_token(ref.get("detectedView") or declared)
        if declared and detected and declared != detected:
            conflicts.append(
                f"reference {ref.get('id')}: declaredView={declared} conflicts with detectedView={detected}"
            )
        view = detected or declared or "unknown"
        coverage.setdefault(view, []).append(str(ref.get("id")))
        classified.append(
            {
                "id": ref.get("id"),
                "declaredView": declared,
                "detectedView": detected,
                "effectiveView": view,
                "evidenceClass": ref.get("evidenceClass"),
            }
        )

    unique_views = sorted(coverage.keys())
    return {
        "schemaVersion": 1,
        "views": classified,
        "coverage": {view: ids for view, ids in sorted(coverage.items())},
        "uniqueViews": unique_views,
        "viewCount": len(unique_views),
        "hasSide": any(v in unique_views for v in ("left", "right")),
        "hasBack": "back" in unique_views,
        "hasFront": "front" in unique_views or "source-34" in unique_views,
        "conflicts": conflicts,
        "warnings": list(conflicts),
    }


def resolve_view_flags(
    reference_set: dict[str, Any],
    *,
    cli_view_count: int | None = None,
    cli_has_side: bool | None = None,
    cli_has_back: bool | None = None,
) -> dict[str, Any]:
    """
    Prefer manifest-derived evidence over CLI flags.

    When CLI and manifest disagree, manifest wins and a warning is recorded.
    """

    derived = classify_reference_views(reference_set)
    warnings = list(derived.get("warnings") or [])

    view_count = derived["viewCount"]
    has_side = derived["hasSide"]
    has_back = derived["hasBack"]

    if cli_view_count is not None and cli_view_count != view_count:
        warnings.append(
            f"CLI view_count={cli_view_count} overridden by manifest viewCount={view_count}"
        )
    if cli_has_side is not None and cli_has_side != has_side:
        warnings.append(
            f"CLI has_side={cli_has_side} overridden by manifest hasSide={has_side}"
        )
    if cli_has_back is not None and cli_has_back != has_back:
        warnings.append(
            f"CLI has_back={cli_has_back} overridden by manifest hasBack={has_back}"
        )

    return {
        "viewCount": view_count,
        "hasSide": has_side,
        "hasBack": has_back,
        "hasFront": derived["hasFront"],
        "coverage": derived["coverage"],
        "uniqueViews": derived["uniqueViews"],
        "warnings": warnings,
        "source": "manifest",
    }


def feature_coverage(
    reference_set: dict[str, Any],
    must_have: list[dict[str, Any]],
) -> dict[str, Any]:
    """Weighted feature coverage across references using visibleFeatures."""

    refs = reference_set.get("references") or []
    visibility: dict[str, float] = {}
    for feature in must_have:
        fid = str(feature.get("id"))
        weight = float(feature.get("weight") or 0)
        best = 0.0
        for ref in refs:
            visible = set(ref.get("visibleFeatures") or [])
            if fid in visible:
                # observed evidence counts fully; inferred/generated discounted.
                cls = ref.get("evidenceClass") or "observed"
                score = 1.0 if cls == "observed" else 0.6 if cls == "design-intent" else 0.4
                best = max(best, score)
        visibility[fid] = best

    total_weight = sum(float(f.get("weight") or 0) for f in must_have) or 1.0
    covered = sum(float(f.get("weight") or 0) * visibility.get(str(f.get("id")), 0.0) for f in must_have)
    return {
        "coverage": covered / total_weight,
        "perFeature": visibility,
        "mustHaveCount": len(must_have),
    }
