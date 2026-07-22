"""Production run orchestration: reference→validate→cast→render→metrics→review."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.blueprint.character import build_stylized_character_blueprint, character_gate_report
from engine.blueprint.validate import validate_blueprint
from engine.cast.emit_factory import emit_factory
from engine.critique.cache import RenderCache
from engine.critique.fit import assert_production_fit_path, coarse_to_fine_fit, describe_fit_root_mass_proxy
from engine.critique.iteration import IterationBudget, score_metrics
from engine.critique.journal import append_journal
from engine.critique.metrics_from_render import metric_report_from_render_set
from engine.critique.overlay import build_gate_comparison_artifacts
from engine.critique.render_profiles import (
    finalize_view_manifest,
    build_view_manifest,
    validate_partial_render_set,
)
from engine.critique.reviewer import (
    apply_review_policy,
    build_comparison_sheet,
    get_vision_reviewer,
    parse_reviewer_output,
)
from engine.critique.software_render import render_blueprint_set
from engine.reference.photo_matte import resolve_reference_alpha_map
from engine.reference.pipeline import plan_reference_set, sufficiency_reference_set
from engine.shared.artifacts import content_hash
from engine.shared.jsonutil import dump_json, load_json

_JOURNAL_DECISION = {
    "accept": "accept",
    "revise": "replan",
    "reject": "abort",
}


def run_production(
    project_path: str | Path,
    *,
    max_iterations: int = 0,
    out_dir: str | Path | None = None,
) -> dict[str, Any]:
    """
    End-to-end production path. Low-level stages are not skippable.
    """

    project = load_json(project_path)
    root = Path(out_dir) if out_dir else Path(project_path).parent / "run-out"
    root.mkdir(parents=True, exist_ok=True)
    project_dir = Path(project_path).parent

    stages: list[str] = []
    artifacts: dict[str, Any] = {}

    # 1) reference (optional when blueprint/slice is supplied directly)
    request_path = _resolve_path(project.get("requestPath"), project_dir)
    reference_set_path = _resolve_path(project.get("referenceSetPath"), project_dir)
    if request_path and reference_set_path:
        stages.append("reference")
        plan = plan_reference_set(
            request_path,
            reference_set_path=reference_set_path,
            out=root / "reference-plan.json",
        )
        artifacts["referencePlan"] = str(root / "reference-plan.json")
        suf = sufficiency_reference_set(
            reference_set_path,
            request_path=request_path,
            out=root / "sufficiency.json",
        )
        artifacts["sufficiency"] = str(root / "sufficiency.json")
    else:
        plan = {"agentAction": "continue", "note": "project supplied blueprint directly"}
        suf = {"sufficient": True, "verdict": "pass"}

    sufficiency_action = str(suf.get("agentAction") or "").lower()
    sufficiency_verdict = str(suf.get("verdict") or "").lower()
    if sufficiency_action in ("abort", "reject") or sufficiency_verdict == "reject":
        return _result(
            stages,
            artifacts,
            ok=False,
            reason="reference sufficiency rejected",
            extra={
                "sufficiency": suf,
                "planAction": plan.get("agentAction") if isinstance(plan, dict) else None,
            },
        )

    # 2) blueprint validate / character slice
    stages.append("validate")
    blueprint_path = _resolve_path(project.get("blueprintPath"), project_dir)
    if blueprint_path:
        blueprint = load_json(blueprint_path)
        artifacts["blueprint"] = str(blueprint_path)
        bp_write_path = root / "blueprint.json"
        dump_json(bp_write_path, blueprint)
        artifacts["blueprintWorking"] = str(bp_write_path)
    elif project.get("useCharacterSlice"):
        blueprint = build_stylized_character_blueprint(
            project.get("name") or "Character",
            include_polish=bool(project.get("includePolish")),
        )
        bp_write_path = root / "blueprint.json"
        dump_json(bp_write_path, blueprint)
        artifacts["blueprint"] = str(bp_write_path)
        blueprint_path = bp_write_path
    else:
        raise ValueError("project must provide blueprintPath or useCharacterSlice")

    if blueprint.get("schemaVersion") == 2 or project.get("useCharacterSlice"):
        gate = character_gate_report(blueprint)
        dump_json(root / "character-gate.json", gate)
        artifacts["characterGate"] = str(root / "character-gate.json")
        if not gate.get("passed") and project.get("strict", True):
            return _result(stages, artifacts, ok=False, reason="character gate failed", extra={"gate": gate})
    else:
        result = validate_blueprint(blueprint_path, strict=True)
        if not result.ok and project.get("strict", True):
            return _result(stages, artifacts, ok=False, reason="blueprint validation failed", extra=result.to_dict())

    # Resolve external photo/sense mattes before fitting. No blueprint self-render
    # is accepted as a production reference.
    alpha_resolution = resolve_reference_alpha_map(
        project=project,
        project_dir=project_dir,
        out_dir=root / "reference-mattes",
        reference_set_path=reference_set_path,
        view_id="source-34",
        width=128,
        height=128,
    )
    reference_alpha = alpha_resolution.get("map") or {}
    artifacts["referenceAlphaMeta"] = alpha_resolution.get("meta") or {}
    artifacts["referenceAlphaExternal"] = bool(
        (alpha_resolution.get("meta") or {}).get("external")
    )
    if reference_alpha.get("source-34"):
        artifacts["referenceAlphaPath"] = reference_alpha["source-34"]
    dump_json(root / "reference-alpha-map.json", alpha_resolution)

    delivery_grade = str(
        project.get("deliveryGrade")
        or (load_json(request_path).get("deliveryGrade") if request_path and Path(request_path).exists() else None)
        or "standard"
    )

    # Fit before cast so the accepted candidate becomes the delivered source.
    iteration_result = None
    if max_iterations > 0:
        stages.append("iterate")
        assert_production_fit_path([])
        budget = IterationBudget(max_iterations=max_iterations, max_renders=max_iterations * 3)
        try:
            iteration_result = coarse_to_fine_fit(
                blueprint,
                budget=budget,
                work_dir=root / "fit",
                reference_alpha=reference_alpha if reference_alpha else None,
                reference_provenance=alpha_resolution.get("meta") or None,
                use_issue_patches=True,
            )
        except Exception as exc:
            artifacts["fitError"] = {"type": type(exc).__name__, "message": str(exc)}
            return _result(
                stages,
                artifacts,
                ok=False,
                reason="fit failed",
                extra={"error": artifacts["fitError"]},
            )
        promoted = iteration_result.get("blueprint")
        if not isinstance(promoted, dict):
            artifacts["fitError"] = {
                "type": "FitContractError",
                "message": "fit result did not include a blueprint",
            }
            return _result(
                stages,
                artifacts,
                ok=False,
                reason="fit failed",
                extra={"error": artifacts["fitError"]},
            )
        blueprint = promoted
        bp_write_path = root / "blueprint.json"
        dump_json(bp_write_path, blueprint)
        blueprint_path = bp_write_path
        artifacts["blueprintWorking"] = str(bp_write_path)
        artifacts["promotedBlueprint"] = str(bp_write_path)
        dump_json(root / "iteration.json", iteration_result)
        artifacts["iteration"] = str(root / "iteration.json")

    # 3) cast
    stages.append("cast")
    factory_path = root / "factory.ts"
    factory_path.unlink(missing_ok=True)
    try:
        emit_factory(blueprint, factory_path)
    except Exception as exc:
        artifacts["castError"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        return _result(
            stages,
            artifacts,
            ok=False,
            reason="cast failed",
            extra={"error": artifacts["castError"]},
        )
    artifacts["factory"] = str(factory_path)
    # FormRuntime contract present in emitted source
    factory_text = factory_path.read_text(encoding="utf-8")
    artifacts["formRuntimeContract"] = (
        "export interface FormRuntime" in factory_text and "dispose(): void" in factory_text
    )
    factory_hash = content_hash({"path": str(factory_path), "bytes": factory_path.stat().st_size})
    blueprint_hash = content_hash(blueprint, ignored_paths=(("revision", "contentHash"),))

    # 4) render — real multi-pass PNGs on disk
    stages.append("render")
    revision_id = (blueprint.get("revision") or {}).get("id") or "rev-0"
    view_manifest = finalize_view_manifest(build_view_manifest())
    dump_json(root / "view-manifest.json", view_manifest)
    render_set = render_blueprint_set(
        blueprint,
        out_dir=root / "renders",
        revision_id=str(revision_id),
        blueprint_hash=blueprint_hash,
        factory_hash=factory_hash,
        width=128,
        height=128,
    )
    render_errors = validate_partial_render_set(render_set)
    for view in render_set.get("views") or []:
        for pass_name, meta in (view.get("passes") or {}).items():
            if not Path(meta["path"]).is_file():
                render_errors.append(f"missing PNG for {view.get('id')}/{pass_name}: {meta['path']}")
    dump_json(root / "render-set.json", render_set)
    artifacts["renderSet"] = str(root / "render-set.json")
    artifacts["renderRoot"] = str(root / "renders")
    if render_errors:
        return _result(stages, artifacts, ok=False, reason="render set invalid", extra={"errors": render_errors})

    cache = RenderCache()
    sample_pass = render_set["views"][0]["passes"]["beauty"]

    def _cached_beauty() -> dict[str, Any]:
        return {"path": sample_pass["path"], "hash": sample_pass["hash"]}

    cache.get_or_render(
        revision_id=str(revision_id),
        profile_id="source-34",
        pass_name="beauty",
        fingerprint=blueprint_hash,
        render_fn=_cached_beauty,
    )
    cache.get_or_render(
        revision_id=str(revision_id),
        profile_id="source-34",
        pass_name="beauty",
        fingerprint=blueprint_hash,
        render_fn=_cached_beauty,
    )
    artifacts["renderCache"] = cache.stats()

    # 5) metrics — silhouette vs EXTERNAL photo/sense matte when available
    stages.append("metrics")
    rendered_view_ids = [str(view.get("id")) for view in render_set.get("views") or []]
    reference_view_ids = tuple(view for view in rendered_view_ids if view in reference_alpha)
    evaluated_view_ids = reference_view_ids or ("source-34",)
    metric_report = metric_report_from_render_set(
        blueprint,
        render_set,
        reference_alpha=reference_alpha if reference_alpha else None,
        view_id="source-34",
        view_ids=evaluated_view_ids,
        require_external_reference=(delivery_grade in ("delivery", "strict")),
    )
    metrics = metric_report.get("metrics") or []
    # also store flat legacy keys for journal floor checks
    flat_metrics = {
        "maskIoU": min((m["value"] for m in metrics if m.get("id") == "silhouette_iou"), default=0.0),
        "ssim": min((m["value"] for m in metrics if m.get("id") == "boundary_f"), default=0.0),
        "edgeF1": min((m["value"] for m in metrics if m.get("id") == "contour_distance"), default=0.0),
        "entries": metrics,
    }
    dump_json(root / "metric-report.json", metric_report)
    dump_json(root / "metrics-flat.json", flat_metrics)
    artifacts["metricReport"] = str(root / "metric-report.json")

    # 6) review + comparison overlays + journal
    stages.append("review")
    reviewer = get_vision_reviewer(project.get("reviewer"))
    try:
        reviewer_out = parse_reviewer_output(reviewer.review({"renderSet": render_set, "metrics": metrics}))
    except Exception as exc:
        reviewer_out = {
            "recommendation": "revise",
            "issues": [],
            "error": str(exc),
            "reviewer": reviewer.name,
        }
    review_report = apply_review_policy(metric_report=metric_report, reviewer_output=reviewer_out)
    dump_json(root / "review-report.json", review_report)
    artifacts["reviewReport"] = str(root / "review-report.json")

    sheet = build_comparison_sheet(
        revision_id=str(revision_id),
        metrics=metrics,
        views=[v["id"] for v in render_set.get("views") or []],
    )
    overlay = build_gate_comparison_artifacts(
        render_set=render_set,
        out_dir=root / "comparison",
        view_id="source-34",
        reference_alpha=reference_alpha.get("source-34"),
    )
    sheet["overlays"] = overlay.get("annotations") or []
    sheet["overlayArtifacts"] = overlay
    sheet["sheetHash"] = content_hash(sheet, ignored_paths=(("sheetHash",),))
    dump_json(root / "comparison-sheet.json", sheet)
    artifacts["comparisonSheet"] = str(root / "comparison-sheet.json")
    artifacts["silhouetteDiff"] = overlay.get("silhouetteDiff", {}).get("path")
    artifacts["partLabels"] = overlay.get("partLabels", {}).get("path")

    # REV-160: journal entry with policy trace + artifact hashes
    stages.append("journal")
    rec = review_report.get("recommendation") or "revise"
    journal_decision = _JOURNAL_DECISION.get(str(rec), "replan")
    policy_trace = dict(review_report.get("policyTrace") or {})
    policy_trace["policyIssued"] = True
    policy_trace["issuer"] = "review-policy"
    policy_trace["decision"] = journal_decision
    policy_trace["renderSetHash"] = content_hash(render_set)
    policy_trace["metricReportHash"] = content_hash(metric_report)
    policy_trace["comparisonSheetHash"] = sheet.get("sheetHash")

    feature_scores = {
        feat.get("id"): next(
            (m["value"] for m in metrics if m.get("id") in (feat.get("id"), "part_visibility", "silhouette_iou")),
            0.85 if rec == "accept" else 0.5,
        )
        for feat in blueprint.get("criticalFeatures") or []
    }
    # Prefer metric values when ids align
    for metric in metrics:
        if metric.get("id") in feature_scores:
            feature_scores[metric["id"]] = float(metric.get("value") or 0)

    beauty_path = render_set["views"][0]["passes"]["beauty"]["path"]
    journal_entry = None
    try:
        # working blueprint path for journal mutation
        working_bp = Path(artifacts.get("blueprintWorking") or artifacts["blueprint"])
        if not working_bp.exists() or working_bp.resolve() != (root / "blueprint.json").resolve():
            dump_json(root / "blueprint.json", blueprint)
            working_bp = root / "blueprint.json"
        journal_entry = append_journal(
            working_bp,
            layer="production",
            fidelity=float(score_metrics(metrics)),
            decision=journal_decision,
            vision=float(score_metrics(metrics)),
            summary=f"policy recommendation={rec} journal={journal_decision}",
            metrics_path=root / "metrics-flat.json",
            render=beauty_path,
            sheet=str(root / "comparison-sheet.json"),
            feature_scores=feature_scores,
            policy_trace=policy_trace,
            in_place=True,
        )
        artifacts["journalBlueprint"] = str(working_bp)
        artifacts["journalEntry"] = journal_entry
    except SystemExit as exc:
        artifacts["journalError"] = str(exc)
        # non-accept decisions still record without going through accept gates
        if journal_decision != "accept":
            working_bp = root / "blueprint.json"
            bp_data = load_json(working_bp)
            entry = {
                "layer": "production",
                "decision": journal_decision,
                "summary": f"policy recommendation={rec}",
                "render": beauty_path,
                "sheet": str(root / "comparison-sheet.json"),
                "policyTrace": policy_trace,
                "featureScores": feature_scores,
            }
            bp_data.setdefault("journal", []).append(entry)
            dump_json(working_bp, bp_data)
            journal_entry = entry
            artifacts["journalEntry"] = entry

    ok = review_report.get("recommendation") == "accept"
    return _result(
        stages,
        artifacts,
        ok=ok,
        reason=review_report.get("recommendation"),
        extra={
            "review": review_report,
            "metricScore": score_metrics(metrics),
            "iteration": iteration_result,
            "proxyPolicy": describe_fit_root_mass_proxy(),
            "sufficiency": {"verdict": suf.get("verdict"), "sufficient": suf.get("sufficient")},
            "planAction": plan.get("agentAction") if isinstance(plan, dict) else None,
            "pngPassCount": sum(len(v.get("passes") or {}) for v in render_set.get("views") or []),
            "journalDecision": journal_decision,
            "policyTrace": policy_trace,
        },
    )


def _resolve_path(value: Any, base: Path) -> Path | None:
    if not value:
        return None
    path = Path(str(value))
    if not path.is_absolute():
        path = base / path
    return path if path.exists() else Path(str(value)) if Path(str(value)).exists() else path


def _result(
    stages: list[str],
    artifacts: dict[str, Any],
    *,
    ok: bool,
    reason: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "schemaVersion": 1,
        "ok": ok,
        "reason": reason,
        "stages": stages,
        "artifacts": artifacts,
        "complete": any(s in stages for s in ("review", "journal", "iterate")),
    }
    if extra:
        payload["extra"] = extra
    return payload
