"""Render and review artifact contracts."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from engine.blueprint.schema import DECISIONS
from engine.shared.artifacts import artifact_content_hash

REQUIRED_RENDER_PASSES = ("beauty", "alpha", "partId")

RENDER_SET_REQUIRED_FIELDS = (
    "schemaVersion",
    "revisionId",
    "blueprintHash",
    "factoryHash",
    "rendererVersion",
    "renderProfileHash",
    "views",
)
RENDER_VIEW_REQUIRED_FIELDS = ("id", "cameraProfileHash", "lightProfileHash", "passes")
RENDER_PASS_REQUIRED_FIELDS = ("path", "hash")

METRIC_REPORT_REQUIRED_FIELDS = (
    "schemaVersion",
    "revisionId",
    "renderSetHash",
    "metricConfigHash",
    "metrics",
)
METRIC_ENTRY_REQUIRED_FIELDS = ("id", "target", "viewId", "pass", "value", "threshold", "passed")

REVIEW_REPORT_REQUIRED_FIELDS = (
    "schemaVersion",
    "revisionId",
    "renderSetHash",
    "metricReportHash",
    "reviewerConfigHash",
    "recommendation",
    "issues",
)
REVIEW_ISSUE_REQUIRED_FIELDS = (
    "severity",
    "criterionId",
    "viewId",
    "evidence",
    "rootCause",
    "action",
    "confidence",
)


def render_set_schema() -> dict[str, Any]:
    return deepcopy(_RENDER_SET_SCHEMA)


def metric_report_schema() -> dict[str, Any]:
    return deepcopy(_METRIC_REPORT_SCHEMA)


def review_report_schema() -> dict[str, Any]:
    return deepcopy(_REVIEW_REPORT_SCHEMA)


def _missing_fields(value: dict[str, Any], fields: tuple[str, ...], path: str) -> list[str]:
    return [f"{path}.{field}: missing required field" for field in fields if field not in value]


def validate_render_set(render_set: dict[str, Any]) -> list[str]:
    errors = _missing_fields(render_set, RENDER_SET_REQUIRED_FIELDS, "$")
    for view_index, view in enumerate(render_set.get("views") or []):
        view_path = f"$.views[{view_index}]"
        errors.extend(_missing_fields(view, RENDER_VIEW_REQUIRED_FIELDS, view_path))
        passes = view.get("passes") or {}
        for pass_name in REQUIRED_RENDER_PASSES:
            pass_path = f"{view_path}.passes.{pass_name}"
            if pass_name not in passes:
                errors.append(f"{pass_path}: missing required render pass")
                continue
            errors.extend(_missing_fields(passes[pass_name], RENDER_PASS_REQUIRED_FIELDS, pass_path))
    if "views" in render_set and not render_set.get("views"):
        errors.append("$.views: at least one render view is required")
    return errors


def validate_metric_report(metric_report: dict[str, Any]) -> list[str]:
    errors = _missing_fields(metric_report, METRIC_REPORT_REQUIRED_FIELDS, "$")
    for index, metric in enumerate(metric_report.get("metrics") or []):
        errors.extend(_missing_fields(metric, METRIC_ENTRY_REQUIRED_FIELDS, f"$.metrics[{index}]"))
    if "metrics" in metric_report and not metric_report.get("metrics"):
        errors.append("$.metrics: at least one metric entry is required")
    return errors


def validate_review_report(review_report: dict[str, Any]) -> list[str]:
    errors = _missing_fields(review_report, REVIEW_REPORT_REQUIRED_FIELDS, "$")
    recommendation = review_report.get("recommendation")
    if recommendation is not None and recommendation not in DECISIONS:
        errors.append(f"$.recommendation: unsupported decision {recommendation!r}")
    for index, issue in enumerate(review_report.get("issues") or []):
        errors.extend(_missing_fields(issue, REVIEW_ISSUE_REQUIRED_FIELDS, f"$.issues[{index}]"))
    return errors


def validate_render_set_freshness(
    render_set: dict[str, Any],
    *,
    blueprint_path: str | Path,
    factory_path: str | Path,
) -> list[str]:
    errors: list[str] = []
    blueprint_hash = artifact_content_hash(blueprint_path)
    factory_hash = _file_hash(factory_path)
    if render_set.get("blueprintHash") != blueprint_hash:
        errors.append("$.blueprintHash: stale Blueprint hash")
    if render_set.get("factoryHash") != factory_hash:
        errors.append("$.factoryHash: stale factory hash")
    return errors


def validate_metric_report_freshness(
    metric_report: dict[str, Any],
    *,
    render_set: dict[str, Any],
) -> list[str]:
    render_set_hash = artifact_content_hash_value(render_set)
    if metric_report.get("renderSetHash") != render_set_hash:
        return ["$.renderSetHash: stale RenderSet hash"]
    return []


def validate_review_report_freshness(
    review_report: dict[str, Any],
    *,
    render_set: dict[str, Any],
    metric_report: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if review_report.get("renderSetHash") != artifact_content_hash_value(render_set):
        errors.append("$.renderSetHash: stale RenderSet hash")
    if review_report.get("metricReportHash") != artifact_content_hash_value(metric_report):
        errors.append("$.metricReportHash: stale MetricReport hash")
    return errors


def artifact_content_hash_value(value: dict[str, Any]) -> str:
    from engine.shared.artifacts import content_hash

    return content_hash(value)


def _file_hash(path: str | Path) -> str:
    import hashlib

    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


_RENDER_SET_SCHEMA = {
    "title": "gpthreejs RenderSet",
    "type": "object",
    "required": list(RENDER_SET_REQUIRED_FIELDS),
    "properties": {
        "schemaVersion": {"const": 1},
        "views": {
            "type": "array",
            "items": {
                "type": "object",
                "required": list(RENDER_VIEW_REQUIRED_FIELDS),
            },
        },
    },
}

_METRIC_REPORT_SCHEMA = {
    "title": "gpthreejs MetricReport",
    "type": "object",
    "required": list(METRIC_REPORT_REQUIRED_FIELDS),
    "properties": {
        "schemaVersion": {"const": 1},
        "metrics": {
            "type": "array",
            "items": {
                "type": "object",
                "required": list(METRIC_ENTRY_REQUIRED_FIELDS),
            },
        },
    },
}

_REVIEW_REPORT_SCHEMA = {
    "title": "gpthreejs ReviewReport",
    "type": "object",
    "required": list(REVIEW_REPORT_REQUIRED_FIELDS),
    "properties": {
        "schemaVersion": {"const": 1},
        "recommendation": {"enum": list(DECISIONS)},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "required": list(REVIEW_ISSUE_REQUIRED_FIELDS),
            },
        },
    },
}
