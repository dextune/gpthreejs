"""Map metric/review issues to constrained JSON patches (ITER-110)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from engine.critique.iteration import map_issue_to_scope, validate_json_patch


def patches_for_issues(
    issues_or_metrics: list[dict[str, Any]],
    *,
    step: int = 1,
) -> list[dict[str, Any]]:
    """
    Produce a limited JSON Patch list from failed metrics / review issues.

    Only allowed surfaces from ITER-102 are used.
    """

    patches: list[dict[str, Any]] = []
    delta = 0.03 * (1 if step % 2 else -1)

    for item in issues_or_metrics:
        mid = str(item.get("id") or item.get("criterionId") or item.get("metricId") or "")
        if item.get("passed") is True:
            continue
        if item.get("severity") == "info":
            continue
        scope = map_issue_to_scope(mid)
        root = scope["root"]
        if root == "renderProfiles" or mid == "camera_framing":
            patches.append(
                {
                    "op": "replace",
                    "path": "/renderProfiles/0/camera/position/2",
                    "value": None,  # filled by apply against document
                    "_relativeDelta": delta,
                    "_pathHint": "camera_z",
                }
            )
        elif mid in ("silhouette_iou", "boundary_f", "contour_distance") or scope["scope"] == "mass":
            patches.append(
                {
                    "op": "replace",
                    "path": "/proportionProfile/shoulderWidthRatio",
                    "_relativeDelta": delta * 0.5,
                    "_pathHint": "shoulder",
                }
            )
        elif mid in ("part_visibility", "landmark_coverage") or root == "poseProfile":
            patches.append(
                {
                    "op": "replace",
                    "path": "/poseProfile/joints/pelvis/rotation/1",
                    "_relativeDelta": delta,
                    "_pathHint": "pelvis_yaw",
                }
            )
        elif mid == "attachment_contact" or scope["scope"] == "attachment":
            patches.append(
                {
                    "op": "replace",
                    "path": "/parts/0/transform/scale/0",
                    "_relativeDelta": delta * 0.25,
                    "_pathHint": "root_scale_x",
                }
            )
        elif mid == "material_readability" or root == "materials":
            patches.append(
                {
                    "op": "replace",
                    "path": "/environment/exposure",
                    "_relativeDelta": abs(delta),
                    "_pathHint": "exposure",
                }
            )

    # Deduplicate by path, keep first
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for patch in patches:
        path = patch.get("path")
        if path in seen:
            continue
        seen.add(str(path))
        unique.append(patch)
    return unique


def materialize_patches(document: dict[str, Any], patches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Resolve relative deltas into concrete replace ops and validate."""

    concrete: list[dict[str, Any]] = []
    for patch in patches:
        path = str(patch["path"])
        if "_relativeDelta" in patch:
            current = _get_pointer(document, path)
            if current is None:
                # try create defaults
                if path.endswith("exposure"):
                    current = float((document.get("environment") or {}).get("exposure", 1.0))
                elif "shoulderWidthRatio" in path:
                    current = float((document.get("proportionProfile") or {}).get("shoulderWidthRatio", 0.4))
                elif "camera/position/2" in path:
                    cams = document.get("renderProfiles") or []
                    if cams:
                        pos = (cams[0].get("camera") or {}).get("position") or [0, 1, 2.4]
                        current = float(pos[2])
                    else:
                        current = 2.4
                else:
                    current = 1.0
            value = float(current) + float(patch["_relativeDelta"])
            if "shoulderWidthRatio" in path:
                value = min(0.9, max(0.2, value))
            if "exposure" in path:
                value = min(2.0, max(0.4, value))
            concrete.append({"op": "replace", "path": path, "value": value})
        else:
            concrete.append({"op": patch["op"], "path": path, "value": patch.get("value")})

    # Drop ops whose paths don't exist when replace would fail — ensure parents
    ready: list[dict[str, Any]] = []
    for op in concrete:
        path = op["path"]
        if _ensure_path(document, path):
            ready.append(op)
    errors = validate_json_patch(ready)
    if errors:
        # filter to only valid paths under allowlist
        ready = [op for op in ready if not any(op["path"] in e for e in errors)]
        errors = validate_json_patch(ready)
        if errors:
            raise ValueError("; ".join(errors))
    return ready


def apply_issue_driven_patch(
    document: dict[str, Any],
    issues_or_metrics: list[dict[str, Any]],
    *,
    step: int = 1,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from engine.critique.iteration import apply_json_patch

    raw = patches_for_issues(issues_or_metrics, step=step)
    base = deepcopy(document)
    if not raw:
        return base, []
    concrete = materialize_patches(base, raw)
    if not concrete:
        return base, []
    return apply_json_patch(base, concrete), concrete


def _get_pointer(doc: Any, path: str) -> Any:
    parts = [p for p in path.strip("/").split("/") if p]
    cur = doc
    for part in parts:
        if isinstance(cur, list):
            idx = int(part)
            if idx >= len(cur):
                return None
            cur = cur[idx]
        elif isinstance(cur, dict):
            if part not in cur:
                return None
            cur = cur[part]
        else:
            return None
    return cur


def _ensure_path(doc: dict[str, Any], path: str) -> bool:
    """Return True if path can be resolved or created for replace."""

    parts = [p for p in path.strip("/").split("/") if p]
    cur: Any = doc
    for i, part in enumerate(parts[:-1]):
        nxt = parts[i + 1]
        if isinstance(cur, dict):
            if part not in cur:
                cur[part] = [] if nxt.isdigit() else {}
            cur = cur[part]
        elif isinstance(cur, list):
            idx = int(part)
            while len(cur) <= idx:
                cur.append({})
            cur = cur[idx]
        else:
            return False
    last = parts[-1]
    if isinstance(cur, dict):
        if last not in cur:
            # for scale/position arrays
            if last.isdigit():
                return False
            cur[last] = 0.0
        return True
    if isinstance(cur, list) and last.isdigit():
        idx = int(last)
        while len(cur) <= idx:
            cur.append(0.0)
        return True
    return False
