"""Structured vision reviewer port and deterministic ReviewPolicy."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Protocol

from engine.shared.artifacts import content_hash


class VisionReviewer(Protocol):
    name: str

    def review(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...


class NullVisionReviewer:
    """Offline reviewer that emits a structured empty recommendation."""

    name = "null"

    def review(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "reviewer": self.name,
            "recommendation": "revise",
            "issues": [
                {
                    "severity": "info",
                    "criterionId": "reviewer-unavailable",
                    "viewId": "source-34",
                    "evidence": {"note": "no vision reviewer configured"},
                    "rootCause": "provider",
                    "action": "continue-with-metrics",
                    "confidence": 0.0,
                }
            ],
            "confidence": 0.0,
            "timeout": False,
            "raw": None,
        }


def parse_reviewer_output(raw: Any) -> dict[str, Any]:
    """Parse and validate structured reviewer output."""

    if raw is None or raw == "":
        raise ValueError("reviewer output is empty")
    if isinstance(raw, str):
        import json

        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"reviewer output is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("reviewer output must be an object")
    if raw.get("timeout") is True:
        raise TimeoutError("reviewer timed out")
    recommendation = raw.get("recommendation")
    if recommendation not in ("accept", "revise", "reject", None):
        raise ValueError(f"invalid recommendation {recommendation!r}")
    issues = raw.get("issues")
    if issues is not None and not isinstance(issues, list):
        raise ValueError("issues must be an array")
    return deepcopy(raw)


def get_vision_reviewer(name: str | None = None) -> VisionReviewer:
    if name in (None, "", "null", "none"):
        return NullVisionReviewer()
    return NullVisionReviewer()


def apply_review_policy(
    *,
    metric_report: dict[str, Any],
    reviewer_output: dict[str, Any] | None,
    critical_feature_floors: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Deterministic ReviewPolicy: hard metrics gate accept; reviewer is advisory only.
    """

    metrics = metric_report.get("metrics") or []
    hard_failures = [m for m in metrics if not m.get("passed")]
    critical_failures = []
    floors = critical_feature_floors or {}
    for metric in metrics:
        floor = floors.get(metric.get("id")) or floors.get(metric.get("target"))
        if floor is not None and float(metric.get("value") or 0) < float(floor):
            critical_failures.append(metric)

    reviewer_rec = (reviewer_output or {}).get("recommendation")
    # Reviewer alone can never force accept.
    if critical_failures or hard_failures:
        decision = "reject" if critical_failures else "revise"
    elif reviewer_rec == "reject":
        decision = "revise"  # still need metric support to hard-reject without floors
    elif reviewer_rec == "accept" and not hard_failures:
        # metrics all passed; accept is allowed because metrics support it
        decision = "accept"
    elif not hard_failures:
        decision = "accept"
    else:
        decision = "revise"

    # Explicit rule: if metrics fail, never accept even if reviewer says accept.
    if hard_failures and decision == "accept":
        decision = "revise"
    if reviewer_rec == "accept" and hard_failures:
        decision = "revise"

    policy_trace = {
        "policyIssued": True,
        "issuer": "review-policy",
        "decision": decision,
        "hardFailureCount": len(hard_failures),
        "criticalFailureCount": len(critical_failures),
        "reviewerRecommendation": reviewer_rec,
        "reviewerCannotOverrideMetrics": True,
        "metricReportHash": content_hash(
            {"revisionId": metric_report.get("revisionId"), "metrics": metrics}
        ),
        "policyVersion": "m4-v1",
    }
    policy_trace["traceHash"] = content_hash(policy_trace, ignored_paths=(("traceHash",),))

    issues = []
    for metric in hard_failures:
        issues.append(
            {
                "severity": "error",
                "criterionId": metric.get("id"),
                "viewId": metric.get("viewId"),
                "evidence": {"metric": metric},
                "rootCause": "metric",
                "action": "revise",
                "confidence": 1.0,
            }
        )
    if reviewer_output:
        for issue in reviewer_output.get("issues") or []:
            issues.append(issue)

    return {
        "schemaVersion": 1,
        "revisionId": metric_report.get("revisionId"),
        "renderSetHash": metric_report.get("renderSetHash"),
        "metricReportHash": policy_trace["metricReportHash"],
        "reviewerConfigHash": content_hash({"reviewer": (reviewer_output or {}).get("reviewer", "null")}),
        "recommendation": decision,
        "issues": issues,
        "policyTrace": policy_trace,
    }


def build_comparison_sheet(
    *,
    revision_id: str,
    metrics: list[dict[str, Any]],
    views: list[str],
) -> dict[str, Any]:
    """Overlay/diff/part-label/metric annotation sheet metadata (artifact contract)."""

    return {
        "schemaVersion": 1,
        "revisionId": revision_id,
        "views": views,
        "annotations": [
            {
                "type": "metric",
                "metricId": m.get("id"),
                "viewId": m.get("viewId"),
                "passed": m.get("passed"),
                "value": m.get("value"),
                "threshold": m.get("threshold"),
            }
            for m in metrics
        ],
        "overlays": [
            {"type": "silhouette-diff", "viewId": view}
            for view in views
        ],
        "partLabels": True,
        "sheetHash": "",
    }
