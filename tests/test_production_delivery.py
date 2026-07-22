"""Production delivery-grade gates, fixtures, and delivery-export tests."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.blueprint.attachments import assess_attachment_contacts, part_world_transforms
from engine.blueprint.character import build_stylized_character_blueprint
from engine.blueprint.draft import draft_ledger
from engine.blueprint.validate import validate_blueprint
from engine.cli import main as cli_main
from engine.delivery.export import delivery_export
from engine.delivery.gates import evaluate_delivery_gates
from engine.orchestration.run import run_production
from engine.reference.consistency import assess_cross_view_consistency
from engine.reference.pipeline import sufficiency_reference_set
from engine.reference.reference_set import parse_reference_set
from engine.shared.jsonutil import dump_json, load_json


class ProductionDeliveryFixtureTests(unittest.TestCase):
    def test_knight_turnaround_sufficiency_has_side(self) -> None:
        report = sufficiency_reference_set(
            ROOT / "tests/golden/knight/reference-set.json",
            request_path=ROOT / "tests/golden/knight/request-spec.json",
        )
        # multi-view set should not emit CHAR_NO_SIDE
        codes = {i["code"] for i in report.get("issues") or []}
        self.assertNotIn("CHAR_NO_SIDE", codes)
        self.assertTrue(report["viewFlags"]["hasSide"])

    def test_single_view_fails_closed(self) -> None:
        base = ROOT / "tests/golden/knight-single-view"
        report = sufficiency_reference_set(
            base / "reference-set.json",
            request_path=base / "request-spec.json",
        )
        codes = {i["code"] for i in report.get("issues") or []}
        self.assertTrue(codes & {"CHAR_NO_SIDE", "DELIVERY_VIEW_INSUFFICIENT"})
        self.assertFalse(report.get("sufficient"))
        expected = load_json(base / "expected.json")
        for code in expected.get("expectCodes") or []:
            # at least one expected code present
            pass
        self.assertTrue(any(c in codes for c in expected.get("expectCodes") or []))

    def test_mutated_side_consistency_rejects(self) -> None:
        base = ROOT / "tests/golden/knight-mutated-side"
        ref = parse_reference_set(base / "reference-set.json")
        report = assess_cross_view_consistency(ref)
        self.assertFalse(report["passed"])
        codes = {i["code"] for i in report.get("issues") or []}
        self.assertTrue(
            codes
            & {
                "SIDE_VIEW_MUTATED",
                "COLOR_INCONSISTENT",
                "EQUIPMENT_TAMPERED",
                "HANDEDNESS_FLIP",
            }
        )

    def test_generated_cannot_be_observed(self) -> None:
        from engine.reference.reference_set import validate_reference_set

        bad = {
            "schemaVersion": 1,
            "references": [
                {
                    "id": "x",
                    "path": "a.png",
                    "assetHash": "0" * 64,
                    "declaredView": "back",
                    "evidenceClass": "observed",
                    "origin": "generated",
                }
            ],
        }
        errors = validate_reference_set(bad)
        self.assertTrue(any("cannot be classed as observed" in e for e in errors))


class ProductionDeliveryPathTests(unittest.TestCase):
    def test_rotation_aware_attachments(self) -> None:
        bp = build_stylized_character_blueprint()
        transforms = part_world_transforms(bp.get("parts") or [])
        self.assertIn("shield", transforms)
        self.assertIn("sword", transforms)
        # matrices are 4x4
        self.assertEqual(len(transforms["pelvis"]), 4)
        contacts = assess_attachment_contacts(bp.get("parts") or [], bp.get("handles"))
        self.assertTrue(contacts.get("rotationAware"))
        self.assertTrue(contacts["passed"], contacts.get("issues"))

    def test_production_ledger_has_evidence_refs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sense = Path(td) / "sense"
            sense.mkdir()
            (sense / "sense_pack.json").write_text(
                json.dumps(
                    {
                        "palette": {"colors": [{"hex": "#3366cc"}]},
                        "maps": {"edges": {"edge_density": 0.12}},
                        "part_grid": [
                            {"id": "z00", "region": {"x": 0, "y": 0, "w": 0.5, "h": 0.5}}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            out = Path(td) / "ledger.json"
            ledger = draft_ledger(
                "x.png",
                sense,
                out,
                mode="production",
                modeling_profile="stylized-character",
                target_min=8,
            )
            self.assertFalse(any(e.get("status") == "todo" for e in ledger["entries"]))
            self.assertTrue(all(e.get("evidenceRefs") for e in ledger["entries"]))
            self.assertTrue(any("palette:" in str(e.get("evidenceRefs")) for e in ledger["entries"]))

    def test_v2_target_strict_validate(self) -> None:
        result = validate_blueprint(
            ROOT / "tests/golden/knight/blueprints/v2-target.json",
            strict=True,
        )
        self.assertTrue(result.ok, result.errors)

    def test_run_rejects_insufficient_multiview_fixture_before_cast(self) -> None:
        # Multi-view presence does not override low-resolution/consistency blockers.
        project = ROOT / "tests/golden/knight/project.json"
        with tempfile.TemporaryDirectory() as td:
            result = run_production(project, max_iterations=1, out_dir=Path(td) / "out")
            self.assertFalse(result["ok"])
            self.assertEqual(result["reason"], "reference sufficiency rejected")
            self.assertEqual(result["stages"], ["reference"])
            self.assertEqual(result["extra"]["sufficiency"]["agentAction"], "abort")
            self.assertEqual(result["extra"]["sufficiency"]["verdict"], "reject")
            self.assertNotIn("factory", result["artifacts"])
            self.assertNotIn("renderSet", result["artifacts"])

    def test_delivery_export_fail_closed_single_view(self) -> None:
        project = ROOT / "tests/golden/knight-single-view/project.json"
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "delivery"
            result = delivery_export(project, out_dir=out, max_iterations=0)
            # may fail gates even if run partially works
            self.assertFalse(result.get("ok"))
            self.assertTrue((out / "delivery-checklist.json").exists() or (out / "delivery-failed.json").exists())
            checklist = result.get("checklist") or {}
            # DG-01 should fail for missing side when delivery grade set
            if "DG-01" in (checklist.get("gates") or {}):
                self.assertFalse(checklist["gates"]["DG-01"]["passed"])

    def test_delivery_grade_fails_without_external_matte(self) -> None:
        """deliveryGrade=delivery without ReferenceSet/photo matte must fail-closed (no self-IoU theater)."""
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "project.json"
            dump_json(
                project,
                {
                    "useCharacterSlice": True,
                    "name": "NoMatteKnight",
                    "strict": True,
                    "includePolish": True,
                    "deliveryGrade": "delivery",
                },
            )
            out = Path(td) / "delivery"
            result = delivery_export(project, out_dir=out, max_iterations=0)
            self.assertFalse(result.get("ok"))
            checklist = result.get("checklist") or {}
            self.assertFalse(checklist.get("passed"))
            codes = {i["code"] for i in checklist.get("issues") or []}
            self.assertIn("DELIVERY_SILHOUETTE_FAIL", codes)
            dg06 = (checklist.get("gates") or {}).get("DG-06") or {}
            self.assertFalse(dg06.get("passed"))
            # Must not claim external reference on self-only path
            self.assertFalse(dg06.get("externalReference", True))

    def test_delivery_export_rejects_insufficient_multiview_fixture(self) -> None:
        """Delivery export cannot bypass production reference rejection."""
        project = ROOT / "tests/golden/knight/project.json"
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "delivery"
            result = delivery_export(project, out_dir=out, max_iterations=0)
            self.assertFalse(result.get("ok"))
            checklist = result["checklist"]
            self.assertFalse(checklist["passed"])
            self.assertEqual(result["run"]["stages"], ["reference"])
            self.assertFalse(result["run"]["ok"])
            self.assertIsNone(result["bundle"])
            self.assertTrue((out / "delivery-failed.json").is_file())

    def test_delivery_export_cli(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "p.json"
            dump_json(
                project,
                {"useCharacterSlice": True, "name": "CliK", "strict": True, "deliveryGrade": "standard"},
            )
            code = cli_main(
                ["delivery-export", str(project), "--out", str(Path(td) / "out"), "--max-iterations", "0"]
            )
            self.assertIn(code, (0, 2))

    def test_evaluate_gates_rejects_accept_without_policy(self) -> None:
        checklist = evaluate_delivery_gates(
            project={"deliveryGrade": "delivery", "modelingProfile": "stylized-character"},
            project_dir=ROOT,
            review_report={"recommendation": "accept", "policyTrace": {}},
            blueprint=build_stylized_character_blueprint(),
            metric_report={
                "metrics": [
                    {
                        "id": "silhouette_iou",
                        "value": 0.9,
                        "passed": True,
                        "externalReference": True,
                    },
                    {"id": "camera_framing", "value": 0.9, "passed": True},
                    {"id": "part_visibility", "value": 0.9, "passed": True},
                    {"id": "material_readability", "value": 0.9, "passed": True},
                    {"id": "attachment_contact", "value": 0.9, "passed": True},
                    {"id": "handedness", "value": 0.9, "passed": True},
                ]
            },
            factory_path=None,
        )
        self.assertFalse(checklist["gates"]["DG-11"]["passed"])
        codes = {i["code"] for i in checklist["issues"]}
        self.assertIn("DELIVERY_POLICY_DENY", codes)

    def test_dg09_fails_on_low_handedness_metric(self) -> None:
        checklist = evaluate_delivery_gates(
            project={"deliveryGrade": "delivery", "modelingProfile": "stylized-character"},
            project_dir=ROOT,
            review_report={
                "recommendation": "accept",
                "policyTrace": {
                    "policyIssued": True,
                    "issuer": "review-policy",
                    "decision": "accept",
                },
            },
            blueprint=build_stylized_character_blueprint(),
            metric_report={
                "metrics": [
                    {
                        "id": "silhouette_iou",
                        "value": 0.9,
                        "passed": True,
                        "externalReference": True,
                    },
                    {"id": "camera_framing", "value": 0.9, "passed": True},
                    {"id": "part_visibility", "value": 0.9, "passed": True},
                    {"id": "material_readability", "value": 0.9, "passed": True},
                    {"id": "attachment_contact", "value": 0.9, "passed": True},
                    {"id": "handedness", "value": 0.1, "passed": False},
                ]
            },
            render_set={
                "blueprintHash": "a" * 64,
                "factoryHash": "b" * 64,
                "views": [],
            },
            factory_path=None,
        )
        self.assertFalse(checklist["gates"]["DG-09"]["passed"])
        codes = {i["code"] for i in checklist["issues"]}
        self.assertIn("DELIVERY_HANDEDNESS_FAIL", codes)


if __name__ == "__main__":
    unittest.main()
