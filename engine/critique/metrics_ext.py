"""Extended metrics: framing, silhouette, landmarks, attachments, materials."""

from __future__ import annotations

from typing import Any

from engine.blueprint.attachments import assess_attachment_contacts
from engine.blueprint.materials_profile import assess_material_readability
from engine.blueprint.profiles import project_landmark_to_screen
from engine.shared.artifacts import content_hash


def camera_framing_metric(
    subject_bbox: dict[str, float],
    *,
    view_id: str,
    target_occupancy: float = 0.45,
) -> dict[str, Any]:
    """bbox center / occupancy / aspect alignment metric."""

    cx = float(subject_bbox.get("x", 0)) + float(subject_bbox.get("w", 1)) / 2
    cy = float(subject_bbox.get("y", 0)) + float(subject_bbox.get("h", 1)) / 2
    occupancy = float(subject_bbox.get("w", 1)) * float(subject_bbox.get("h", 1))
    aspect = float(subject_bbox.get("w", 1)) / max(1e-6, float(subject_bbox.get("h", 1)))
    center_err = ((cx - 0.5) ** 2 + (cy - 0.5) ** 2) ** 0.5
    occupancy_err = abs(occupancy - target_occupancy)
    value = max(0.0, 1.0 - (center_err * 2.0 + occupancy_err))
    return {
        "id": "camera_framing",
        "target": "framing",
        "viewId": view_id,
        "pass": "alpha",
        "value": value,
        "threshold": 0.6,
        "passed": value >= 0.6,
        "details": {
            "center": [cx, cy],
            "occupancy": occupancy,
            "aspect": aspect,
            "centerError": center_err,
        },
    }


def silhouette_metrics(
    *,
    view_id: str,
    iou: float,
    boundary_f: float,
    contour_distance: float,
    iou_threshold: float = 0.55,
    boundary_threshold: float = 0.5,
    contour_threshold: float = 0.35,
) -> list[dict[str, Any]]:
    return [
        {
            "id": "silhouette_iou",
            "target": "silhouette",
            "viewId": view_id,
            "pass": "alpha",
            "value": float(iou),
            "threshold": iou_threshold,
            "passed": float(iou) >= iou_threshold,
        },
        {
            "id": "boundary_f",
            "target": "silhouette",
            "viewId": view_id,
            "pass": "alpha",
            "value": float(boundary_f),
            "threshold": boundary_threshold,
            "passed": float(boundary_f) >= boundary_threshold,
        },
        {
            "id": "contour_distance",
            "target": "silhouette",
            "viewId": view_id,
            "pass": "alpha",
            "value": max(0.0, 1.0 - float(contour_distance)),
            "threshold": contour_threshold,
            "passed": max(0.0, 1.0 - float(contour_distance)) >= contour_threshold,
            "details": {"rawDistance": contour_distance},
        },
    ]


def landmark_and_part_metrics(
    landmarks: list[dict[str, Any]],
    *,
    view_id: str,
    camera: dict[str, Any] | None = None,
    visible_parts: list[str] | None = None,
    required_features: list[str] | None = None,
) -> list[dict[str, Any]]:
    metrics: list[dict[str, Any]] = []
    projected = [project_landmark_to_screen(lm, camera=camera) for lm in landmarks]
    in_frame = sum(1 for p in projected if 0.0 <= p["x"] <= 1.0 and 0.0 <= p["y"] <= 1.0)
    coverage = in_frame / max(1, len(projected))
    metrics.append(
        {
            "id": "landmark_coverage",
            "target": "landmarks",
            "viewId": view_id,
            "pass": "beauty",
            "value": coverage,
            "threshold": 0.7,
            "passed": coverage >= 0.7,
            "details": {"inFrame": in_frame, "total": len(projected)},
        }
    )
    visible = set(visible_parts or [])
    required = list(required_features or [])
    if required:
        hit = sum(1 for feat in required if feat in visible)
        part_cov = hit / len(required)
        metrics.append(
            {
                "id": "part_visibility",
                "target": "parts",
                "viewId": view_id,
                "pass": "partId",
                "value": part_cov,
                "threshold": 0.6,
                "passed": part_cov >= 0.6,
                "details": {"visible": sorted(visible), "required": required},
            }
        )
    return metrics


def attachment_and_material_metrics(
    blueprint: dict[str, Any],
    *,
    view_id: str = "source-34",
) -> list[dict[str, Any]]:
    contacts = assess_attachment_contacts(blueprint.get("parts") or [], blueprint.get("handles"))
    readability = assess_material_readability(blueprint.get("materials") or [])
    contact_score = 1.0 if contacts["passed"] else max(0.0, 1.0 - 0.2 * len(contacts["issues"]))
    material_score = 1.0 if readability["passed"] else max(0.0, 1.0 - 0.2 * len(readability["issues"]))
    return [
        {
            "id": "attachment_contact",
            "target": "attachments",
            "viewId": view_id,
            "pass": "partId",
            "value": contact_score,
            "threshold": 0.8,
            "passed": contact_score >= 0.8,
            "details": contacts,
        },
        {
            "id": "material_readability",
            "target": "materials",
            "viewId": view_id,
            "pass": "materialDebug",
            "value": material_score,
            "threshold": 0.8,
            "passed": material_score >= 0.8,
            "details": readability,
        },
    ]


def build_metric_report(
    *,
    revision_id: str,
    render_set_hash: str,
    metrics: list[dict[str, Any]],
    metric_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = metric_config or {"suite": "m4-default"}
    return {
        "schemaVersion": 1,
        "revisionId": revision_id,
        "renderSetHash": render_set_hash,
        "metricConfigHash": content_hash(config),
        "metrics": metrics,
    }
