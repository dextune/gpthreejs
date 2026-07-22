"""Map metric/review issues to constrained JSON patches (ITER-110)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from engine.critique.iteration import map_issue_to_scope, validate_json_patch


def patches_for_issues(
    issues_or_metrics: list[dict[str, Any]],
    *,
    step: int = 1,
    document: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Produce a limited JSON Patch list from failed metrics / review issues.

    Only allowed surfaces from ITER-102 are used.
    """

    patches: list[dict[str, Any]] = []
    fallback_delta = 0.03 * (1 if step % 2 else -1)

    for item in issues_or_metrics:
        mid = str(item.get("id") or item.get("criterionId") or item.get("metricId") or "")
        if item.get("passed") is True:
            continue
        if item.get("severity") == "info":
            continue
        scope = map_issue_to_scope(mid)
        root = scope["root"]
        if root == "renderProfiles" or mid == "camera_framing":
            details = item.get("details") or {}
            render_bbox = details.get("render") or {}
            reference_bbox = details.get("reference") or {}
            render_occ = float(render_bbox.get("occupancy") or 0)
            reference_occ = float(reference_bbox.get("occupancy") or 0)
            if reference_occ > 0 and render_occ > 0:
                magnitude = min(0.12, max(0.02, abs(render_occ - reference_occ) * 0.5))
                camera_delta = magnitude if render_occ > reference_occ else -magnitude
            else:
                camera_delta = fallback_delta
            profile_index, camera_axis, camera_sign = _camera_patch_target(
                document,
                str(item.get("viewId") or "source-34"),
            )
            patches.append(
                {
                    "op": "replace",
                    "path": f"/renderProfiles/{profile_index}/camera/position/{camera_axis}",
                    "value": None,  # filled by apply against document
                    "_relativeDelta": camera_delta * camera_sign,
                    "_pathHint": "camera_distance",
                }
            )
        elif mid in ("silhouette_iou", "boundary_f", "contour_distance") or scope["scope"] == "mass":
            details = item.get("details") or {}
            render_bbox = details.get("render") or {}
            reference_bbox = details.get("reference") or {}
            for axis, key in ((0, "w"), (1, "h")):
                rendered = float(render_bbox.get(key) or 0)
                target = float(reference_bbox.get(key) or 0)
                if rendered > 0 and target > 0:
                    mass_delta = min(0.12, max(-0.12, (target / rendered - 1.0) * 0.25))
                else:
                    mass_delta = fallback_delta * 0.5
                patches.append(
                    {
                        "op": "replace",
                        "path": f"/parts/0/transform/scale/{axis}",
                        "_relativeDelta": mass_delta,
                        "_pathHint": f"root_scale_{'xy'[axis]}",
                    }
                )
        elif mid in ("part_visibility", "landmark_coverage") or root == "poseProfile":
            patches.append(
                {
                    "op": "replace",
                    "path": "/poseProfile/joints/pelvis/rotation/1",
                    "_relativeDelta": fallback_delta,
                    "_pathHint": "pelvis_yaw",
                }
            )
        elif mid == "attachment_contact" or scope["scope"] == "attachment":
            patches.append(
                {
                    "op": "replace",
                    "path": "/parts/0/transform/scale/0",
                    "_relativeDelta": fallback_delta * 0.25,
                    "_pathHint": "root_scale_x",
                }
            )
        elif mid == "material_readability" or root == "materials":
            patches.append(
                {
                    "op": "replace",
                    "path": "/environment/exposure",
                    "_relativeDelta": abs(fallback_delta),
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

    raw = patches_for_issues(issues_or_metrics, step=step, document=document)
    base = deepcopy(document)
    if not raw:
        return base, []
    concrete = materialize_patches(base, raw)
    if not concrete:
        return base, []
    return apply_json_patch(base, concrete), concrete


def _camera_patch_target(
    document: dict[str, Any] | None,
    view_id: str,
) -> tuple[int, int, float]:
    for index, profile in enumerate((document or {}).get("renderProfiles") or []):
        if profile.get("id") == view_id or profile.get("view") == view_id:
            camera = profile.get("camera") or {}
            position = list(camera.get("position") or [0.0, 1.0, 2.4])
            look_at = list(camera.get("lookAt") or [0.0, 1.0, 0.0])
            offsets = [float(position[axis]) - float(look_at[axis]) for axis in range(3)]
            axis = max(range(3), key=lambda candidate: abs(offsets[candidate]))
            sign = -1.0 if offsets[axis] < 0 else 1.0
            return index, axis, sign
    return 0, 2, 1.0


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
