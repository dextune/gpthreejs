"""Iteration records, JSON patch limits, rollback, budgets, and root-cause mapping."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from engine.shared.artifacts import content_hash

ALLOWED_PATCH_PREFIXES = (
    "/proportionProfile/",
    "/poseProfile/joints/",
    "/parts/",
    "/materials/",
    "/environment/",
    "/renderProfiles/",
    "/handedness",
)

ALLOWED_OPS = ("add", "remove", "replace", "move", "copy", "test")


@dataclass
class IterationBudget:
    max_iterations: int = 8
    max_wall_seconds: float = 300.0
    max_cpu_seconds: float = 300.0
    max_renders: int = 32
    max_reviewer_calls: int = 8
    stagnation_limit: int = 3
    iterations: int = 0
    wall_seconds: float = 0.0
    cpu_seconds: float = 0.0
    renders: int = 0
    reviewer_calls: int = 0
    stagnant_steps: int = 0

    def remaining(self) -> bool:
        return (
            self.iterations < self.max_iterations
            and self.wall_seconds < self.max_wall_seconds
            and self.cpu_seconds < self.max_cpu_seconds
            and self.renders < self.max_renders
            and self.reviewer_calls < self.max_reviewer_calls
            and self.stagnant_steps < self.stagnation_limit
        )

    def stop_reason(self) -> str | None:
        if self.iterations >= self.max_iterations:
            return "max_iterations"
        if self.wall_seconds >= self.max_wall_seconds:
            return "max_wall_seconds"
        if self.cpu_seconds >= self.max_cpu_seconds:
            return "max_cpu_seconds"
        if self.renders >= self.max_renders:
            return "max_renders"
        if self.reviewer_calls >= self.max_reviewer_calls:
            return "max_reviewer_calls"
        if self.stagnant_steps >= self.stagnation_limit:
            return "stagnation"
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "maxIterations": self.max_iterations,
            "maxWallSeconds": self.max_wall_seconds,
            "maxCpuSeconds": self.max_cpu_seconds,
            "maxRenders": self.max_renders,
            "maxReviewerCalls": self.max_reviewer_calls,
            "stagnationLimit": self.stagnation_limit,
            "iterations": self.iterations,
            "wallSeconds": self.wall_seconds,
            "cpuSeconds": self.cpu_seconds,
            "renders": self.renders,
            "reviewerCalls": self.reviewer_calls,
            "stagnantSteps": self.stagnant_steps,
            "stopReason": self.stop_reason(),
        }


ISSUE_SCOPE_MAP = {
    "camera_framing": ("renderProfiles", "camera"),
    "silhouette_iou": ("parts", "mass"),
    "boundary_f": ("parts", "mass"),
    "contour_distance": ("parts", "contour"),
    "landmark_coverage": ("poseProfile", "landmarks"),
    "part_visibility": ("parts", "pose"),
    "attachment_contact": ("parts", "attachment"),
    "material_readability": ("materials", "environment"),
    "BLACK_CRUSH": ("materials", "environment"),
    "ATTACHMENT_GAP": ("parts", "attachment"),
    "HANDEDNESS_FLIP": ("poseProfile", "handedness"),
}


def map_issue_to_scope(issue_or_metric_id: str) -> dict[str, Any]:
    scope = ISSUE_SCOPE_MAP.get(issue_or_metric_id, ("parts", "unknown"))
    return {
        "issueId": issue_or_metric_id,
        "root": scope[0],
        "scope": scope[1],
        "allowedPatchPrefixes": [p for p in ALLOWED_PATCH_PREFIXES if scope[0] in p or p.endswith(scope[0])],
    }


def validate_json_patch(patch: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if not isinstance(patch, list):
        return ["$: expected JSON Patch array"]
    for index, op in enumerate(patch):
        path = f"$[{index}]"
        if not isinstance(op, dict):
            errors.append(f"{path}: expected object")
            continue
        operation = op.get("op")
        if operation not in ALLOWED_OPS:
            errors.append(f"{path}.op: unsupported op {operation!r}")
        target = op.get("path")
        if not isinstance(target, str) or not target.startswith("/"):
            errors.append(f"{path}.path: expected JSON pointer")
            continue
        if not any(target == p.rstrip("/") or target.startswith(p) for p in ALLOWED_PATCH_PREFIXES):
            # also allow exact roots without trailing slash variants
            allowed = False
            for prefix in ALLOWED_PATCH_PREFIXES:
                root = prefix.rstrip("/")
                if target == root or target.startswith(root + "/"):
                    allowed = True
                    break
            if not allowed:
                errors.append(f"{path}.path: path {target!r} outside allowed patch surface")
        if operation in ("replace", "add") and "value" in op:
            value = op["value"]
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if not (-1000 <= float(value) <= 1000):
                    errors.append(f"{path}.value: numeric value out of allowed range")
            if isinstance(value, list) and value and all(isinstance(v, (int, float)) for v in value):
                if any(abs(float(v)) > 1000 for v in value):
                    errors.append(f"{path}.value: numeric array value out of allowed range")
    return errors


def apply_json_patch(document: dict[str, Any], patch: list[dict[str, Any]]) -> dict[str, Any]:
    errors = validate_json_patch(patch)
    if errors:
        raise ValueError("; ".join(errors))
    doc = copy.deepcopy(document)
    for op in patch:
        pointer = op["path"].strip("/").split("/") if op["path"] != "/" else []
        operation = op["op"]
        if operation == "replace":
            _set_pointer(doc, pointer, op["value"])
        elif operation == "add":
            _set_pointer(doc, pointer, op["value"])
        elif operation == "remove":
            _remove_pointer(doc, pointer)
        else:
            raise ValueError(f"op {operation} not implemented in MVP applicator")
    return doc


def _set_pointer(doc: Any, pointer: list[str], value: Any) -> None:
    cur = doc
    for key in pointer[:-1]:
        if key.isdigit() and isinstance(cur, list):
            cur = cur[int(key)]
        else:
            cur = cur[key]
    last = pointer[-1]
    if last.isdigit() and isinstance(cur, list):
        cur[int(last)] = value
    else:
        cur[last] = value


def _remove_pointer(doc: Any, pointer: list[str]) -> None:
    cur = doc
    for key in pointer[:-1]:
        if key.isdigit() and isinstance(cur, list):
            cur = cur[int(key)]
        else:
            cur = cur[key]
    last = pointer[-1]
    if last.isdigit() and isinstance(cur, list):
        cur.pop(int(last))
    else:
        del cur[last]


@dataclass
class IterationGraph:
    records: list[dict[str, Any]] = field(default_factory=list)
    best_revision_id: str | None = None
    best_score: float = float("-inf")

    def add(
        self,
        *,
        revision_id: str,
        parent_id: str | None,
        blueprint: dict[str, Any],
        score: float,
        metrics: list[dict[str, Any]] | None = None,
        critical_ids: set[str] | None = None,
    ) -> dict[str, Any]:
        record = {
            "revisionId": revision_id,
            "parentId": parent_id,
            "score": score,
            "blueprintHash": content_hash(blueprint, ignored_paths=(("revision", "contentHash"),)),
            "metrics": metrics or [],
            "criticalIds": sorted(critical_ids or set()),
        }
        self.records.append(record)
        if score > self.best_score:
            self.best_score = score
            self.best_revision_id = revision_id
        return record

    def parents(self, revision_id: str) -> list[str]:
        by_id = {r["revisionId"]: r for r in self.records}
        chain: list[str] = []
        current = revision_id
        seen: set[str] = set()
        while current and current in by_id and current not in seen:
            seen.add(current)
            chain.append(current)
            current = by_id[current].get("parentId")
        return chain

    def detect_critical_regression(
        self,
        candidate_metrics: list[dict[str, Any]],
        baseline_metrics: list[dict[str, Any]],
        *,
        critical_ids: set[str],
    ) -> list[dict[str, Any]]:
        base = {
            (m["id"], str(m.get("viewId") or "")): m
            for m in baseline_metrics
            if "id" in m
        }
        regressions = []
        for metric in candidate_metrics:
            mid = metric.get("id")
            key = (mid, str(metric.get("viewId") or ""))
            if mid not in critical_ids or key not in base:
                continue
            baseline = base[key]
            if float(metric.get("value") or 0) + 1e-9 < float(baseline.get("value") or 0):
                if baseline.get("passed") and not metric.get("passed"):
                    regressions.append(
                        {
                            "metricId": mid,
                            "viewId": metric.get("viewId"),
                            "baseline": baseline.get("value"),
                            "candidate": metric.get("value"),
                        }
                    )
                elif float(metric.get("value") or 0) < float(baseline.get("value") or 0) - 0.05:
                    regressions.append(
                        {
                            "metricId": mid,
                            "viewId": metric.get("viewId"),
                            "baseline": baseline.get("value"),
                            "candidate": metric.get("value"),
                        }
                    )
        return regressions

    def to_dict(self) -> dict[str, Any]:
        return {
            "records": self.records,
            "bestRevisionId": self.best_revision_id,
            "bestScore": self.best_score,
        }


def score_metrics(metrics: list[dict[str, Any]]) -> float:
    if not metrics:
        return 0.0
    return sum(float(m.get("value") or 0) for m in metrics) / len(metrics)
