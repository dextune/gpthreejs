"""Integration/unit tests for quality-upgrade M3–M6 shipped surfaces."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.blueprint.attachments import assess_attachment_contacts, validate_attachment_schema
from engine.blueprint.character import (
    build_stylized_character_blueprint,
    character_gate_report,
    validate_character_slice,
)
from engine.blueprint.materials_profile import assess_material_readability, material_role_profile
from engine.blueprint.profiles import (
    apply_pose_to_parts,
    build_pose_profile,
    modeling_profile_rules,
    project_landmark_to_screen,
    validate_proportion_profile,
)
from engine.cast.emit_factory import emit_factory
from engine.cast.fit_params import EXPERIMENTAL_PROXY, EXPERIMENTAL_PROXY_TAG
from engine.cli import main as cli_main
from engine.critique.cache import RenderCache
from engine.critique.fit import assert_production_fit_path, coarse_to_fine_fit, describe_fit_root_mass_proxy
from engine.critique.iteration import (
    IterationBudget,
    IterationGraph,
    apply_json_patch,
    map_issue_to_scope,
    validate_json_patch,
)
from engine.critique.render_profiles import (
    VIEW_PROFILE_IDS,
    build_view_manifest,
    camera_profile,
    finalize_view_manifest,
    validate_partial_render_set,
)
from engine.critique.reviewer import apply_review_policy, get_vision_reviewer, parse_reviewer_output
from engine.geometry.builders import build_geometry
from engine.orchestration.run import run_production
from engine.runtime.budget import ComputeBudget, ProfileReport, promote_coarse_to_fine
from engine.runtime.dispose import FormRuntime, leak_probe
from engine.runtime.portable import emit_portable_bundle, rewrite_positional_helpers_to_named, utf8_gate
from engine.runtime.skill_validate import validate_skill_folder
from engine.shared.jsonutil import dump_json


class M3CharacterGeometryTests(unittest.TestCase):
    def test_modeling_profile_rules_isolated(self) -> None:
        prop = modeling_profile_rules("generic-prop")
        hero = modeling_profile_rules("hard-surface-hero")
        char = modeling_profile_rules("stylized-character")
        self.assertFalse(prop["requirePose"])
        self.assertTrue(char["requirePose"])
        self.assertNotEqual(prop["requiredRoles"], hero["requiredRoles"])

    def test_proportion_and_pose_switch_keeps_geometry(self) -> None:
        prop = {"headUnits": 4.2, "headHeightRatio": 0.235, "shoulderWidthRatio": 0.42, "limbThickness": "chunky"}
        self.assertEqual(validate_proportion_profile(prop), [])
        parts = [
            {
                "id": "pelvis",
                "joint": "pelvis",
                "poseDriven": True,
                "geometry": {"kind": "box", "size": [1, 1, 1]},
                "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
                "children": [],
            }
        ]
        geom_before = json.dumps(parts[0]["geometry"])
        posed = apply_pose_to_parts(parts, build_pose_profile("source-34"))
        self.assertEqual(json.dumps(posed[0]["geometry"]), geom_before)
        self.assertNotEqual(posed[0]["transform"]["position"], [0, 0, 0])
        neutral = apply_pose_to_parts(parts, build_pose_profile("neutral"))
        self.assertEqual(json.dumps(neutral[0]["geometry"]), geom_before)

    def test_geometry_builders_bounds_and_keys(self) -> None:
        for spec in (
            {"kind": "rounded-box", "size": [1, 0.5, 0.4], "radius": 0.05},
            {"kind": "shape-extrude", "shape": [[0, 0], [1, 0], [0.5, 1]], "depth": 0.1},
            {"kind": "lathe", "profile": [[0.1, 0], [0.2, 0.5], [0.0, 1.0]]},
            {"kind": "tube", "path": [[0, 0, 0], [0, 1, 0], [1, 1, 0]], "radius": 0.05},
            {"kind": "beveled-plate", "outline": [[-1, -1], [1, -1], [1, 1], [-1, 1]], "thickness": 0.05, "bevel": 0.01},
            {"kind": "curve-blade", "length": 0.5, "width": 0.08, "curve": 0.05},
            {"kind": "feather", "length": 0.2, "width": 0.05, "barbCount": 5},
            {"kind": "cloth-patch", "width": 0.3, "height": 0.4, "drape": 0.1},
        ):
            desc = build_geometry(spec)
            self.assertIn("bounds", desc)
            self.assertIn("key", desc)
            self.assertEqual(len(desc["key"]), 64)

        with self.assertRaises(ValueError):
            build_geometry({"kind": "rounded-box", "size": [0.1, 0.1, 0.1], "radius": 0.2})

    def test_attachment_schema_and_contacts(self) -> None:
        parts = [
            {
                "id": "hand",
                "transform": {"position": [0, 0, 0]},
                "children": [
                    {
                        "id": "sword",
                        "transform": {"position": [0, 0.05, 0]},
                        "attachment": {
                            "parentSocket": "socket-hand",
                            "childSocket": "socket-sword",
                            "contact": "grip",
                            "maxGap": 0.2,
                            "maxPenetration": 0.1,
                            "required": True,
                        },
                        "children": [],
                    }
                ],
            }
        ]
        handles = {
            "sockets": [
                {"id": "socket-hand", "partId": "hand", "kind": "grip", "local": [0, 0, 0], "radius": 0.04},
                {"id": "socket-sword", "partId": "sword", "kind": "grip", "local": [0, 0, 0], "radius": 0.04},
            ]
        }
        self.assertEqual(validate_attachment_schema(parts, handles), [])
        report = assess_attachment_contacts(parts, handles)
        self.assertTrue(report["passed"])

        bad = {
            "sockets": [
                {"id": "socket-hand", "partId": "hand", "kind": "grip"},
                # dangling child socket omitted
            ]
        }
        errors = validate_attachment_schema(parts, bad)
        self.assertTrue(any("dangling socket" in e for e in errors))

    def test_character_vertical_slice_gates(self) -> None:
        bp = build_stylized_character_blueprint(include_polish=False)
        validation = validate_character_slice(bp)
        self.assertTrue(validation["ok"], validation["errors"])
        gate = character_gate_report(bp)
        self.assertTrue(gate["passed"], gate)
        self.assertFalse(gate["polishApplied"])

        polished = build_stylized_character_blueprint(include_polish=True)
        gate2 = character_gate_report(polished)
        self.assertTrue(gate2["passed"])
        self.assertTrue(gate2["polishApplied"])

        # landmark projection
        lm = bp["landmarks"][0]
        screen = project_landmark_to_screen(lm, camera=bp["renderProfiles"][0]["camera"])
        self.assertIn("x", screen)

    def test_material_roles_and_black_crush(self) -> None:
        steel = material_role_profile("steel")
        cloth = material_role_profile("cloth")
        self.assertGreater(steel["metalness"], cloth["metalness"])
        bad = [{"id": "m", "baseColor": "#010101", "metalness": 0.9, "aoIntensity": 0.9}]
        report = assess_material_readability(bad)
        self.assertFalse(report["passed"])
        codes = {i["code"] for i in report["issues"]}
        self.assertTrue({"BLACK_CRUSH", "AO_OVERDRIVE"} & codes)

        # high detail worse than no detail
        report2 = assess_material_readability(
            [{"id": "ok", "baseColor": "#888888", "metalness": 0.0, "aoIntensity": 0.2}],
            high_detail_scores={"form": 0.4},
            no_detail_scores={"form": 0.7},
        )
        self.assertFalse(report2["passed"])
        self.assertTrue(any(i["code"] == "DETAIL_REDUCES_READABILITY" for i in report2["issues"]))

    def test_emit_factory_supports_character_geometry(self) -> None:
        bp = build_stylized_character_blueprint()
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "factory.ts"
            emit_factory(bp, out)
            text = out.read_text(encoding="utf-8")
            self.assertIn("THREE.", text)
            self.assertNotIn("silent box fallback", text)


class M4RenderReviewTests(unittest.TestCase):
    def test_view_profiles_and_render_set(self) -> None:
        from engine.critique.software_render import render_blueprint_set

        manifest = finalize_view_manifest(build_view_manifest())
        self.assertEqual(set(manifest["views"]), set(VIEW_PROFILE_IDS))
        hashes = {camera_profile(v)["hash"] for v in VIEW_PROFILE_IDS}
        self.assertEqual(len(hashes), len(VIEW_PROFILE_IDS))
        with tempfile.TemporaryDirectory() as td:
            bp = build_stylized_character_blueprint()
            rs = render_blueprint_set(
                bp,
                out_dir=td,
                revision_id="rev-1",
                blueprint_hash="a" * 64,
                factory_hash="b" * 64,
                width=64,
                height=64,
            )
            self.assertEqual(validate_partial_render_set(rs), [])
            for view in rs["views"]:
                for pass_name, meta in view["passes"].items():
                    self.assertTrue(Path(meta["path"]).is_file(), f"{view['id']}/{pass_name}")
            del rs["views"][0]["passes"]["wireframe"]
            self.assertTrue(validate_partial_render_set(rs))

    def test_metrics_and_policy_reject_reviewer_only_accept(self) -> None:
        metrics = [
            {
                "id": "silhouette_iou",
                "target": "silhouette",
                "viewId": "front",
                "pass": "alpha",
                "value": 0.2,
                "threshold": 0.55,
                "passed": False,
            },
            {
                "id": "camera_framing",
                "target": "framing",
                "viewId": "front",
                "pass": "alpha",
                "value": 0.1,
                "threshold": 0.6,
                "passed": False,
            },
        ]
        metric_report = {
            "revisionId": "rev-1",
            "renderSetHash": "r" * 64,
            "metrics": metrics,
        }
        reviewer = {"recommendation": "accept", "issues": [], "reviewer": "fake"}
        decision = apply_review_policy(metric_report=metric_report, reviewer_output=reviewer)
        self.assertNotEqual(decision["recommendation"], "accept")
        self.assertTrue(decision["policyTrace"]["reviewerCannotOverrideMetrics"])
        self.assertEqual(decision["policyTrace"]["issuer"], "review-policy")

    def test_reviewer_parser_rejects_empty_and_timeout(self) -> None:
        with self.assertRaises(ValueError):
            parse_reviewer_output("")
        with self.assertRaises(TimeoutError):
            parse_reviewer_output({"timeout": True, "recommendation": "revise"})
        out = parse_reviewer_output(json.dumps({"recommendation": "revise", "issues": []}))
        self.assertEqual(out["recommendation"], "revise")
        null = get_vision_reviewer(None)
        self.assertEqual(null.name, "null")

    def test_production_run_command_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = {
                "useCharacterSlice": True,
                "name": "KnightSlice",
                "strict": True,
            }
            proj_path = root / "project.json"
            dump_json(proj_path, project)
            result = run_production(proj_path, max_iterations=0, out_dir=root / "out")
            for stage in ("validate", "cast", "render", "metrics", "review"):
                self.assertIn(stage, result["stages"])
            self.assertTrue((root / "out" / "render-set.json").exists())
            self.assertTrue((root / "out" / "metric-report.json").exists())
            self.assertTrue((root / "out" / "review-report.json").exists())
            pngs = list((root / "out" / "renders").rglob("*.png"))
            self.assertGreaterEqual(len(pngs), 8 * 6)  # 8 passes × 6 views
            # metrics must cite evidence paths to real PNG files
            report = json.loads((root / "out" / "metric-report.json").read_text(encoding="utf-8"))
            for metric in report["metrics"]:
                evidence = metric.get("evidencePath")
                self.assertTrue(evidence, metric)
                self.assertTrue(Path(evidence).is_file(), evidence)
            self.assertGreaterEqual(result.get("extra", {}).get("pngPassCount", 0), 48)
            code = cli_main(["run", str(proj_path), "--out", str(root / "out2"), "--max-iterations", "0"])
            self.assertIn(code, (0, 2))


class M5IterationFitTests(unittest.TestCase):
    def test_patch_validator_and_graph_rollback(self) -> None:
        errors = validate_json_patch([{"op": "replace", "path": "/secret", "value": 1}])
        self.assertTrue(errors)
        ok = validate_json_patch([{"op": "replace", "path": "/proportionProfile/headUnits", "value": 4.0}])
        self.assertEqual(ok, [])
        doc = {"proportionProfile": {"headUnits": 4.2}, "parts": []}
        patched = apply_json_patch(doc, [{"op": "replace", "path": "/proportionProfile/headUnits", "value": 4.0}])
        self.assertEqual(patched["proportionProfile"]["headUnits"], 4.0)

        graph = IterationGraph()
        base_metrics = [{"id": "helmet_identity", "value": 0.9, "passed": True}]
        graph.add(revision_id="r0", parent_id=None, blueprint=doc, score=0.9, metrics=base_metrics)
        candidate = [{"id": "helmet_identity", "value": 0.5, "passed": False}]
        regressions = graph.detect_critical_regression(
            candidate,
            base_metrics,
            critical_ids={"helmet_identity"},
        )
        self.assertTrue(regressions)
        self.assertEqual(map_issue_to_scope("attachment_contact")["root"], "parts")

    def test_budget_stagnation_stop(self) -> None:
        budget = IterationBudget(max_iterations=10, stagnation_limit=2)
        budget.stagnant_steps = 2
        self.assertFalse(budget.remaining())
        self.assertEqual(budget.stop_reason(), "stagnation")

    def test_production_fit_forbids_proxy_and_uses_metrics(self) -> None:
        self.assertTrue(EXPERIMENTAL_PROXY)
        self.assertEqual(EXPERIMENTAL_PROXY_TAG, "experimental-proxy")
        self.assertFalse(describe_fit_root_mass_proxy()["productionAllowed"])
        with self.assertRaises(RuntimeError):
            assert_production_fit_path(["run_production", "fit_root_mass"])

        bp = build_stylized_character_blueprint()
        with tempfile.TemporaryDirectory() as td:
            result = coarse_to_fine_fit(
                bp,
                budget=IterationBudget(max_iterations=2, max_renders=6),
                work_dir=td,
            )
            self.assertFalse(result["proxyUsed"])
            self.assertIn("alpha/part-id", result["objective"])
            self.assertIsNotNone(result["bestRevisionId"])
            self.assertTrue(Path(result["referenceAlpha"]["source-34"]).is_file())
            # history records accept/rollback decisions
            self.assertTrue(any(h.get("stage") == "initial" for h in result["history"]))

    def test_render_cache_reuses_unaffected(self) -> None:
        cache = RenderCache()
        calls = {"n": 0}

        def render():
            calls["n"] += 1
            return {"path": "x.png", "hash": "h"}

        a = cache.get_or_render(
            revision_id="r1", profile_id="front", pass_name="beauty", fingerprint="fp", render_fn=render
        )
        b = cache.get_or_render(
            revision_id="r1", profile_id="front", pass_name="beauty", fingerprint="fp", render_fn=render
        )
        self.assertEqual(a["cache"], "miss")
        self.assertEqual(b["cache"], "hit")
        self.assertEqual(calls["n"], 1)


class M6PortabilityRuntimeTests(unittest.TestCase):
    def test_named_helper_rewrite_and_portable_bundle(self) -> None:
        src = "function box(w, h, d) { return new Box(w,h,d); }"
        rewritten = rewrite_positional_helpers_to_named(src)
        self.assertIn("function box(args)", rewritten)
        with tempfile.TemporaryDirectory() as td:
            manifest = emit_portable_bundle(
                factory_source='import x from "../../../engine/cast/surface/presets.json";\nexport const n=1;\n',
                out_dir=td,
            )
            self.assertIn("factory.ts", manifest["files"])
            factory = (Path(td) / "factory.ts").read_text(encoding="utf-8")
            self.assertNotIn("../../../engine/", factory)
            self.assertEqual(manifest["externalPathLeaks"], [])

    def test_utf8_gate(self) -> None:
        self.assertEqual(utf8_gate("hello"), [])
        self.assertIn("replacement_character", utf8_gate("bad\ufffdtext"))

    def test_dispose_and_leak_probe(self) -> None:
        rt = FormRuntime()
        state = {"n": 0}
        rt.track("geometry", "g1", lambda: state.__setitem__("n", state["n"] + 1), size_bytes=100)
        rt.track("material", "m1", lambda: state.__setitem__("n", state["n"] + 1), size_bytes=50)
        result = rt.dispose()
        self.assertTrue(result["allDisposed"])
        self.assertEqual(state["n"], 2)
        self.assertEqual(rt.live_bytes, 0)
        rt.dispose()
        self.assertEqual(state["n"], 2)
        with tempfile.TemporaryDirectory() as td:
            probe = leak_probe(3, work_dir=td)
            self.assertTrue(probe["ownershipReleasedEachCycle"])
            self.assertEqual(probe["finalLiveBytes"], 0)
            self.assertIn("rssBytesSeries", probe)
            self.assertEqual(len(probe["rssBytesSeries"]), 3)

    def test_compute_budget_and_promotion(self) -> None:
        budget = ComputeBudget(max_parallel_stages=1)
        report = ProfileReport()
        with budget.stage("sense") as profile:
            profile.render_count = 2
        report.add(profile)
        self.assertEqual(budget.active_stages, 0)
        self.assertGreaterEqual(report.to_dict()["stages"][0]["wallSeconds"], 0.0)
        with self.assertRaises(RuntimeError):
            budget.acquire()
            budget.acquire()
        budget.release()
        promoted = promote_coarse_to_fine([{"score": 0.2}, {"score": 0.9}, {"score": 0.5}], keep=2)
        self.assertEqual([p["score"] for p in promoted], [0.9, 0.5])

    def test_skill_validation_and_forward_fixture(self) -> None:
        report = validate_skill_folder(ROOT)
        self.assertTrue(report["ok"], report)
        self.assertLessEqual(report["lineCount"], 500)
        # forward-test artifact: generic prop vs character project stubs
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name, use_char in (("character", True), ("prop", False)):
                if use_char:
                    project = {"useCharacterSlice": True, "name": name, "strict": True}
                    dump_json(root / f"{name}.json", project)
                    result = run_production(root / f"{name}.json", out_dir=root / name)
                    self.assertIn("review", result["stages"])

    def test_surface_preset_local_module_exists(self) -> None:
        path = ROOT / "demo" / "src" / "detail" / "surfacePresets.ts"
        self.assertTrue(path.exists())
        kit = (ROOT / "demo" / "src" / "detail" / "surfaceKit.ts").read_text(encoding="utf-8")
        self.assertIn('from "./surfacePresets"', kit)
        self.assertNotIn("../../../engine/", kit)

    def test_ci_workflow_exists(self) -> None:
        ci = ROOT / ".github" / "workflows" / "ci.yml"
        self.assertTrue(ci.exists())
        text = ci.read_text(encoding="utf-8")
        self.assertIn("unittest discover", text)
        self.assertIn("typecheck", text)
        self.assertIn("python -m build", text)
        provision = text.index("- name: Provision Playwright Chromium")
        preflight = text.index("- name: Preflight")
        runtime = text.index("- name: Runtime smoke")
        self.assertLess(provision, preflight)
        self.assertLess(preflight, runtime)
        self.assertIn("playwright install --with-deps chromium", text)
        self.assertNotIn("|| true", text)
        self.assertNotIn("continue-on-error: true", text)
        self.assertIn("gpthreejs --help", text)
        self.assertIn("test:runtime", text)


if __name__ == "__main__":
    unittest.main()
