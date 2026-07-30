"""Benchmark runner with explicit failure accounting.

Executes each fixture in a manifest through the production path, records
environment metadata, and produces per-fixture results plus an aggregate
summary. Missing renders, crashes, and timeouts are explicit failure states
that are never hidden from the aggregate denominator.
"""

from __future__ import annotations

import platform
import sys
import time
import traceback
from pathlib import Path
from typing import Any

from engine.benchmark.manifest import parse_manifest, validate_manifest
from engine.shared.jsonutil import dump_json, load_json


# --- Fixture result status values ---
STATUS_PASS = "pass"
STATUS_CONDITIONAL = "conditional"
STATUS_FAIL = "fail"
STATUS_CRASH = "crash"
STATUS_TIMEOUT = "timeout"
STATUS_MISSING_RENDER = "missing-render"
STATUS_SKIPPED = "skipped"

ALL_STATUSES = (
    STATUS_PASS,
    STATUS_CONDITIONAL,
    STATUS_FAIL,
    STATUS_CRASH,
    STATUS_TIMEOUT,
    STATUS_MISSING_RENDER,
    STATUS_SKIPPED,
)


def collect_environment() -> dict[str, Any]:
    """Capture environment metadata for reproducibility."""
    return {
        "pythonVersion": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "node": platform.node(),
        "engineVersion": _engine_version(),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }


def _engine_version() -> str:
    try:
        from engine import __version__
        return __version__
    except (ImportError, AttributeError):
        return "0.2.0-dev"


def run_benchmark(
    manifest_path: str | Path,
    *,
    out_dir: str | Path,
    timeout_seconds: float = 120.0,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run all fixtures in a benchmark manifest.

    Args:
        manifest_path: Path to the benchmark manifest JSON.
        out_dir: Directory for output artifacts (created if missing).
        timeout_seconds: Per-fixture wall-clock limit.
        dry_run: If True, validate manifest and report plan without executing.

    Returns:
        Benchmark report dict with environment, per-fixture results, and summary.
    """
    manifest_path = Path(manifest_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = load_json(manifest_path)
    errors = validate_manifest(raw)
    if errors:
        return {
            "ok": False,
            "error": "manifest-validation-failed",
            "validationErrors": errors,
        }

    manifest = parse_manifest(raw)
    fixtures = manifest["fixtures"]
    environment = collect_environment()

    if dry_run:
        return {
            "ok": True,
            "dryRun": True,
            "environment": environment,
            "fixtureCount": len(fixtures),
            "fixtures": [{"id": f["id"], "category": f["category"]} for f in fixtures],
        }

    results: list[dict[str, Any]] = []
    for fixture in fixtures:
        result = _run_single_fixture(
            fixture,
            manifest_path=manifest_path,
            out_dir=out_dir,
            timeout_seconds=timeout_seconds,
        )
        results.append(result)

    summary = _build_summary(results)

    report = {
        "ok": True,
        "schemaVersion": 1,
        "manifestPath": str(manifest_path),
        "environment": environment,
        "results": results,
        "summary": summary,
    }

    dump_json(out_dir / "benchmark-report.json", report)
    return report


def _run_single_fixture(
    fixture: dict[str, Any],
    *,
    manifest_path: Path,
    out_dir: Path,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Execute one fixture through the production path."""
    fid = fixture["id"]
    fixture_out = out_dir / fid
    fixture_out.mkdir(parents=True, exist_ok=True)

    start = time.monotonic()
    result: dict[str, Any] = {
        "id": fid,
        "category": fixture.get("category"),
        "profile": fixture.get("profile"),
    }

    try:
        project_path = _resolve_project_path(fixture, manifest_path)
        if project_path is None:
            result["status"] = STATUS_SKIPPED
            result["reason"] = "no-project-path-resolvable"
            result["elapsedSeconds"] = round(time.monotonic() - start, 3)
            return result

        if not project_path.is_file():
            result["status"] = STATUS_MISSING_RENDER
            result["reason"] = f"project path not found: {project_path}"
            result["elapsedSeconds"] = round(time.monotonic() - start, 3)
            return result

        from engine.orchestration.run import run_production

        run_result = run_production(
            str(project_path),
            out_dir=str(fixture_out),
        )
        elapsed = time.monotonic() - start
        result["elapsedSeconds"] = round(elapsed, 3)

        if elapsed > timeout_seconds:
            result["status"] = STATUS_TIMEOUT
            result["reason"] = f"exceeded {timeout_seconds}s limit"
            return result

        reason = str(run_result.get("reason") or run_result.get("error") or "")
        stages = run_result.get("stages") or []
        render_expected = bool(run_result.get("ok")) or "render" in stages or reason in {
            "accept",
            "conditional",
            "revise",
            "reject",
        }
        missing_outputs = (
            _required_output_errors(fixture, run_result, fixture_out=fixture_out)
            if render_expected
            else []
        )
        if missing_outputs:
            result["status"] = STATUS_MISSING_RENDER
            result["reason"] = "; ".join(missing_outputs)
        elif run_result.get("ok"):
            verdict = str(run_result.get("verdict") or reason).lower()
            result["status"] = (
                STATUS_CONDITIONAL
                if verdict == "conditional" or run_result.get("conditional")
                else STATUS_PASS
            )
        elif reason.lower() in {"conditional", "revise"}:
            result["status"] = STATUS_CONDITIONAL
            result["reason"] = reason
        else:
            result["status"] = STATUS_FAIL
            result["reason"] = reason or "production-run-failed"

        result["artifacts"] = _collect_artifacts(fixture_out)
        result["productionResult"] = _summarize_production_result(run_result)

    except Exception as exc:
        elapsed = time.monotonic() - start
        result["status"] = STATUS_CRASH
        result["reason"] = f"{type(exc).__name__}: {exc}"
        result["traceback"] = traceback.format_exc()
        result["elapsedSeconds"] = round(elapsed, 3)

    return result


def _required_output_errors(
    fixture: dict[str, Any],
    run_result: dict[str, Any],
    *,
    fixture_out: Path,
) -> list[str]:
    """Return errors for absent required views, passes, or pass files."""
    artifacts = run_result.get("artifacts") or {}
    render_set_value = artifacts.get("renderSet") if isinstance(artifacts, dict) else None
    if not render_set_value:
        return ["production result did not report a renderSet artifact"]

    render_set_path = Path(str(render_set_value))
    if not render_set_path.is_absolute():
        render_set_path = fixture_out / render_set_path
    if not render_set_path.is_file():
        return [f"renderSet artifact not found: {render_set_path}"]

    try:
        render_set = load_json(render_set_path)
    except Exception as exc:
        return [f"renderSet artifact unreadable: {type(exc).__name__}: {exc}"]

    views_by_id = {
        str(view.get("id")): view
        for view in (render_set.get("views") or [])
        if isinstance(view, dict) and view.get("id") is not None
    }
    expected_views = [
        str(view.get("id"))
        for view in [*(fixture.get("views") or []), *(fixture.get("heldOutViews") or [])]
        if isinstance(view, dict) and view.get("id") is not None
    ]
    required_passes = [str(value) for value in (fixture.get("requiredPasses") or [])]
    errors: list[str] = []

    for view_id in expected_views:
        view = views_by_id.get(view_id)
        if view is None:
            errors.append(f"required render view missing: {view_id}")
            continue
        passes = view.get("passes") or {}
        for pass_name in required_passes:
            pass_meta = passes.get(pass_name)
            if not isinstance(pass_meta, dict):
                errors.append(f"required render pass missing: {view_id}/{pass_name}")
                continue
            pass_path_value = pass_meta.get("path")
            if not pass_path_value:
                errors.append(f"required render path missing: {view_id}/{pass_name}")
                continue
            pass_path = Path(str(pass_path_value))
            if not pass_path.is_absolute():
                pass_path = render_set_path.parent / pass_path
            if not pass_path.is_file():
                errors.append(f"required render file missing: {view_id}/{pass_name}: {pass_path}")

    return errors


def _resolve_project_path(fixture: dict[str, Any], manifest_path: Path) -> Path | None:
    """Resolve the project.json path for a fixture.

    Looks for a projectPath field, then tries to find project.json in the
    fixture's source directory relative to the manifest.
    """
    # Direct project path
    project_path = fixture.get("projectPath")
    if project_path:
        path = manifest_path.parent / project_path
        return path

    # Try source-relative resolution
    source = fixture.get("source", {})
    source_dir = source.get("directory")
    if source_dir:
        candidate = manifest_path.parent / source_dir / "project.json"
        if candidate.exists():
            return candidate

    return None


def _collect_artifacts(fixture_out: Path) -> dict[str, Any]:
    """Collect paths of generated artifacts in the fixture output directory."""
    artifacts: dict[str, str] = {}
    for item in sorted(fixture_out.iterdir()):
        if item.is_file() and item.suffix == ".json":
            artifacts[item.stem] = str(item)
    return artifacts


def _summarize_production_result(run_result: dict[str, Any]) -> dict[str, Any]:
    """Extract a safe summary from a production run result (no large payloads)."""
    keys_to_keep = ("ok", "verdict", "stages", "error", "reason", "conditional")
    return {k: run_result[k] for k in keys_to_keep if k in run_result}


def _build_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Build an aggregate summary from fixture results.

    The denominator always equals len(results) — failures cannot disappear.
    """
    total = len(results)
    by_status: dict[str, int] = {s: 0 for s in ALL_STATUSES}
    by_category: dict[str, dict[str, int]] = {}

    for result in results:
        status = result.get("status", STATUS_CRASH)
        by_status[status] = by_status.get(status, 0) + 1

        category = result.get("category") or "unknown"
        if category not in by_category:
            by_category[category] = {s: 0 for s in ALL_STATUSES}
        by_category[category][status] = by_category[category].get(status, 0) + 1

    return {
        "total": total,
        "byStatus": by_status,
        "byCategory": by_category,
        "passRate": round(by_status[STATUS_PASS] / total, 4) if total else 0.0,
        "failureRate": round(
            (total - by_status[STATUS_PASS] - by_status[STATUS_CONDITIONAL]) / total,
            4,
        )
        if total
        else 0.0,
    }
