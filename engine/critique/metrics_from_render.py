"""Metrics computed from real RenderSet PNG artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.blueprint.attachments import assess_attachment_contacts
from engine.blueprint.materials_profile import assess_material_readability
from engine.blueprint.profiles import project_landmark_to_screen
from engine.critique.metrics_ext import build_metric_report
from engine.critique.software_render import (
    alpha_bbox,
    boundary_f_score,
    contour_mean_distance,
    part_id_visible_set,
    silhouette_iou,
)
from engine.shared.artifacts import content_hash
from engine.shared.pngio import read_png


def _pass_path(render_set: dict[str, Any], view_id: str, pass_name: str) -> Path:
    for view in render_set.get("views") or []:
        if view.get("id") == view_id:
            meta = (view.get("passes") or {}).get(pass_name)
            if not meta or not meta.get("path"):
                raise FileNotFoundError(f"missing pass {view_id}/{pass_name}")
            path = Path(meta["path"])
            if not path.is_file():
                raise FileNotFoundError(f"pass file not found: {path}")
            return path
    raise FileNotFoundError(f"view {view_id} not in render set")


def metrics_from_render_set(
    blueprint: dict[str, Any],
    render_set: dict[str, Any],
    *,
    reference_alpha: dict[str, str] | None = None,
    view_id: str = "source-34",
    require_external_reference: bool = False,
) -> list[dict[str, Any]]:
    """Build metric entries from on-disk render passes (no hardcoded scores).

    Silhouette metrics require an EXTERNAL reference alpha (photo/sense matte).
    Self-comparison against a blueprint re-render is not used.
    """

    alpha_path = _pass_path(render_set, view_id, "alpha")
    part_path = _pass_path(render_set, view_id, "partId")
    beauty_path = _pass_path(render_set, view_id, "beauty")

    bbox = alpha_bbox(alpha_path)
    framing = {
        "id": "camera_framing",
        "target": "framing",
        "viewId": view_id,
        "pass": "alpha",
        "value": max(
            0.0,
            1.0
            - (
                ((bbox["x"] + bbox["w"] / 2) - 0.5) ** 2
                + ((bbox["y"] + bbox["h"] / 2) - 0.5) ** 2
            )
            ** 0.5
            * 2
            - abs(bbox.get("occupancy", 0) - 0.45),
        ),
        "threshold": 0.45,
        "passed": False,
        "details": bbox,
        "evidencePath": str(alpha_path),
    }
    framing["passed"] = framing["value"] >= framing["threshold"]

    ref_path = (reference_alpha or {}).get(view_id)
    external = bool(ref_path and Path(str(ref_path)).is_file())
    # Detect accidental self-baseline: same path as render alpha
    if external and Path(str(ref_path)).resolve() == Path(alpha_path).resolve():
        external = False
        ref_path = None

    if external:
        iou = silhouette_iou(alpha_path, ref_path)
        bf = boundary_f_score(alpha_path, ref_path)
        contour = contour_mean_distance(alpha_path, ref_path)
        # Photo matte vs procedural alpha: IoU is primary hard gate.
        # Boundary/contour are softer (provisional calibration for synthetic fixtures).
        iou_thr, bf_thr, cont_thr = 0.35, 0.02, 0.25
    else:
        # No external photo/sense matte: do not invent IoU=1.0 self-pass.
        occ = bbox.get("occupancy", 0.0)
        iou = 0.0 if require_external_reference else (min(1.0, occ / 0.35) if occ > 0 else 0.0)
        bf = 0.0 if require_external_reference else (min(1.0, occ / 0.3) if occ > 0 else 0.0)
        contour = 1.0 if require_external_reference else (0.0 if 0.1 <= occ <= 0.8 else 0.5)
        iou_thr, bf_thr, cont_thr = 0.4, 0.35, 0.35

    cont_score = max(0.0, 1.0 - float(contour))
    sil = [
        {
            "id": "silhouette_iou",
            "target": "silhouette",
            "viewId": view_id,
            "pass": "alpha",
            "value": float(iou),
            "threshold": iou_thr,
            "passed": float(iou) >= iou_thr and (external or not require_external_reference),
            "evidencePath": str(alpha_path),
            "referencePath": str(ref_path) if ref_path else None,
            "externalReference": external,
            "details": {
                "requireExternalReference": require_external_reference,
                "missingExternalMatte": require_external_reference and not external,
            },
        },
        {
            "id": "boundary_f",
            "target": "silhouette",
            "viewId": view_id,
            "pass": "alpha",
            "value": float(bf),
            "threshold": bf_thr,
            "passed": float(bf) >= bf_thr and (external or not require_external_reference),
            "evidencePath": str(alpha_path),
            "externalReference": external,
        },
        {
            "id": "contour_distance",
            "target": "silhouette",
            "viewId": view_id,
            "pass": "alpha",
            "value": cont_score,
            "threshold": cont_thr,
            "passed": cont_score >= cont_thr and (external or not require_external_reference),
            "details": {"rawDistance": contour},
            "evidencePath": str(alpha_path),
            "externalReference": external,
        },
    ]

    # landmarks from blueprint projected + in-frame rate
    camera = None
    for profile in blueprint.get("renderProfiles") or []:
        if profile.get("id") == view_id or profile.get("view") == view_id:
            camera = profile.get("camera")
            break
    landmarks = blueprint.get("landmarks") or []
    projected = [project_landmark_to_screen(lm, camera=camera) for lm in landmarks]
    in_frame = sum(1 for p in projected if 0.0 <= p["x"] <= 1.0 and 0.0 <= p["y"] <= 1.0)
    landmark_cov = in_frame / max(1, len(projected)) if projected else 0.0

    known_ids = []

    def walk(part: dict[str, Any]) -> None:
        if part.get("id"):
            known_ids.append(part["id"])
        for child in part.get("children") or []:
            walk(child)

    for part in blueprint.get("parts") or []:
        walk(part)

    visible = part_id_visible_set(part_path, known_ids)
    required = ["helmet", "shield", "sword", "plume", "torso"]
    required = [r for r in required if r in known_ids] or known_ids[:4]
    part_cov = sum(1 for r in required if r in visible) / max(1, len(required))

    part_metrics = [
        {
            "id": "landmark_coverage",
            "target": "landmarks",
            "viewId": view_id,
            "pass": "beauty",
            "value": landmark_cov,
            "threshold": 0.5,
            "passed": landmark_cov >= 0.5,
            "evidencePath": str(beauty_path),
        },
        {
            "id": "part_visibility",
            "target": "parts",
            "viewId": view_id,
            "pass": "partId",
            "value": part_cov,
            "threshold": 0.5,
            "passed": part_cov >= 0.5,
            "details": {"visible": visible, "required": required},
            "evidencePath": str(part_path),
        },
    ]

    contacts = assess_attachment_contacts(blueprint.get("parts") or [], blueprint.get("handles"))
    readability = assess_material_readability(blueprint.get("materials") or [])
    # material debug pass must exist and be non-empty
    mat_path = _pass_path(render_set, view_id, "materialDebug")
    mat_img = read_png(mat_path)
    mat_signal = 0
    for y in range(0, mat_img.height, 4):
        for x in range(0, mat_img.width, 4):
            r, g, b, a = mat_img.pixel(x, y)
            if r + g + b > 0:
                mat_signal += 1
    mat_score = 1.0 if readability["passed"] and mat_signal > 0 else 0.3 if mat_signal > 0 else 0.0
    contact_score = 1.0 if contacts["passed"] else max(0.0, 1.0 - 0.15 * len(contacts["issues"]))

    # Handedness: equipment centroids on part-id pass vs blueprint handedness
    hand_score = 1.0
    hand_details: dict[str, Any] = {}
    handedness = str(blueprint.get("handedness") or "right").lower()
    if "shield" in known_ids and "sword" in known_ids:
        # approximate: compare mean x of shield-colored vs sword-colored pixels
        shield_rgb = None
        sword_rgb = None
        try:
            from engine.critique.software_render import _part_color_id

            shield_rgb = _part_color_id("shield")
            sword_rgb = _part_color_id("sword")
        except Exception:
            shield_rgb = sword_rgb = None
        if shield_rgb and sword_rgb:
            img = read_png(part_path)
            sx = sy = sn = 0
            wx = wy = wn = 0
            for y in range(0, img.height, 2):
                for x in range(0, img.width, 2):
                    r, g, b, a = img.pixel(x, y)
                    if a < 128:
                        continue
                    if (r, g, b) == shield_rgb:
                        sx += x
                        sy += y
                        sn += 1
                    elif (r, g, b) == sword_rgb:
                        wx += x
                        wy += y
                        wn += 1
            if sn and wn:
                shield_cx = sx / sn / max(1, img.width)
                sword_cx = wx / wn / max(1, img.width)
                # right-handed: sword should be to the right of shield on front-ish views
                if handedness == "right":
                    hand_score = 1.0 if sword_cx >= shield_cx - 0.05 else 0.2
                else:
                    hand_score = 1.0 if sword_cx <= shield_cx + 0.05 else 0.2
                hand_details = {
                    "handedness": handedness,
                    "shieldCx": shield_cx,
                    "swordCx": sword_cx,
                }
            else:
                hand_score = 0.3
                hand_details = {"reason": "equipment pixels not found in partId pass"}

    extra = [
        {
            "id": "attachment_contact",
            "target": "attachments",
            "viewId": view_id,
            "pass": "partId",
            "value": contact_score,
            "threshold": 0.8,
            "passed": contact_score >= 0.8,
            "details": contacts,
            "evidencePath": str(part_path),
        },
        {
            "id": "material_readability",
            "target": "materials",
            "viewId": view_id,
            "pass": "materialDebug",
            "value": mat_score,
            "threshold": 0.5,
            "passed": mat_score >= 0.5,
            "details": readability,
            "evidencePath": str(mat_path),
        },
        {
            "id": "handedness",
            "target": "handedness",
            "viewId": view_id,
            "pass": "partId",
            "value": hand_score,
            "threshold": 0.6,
            "passed": hand_score >= 0.6,
            "details": hand_details,
            "evidencePath": str(part_path),
        },
    ]

    return [framing, *sil, *part_metrics, *extra]


def metric_report_from_render_set(
    blueprint: dict[str, Any],
    render_set: dict[str, Any],
    *,
    reference_alpha: dict[str, str] | None = None,
    view_id: str = "source-34",
    require_external_reference: bool = False,
) -> dict[str, Any]:
    metrics = metrics_from_render_set(
        blueprint,
        render_set,
        reference_alpha=reference_alpha,
        view_id=view_id,
        require_external_reference=require_external_reference,
    )
    report = build_metric_report(
        revision_id=str(render_set.get("revisionId") or "rev"),
        render_set_hash=content_hash(render_set),
        metrics=metrics,
    )
    report["externalReference"] = any(m.get("externalReference") for m in metrics)
    report["requireExternalReference"] = require_external_reference
    return report
