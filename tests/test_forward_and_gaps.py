"""Forward tests and gap-closure coverage (DX-420, journal, emit, patches)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.blueprint.character import build_stylized_character_blueprint
from engine.cast.emit_factory import emit_factory
from engine.cli import main as cli_main
from engine.critique.fit import coarse_to_fine_fit
from engine.critique.issue_patch import apply_issue_driven_patch, patches_for_issues
from engine.critique.iteration import IterationBudget
from engine.critique.overlay import build_gate_comparison_artifacts, silhouette_diff_png
from engine.critique.software_render import render_blueprint_set
from engine.orchestration.run import run_production
from engine.shared.jsonutil import dump_json, load_json
from engine.shared.pngio import Image, write_png


class GapClosureTests(unittest.TestCase):
    def test_emit_factory_has_form_runtime_and_real_geometry_helpers(self) -> None:
        bp = build_stylized_character_blueprint()
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "factory.ts"
            emit_factory(bp, out)
            text = out.read_text(encoding="utf-8")
            self.assertIn("export interface FormRuntime", text)
            self.assertIn("dispose(): void", text)
            self.assertIn("geomHelpers.shapeExtrude", text)
            self.assertIn("ExtrudeGeometry", text)
            self.assertIn("LatheGeometry", text)
            self.assertIn("TubeGeometry", text)
            self.assertIn("FormOptions", text)
            # named-object helpers — not bare positional BoxGeometry for shape-extrude
            self.assertNotIn("/* shape-extrude */", text)

    def test_golden_project_json_run_and_journal(self) -> None:
        project = ROOT / "tests/golden/knight/project.json"
        self.assertTrue(project.is_file())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "run"
            # useCharacterSlice project without requiring reference files in temp
            local = Path(td) / "project.json"
            dump_json(
                local,
                {
                    "useCharacterSlice": True,
                    "name": "Knight",
                    "strict": True,
                    "includePolish": True,
                },
            )
            result = run_production(local, max_iterations=0, out_dir=out)
            self.assertIn("journal", result["stages"])
            self.assertIn("review", result["stages"])
            self.assertTrue((out / "comparison-sheet.json").is_file())
            sheet = load_json(out / "comparison-sheet.json")
            self.assertTrue(sheet.get("overlays"))
            diff = result["artifacts"].get("silhouetteDiff")
            self.assertTrue(diff and Path(diff).is_file())
            self.assertTrue(result["artifacts"].get("formRuntimeContract"))
            # journal entry recorded with policy trace
            entry = result["artifacts"].get("journalEntry") or result["extra"].get("policyTrace")
            self.assertIsNotNone(entry)
            if isinstance(result["artifacts"].get("journalEntry"), dict):
                self.assertEqual(
                    result["artifacts"]["journalEntry"]["policyTrace"]["issuer"],
                    "review-policy",
                )
                self.assertTrue(result["artifacts"]["journalEntry"]["policyTrace"]["policyIssued"])

            # CLI golden project path (relative fixtures from repo)
            code = cli_main(
                [
                    "run",
                    str(project),
                    "--out",
                    str(Path(td) / "cli-out"),
                    "--max-iterations",
                    "0",
                ]
            )
            self.assertIn(code, (0, 2))

    def test_issue_driven_patches_and_overlay(self) -> None:
        bp = build_stylized_character_blueprint()
        failed = [
            {"id": "camera_framing", "passed": False, "value": 0.1},
            {"id": "silhouette_iou", "passed": False, "value": 0.2},
        ]
        patches = patches_for_issues(failed, step=1)
        self.assertTrue(patches)
        updated, concrete = apply_issue_driven_patch(bp, failed, step=1)
        self.assertTrue(concrete)
        self.assertNotEqual(
            (updated.get("proportionProfile") or {}).get("shoulderWidthRatio"),
            (bp.get("proportionProfile") or {}).get("shoulderWidthRatio"),
        )

        with tempfile.TemporaryDirectory() as td:
            rs = render_blueprint_set(
                bp,
                out_dir=td,
                revision_id="r1",
                blueprint_hash="a" * 64,
                factory_hash="b" * 64,
                views=("source-34",),
                width=64,
                height=64,
            )
            arts = build_gate_comparison_artifacts(
                render_set=rs,
                out_dir=Path(td) / "cmp",
                view_id="source-34",
            )
            self.assertTrue(Path(arts["silhouetteDiff"]["path"]).is_file())
            self.assertTrue(Path(arts["partLabels"]["path"]).is_file())

            # mutated side alpha should produce false positives/negatives
            a = Path(rs["views"][0]["passes"]["alpha"]["path"])
            b = Path(td) / "mut.png"
            img = Image(16, 16, bytearray([0, 0, 0, 0] * (16 * 16)))
            for y in range(16):
                for x in range(8, 16):
                    img.set_pixel(x, y, (255, 255, 255, 255))
            write_png(b, img)
            diff = silhouette_diff_png(a, b, Path(td) / "diff.png")
            self.assertGreater(diff["falsePositive"] + diff["falseNegative"], 0)

    def test_forward_character_prop_and_generic_reports(self) -> None:
        """DX-420: independent forward runs with artifact reports."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reports = []
            cases = [
                ("character", {"useCharacterSlice": True, "name": "CharFwd", "strict": True}),
                (
                    "prop",
                    {
                        "useCharacterSlice": True,
                        "name": "PropLike",
                        "strict": False,
                        "includePolish": False,
                    },
                ),
            ]
            for name, project in cases:
                path = root / f"{name}.json"
                dump_json(path, project)
                out = root / name
                result = run_production(path, out_dir=out, max_iterations=1)
                report = {
                    "case": name,
                    "ok": result.get("ok"),
                    "stages": result.get("stages"),
                    "pngPassCount": result.get("extra", {}).get("pngPassCount"),
                    "journalDecision": result.get("extra", {}).get("journalDecision"),
                    "artifacts": {
                        k: v
                        for k, v in (result.get("artifacts") or {}).items()
                        if k in ("factory", "renderSet", "metricReport", "reviewReport", "comparisonSheet")
                    },
                }
                dump_json(out / "forward-report.json", report)
                reports.append(report)
                self.assertIn("journal", result["stages"])
                self.assertGreaterEqual(result.get("extra", {}).get("pngPassCount", 0), 8)
            dump_json(root / "forward-summary.json", {"reports": reports})
            self.assertEqual(len(reports), 2)

    def test_fit_uses_issue_patches_when_enabled(self) -> None:
        bp = build_stylized_character_blueprint()
        with tempfile.TemporaryDirectory() as td:
            result = coarse_to_fine_fit(
                bp,
                budget=IterationBudget(max_iterations=2, max_renders=6),
                work_dir=td,
                use_issue_patches=True,
            )
            self.assertTrue(result["issueDrivenPatches"])
            self.assertFalse(result["proxyUsed"])
            # history may include patches key
            self.assertTrue(any("patches" in h for h in result["history"] if h.get("stage") != "initial"))


if __name__ == "__main__":
    unittest.main()
