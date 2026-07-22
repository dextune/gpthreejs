"""Production fit path: mark experimental proxy and render-in-loop coarse-to-fine."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable

from engine.critique.iteration import (
    IterationBudget,
    IterationGraph,
    score_metrics,
)
from engine.shared.artifacts import content_hash
from engine.shared.jsonutil import dump_json

EXPERIMENTAL_PROXY_NAME = "fit_root_mass"
EXPERIMENTAL_PROXY_TAG = "experimental-proxy"


def describe_fit_root_mass_proxy() -> dict[str, Any]:
    return {
        "name": EXPERIMENTAL_PROXY_NAME,
        "tag": EXPERIMENTAL_PROXY_TAG,
        "productionAllowed": False,
        "reason": "96x96 matte proxy optimizes the wrong objective for character production",
    }


def assert_production_fit_path(call_stack_names: list[str]) -> None:
    if EXPERIMENTAL_PROXY_NAME in call_stack_names:
        raise RuntimeError(
            f"{EXPERIMENTAL_PROXY_NAME} is {EXPERIMENTAL_PROXY_TAG} and forbidden on production path"
        )


def evaluate_blueprint_render_metrics(
    blueprint: dict[str, Any],
    *,
    work_dir: str | Path,
    reference_alpha: dict[str, str] | None = None,
    view_id: str = "source-34",
    view_ids: tuple[str, ...] | list[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Render alpha/part-ID passes and compute metrics from the PNG files."""

    from engine.critique.metrics_from_render import metrics_from_render_set
    from engine.critique.software_render import render_blueprint_set

    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    rev = (blueprint.get("revision") or {}).get("id") or "rev-eval"
    bp_hash = content_hash(blueprint, ignored_paths=(("revision", "contentHash"),))
    requested_views = tuple(view_ids or (view_id,))
    render_set = render_blueprint_set(
        blueprint,
        out_dir=work / "renders",
        revision_id=str(rev),
        blueprint_hash=bp_hash,
        factory_hash=content_hash({"eval": True}),
        views=requested_views,
        width=96,
        height=96,
    )
    dump_json(work / "render-set.json", render_set)
    metrics = metrics_from_render_set(
        blueprint,
        render_set,
        reference_alpha=reference_alpha,
        view_id=view_id,
        view_ids=requested_views,
    )
    return metrics, render_set


def coarse_to_fine_fit(
    blueprint: dict[str, Any],
    *,
    evaluate: Callable[[dict[str, Any]], list[dict[str, Any]]] | None = None,
    budget: IterationBudget | None = None,
    stages: tuple[str, ...] = ("camera", "global_mass", "major_part"),
    work_dir: str | Path | None = None,
    critical_ids: set[str] | None = None,
    reference_alpha: dict[str, str] | None = None,
    reference_provenance: dict[str, Any] | None = None,
    use_issue_patches: bool = False,
) -> dict[str, Any]:
    """
    Render-in-loop coarse-to-fine MVP with critical regression rollback.

    When ``evaluate`` is omitted, uses real software-render alpha/part-ID metrics.
    A caller-supplied reference alpha is normalized and used instead of a
    Blueprint self-baseline.
    When ``use_issue_patches`` is true, failed metrics drive constrained JSON patches
    (ITER-110) instead of fixed stage perturbations only.
    """

    budget = budget or IterationBudget(max_iterations=6, max_renders=12)
    graph = IterationGraph()
    work = Path(work_dir) if work_dir else Path(".")
    critical = critical_ids or {
        "helmet_identity",
        "part_visibility",
        "silhouette_iou",
        "attachment_contact",
    }

    from engine.critique.issue_patch import apply_issue_driven_patch

    ref_dir = work / "fit-ref"
    ref_dir.mkdir(parents=True, exist_ok=True)
    if reference_alpha:
        ref_alpha, ref_provenance = _prepare_external_reference_alpha(
            reference_alpha,
            ref_dir=ref_dir,
            metadata=reference_provenance,
        )
    else:
        from engine.critique.software_render import reference_alpha_from_blueprint

        ref_alpha = {
            "source-34": reference_alpha_from_blueprint(
                blueprint,
                view_id="source-34",
                out_path=ref_dir / "source-34-alpha.png",
                width=96,
                height=96,
            )
        }
        ref_provenance = {
            "source": "blueprint-self-baseline",
            "external": False,
            "selfBaseline": True,
            "sourcePaths": {},
            "resolvedPaths": dict(ref_alpha),
            "metadata": {},
        }

    def default_evaluate(bp: dict[str, Any]) -> list[dict[str, Any]]:
        from engine.critique.render_profiles import VIEW_PROFILE_IDS

        evaluation_views = tuple(view for view in VIEW_PROFILE_IDS if view in ref_alpha) or ("source-34",)
        metrics, _rs = evaluate_blueprint_render_metrics(
            bp,
            work_dir=work / f"eval-{budget.iterations}",
            reference_alpha=ref_alpha,
            view_ids=evaluation_views,
        )
        return metrics

    evaluate_fn = evaluate or default_evaluate

    current = blueprint
    parent_id = (blueprint.get("revision") or {}).get("id") or "rev-0"
    metrics = evaluate_fn(current)
    budget.renders += 1
    score = score_metrics(metrics)
    graph.add(
        revision_id=parent_id,
        parent_id=None,
        blueprint=current,
        score=score,
        metrics=metrics,
        critical_ids=critical,
    )
    best_bp = current
    best_metrics = metrics
    history = [{"stage": "initial", "revisionId": parent_id, "score": score, "accepted": True}]

    for stage in stages:
        if not budget.remaining():
            break
        applied_patches: list[dict[str, Any]] = []
        if use_issue_patches:
            failed = [m for m in metrics if not m.get("passed")]
            candidate, applied_patches = apply_issue_driven_patch(
                current,
                failed or metrics,
                step=budget.iterations + 1,
            )
            if not applied_patches:
                candidate = _perturb_for_stage(current, stage, step=budget.iterations + 1)
        else:
            candidate = _perturb_for_stage(current, stage, step=budget.iterations + 1)

        budget.iterations += 1
        budget.renders += 1
        cand_metrics = evaluate_fn(candidate)
        cand_score = score_metrics(cand_metrics)
        rev_id = f"rev-fit-{budget.iterations}"

        regressions = graph.detect_critical_regression(
            cand_metrics,
            best_metrics,
            critical_ids=critical,
        )
        if regressions:
            history.append(
                {
                    "stage": stage,
                    "revisionId": rev_id,
                    "score": cand_score,
                    "accepted": False,
                    "rollback": True,
                    "regressions": regressions,
                    "patches": applied_patches,
                }
            )
            graph.add(
                revision_id=rev_id,
                parent_id=parent_id,
                blueprint=candidate,
                score=cand_score,
                metrics=cand_metrics,
                critical_ids=critical,
            )
            budget.stagnant_steps += 1
        elif cand_score + 1e-9 >= score:
            graph.add(
                revision_id=rev_id,
                parent_id=parent_id,
                blueprint=candidate,
                score=cand_score,
                metrics=cand_metrics,
                critical_ids=critical,
            )
            current = candidate
            parent_id = rev_id
            score = cand_score
            metrics = cand_metrics
            if cand_score >= graph.best_score:
                best_bp = candidate
                best_metrics = cand_metrics
                graph.best_score = cand_score
                graph.best_revision_id = rev_id
            budget.stagnant_steps = 0
            history.append(
                {
                    "stage": stage,
                    "revisionId": rev_id,
                    "score": cand_score,
                    "accepted": True,
                    "rollback": False,
                    "patches": applied_patches,
                }
            )
        else:
            graph.add(
                revision_id=rev_id,
                parent_id=parent_id,
                blueprint=candidate,
                score=cand_score,
                metrics=cand_metrics,
                critical_ids=critical,
            )
            budget.stagnant_steps += 1
            history.append(
                {
                    "stage": stage,
                    "revisionId": rev_id,
                    "score": cand_score,
                    "accepted": False,
                    "rollback": False,
                    "patches": applied_patches,
                }
            )

    return {
        "schemaVersion": 1,
        "bestRevisionId": graph.best_revision_id,
        "bestScore": graph.best_score,
        "blueprint": best_bp,
        "history": history,
        "budget": budget.to_dict(),
        "graph": graph.to_dict(),
        "objective": "multi-view external alpha/part-id metrics from software render PNGs",
        "proxyUsed": False,
        "referenceAlpha": ref_alpha,
        "referenceProvenance": ref_provenance,
        "issueDrivenPatches": use_issue_patches,
    }


def _prepare_external_reference_alpha(
    reference_alpha: dict[str, str],
    *,
    ref_dir: Path,
    metadata: dict[str, Any] | None,
) -> tuple[dict[str, str], dict[str, Any]]:
    from engine.shared.pngio import read_png, resize_nearest, write_png

    source_paths: dict[str, str] = {}
    source_hashes: dict[str, str] = {}
    resolved_paths: dict[str, str] = {}
    for view, value in reference_alpha.items():
        source_path = Path(str(value))
        if not source_path.is_file():
            raise FileNotFoundError(f"external reference alpha not found: {source_path}")
        image = read_png(source_path)
        if image.width != 96 or image.height != 96:
            image = resize_nearest(image, 96, 96)
        resolved_path = ref_dir / f"{view}-external-alpha.png"
        write_png(resolved_path, image)
        source_paths[str(view)] = str(source_path)
        source_hashes[str(view)] = hashlib.sha256(source_path.read_bytes()).hexdigest()
        resolved_paths[str(view)] = str(resolved_path)
    if not resolved_paths:
        raise ValueError("external reference_alpha must include at least one view")
    return (
        resolved_paths,
        {
            "source": "caller-external",
            "external": True,
            "selfBaseline": False,
            "sourcePaths": source_paths,
            "sourceHashes": source_hashes,
            "resolvedPaths": resolved_paths,
            "metadata": dict(metadata or {}),
        },
    )


def _perturb_for_stage(blueprint: dict[str, Any], stage: str, *, step: int) -> dict[str, Any]:
    import copy

    bp = copy.deepcopy(blueprint)
    delta = 0.02 * ((step % 3) - 1)
    if stage == "camera":
        for profile in bp.get("renderProfiles") or []:
            cam = profile.get("camera") or {}
            pos = list(cam.get("position") or [0, 1, 2])
            pos[2] = float(pos[2]) + delta
            cam["position"] = pos
            profile["camera"] = cam
    elif stage == "global_mass":
        prop = bp.setdefault("proportionProfile", {})
        prop["shoulderWidthRatio"] = float(prop.get("shoulderWidthRatio") or 0.4) + delta
        prop["shoulderWidthRatio"] = min(0.9, max(0.2, prop["shoulderWidthRatio"]))
    elif stage == "major_part":
        parts = bp.get("parts") or []
        if parts:
            scale = list((parts[0].get("transform") or {}).get("scale") or [1, 1, 1])
            scale[0] = float(scale[0]) + delta
            scale[1] = float(scale[1]) + delta
            parts[0].setdefault("transform", {})["scale"] = scale
    rev = bp.setdefault("revision", {"id": "rev", "parent": None, "contentHash": ""})
    rev["id"] = f"{rev.get('id', 'rev')}-{stage}-{step}"
    rev["contentHash"] = content_hash(bp, ignored_paths=(("revision", "contentHash"),))
    return bp
