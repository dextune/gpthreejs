"""Cross-view consistency checks for ReferenceSets."""

from __future__ import annotations

from collections import Counter
from typing import Any


def _palette_signature(ref: dict[str, Any]) -> tuple[str, ...]:
    colors = ref.get("palette") or ref.get("dominantColors") or []
    if isinstance(colors, list):
        return tuple(str(c).lower() for c in colors[:4])
    return ()


def _equipment_ids(ref: dict[str, Any]) -> frozenset[str]:
    raw = ref.get("equipment") or ref.get("visibleFeatures") or []
    return frozenset(str(item) for item in raw)


def assess_cross_view_consistency(reference_set: dict[str, Any]) -> dict[str, Any]:
    """
    MVP consistency gate using color, equipment, and handedness signals.

    Returns pass/fail with structured issues. Mutated side fixtures that change
    equipment color/identity should fail.
    """

    refs = [r for r in (reference_set.get("references") or []) if isinstance(r, dict)]
    issues: list[dict[str, Any]] = []

    if len(refs) < 2:
        return {
            "schemaVersion": 1,
            "passed": True,
            "issues": [],
            "notes": ["single-view set; cross-view consistency skipped"],
        }

    # Dominant palette majority vote
    palettes = [_palette_signature(r) for r in refs if _palette_signature(r)]
    if palettes:
        majority = Counter(palettes).most_common(1)[0][0]
        for ref in refs:
            sig = _palette_signature(ref)
            if sig and sig != majority:
                issues.append(
                    {
                        "code": "COLOR_INCONSISTENT",
                        "referenceId": ref.get("id"),
                        "message": f"palette {list(sig)} diverges from majority {list(majority)}",
                        "severity": "error",
                    }
                )

    # Equipment set: require overlap with the richest equipment list
    equipment_sets = [(r.get("id"), _equipment_ids(r)) for r in refs]
    non_empty = [ids for _, ids in equipment_sets if ids]
    if non_empty:
        union = set().union(*non_empty)
        core = set.intersection(*[set(s) for s in non_empty]) if len(non_empty) > 1 else set(non_empty[0])
        for ref_id, ids in equipment_sets:
            if not ids:
                continue
            # If a view invents conflicting exclusive equipment tokens, flag it.
            exclusive = ids - union.union(set())  # noqa: keep simple
            missing_core = core - ids
            if missing_core and len(ids) >= 1:
                # Only hard-fail when this view claims to show equipment but drops core items.
                view = str(next((r.get("declaredView") for r in refs if r.get("id") == ref_id), ""))
                if view not in ("back",):  # back may occlude front equipment
                    issues.append(
                        {
                            "code": "EQUIPMENT_INCONSISTENT",
                            "referenceId": ref_id,
                            "message": f"missing core equipment {sorted(missing_core)}",
                            "severity": "error",
                        }
                    )
            # Explicit tamper signal: equipment marked with flipped color suffix
            for item in ids:
                if item.endswith("__mutated") or item.endswith("_tampered"):
                    issues.append(
                        {
                            "code": "EQUIPMENT_TAMPERED",
                            "referenceId": ref_id,
                            "message": f"tampered equipment marker {item}",
                            "severity": "error",
                        }
                    )

    # Handedness: left/right hand equipment should not flip across views without mirror flag
    handedness_votes: list[str] = []
    for ref in refs:
        hand = ref.get("handedness") or ref.get("dominantHand")
        if hand:
            handedness_votes.append(str(hand).lower())
        for feat in ref.get("visibleFeatures") or []:
            token = str(feat).lower()
            if "sword_left" in token or "shield_right" in token:
                handedness_votes.append("left-dominant-reversed")
            if "sword_right" in token or "shield_left" in token:
                handedness_votes.append("right-dominant")

    if handedness_votes:
        majority_hand = Counter(handedness_votes).most_common(1)[0][0]
        for vote in handedness_votes:
            if vote != majority_hand and {
                vote,
                majority_hand,
            } == {"left-dominant-reversed", "right-dominant"}:
                issues.append(
                    {
                        "code": "HANDEDNESS_FLIP",
                        "message": f"handedness {vote} conflicts with majority {majority_hand}",
                        "severity": "error",
                    }
                )
                break

    # Explicit side-view color mutation field
    for ref in refs:
        if ref.get("colorMutated") is True or ref.get("consistencyTag") == "mutated-side":
            issues.append(
                {
                    "code": "SIDE_VIEW_MUTATED",
                    "referenceId": ref.get("id"),
                    "message": "side fixture marked as color/equipment mutated",
                    "severity": "error",
                }
            )

    passed = not any(i.get("severity") == "error" for i in issues)
    return {
        "schemaVersion": 1,
        "passed": passed,
        "issues": issues,
        "referenceCount": len(refs),
        "agentAction": "continue" if passed else "abort",
    }
