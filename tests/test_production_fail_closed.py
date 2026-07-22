"""Fail-closed production orchestration and external-fit regressions."""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.blueprint.character import build_stylized_character_blueprint
from engine.critique.fit import coarse_to_fine_fit
from engine.critique.issue_patch import apply_issue_driven_patch
from engine.critique.iteration import IterationBudget
from engine.orchestration.run import run_production
from engine.shared.jsonutil import dump_json
from engine.shared.pngio import Image, read_png, write_png


def _write_alpha(path: Path, *, width: int = 128, height: int = 128) -> None:
    image = Image(width, height, bytearray(width * height * 4))
    for y in range(height // 8, height * 7 // 8):
        for x in range(width // 4, width * 3 // 4):
            image.set_pixel(x, y, (255, 255, 255, 255))
    write_png(path, image)


class ProductionFailClosedTests(unittest.TestCase):
    def test_reference_abort_or_reject_stops_before_validate_and_cast(self) -> None:
        cases = (
            {"agentAction": "abort", "verdict": "conditional", "sufficient": False},
            {"agentAction": "reject", "verdict": "conditional", "sufficient": False},
            {"agentAction": "continue", "verdict": "reject", "sufficient": False},
        )
        for sufficiency in cases:
            with self.subTest(sufficiency=sufficiency), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                project = root / "project.json"
                dump_json(
                    project,
                    {
                        "useCharacterSlice": True,
                        "requestPath": "request.json",
                        "referenceSetPath": "reference-set.json",
                    },
                )
                with (
                    patch(
                        "engine.orchestration.run.plan_reference_set",
                        return_value={"agentAction": "continue"},
                    ),
                    patch(
                        "engine.orchestration.run.sufficiency_reference_set",
                        return_value=sufficiency,
                    ),
                    patch("engine.orchestration.run.build_stylized_character_blueprint") as build,
                    patch("engine.orchestration.run.emit_factory") as emit,
                ):
                    result = run_production(project, out_dir=root / "out")

                self.assertFalse(result["ok"])
                self.assertEqual(result["reason"], "reference sufficiency rejected")
                self.assertEqual(result["stages"], ["reference"])
                self.assertEqual(result["extra"]["sufficiency"], sufficiency)
                build.assert_not_called()
                emit.assert_not_called()
                self.assertFalse((root / "out" / "factory.ts").exists())

    def test_cast_exception_stops_and_removes_stale_factory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = root / "project.json"
            out = root / "out"
            out.mkdir()
            factory = out / "factory.ts"
            factory.write_text("stale factory", encoding="utf-8")
            dump_json(project, {"useCharacterSlice": True, "name": "CastFailure"})

            with (
                patch(
                    "engine.orchestration.run.emit_factory",
                    side_effect=RuntimeError("unsupported geometry"),
                ),
                patch("engine.orchestration.run.render_blueprint_set") as render,
            ):
                result = run_production(project, out_dir=out)

            self.assertFalse(result["ok"])
            self.assertEqual(result["reason"], "cast failed")
            self.assertEqual(result["stages"], ["validate", "cast"])
            self.assertEqual(result["artifacts"]["castError"]["type"], "RuntimeError")
            self.assertIn("unsupported geometry", result["artifacts"]["castError"]["message"])
            self.assertFalse(factory.exists())
            render.assert_not_called()

    def test_fit_prefers_external_reference_and_records_provenance(self) -> None:
        blueprint = build_stylized_character_blueprint()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            external = root / "external-alpha.png"
            _write_alpha(external)
            metadata = {
                "external": True,
                "sources": {"source-34": {"kind": "test-photo", "path": "photo.png"}},
            }

            with patch(
                "engine.critique.software_render.reference_alpha_from_blueprint",
                side_effect=AssertionError("self baseline must not run"),
            ) as self_baseline:
                result = coarse_to_fine_fit(
                    blueprint,
                    budget=IterationBudget(max_iterations=0, max_renders=1),
                    work_dir=root / "fit",
                    reference_alpha={"source-34": str(external)},
                    reference_provenance=metadata,
                )

            self_baseline.assert_not_called()
            provenance = result["referenceProvenance"]
            self.assertTrue(provenance["external"])
            self.assertFalse(provenance["selfBaseline"])
            self.assertEqual(provenance["source"], "caller-external")
            self.assertEqual(provenance["sourcePaths"]["source-34"], str(external))
            self.assertEqual(provenance["metadata"], metadata)
            self.assertEqual(
                provenance["sourceHashes"]["source-34"],
                hashlib.sha256(external.read_bytes()).hexdigest(),
            )
            resolved = Path(result["referenceAlpha"]["source-34"])
            self.assertTrue(resolved.is_file())
            normalized = read_png(resolved)
            self.assertEqual((normalized.width, normalized.height), (96, 96))

    def test_fit_normalizes_and_evaluates_all_supported_external_views(self) -> None:
        blueprint = build_stylized_character_blueprint()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.png"
            left = root / "left.png"
            _write_alpha(source)
            _write_alpha(left, width=96, height=160)

            result = coarse_to_fine_fit(
                blueprint,
                budget=IterationBudget(max_iterations=0, max_renders=1),
                work_dir=root / "fit",
                reference_alpha={"source-34": str(source), "left": str(left)},
            )

            self.assertEqual(set(result["referenceAlpha"]), {"source-34", "left"})
            self.assertEqual(
                {metric["viewId"] for metric in result["graph"]["records"][0]["metrics"]},
                {"source-34", "left"},
            )
            for path in result["referenceAlpha"].values():
                image = read_png(path)
                self.assertEqual((image.width, image.height), (96, 96))

    def test_photo_bbox_drives_camera_and_root_geometry_patches(self) -> None:
        blueprint = build_stylized_character_blueprint()
        metrics = [
            {
                "id": "camera_framing",
                "viewId": "left",
                "passed": False,
                "details": {
                    "render": {"occupancy": 0.2},
                    "reference": {"occupancy": 0.5},
                },
            },
            {
                "id": "silhouette_iou",
                "viewId": "left",
                "passed": False,
                "details": {
                    "render": {"w": 0.4, "h": 0.5},
                    "reference": {"w": 0.6, "h": 0.75},
                },
            },
        ]

        updated, patches = apply_issue_driven_patch(blueprint, metrics)

        left_index = next(
            index for index, profile in enumerate(blueprint["renderProfiles"])
            if profile["id"] == "left"
        )
        self.assertLess(
            abs(updated["renderProfiles"][left_index]["camera"]["position"][0]),
            abs(blueprint["renderProfiles"][left_index]["camera"]["position"][0]),
        )
        self.assertGreater(updated["parts"][0]["transform"]["scale"][0], 1.0)
        self.assertGreater(updated["parts"][0]["transform"]["scale"][1], 1.0)
        self.assertEqual(len(patches), 3)

    def test_run_threads_resolved_external_reference_into_fit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            external = root / "external-alpha.png"
            _write_alpha(external)
            project = root / "project.json"
            dump_json(
                project,
                {
                    "useCharacterSlice": True,
                    "name": "ExternalFit",
                    "referenceAlphaPath": "external-alpha.png",
                },
            )
            fit_result = {
                "schemaVersion": 1,
                "bestRevisionId": "rev-test",
                "referenceProvenance": {"external": True, "selfBaseline": False},
            }
            promoted = build_stylized_character_blueprint("ExternalFit")
            promoted["parts"][0]["transform"]["scale"] = [1.125, 1.25, 1.0]
            promoted["revision"]["id"] = "rev-test"
            fit_result["blueprint"] = promoted

            with patch(
                "engine.orchestration.run.coarse_to_fine_fit",
                return_value=fit_result,
            ) as fit:
                result = run_production(project, max_iterations=1, out_dir=root / "out")

            self.assertIn("iterate", result["stages"])
            fit.assert_called_once()
            kwargs = fit.call_args.kwargs
            self.assertTrue(Path(kwargs["reference_alpha"]["source-34"]).is_file())
            self.assertTrue(kwargs["reference_provenance"]["external"])
            source = kwargs["reference_provenance"]["sources"]["source-34"]
            self.assertEqual(source["kind"], "project.referenceAlphaPath")
            self.assertEqual(Path(source["path"]), external)
            self.assertLess(result["stages"].index("iterate"), result["stages"].index("cast"))
            self.assertEqual(result["artifacts"]["promotedBlueprint"], str(root / "out" / "blueprint.json"))
            factory = (root / "out" / "factory.ts").read_text(encoding="utf-8")
            self.assertIn("mesh_pelvis.scale.set(1.125, 1.25, 1.0)", factory)


if __name__ == "__main__":
    unittest.main()
