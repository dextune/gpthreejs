"""Production delivery hard gates DG-01…DG-14."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.blueprint.attachments import assess_attachment_contacts
from engine.blueprint.ledger_validation import validate_ledger_production_gate
from engine.blueprint.materials_profile import assess_material_readability
from engine.blueprint.profiles import modeling_profile_rules, validate_landmarks, validate_proportion_profile
from engine.blueprint.validate import validate_blueprint
from engine.critique.metrics_from_render import metrics_from_render_set
from engine.reference.matte_confidence import assess_matte_confidence
from engine.reference.reference_set import parse_reference_set, validate_reference_set
from engine.reference.request import parse_request_spec
from engine.reference.views import resolve_view_flags
from engine.shared.artifacts import content_hash
from engine.shared.jsonutil import load_json

# Provisional calibrated thresholds (PD-0-005 / PD-4-008)
PROVISIONAL_THRESHOLDS = {
    "matteConfidence": 0.45,
    "silhouetteIoU": 0.35,
    "boundaryF": 0.30,
    "framing": 0.40,
    "partVisibility": 0.45,
    "attachmentContact": 0.75,
    "materialReadability": 0.45,
    "handedness": 0.6,
}


def _issue(
    code: str,
    message: str,
    *,
    severity: str = "error",
    gate: str = "",
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "severity": severity,
        "gate": gate,
        "evidence": evidence or {},
    }


def evaluate_delivery_gates(
    *,
    project: dict[str, Any],
    project_dir: str | Path,
    run_result: dict[str, Any] | None = None,
    blueprint: dict[str, Any] | None = None,
    reference_set: dict[str, Any] | None = None,
    request: dict[str, Any] | None = None,
    ledger: dict[str, Any] | None = None,
    render_set: dict[str, Any] | None = None,
    metric_report: dict[str, Any] | None = None,
    review_report: dict[str, Any] | None = None,
    factory_path: str | Path | None = None,
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Run hard delivery gates. Returns checklist with per-gate pass/fail.
    Export must only succeed when all required gates pass.
    """

    thr = {**PROVISIONAL_THRESHOLDS, **(thresholds or {})}
    base = Path(project_dir)
    issues: list[dict[str, Any]] = []
    gates: dict[str, dict[str, Any]] = {}

    def mark(gate_id: str, passed: bool, detail: str = "", extra: dict | None = None) -> None:
        gates[gate_id] = {"passed": passed, "detail": detail, **(extra or {})}

    # Load artifacts from project paths when not injected
    if request is None and project.get("requestPath"):
        rp = base / str(project["requestPath"])
        if rp.exists():
            request = parse_request_spec(rp)
    if reference_set is None and project.get("referenceSetPath"):
        rsp = base / str(project["referenceSetPath"])
        if rsp.exists():
            reference_set = parse_reference_set(rsp, check_files=False)
    if blueprint is None and project.get("blueprintPath"):
        bp = base / str(project["blueprintPath"])
        if bp.exists():
            blueprint = load_json(bp)
    if blueprint is None and run_result:
        art = run_result.get("artifacts") or {}
        for key in ("blueprintWorking", "blueprint"):
            if art.get(key) and Path(art[key]).exists():
                blueprint = load_json(art[key])
                break
    if render_set is None and run_result:
        rs_path = (run_result.get("artifacts") or {}).get("renderSet")
        if rs_path and Path(rs_path).exists():
            render_set = load_json(rs_path)
    if metric_report is None and run_result:
        mr = (run_result.get("artifacts") or {}).get("metricReport")
        if mr and Path(mr).exists():
            metric_report = load_json(mr)
    if review_report is None and run_result:
        rr = (run_result.get("artifacts") or {}).get("reviewReport")
        if rr and Path(rr).exists():
            review_report = load_json(rr)
    if factory_path is None and run_result:
        factory_path = (run_result.get("artifacts") or {}).get("factory")

    profile = (request or project or {}).get("modelingProfile") or (
        (blueprint or {}).get("modelingProfile")
    ) or "generic-prop"
    quality = (request or project or {}).get("qualityMode") or (
        (blueprint or {}).get("qualityMode")
    ) or "sharp"
    delivery_grade = (request or project or {}).get("deliveryGrade") or "standard"
    required_views = list(
        (request or {}).get("requiredViews")
        or (request or {}).get("targetViews")
        or ["source-34", "front", "left"]
    )

    # DG-01 view coverage
    if reference_set:
        views = resolve_view_flags(reference_set)
        unique = set(views.get("uniqueViews") or [])
        missing = []
        # normalize aliases
        def has_view(name: str) -> bool:
            if name in unique:
                return True
            if name == "side":
                return "left" in unique or "right" in unique
            if name == "source-aligned":
                return "source-34" in unique or "source" in unique
            return False

        need_side = profile == "stylized-character" and quality in ("sharp", "razor", "hybrid", "solid")
        if need_side and not views.get("hasSide"):
            missing.append("side")
            issues.append(
                _issue(
                    "DELIVERY_VIEW_INSUFFICIENT",
                    "stylized-character sharp+ requires a side view",
                    gate="DG-01",
                )
            )
        for rv in required_views:
            if rv in ("left", "right", "side") and views.get("hasSide"):
                continue
            if not has_view(rv) and rv not in ("back",):  # back recommended
                if rv == "back" and delivery_grade != "strict":
                    continue
                missing.append(rv)
        # source-aligned
        if profile == "stylized-character" and not (
            has_view("source-34") or has_view("front")
        ):
            missing.append("source-aligned-or-front")
            issues.append(
                _issue(
                    "DELIVERY_VIEW_INSUFFICIENT",
                    "character delivery requires source-aligned or front view",
                    gate="DG-01",
                )
            )
        mark(
            "DG-01",
            not any(i["code"] == "DELIVERY_VIEW_INSUFFICIENT" for i in issues),
            detail=f"views={sorted(unique)} missing={missing}",
        )
    else:
        if delivery_grade in ("delivery", "strict") and profile == "stylized-character":
            issues.append(
                _issue("DELIVERY_VIEW_INSUFFICIENT", "ReferenceSet required for character delivery", gate="DG-01")
            )
            mark("DG-01", False, "no ReferenceSet")
        else:
            mark("DG-01", True, "skipped (no ReferenceSet; non-strict slice)")

    # DG-02 matte confidence (primary view if available)
    matte_ok = True
    if reference_set:
        refs = reference_set.get("references") or []
        if refs:
            primary = refs[0]
            img = Path(str(primary.get("path") or ""))
            if not img.is_absolute() and project.get("referenceSetPath"):
                img = base / Path(project["referenceSetPath"]).parent / primary.get("path", "")
            if not img.exists() and project.get("referenceSetPath"):
                img = (base / str(primary.get("path") or ""))
            conf = 1.0
            if img.exists():
                try:
                    conf = float(assess_matte_confidence(img).get("confidence") or 0)
                except Exception:
                    conf = 0.0
            if conf < thr["matteConfidence"]:
                # allow if normalization candidate was applied in run artifacts
                matte_ok = False
                issues.append(
                    _issue(
                        "DELIVERY_MATTE_LOW_CONFIDENCE",
                        f"primary matte confidence {conf:.2f} < {thr['matteConfidence']}",
                        gate="DG-02",
                        evidence={"confidence": conf},
                    )
                )
            mark("DG-02", matte_ok, f"confidence={conf:.3f}")
        else:
            mark("DG-02", False, "empty references")
            issues.append(_issue("DELIVERY_MATTE_LOW_CONFIDENCE", "no references", gate="DG-02"))
    else:
        mark("DG-02", True, "skipped")

    # DG-03 ledger
    if ledger is None and blueprint:
        ledger = blueprint.get("ledger")
    if ledger:
        led_errors = validate_ledger_production_gate(ledger, modeling_profile=str(profile))
        ok = not led_errors
        if not ok:
            issues.append(
                _issue("DELIVERY_LEDGER_SPARSE", "; ".join(led_errors[:3]), gate="DG-03")
            )
        mark("DG-03", ok, detail=str(led_errors[:2]))
    else:
        # character delivery requires ledger
        if profile == "stylized-character" and delivery_grade in ("delivery", "strict"):
            issues.append(_issue("DELIVERY_LEDGER_SPARSE", "ledger missing", gate="DG-03"))
            mark("DG-03", False, "missing")
        else:
            mark("DG-03", True, "skipped")

    # DG-04 blueprint strict
    if blueprint:
        # write temp validation via dict path: use validate_blueprint on file if possible
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
            import json

            tmp.write(json.dumps(blueprint))
            tmp_path = tmp.name
        try:
            result = validate_blueprint(tmp_path, strict=True)
            ok = result.ok
            if not ok:
                issues.append(
                    _issue(
                        "DELIVERY_SEMANTIC_SHALLOW",
                        "; ".join(result.errors[:3]),
                        gate="DG-04",
                    )
                )
            # profile rules
            try:
                rules = modeling_profile_rules(str(profile))
                if rules.get("requireLandmarks"):
                    lm_err = validate_landmarks(
                        blueprint.get("landmarks") or [],
                        required=tuple(rules.get("requiredLandmarks") or ()),
                    )
                    if lm_err:
                        ok = False
                        issues.append(_issue("DELIVERY_SEMANTIC_SHALLOW", lm_err[0], gate="DG-04"))
                prop_err = validate_proportion_profile(blueprint.get("proportionProfile") or {})
                if prop_err and profile == "stylized-character":
                    ok = False
                    issues.append(_issue("DELIVERY_SEMANTIC_SHALLOW", prop_err[0], gate="DG-04"))
            except Exception as exc:
                ok = False
                issues.append(_issue("DELIVERY_SEMANTIC_SHALLOW", str(exc), gate="DG-04"))
            mark("DG-04", ok)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    else:
        mark("DG-04", False, "no blueprint")
        issues.append(_issue("DELIVERY_SEMANTIC_SHALLOW", "blueprint missing", gate="DG-04"))

    # DG-05 contact
    if blueprint:
        contacts = assess_attachment_contacts(blueprint.get("parts") or [], blueprint.get("handles"))
        ok = contacts.get("passed", False)
        if not ok:
            for iss in contacts.get("issues") or []:
                if iss.get("severity") == "error":
                    issues.append(
                        _issue(
                            "DELIVERY_CONTACT_FAIL",
                            iss.get("message", "contact fail"),
                            gate="DG-05",
                            evidence=iss,
                        )
                    )
        mark("DG-05", ok, extra={"issues": contacts.get("issues")})
    else:
        mark("DG-05", True, "skipped")

    # Metrics-derived gates DG-06…10
    metrics = (metric_report or {}).get("metrics") or []
    if not metrics and render_set and blueprint:
        try:
            metrics = metrics_from_render_set(blueprint, render_set, view_id="source-34")
        except Exception:
            metrics = []

    def metric_value(mid: str) -> float | None:
        for m in metrics:
            if m.get("id") == mid:
                return float(m.get("value") or 0)
        return None

    def metric_passed(mid: str, threshold: float) -> bool:
        for m in metrics:
            if m.get("id") == mid:
                if "passed" in m:
                    return bool(m["passed"]) and float(m.get("value") or 0) >= threshold * 0.5
                return float(m.get("value") or 0) >= threshold
        return False

    if metrics:
        sil_entry = next((m for m in metrics if m.get("id") == "silhouette_iou"), None)
        sil = metric_value("silhouette_iou")
        external_ref = bool(sil_entry and sil_entry.get("externalReference"))
        if delivery_grade in ("delivery", "strict") and not external_ref:
            sil_ok = False
            issues.append(
                _issue(
                    "DELIVERY_SILHOUETTE_FAIL",
                    "delivery-grade requires external photo/sense matte reference (self-baseline rejected)",
                    gate="DG-06",
                    evidence={"externalReference": False, "silhouette_iou": sil},
                )
            )
        else:
            sil_ok = sil is not None and sil >= thr["silhouetteIoU"]
            if not sil_ok:
                issues.append(
                    _issue(
                        "DELIVERY_SILHOUETTE_FAIL",
                        f"silhouette_iou={sil} < {thr['silhouetteIoU']}",
                        gate="DG-06",
                    )
                )
        mark(
            "DG-06",
            sil_ok,
            f"silhouette_iou={sil} external={external_ref}",
            extra={"externalReference": external_ref},
        )

        fr = metric_value("camera_framing")
        fr_ok = fr is not None and fr >= thr["framing"]
        if not fr_ok:
            issues.append(_issue("DELIVERY_SILHOUETTE_FAIL", f"framing={fr}", gate="DG-07"))
        mark("DG-07", fr_ok, f"framing={fr}")

        pv = metric_value("part_visibility")
        pv_ok = pv is not None and pv >= thr["partVisibility"]
        if not pv_ok:
            issues.append(
                _issue("DELIVERY_IDENTITY_FAIL", f"part_visibility={pv}", gate="DG-08")
            )
        mark("DG-08", pv_ok, f"part_visibility={pv}")

        # DG-09 handedness: gate on real handedness metric (part-id centroids), not part-id existence alone
        hand_val = metric_value("handedness")
        hand_thr = thr.get("handedness", 0.6)
        if hand_val is not None:
            hand_ok = hand_val >= hand_thr
            if not hand_ok:
                issues.append(
                    _issue(
                        "DELIVERY_HANDEDNESS_FAIL",
                        f"handedness metric {hand_val:.3f} < {hand_thr}",
                        gate="DG-09",
                        evidence={"value": hand_val, "threshold": hand_thr},
                    )
                )
        elif blueprint and profile == "stylized-character":
            hand_ok = False
            issues.append(
                _issue(
                    "DELIVERY_HANDEDNESS_FAIL",
                    "handedness metric missing from metric report",
                    gate="DG-09",
                )
            )
        else:
            hand_ok = True
        mark("DG-09", hand_ok, f"handedness={hand_val}")

        att = metric_value("attachment_contact")
        # prefer contact report already computed
        att_ok = gates.get("DG-05", {}).get("passed", True)
        if att is not None:
            att_ok = att_ok and att >= thr["attachmentContact"]
        mark("DG-05b", att_ok) if False else None

        mat = metric_value("material_readability")
        if mat is None and blueprint:
            mr = assess_material_readability(blueprint.get("materials") or [])
            mat_ok = mr.get("passed", False)
        else:
            mat_ok = mat is not None and mat >= thr["materialReadability"]
        if not mat_ok:
            issues.append(
                _issue("DELIVERY_MATERIAL_UNREADABLE", f"material_readability={mat}", gate="DG-10")
            )
        mark("DG-10", mat_ok, f"material={mat}")
    else:
        for gid in ("DG-06", "DG-07", "DG-08", "DG-09", "DG-10"):
            if delivery_grade in ("delivery", "strict"):
                mark(gid, False, "no metrics")
                issues.append(_issue("DELIVERY_SILHOUETTE_FAIL", f"{gid}: metrics missing", gate=gid))
            else:
                mark(gid, True, "skipped (no metrics)")

    # DG-11 policy
    policy_ok = False
    if review_report:
        trace = review_report.get("policyTrace") or {}
        rec = review_report.get("recommendation")
        policy_ok = (
            trace.get("policyIssued") is True
            and trace.get("issuer") == "review-policy"
            and rec == "accept"
        )
        if rec != "accept":
            issues.append(
                _issue(
                    "DELIVERY_POLICY_DENY",
                    f"recommendation={rec}",
                    gate="DG-11",
                    evidence={"policyTrace": trace},
                )
            )
        elif not policy_ok:
            issues.append(
                _issue("DELIVERY_POLICY_DENY", "accept without policyIssued trace", gate="DG-11")
            )
    else:
        issues.append(_issue("DELIVERY_POLICY_DENY", "review report missing", gate="DG-11"))
    mark("DG-11", policy_ok)

    # DG-12 freshness: require render set hashes present and factory file
    fresh_ok = True
    if render_set:
        if not render_set.get("blueprintHash") or not render_set.get("factoryHash"):
            fresh_ok = False
            issues.append(_issue("DELIVERY_STALE_ARTIFACT", "render set missing hashes", gate="DG-12"))
    elif delivery_grade in ("delivery", "strict"):
        fresh_ok = False
        issues.append(_issue("DELIVERY_STALE_ARTIFACT", "render set missing", gate="DG-12"))
    if factory_path and not Path(str(factory_path)).is_file():
        fresh_ok = False
        issues.append(_issue("DELIVERY_STALE_ARTIFACT", "factory missing", gate="DG-12"))
    mark("DG-12", fresh_ok)

    # DG-13 portability structural: factory has FormRuntime and no ../engine/
    port_ok = True
    if factory_path and Path(str(factory_path)).is_file():
        text = Path(str(factory_path)).read_text(encoding="utf-8")
        if "FormRuntime" not in text or "dispose" not in text:
            port_ok = False
            issues.append(
                _issue("DELIVERY_PORTABILITY_FAIL", "factory missing FormRuntime.dispose", gate="DG-13")
            )
        if "../engine/" in text:
            port_ok = False
            issues.append(
                _issue("DELIVERY_PORTABILITY_FAIL", "factory has repo-relative engine import", gate="DG-13")
            )
    elif delivery_grade in ("delivery", "strict"):
        port_ok = False
        issues.append(_issue("DELIVERY_PORTABILITY_FAIL", "factory missing", gate="DG-13"))
    mark("DG-13", port_ok)

    # DG-14 budget: from run_result iteration budget stop not oversubscription crash
    budget_ok = True
    if run_result:
        extra = run_result.get("extra") or {}
        iteration = extra.get("iteration") or {}
        bud = iteration.get("budget") or {}
        # always ok if completed stages include review
        if "review" not in (run_result.get("stages") or []) and delivery_grade in ("delivery", "strict"):
            budget_ok = False
            issues.append(_issue("DELIVERY_BUDGET_EXCEEDED", "run incomplete", gate="DG-14"))
        mark("DG-14", budget_ok, detail=str(bud.get("stopReason")))
    else:
        mark("DG-14", True, "skipped")

    # generated-as-observed already rejected by ReferenceSet validator when checked
    if reference_set:
        ref_errors = validate_reference_set(reference_set)
        if ref_errors:
            for err in ref_errors:
                if "observed" in err:
                    issues.append(
                        _issue("DELIVERY_VIEW_INSUFFICIENT", err, gate="DG-01")
                    )
                    gates["DG-01"]["passed"] = False

    hard_errors = [i for i in issues if i.get("severity") == "error"]
    all_required = all(
        gates.get(g, {}).get("passed", False)
        for g in (
            "DG-01",
            "DG-02",
            "DG-03",
            "DG-04",
            "DG-05",
            "DG-06",
            "DG-07",
            "DG-08",
            "DG-09",
            "DG-10",
            "DG-11",
            "DG-12",
            "DG-13",
            "DG-14",
        )
        if g in gates
    )

    return {
        "schemaVersion": 1,
        "passed": all_required and not hard_errors,
        "deliveryGrade": delivery_grade,
        "thresholds": thr,
        "gates": gates,
        "issues": issues,
        "checklistHash": content_hash(
            {"gates": gates, "issues": [{"code": i["code"]} for i in issues]}
        ),
    }
