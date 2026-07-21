"""delivery-export: hard-gated packaging of run artifacts."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from engine.delivery.gates import evaluate_delivery_gates
from engine.orchestration.run import run_production
from engine.runtime.portable import emit_portable_bundle, utf8_gate
from engine.shared.artifacts import content_hash
from engine.shared.jsonutil import dump_json, load_json


def delivery_export(
    project_path: str | Path,
    *,
    out_dir: str | Path,
    max_iterations: int = 0,
    skip_run: bool = False,
    run_out: str | Path | None = None,
) -> dict[str, Any]:
    """
    Run production path (unless skip_run), evaluate DG-01…14, and package a portable
    delivery bundle only when all hard gates pass.
    """

    project_path = Path(project_path)
    project = load_json(project_path)
    project_dir = project_path.parent
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    work = Path(run_out) if run_out else out / "_run"
    if skip_run and (work / "review-report.json").exists():
        run_result = {
            "stages": ["validate", "cast", "render", "metrics", "review", "journal"],
            "artifacts": {
                "blueprint": str(work / "blueprint.json"),
                "factory": str(work / "factory.ts"),
                "renderSet": str(work / "render-set.json"),
                "metricReport": str(work / "metric-report.json"),
                "reviewReport": str(work / "review-report.json"),
                "comparisonSheet": str(work / "comparison-sheet.json"),
            },
            "ok": True,
            "extra": {},
        }
        # load ok from review
        rev = load_json(work / "review-report.json")
        run_result["ok"] = rev.get("recommendation") == "accept"
    else:
        run_result = run_production(
            project_path,
            max_iterations=max_iterations,
            out_dir=work,
        )

    blueprint = None
    bp_path = (run_result.get("artifacts") or {}).get("blueprintWorking") or (
        run_result.get("artifacts") or {}
    ).get("blueprint")
    if bp_path and Path(bp_path).exists():
        blueprint = load_json(bp_path)

    ledger = (blueprint or {}).get("ledger") if blueprint else None
    request = None
    if project.get("requestPath"):
        rp = project_dir / str(project["requestPath"])
        if rp.exists():
            from engine.reference.request import parse_request_spec

            request = parse_request_spec(rp)

    # Force delivery grade for export packaging
    export_project = dict(project)
    if request:
        export_project["deliveryGrade"] = request.get("deliveryGrade") or project.get(
            "deliveryGrade", "delivery"
        )
        export_project["modelingProfile"] = request.get("modelingProfile")
        export_project["qualityMode"] = request.get("qualityMode")
    else:
        export_project.setdefault("deliveryGrade", project.get("deliveryGrade") or "delivery")

    checklist = evaluate_delivery_gates(
        project=export_project,
        project_dir=project_dir,
        run_result=run_result,
        blueprint=blueprint,
        ledger=ledger,
        request=request,
        factory_path=(run_result.get("artifacts") or {}).get("factory"),
    )
    dump_json(out / "delivery-checklist.json", checklist)

    if not checklist.get("passed"):
        dump_json(
            out / "delivery-failed.json",
            {
                "ok": False,
                "reason": "hard gates failed",
                "checklist": checklist,
                "runStages": run_result.get("stages"),
            },
        )
        return {
            "ok": False,
            "outDir": str(out),
            "checklist": checklist,
            "run": {"stages": run_result.get("stages"), "ok": run_result.get("ok")},
            "bundle": None,
        }

    # Package success bundle
    bundle_dir = out / "bundle"
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True)

    reports = bundle_dir / "reports"
    renders_dst = bundle_dir / "renders"
    reports.mkdir()
    renders_dst.mkdir()

    art = run_result.get("artifacts") or {}
    for key, name in (
        ("metricReport", "metric-report.json"),
        ("reviewReport", "review-report.json"),
        ("comparisonSheet", "comparison-sheet.json"),
        ("renderSet", "render-set.json"),
        ("characterGate", "character-gate.json"),
    ):
        src = art.get(key)
        if src and Path(src).exists():
            shutil.copy2(src, reports / name)

    dump_json(reports / "delivery-checklist.json", checklist)
    if bp_path and Path(bp_path).exists():
        shutil.copy2(bp_path, bundle_dir / "blueprint.json")

    factory_src = art.get("factory")
    factory_text = Path(factory_src).read_text(encoding="utf-8") if factory_src and Path(factory_src).exists() else ""
    preset_path = Path(__file__).resolve().parents[2] / "demo" / "src" / "detail" / "surfacePresets.ts"
    surface_module = preset_path.read_text(encoding="utf-8") if preset_path.exists() else None
    portable = emit_portable_bundle(
        factory_source=factory_text,
        out_dir=bundle_dir / "portable",
        surface_preset_module=surface_module,
    )
    # also place factory at bundle root for convenience
    if factory_text:
        (bundle_dir / "factory.ts").write_text(factory_text, encoding="utf-8")
        utf_issues = utf8_gate(factory_text)
    else:
        utf_issues = ["missing_factory"]

    # copy renders tree
    render_root = art.get("renderRoot")
    if render_root and Path(render_root).is_dir():
        for png in Path(render_root).rglob("*.png"):
            rel = png.relative_to(render_root)
            dest = renders_dst / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(png, dest)

    # journal excerpt
    if bp_path and Path(bp_path).exists():
        bp_data = load_json(bp_path)
        dump_json(reports / "journal-excerpt.json", {"journal": bp_data.get("journal") or []})

    manifest = {
        "schemaVersion": 1,
        "subject": (request or {}).get("subject") or project.get("name") or "subject",
        "revisionId": (blueprint or {}).get("revision", {}).get("id") if blueprint else None,
        "deliveryGrade": export_project.get("deliveryGrade"),
        "gatesPassed": True,
        "checklistHash": checklist.get("checklistHash"),
        "portable": portable,
        "utf8Issues": utf_issues,
        "files": sorted(str(p.relative_to(bundle_dir)) for p in bundle_dir.rglob("*") if p.is_file()),
        "toolchain": {
            "renderer": "gpthreejs-software/0.2",
            "engine": "gpthreejs",
        },
    }
    # forbid repo-relative leaks in factory
    leaks = []
    for path in bundle_dir.rglob("*.ts"):
        text = path.read_text(encoding="utf-8")
        if "../engine/" in text:
            leaks.append(str(path.relative_to(bundle_dir)))
    manifest["externalPathLeaks"] = leaks
    if leaks or utf_issues:
        manifest["gatesPassed"] = False
        dump_json(bundle_dir / "manifest.json", manifest)
        return {
            "ok": False,
            "outDir": str(out),
            "checklist": checklist,
            "bundle": str(bundle_dir),
            "manifest": manifest,
            "reason": "portability/utf8 gate failed after packaging",
        }

    manifest["contentHash"] = content_hash(manifest, ignored_paths=(("contentHash",),))
    dump_json(bundle_dir / "manifest.json", manifest)
    dump_json(out / "manifest.json", manifest)

    return {
        "ok": True,
        "outDir": str(out),
        "bundle": str(bundle_dir),
        "checklist": checklist,
        "manifest": manifest,
        "run": {"stages": run_result.get("stages"), "ok": run_result.get("ok")},
    }
