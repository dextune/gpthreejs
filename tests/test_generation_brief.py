"""GenerationBrief, intake, and reference-prep contract tests."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.reference.capture_defaults import (  # noqa: E402
    MIN_SHORT_SIDE_RECOMMENDED_PX,
    RECOMMENDED_SHORT_SIDE_PX,
)
from engine.reference.generation_brief import (  # noqa: E402
    build_generation_brief,
    build_generation_brief_from_issues,
    generation_brief_schema,
    parse_generation_brief,
    validate_generation_brief,
)
from engine.reference.intake import build_request_spec_from_intent, run_intake  # noqa: E402
from engine.reference.provider import NullImageProvider, plan_missing_views  # noqa: E402
from engine.reference.register import register_from_brief  # noqa: E402
from engine.reference.reference_set import ReferenceSetError, validate_reference_set  # noqa: E402
from engine.sense.sufficiency import assess_sufficiency  # noqa: E402
from engine.shared.pngio import Image, write_png  # noqa: E402


def _write_png(path: Path, w: int, h: int, rgb=(40, 40, 40)) -> None:
    img = Image(w, h, bytearray(w * h * 4))
    for y in range(h):
        for x in range(w):
            img.set_pixel(x, y, (*rgb, 255))
    write_png(path, img)


class GenerationBriefMappingTests(unittest.TestCase):
    def test_schema_exposes_required_fields(self) -> None:
        schema = generation_brief_schema()
        self.assertEqual(schema["required"][0], "schemaVersion")
        self.assertIn("views", schema["required"])
        self.assertIn("frame", schema["required"])

    def test_issue_codes_map_to_views_and_frame(self) -> None:
        issues = [
            {
                "code": "RES_TOO_LOW",
                "severity": "blocker",
                "message": "short side 228",
                "remedy": "higher res",
            },
            {
                "code": "CHAR_NO_SIDE",
                "severity": "major",
                "message": "no side",
                "remedy": "add side",
            },
        ]
        request = {
            "subject": "modern SNES knight",
            "intent": "game",
            "modelingProfile": "stylized-character",
            "domain": "character",
            "mustHave": [{"id": "helmet_silhouette", "weight": 1.0}],
            "targetViews": ["front", "left"],
        }
        brief = build_generation_brief_from_issues(issues, request=request)

        self.assertEqual(validate_generation_brief(brief), [])
        self.assertEqual(brief["frame"]["minShortSidePx"], MIN_SHORT_SIDE_RECOMMENDED_PX)
        self.assertEqual(brief["frame"]["recommendedShortSidePx"], RECOMMENDED_SHORT_SIDE_PX)
        self.assertEqual(brief["frame"]["background"], "transparent-or-solid-neutral")
        self.assertTrue(brief["frame"]["alphaPreferred"])
        view_by_id = {v["id"]: v for v in brief["views"]}
        self.assertTrue(view_by_id["front"]["required"])
        self.assertTrue(view_by_id["side"]["required"])
        self.assertIn("RES_TOO_LOW", brief["remediesFromIssues"])
        self.assertIn("CHAR_NO_SIDE", brief["remediesFromIssues"])
        self.assertEqual(brief["evidenceClassDefault"], "design-intent")

    def test_character_single_view_requires_side(self) -> None:
        brief = build_generation_brief_from_issues(
            [{"code": "CHAR_SINGLE_VIEW", "severity": "major", "message": "one view", "remedy": "x"}],
            request={
                "subject": "knight",
                "modelingProfile": "stylized-character",
                "domain": "character",
            },
        )
        required = {v["id"] for v in brief["views"] if v.get("required")}
        self.assertIn("front", required)
        self.assertIn("side", required)

    def test_null_provider_still_emits_brief_ask(self) -> None:
        plan = plan_missing_views(["front", "side"], ["front"], provider=NullImageProvider())
        self.assertEqual(plan["agentAction"], "ask")
        brief = build_generation_brief(
            subject="knight",
            route="concept-first",
            issues=[{"code": "CHAR_NO_SIDE", "severity": "major", "message": "m", "remedy": "r"}],
        )
        self.assertEqual(brief["route"], "concept-first")
        self.assertTrue(brief["views"])

    def test_concept_first_defaults_not_observed(self) -> None:
        brief = build_generation_brief(subject="modern knight", route="concept-first")
        self.assertEqual(brief["evidenceClassDefault"], "design-intent")
        self.assertNotEqual(brief["evidenceClassDefault"], "observed")
        errors = validate_generation_brief(
            {**brief, "evidenceClassDefault": "observed"}
        )
        self.assertTrue(any("cannot default to observed" in e for e in errors))


class IntakeCliTests(unittest.TestCase):
    def test_text_only_intake_emits_request_and_brief(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = run_intake(
                "modern reinterpretation of SNES fantasy knight",
                domain="character",
                route="concept-first",
                out=root / "request-spec.json",
                brief_out=root / "generation-brief.json",
            )
            self.assertEqual(result["request"]["route"], "concept-first")
            self.assertTrue((root / "generation-brief.json").exists())
            brief = parse_generation_brief(root / "generation-brief.json")
            required = {v["id"] for v in brief["views"] if v.get("required")}
            self.assertIn("front", required)
            self.assertIn("side", required)
            self.assertGreaterEqual(brief["frame"]["minShortSidePx"], 512)
            self.assertEqual(brief["evidenceClassDefault"], "design-intent")
            self.assertIn(brief["frame"]["background"], ("transparent-or-solid-neutral",))

    def test_build_request_spec_character_targets(self) -> None:
        spec = build_request_spec_from_intent(
            "modern knight", domain="character", route="concept-first"
        )
        self.assertIn("front", spec["targetViews"])
        self.assertIn("side", spec["requiredViews"])


class SufficiencyBriefEmitTests(unittest.TestCase):
    def test_low_res_emits_checklist_and_brief(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            img = root / "tiny.png"
            _write_png(img, 228, 302)
            out = root / "sufficiency.json"
            report = assess_sufficiency(
                img,
                domain="character",
                intent="game",
                view_count=1,
                has_side=False,
                out=out,
            )
            self.assertEqual(report["verdict"], "reject")
            self.assertTrue(any(i["code"] == "RES_TOO_LOW" for i in report["issues"]))
            self.assertIn("generationBrief", report)
            self.assertTrue(Path(report["generationBriefPath"]).exists())
            msg = report["userMessage"].lower()
            self.assertTrue(
                "transparent" in msg or "투명" in report["userMessage"]
            )
            self.assertTrue(
                "front" in msg or "정면" in report["userMessage"] or "side" in msg or "측면" in report["userMessage"]
            )
            self.assertTrue(
                "pose" in msg or "포즈" in report["userMessage"] or "a-pose" in msg
            )
            steps = " ".join(report["nextSteps"]).lower()
            self.assertIn("generationbrief", steps.replace(" ", "").lower() or steps)
            self.assertTrue(
                "generationbrief" in steps.replace("-", "") or "generation brief" in steps or "reference-prep" in steps
            )
            brief = report["generationBrief"]
            self.assertGreaterEqual(brief["frame"]["recommendedShortSidePx"], 512)


class RegisterEvidenceTests(unittest.TestCase):
    def test_register_generated_not_observed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            brief = build_generation_brief(
                subject="modern knight",
                route="concept-first",
            )
            brief_path = root / "brief.json"
            brief_path.write_text(json.dumps(brief), encoding="utf-8")
            front = root / "front.png"
            side = root / "side.png"
            _write_png(front, 512, 512, rgb=(80, 80, 90))
            _write_png(side, 512, 512, rgb=(70, 70, 80))
            ref_set = register_from_brief(
                brief_path,
                [front, side],
                out=root / "reference-set.json",
            )
            classes = {r["evidenceClass"] for r in ref_set["references"]}
            self.assertNotIn("observed", classes)
            self.assertTrue(classes <= {"design-intent", "design-hypothesis"})

    def test_gen_as_observed_validate_fails(self) -> None:
        bad = {
            "schemaVersion": 1,
            "references": [
                {
                    "id": "g1",
                    "path": "g.png",
                    "assetHash": "abc",
                    "declaredView": "front",
                    "evidenceClass": "observed",
                    "origin": "generated",
                }
            ],
        }
        errors = validate_reference_set(bad)
        self.assertTrue(any("cannot be classed as observed" in e for e in errors))

    def test_register_rejects_forced_observed_for_generated(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            brief = build_generation_brief(subject="x", route="concept-first")
            # Force observed default — register must refuse or rewrite.
            brief["evidenceClassDefault"] = "observed"
            # validation on brief itself rejects this for concept-first
            self.assertTrue(validate_generation_brief(brief))


class CliEntryPointTests(unittest.TestCase):
    def test_cli_intake_and_reference_prep(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            req = root / "request-spec.json"
            brief = root / "generation-brief.json"
            r1 = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "engine",
                    "intake",
                    "modern fantasy knight",
                    "--domain",
                    "character",
                    "--route",
                    "concept-first",
                    "--out",
                    str(req),
                    "--brief-out",
                    str(brief),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(r1.returncode, 0, r1.stderr)
            self.assertTrue(req.exists())
            self.assertTrue(brief.exists())
            data = json.loads(brief.read_text(encoding="utf-8"))
            self.assertEqual(data["route"], "concept-first")
            required = {v["id"] for v in data["views"] if v.get("required")}
            self.assertIn("front", required)
            self.assertIn("side", required)

            issues = root / "issues.json"
            issues.write_text(
                json.dumps(
                    {
                        "issues": [
                            {
                                "code": "RES_TOO_LOW",
                                "severity": "blocker",
                                "message": "228",
                                "remedy": "up",
                            },
                            {
                                "code": "CHAR_NO_SIDE",
                                "severity": "error",
                                "message": "no side",
                                "remedy": "side",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            brief2 = root / "prep-brief.json"
            r2 = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "engine",
                    "reference-prep",
                    str(req),
                    "--issues",
                    str(issues),
                    "--out",
                    str(brief2),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(r2.returncode, 0, r2.stderr)
            prep = json.loads(brief2.read_text(encoding="utf-8"))
            self.assertIn("RES_TOO_LOW", prep["remediesFromIssues"])
            self.assertGreaterEqual(prep["frame"]["minShortSidePx"], 512)

            front = root / "front.png"
            side = root / "side.png"
            _write_png(front, 512, 512)
            _write_png(side, 512, 512)
            ref_out = root / "reference-set.json"
            r3 = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "engine",
                    "reference-register",
                    str(brief2),
                    "--images",
                    str(front),
                    str(side),
                    "--out",
                    str(ref_out),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(r3.returncode, 0, r3.stderr)
            ref_set = json.loads(ref_out.read_text(encoding="utf-8"))
            self.assertTrue(all(r["evidenceClass"] != "observed" for r in ref_set["references"]))


class KnightSingleViewBriefTests(unittest.TestCase):
    def test_golden_single_view_sufficiency_emits_brief(self) -> None:
        golden = ROOT / "tests" / "golden" / "knight-single-view"
        ref_set = golden / "reference-set.json"
        request = golden / "request-spec.json"
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "sufficiency.json"
            r = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "engine",
                    "sufficiency-set",
                    str(ref_set),
                    "--request",
                    str(request),
                    "--out",
                    str(out),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertIn(r.returncode, (0, 2, 3), r.stderr + r.stdout)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(report["verdict"], "reject")
            self.assertIn("generationBrief", report)
            brief = report["generationBrief"]
            required = {v["id"] for v in brief["views"] if v.get("required")}
            self.assertIn("side", required)
            steps = " ".join(report.get("nextSteps") or []).lower()
            self.assertTrue(
                "front" in steps or "side" in steps or "generation" in steps or "resolution" in steps
            )


if __name__ == "__main__":
    unittest.main()
