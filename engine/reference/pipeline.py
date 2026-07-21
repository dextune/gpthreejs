"""ReferenceSet planning and multi-view sense/sufficiency/ledger pipelines."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.blueprint.draft import draft_ledger
from engine.blueprint.ledger_validation import validate_ledger_production_gate
from engine.reference.adapter import single_image_to_reference_set
from engine.reference.consistency import assess_cross_view_consistency
from engine.reference.matte_confidence import assess_matte_confidence
from engine.reference.normalize import normalize_reference
from engine.reference.provider import ProviderBudget, get_image_provider, plan_missing_views
from engine.reference.reference_set import (
    ReferenceSetError,
    build_reference_set,
    parse_reference_set,
    write_reference_set,
)
from engine.reference.request import parse_request_spec
from engine.reference.views import feature_coverage, resolve_view_flags
from engine.sense.pack import build_sense_pack
from engine.sense.sufficiency import assess_sufficiency
from engine.shared.jsonutil import dump_json, load_json


def plan_reference_set(
    request_path: str | Path,
    *,
    images: list[str | Path] | None = None,
    reference_set_path: str | Path | None = None,
    out: str | Path,
) -> dict[str, Any]:
    """Build a reference plan from RequestSpec + optional images/ReferenceSet."""

    request = parse_request_spec(request_path)
    if reference_set_path:
        reference_set = parse_reference_set(reference_set_path, check_files=False)
    elif images:
        refs = []
        target_views = list(request.get("targetViews") or ["source-34"])
        for index, image in enumerate(images):
            view = target_views[index] if index < len(target_views) else f"view-{index}"
            partial = single_image_to_reference_set(
                image,
                declared_view=view,
                ref_id=f"ref-{view}",
                visible_features=[f["id"] for f in request.get("mustHave") or []],
            )
            refs.extend(partial["references"])
        reference_set = build_reference_set(refs)
    else:
        reference_set = {
            "schemaVersion": 1,
            "references": [],
            "contentHash": "",
        }

    views = resolve_view_flags(reference_set)
    present = views.get("uniqueViews") or []
    missing_plan = plan_missing_views(
        list(request.get("targetViews") or []),
        list(present),
        budget=ProviderBudget(),
        provider=get_image_provider(),
    )
    coverage = feature_coverage(reference_set, list(request.get("mustHave") or []))
    consistency = (
        assess_cross_view_consistency(reference_set)
        if reference_set.get("references")
        else {"passed": True, "issues": [], "notes": ["no references yet"]}
    )

    plan = {
        "schemaVersion": 1,
        "request": request,
        "referenceSet": reference_set,
        "viewFlags": views,
        "featureCoverage": coverage,
        "consistency": consistency,
        "missingViewPlan": missing_plan,
        "agentAction": missing_plan.get("agentAction")
        if missing_plan.get("missingViews")
        else ("continue" if consistency.get("passed", True) else "abort"),
    }
    dump_json(out, plan)
    return plan


def sense_reference_set(
    reference_set_path: str | Path,
    *,
    out_dir: str | Path,
    mode: str = "sharp",
    normalize: bool = True,
) -> dict[str, Any]:
    """Run sense (and optional normalize) for each reference in a set."""

    reference_set = parse_reference_set(reference_set_path, check_files=False)
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    for ref in reference_set.get("references") or []:
        ref_id = str(ref.get("id") or "ref")
        image_path = Path(str(ref["path"]))
        if not image_path.is_absolute():
            image_path = Path(reference_set_path).parent / image_path
        ref_out = out_root / ref_id
        ref_out.mkdir(parents=True, exist_ok=True)

        norm_report = None
        sense_image = image_path
        if normalize:
            try:
                norm_report = normalize_reference(
                    image_path,
                    out_path=ref_out / "normalized.png",
                )
                if norm_report.get("normalizedPath"):
                    sense_image = Path(norm_report["normalizedPath"])
            except Exception as exc:  # pragma: no cover - defensive
                norm_report = {"error": str(exc)}

        try:
            confidence = assess_matte_confidence(sense_image)
        except Exception as exc:  # pragma: no cover
            confidence = {"error": str(exc), "confidence": 0.0}

        try:
            pack = build_sense_pack(sense_image, ref_out, mode=mode)
            sense_pack_path = str(ref_out / "sense_pack.json")
        except Exception as exc:
            pack = {"error": str(exc)}
            sense_pack_path = None

        ref["sensePack"] = sense_pack_path
        results.append(
            {
                "id": ref_id,
                "image": str(image_path),
                "sensePack": sense_pack_path,
                "normalization": norm_report,
                "matteConfidence": confidence,
                "sense": pack if isinstance(pack, dict) else {"ok": True},
            }
        )

    summary = {
        "schemaVersion": 1,
        "outDir": str(out_root),
        "references": results,
        "referenceSet": reference_set,
    }
    dump_json(out_root / "sense-set-summary.json", summary)
    write_reference_set(out_root / "reference-set.sensed.json", reference_set)
    return summary


def sufficiency_reference_set(
    reference_set_path: str | Path,
    *,
    request_path: str | Path,
    out: str | Path | None = None,
    sense_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Assess ReferenceSet sufficiency using request targets and consistency."""

    request = parse_request_spec(request_path)
    reference_set = parse_reference_set(reference_set_path, check_files=False)
    views = resolve_view_flags(reference_set)
    coverage = feature_coverage(reference_set, list(request.get("mustHave") or []))
    consistency = assess_cross_view_consistency(reference_set)

    primary = (reference_set.get("references") or [{}])[0]
    image = primary.get("path")
    if image and not Path(str(image)).is_absolute():
        image = str(Path(reference_set_path).parent / image)

    per_image = None
    if image and Path(str(image)).exists():
        sense = primary.get("sensePack")
        if sense_dir and not sense:
            candidate = Path(sense_dir) / str(primary.get("id")) / "sense_pack.json"
            if candidate.exists():
                sense = str(candidate)
        per_image = assess_sufficiency(
            image,
            sense_path=sense,
            domain="character" if request.get("modelingProfile") == "stylized-character" else "object",
            intent=str(request.get("intent") or "game"),
            view_count=views["viewCount"],
            has_side=views["hasSide"],
            has_back=views["hasBack"],
        )

    issues: list[dict[str, Any]] = []
    quality = str(request.get("qualityMode") or "sharp")
    profile = str(request.get("modelingProfile") or "generic-prop")
    delivery_grade = str(request.get("deliveryGrade") or "standard")
    required_views = list(request.get("requiredViews") or request.get("targetViews") or [])

    if views["viewCount"] < len(request.get("targetViews") or []):
        issues.append(
            {
                "code": "VIEW_COVERAGE_THIN",
                "severity": "warning" if delivery_grade == "standard" else "error",
                "message": f"manifest has {views['viewCount']} views; request targets {len(request.get('targetViews') or [])}",
            }
        )

    # PD-1: stylized-character sharp+ side is hard error (delivery and standard)
    if profile == "stylized-character" and quality in ("sharp", "razor", "hybrid", "solid"):
        if not views["hasSide"]:
            issues.append(
                {
                    "code": "CHAR_NO_SIDE",
                    "severity": "error",
                    "message": "stylized-character sharp+ requires a side view in the ReferenceSet",
                    "field": "views",
                }
            )
        if not views.get("hasFront") and "source-34" not in (views.get("uniqueViews") or []):
            issues.append(
                {
                    "code": "DELIVERY_VIEW_INSUFFICIENT",
                    "severity": "error",
                    "message": "character delivery requires front or source-aligned view",
                    "field": "views",
                }
            )

    for rv in required_views:
        unique = views.get("uniqueViews") or []
        if rv in unique:
            continue
        if rv in ("left", "right", "side") and views.get("hasSide"):
            continue
        if rv in ("source-34", "source") and (
            "source-34" in unique or "front" in unique
        ):
            continue
        if rv == "back" and delivery_grade == "standard":
            continue
        issues.append(
            {
                "code": "DELIVERY_VIEW_INSUFFICIENT",
                "severity": "error" if delivery_grade in ("delivery", "strict") else "warning",
                "message": f"required view missing: {rv}",
                "field": "views",
            }
        )
    if coverage["coverage"] < 0.5 and request.get("mustHave"):
        issues.append(
            {
                "code": "FEATURE_COVERAGE_LOW",
                "severity": "warning",
                "message": f"feature coverage {coverage['coverage']:.2f} below 0.5",
            }
        )
    for issue in consistency.get("issues") or []:
        issues.append(issue)
    if per_image:
        issues.extend(per_image.get("issues") or [])

    hard = [i for i in issues if i.get("severity") in ("error", "blocker")]
    sufficient = not hard and consistency.get("passed", True)
    if hard:
        verdict, action = "reject", "abort"
    elif issues:
        verdict, action = "conditional", "ask"
    else:
        verdict, action = "pass", "continue"

    # Prefer provider ask when views are missing and no hard consistency fail.
    missing = [
        v
        for v in (request.get("targetViews") or [])
        if v not in (views.get("uniqueViews") or [])
    ]
    if missing and not hard:
        action = "ask"
        verdict = "conditional"
        sufficient = False

    report = {
        "schemaVersion": 1,
        "sufficient": sufficient,
        "verdict": verdict,
        "agentAction": action,
        "issues": issues,
        "viewFlags": views,
        "featureCoverage": coverage,
        "consistency": consistency,
        "perImage": per_image,
        "requestSubject": request.get("subject"),
        "warnings": views.get("warnings") or [],
    }
    if out:
        dump_json(out, report)
    return report


def ledger_reference_set(
    reference_set_path: str | Path,
    *,
    sense_dir: str | Path,
    out: str | Path,
    request_path: str | Path | None = None,
    mode: str = "production",
) -> dict[str, Any]:
    """Draft a production ledger from a ReferenceSet + sense outputs."""

    reference_set = parse_reference_set(reference_set_path, check_files=False)
    modeling_profile = "generic-prop"
    if request_path:
        request = parse_request_spec(request_path)
        modeling_profile = str(request.get("modelingProfile") or modeling_profile)

    primary = (reference_set.get("references") or [{}])[0]
    image = str(primary.get("path") or "")
    sense_root = Path(sense_dir)
    # Prefer per-ref sense folder when available.
    primary_sense = sense_root
    if primary.get("id") and (sense_root / str(primary["id"])).is_dir():
        primary_sense = sense_root / str(primary["id"])
    elif (sense_root / "sense_pack.json").exists():
        primary_sense = sense_root

    ledger = draft_ledger(
        image,
        primary_sense,
        out,
        mode=mode,
        modeling_profile=modeling_profile,
    )
    gate_errors = validate_ledger_production_gate(ledger, modeling_profile=modeling_profile)
    ledger["gateErrors"] = gate_errors
    if gate_errors and mode == "production":
        ledger["agentAction"] = "ask"
    dump_json(out, ledger)
    return ledger
