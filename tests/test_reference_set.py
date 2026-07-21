"""ReferenceSet, matte, ledger production, and set-CLI contract tests."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.blueprint.draft import draft_ledger  # noqa: E402
from engine.blueprint.ledger_validation import (  # noqa: E402
    CHARACTER_LEDGER_CATEGORIES,
    validate_ledger_production_gate,
)
from engine.cli import main as cli_main  # noqa: E402
from engine.reference.adapter import (  # noqa: E402
    assess_sufficiency_from_reference_set,
    single_image_to_reference_set,
)
from engine.reference.consistency import assess_cross_view_consistency  # noqa: E402
from engine.reference.matte_confidence import assess_matte_confidence  # noqa: E402
from engine.reference.normalize import normalize_reference, pad_image  # noqa: E402
from engine.reference.provider import (  # noqa: E402
    NullImageProvider,
    ProviderBudget,
    get_image_provider,
    plan_missing_views,
)
from engine.reference.reference_set import (  # noqa: E402
    ReferenceSetError,
    build_reference_entry,
    build_reference_set,
    parse_reference_set,
    validate_reference_set,
    write_reference_set,
)
from engine.reference.views import feature_coverage, resolve_view_flags  # noqa: E402
from engine.shared.pngio import Image, write_png  # noqa: E402


def _solid_png(path: Path, w: int = 128, h: int = 128, rgb=(200, 40, 40), bg=(240, 240, 240)) -> None:
    img = Image(w, h, bytearray(w * h * 4))
    for y in range(h):
        for x in range(w):
            img.set_pixel(x, y, (*bg, 255))
    # centered subject leaving margin
    x0, y0, x1, y1 = w // 4, h // 4, 3 * w // 4, 3 * h // 4
    for y in range(y0, y1):
        for x in range(x0, x1):
            img.set_pixel(x, y, (*rgb, 255))
    write_png(path, img)


def _frame_filling_png(path: Path, w: int = 64, h: int = 64, rgb=(30, 80, 200)) -> None:
    """Near-full subject with only corner-sampled pixels left as background.

    Corner-distance matte needs a distinct background sample at the corners, but
    the opaque subject still touches most of the frame edge (high edge contact).
    """
    img = Image(w, h, bytearray(w * h * 4))
    bg = (245, 245, 245)
    for y in range(h):
        for x in range(w):
            img.set_pixel(x, y, (*rgb, 255))
    # paint only the four corner samples as background so matte can run
    for x, y in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (0, h // 2)):
        img.set_pixel(x, y, (*bg, 255))
    write_png(path, img)


class ReferenceSetContractTests(unittest.TestCase):
    def test_reference_set_validates_observed_generated_inferred(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            img = root / "hero.png"
            _solid_png(img)
            observed = build_reference_entry(
                ref_id="ref-front",
                path=img,
                declared_view="front",
                evidence_class="observed",
            )
            generated = build_reference_entry(
                ref_id="ref-back",
                path=img,
                declared_view="back",
                evidence_class="design-hypothesis",
                origin="generated",
            )
            inferred = build_reference_entry(
                ref_id="ref-left",
                path=img,
                declared_view="left",
                evidence_class="inferred",
            )
            good = build_reference_set([observed, generated, inferred])
            self.assertEqual(validate_reference_set(good), [])

            bad = build_reference_set(
                [
                    build_reference_entry(
                        ref_id="bad",
                        path=img,
                        declared_view="back",
                        evidence_class="observed",
                        origin="generated",
                    )
                ]
            )
            errors = validate_reference_set(bad)
            self.assertTrue(any("cannot be classed as observed" in e for e in errors))

            out = root / "reference-set.json"
            write_reference_set(out, good)
            parsed = parse_reference_set(out)
            self.assertEqual(len(parsed["references"]), 3)

    def test_generated_as_observed_raises_on_parse(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            img = root / "side.png"
            _solid_png(img)
            payload = {
                "schemaVersion": 1,
                "references": [
                    {
                        "id": "ref-side",
                        "path": str(img),
                        "assetHash": "abc",
                        "declaredView": "left",
                        "evidenceClass": "observed",
                        "origin": "generated",
                    }
                ],
            }
            path = root / "bad.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ReferenceSetError):
                parse_reference_set(path)


class AdapterAndMatteTests(unittest.TestCase):
    def test_single_image_adapter_preserves_sufficiency_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            img = root / "ok.png"
            _solid_png(img, 512, 640)
            ref_set = single_image_to_reference_set(img, declared_view="source-34")
            self.assertEqual(len(ref_set["references"]), 1)
            report = assess_sufficiency_from_reference_set(
                ref_set,
                domain="character",
                intent="game",
            )
            self.assertIn(report["agentAction"], ("ask", "continue", "abort"))
            self.assertEqual(report["referenceSet"]["referenceCount"], 1)

    def test_matte_confidence_records_signals(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            img = Path(td) / "subj.png"
            _solid_png(img)
            report = assess_matte_confidence(img)
            signals = report["signals"]
            for key in (
                "occupancy",
                "edgeContactRatio",
                "largestComponentRatio",
                "noiseRatio",
                "cornerBackgroundVariance",
            ):
                self.assertIn(key, signals)
            self.assertGreaterEqual(report["confidence"], 0.0)
            self.assertLessEqual(report["confidence"], 1.0)

    def test_frame_filling_normalizes_with_reversible_transform(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            img = root / "fill.png"
            _frame_filling_png(img)
            before = assess_matte_confidence(img)
            self.assertGreater(before["signals"]["occupancy"], 0.8)
            self.assertTrue(
                before.get("normalizationCandidate")
                or "subject_fills_frame" in before.get("issues", [])
                or before["signals"]["edgeContactRatio"] > 0.3
            )
            result = normalize_reference(img, out_path=root / "fill.normalized.png", force=True)
            self.assertTrue(result["applied"])
            self.assertEqual(result["normalization"]["operation"], "pad")
            self.assertTrue(result["normalization"]["reversible"])
            self.assertEqual(result["sourceHash"], result["normalization"]["sourceHash"])
            self.assertTrue(Path(result["normalizedPath"]).exists())
            # padding should reduce edge contact relative to the pre-pad subject
            after = result["confidenceAfter"]["signals"]
            self.assertLess(after["edgeContactRatio"], before["signals"]["edgeContactRatio"])


class ViewsConsistencyLedgerTests(unittest.TestCase):
    def test_manifest_view_flags_override_cli(self) -> None:
        ref_set = {
            "schemaVersion": 1,
            "references": [
                {
                    "id": "a",
                    "path": "a.png",
                    "assetHash": "1",
                    "declaredView": "front",
                    "detectedView": "front",
                    "evidenceClass": "observed",
                },
                {
                    "id": "b",
                    "path": "b.png",
                    "assetHash": "2",
                    "declaredView": "left",
                    "detectedView": "left",
                    "evidenceClass": "observed",
                },
                {
                    "id": "c",
                    "path": "c.png",
                    "assetHash": "3",
                    "declaredView": "back",
                    "detectedView": "back",
                    "evidenceClass": "design-hypothesis",
                },
            ],
        }
        resolved = resolve_view_flags(
            ref_set,
            cli_view_count=1,
            cli_has_side=False,
            cli_has_back=False,
        )
        self.assertEqual(resolved["viewCount"], 3)
        self.assertTrue(resolved["hasSide"])
        self.assertTrue(resolved["hasBack"])
        self.assertTrue(any("overridden by manifest" in w for w in resolved["warnings"]))

    def test_mutated_side_fixture_rejected(self) -> None:
        ref_set = {
            "schemaVersion": 1,
            "references": [
                {
                    "id": "front",
                    "path": "f.png",
                    "assetHash": "1",
                    "declaredView": "front",
                    "evidenceClass": "observed",
                    "palette": ["#2244aa", "#cccccc"],
                    "visibleFeatures": ["blue_feather_plume", "large_sun_shield"],
                    "handedness": "right",
                },
                {
                    "id": "side",
                    "path": "s.png",
                    "assetHash": "2",
                    "declaredView": "left",
                    "evidenceClass": "observed",
                    "palette": ["#ff0000", "#000000"],
                    "visibleFeatures": ["blue_feather_plume__mutated", "large_sun_shield"],
                    "colorMutated": True,
                    "consistencyTag": "mutated-side",
                },
            ],
        }
        report = assess_cross_view_consistency(ref_set)
        self.assertFalse(report["passed"])
        codes = {i["code"] for i in report["issues"]}
        self.assertTrue(codes & {"SIDE_VIEW_MUTATED", "COLOR_INCONSISTENT", "EQUIPMENT_TAMPERED"})

    def test_production_ledger_meets_target_min_without_todos(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sense_dir = root / "sense"
            sense_dir.mkdir()
            (sense_dir / "sense_pack.json").write_text(
                json.dumps({"palette": {"colors": [{"hex": "#3366cc"}]}, "part_grid": []}),
                encoding="utf-8",
            )
            out = root / "ledger.json"
            ledger = draft_ledger(
                "hero.png",
                sense_dir,
                out,
                mode="production",
                modeling_profile="stylized-character",
                target_min=6,
            )
            self.assertGreaterEqual(len(ledger["entries"]), 6)
            self.assertFalse(any(e.get("status") == "todo" for e in ledger["entries"]))
            self.assertEqual(ledger["agentAction"], "continue")
            categories = {e.get("category") for e in ledger["entries"]}
            for cat in CHARACTER_LEDGER_CATEGORIES:
                self.assertIn(cat, categories)
            self.assertEqual(validate_ledger_production_gate(ledger, modeling_profile="stylized-character"), [])

    def test_character_coverage_gate_reports_missing_categories(self) -> None:
        ledger = {
            "mode": "production",
            "targetMin": 2,
            "modelingProfile": "stylized-character",
            "entries": [
                {
                    "id": "a",
                    "kind": "identity",
                    "description": "only silhouette",
                    "region": {"x": 0, "y": 0, "w": 1, "h": 1},
                    "scale": "global",
                    "affects": "geometry",
                    "confidence": 0.5,
                    "status": "draft",
                    "evidenceRefs": [],
                    "category": "silhouette-proportion",
                },
                {
                    "id": "b",
                    "kind": "identity",
                    "description": "helmet only",
                    "region": {"x": 0, "y": 0, "w": 1, "h": 1},
                    "scale": "meso",
                    "affects": "geometry",
                    "confidence": 0.5,
                    "status": "draft",
                    "evidenceRefs": [],
                    "category": "head-face-helmet",
                },
            ],
        }
        errors = validate_ledger_production_gate(ledger, modeling_profile="stylized-character")
        self.assertTrue(any("missing character coverage categories" in e for e in errors))

    def test_feature_coverage_weights_visible_features(self) -> None:
        ref_set = {
            "references": [
                {
                    "id": "a",
                    "evidenceClass": "observed",
                    "visibleFeatures": ["plume"],
                }
            ]
        }
        report = feature_coverage(
            ref_set,
            [{"id": "plume", "weight": 1.0}, {"id": "shield", "weight": 1.0}],
        )
        self.assertAlmostEqual(report["coverage"], 0.5)

    def test_null_provider_asks_clearly(self) -> None:
        provider = get_image_provider(None)
        self.assertIsInstance(provider, NullImageProvider)
        budget = ProviderBudget(max_generations=2, max_edits=2)
        plan = plan_missing_views(["front", "left", "back"], ["front"], budget=budget, provider=provider)
        self.assertEqual(plan["agentAction"], "ask")
        self.assertIn("no image generation provider", plan["reason"])
        self.assertIn("left", plan["missingViews"])


class ReferenceCliTests(unittest.TestCase):
    def test_reference_plan_and_sufficiency_set_cli(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            img = root / "hero.png"
            _solid_png(img, 400, 400)
            request = {
                "schemaVersion": 1,
                "subject": "test knight",
                "intent": "game",
                "modelingProfile": "stylized-character",
                "qualityMode": "sharp",
                "mustHave": [{"id": "plume", "weight": 1.0}],
                "mustNotHave": [],
                "targetViews": ["source-34", "front", "left", "right", "back"],
            }
            req_path = root / "request-spec.json"
            req_path.write_text(json.dumps(request), encoding="utf-8")

            ref_out = root / "reference-set.json"
            code = cli_main(["wrap-image", str(img), "--view", "source-34", "--out", str(ref_out)])
            self.assertEqual(code, 0)
            self.assertTrue(ref_out.exists())

            plan_out = root / "reference-plan.json"
            code = cli_main(
                [
                    "reference-plan",
                    str(req_path),
                    "--reference-set",
                    str(ref_out),
                    "--out",
                    str(plan_out),
                ]
            )
            self.assertEqual(code, 0)
            plan = json.loads(plan_out.read_text(encoding="utf-8"))
            self.assertEqual(plan["request"]["subject"], "test knight")
            self.assertIn("missingViewPlan", plan)

            report_out = root / "sufficiency.json"
            code = cli_main(
                [
                    "sufficiency-set",
                    str(ref_out),
                    "--request",
                    str(req_path),
                    "--out",
                    str(report_out),
                ]
            )
            self.assertIn(code, (0, 2, 3))
            report = json.loads(report_out.read_text(encoding="utf-8"))
            self.assertIn("verdict", report)
            self.assertIn("viewFlags", report)

            sense_dir = root / "sense-empty"
            sense_dir.mkdir()
            (sense_dir / "sense_pack.json").write_text("{}", encoding="utf-8")
            ledger_out = root / "ledger.json"
            code = cli_main(
                [
                    "ledger-set",
                    str(ref_out),
                    "--sense",
                    str(sense_dir),
                    "--request",
                    str(req_path),
                    "--out",
                    str(ledger_out),
                ]
            )
            self.assertIn(code, (0, 2))
            ledger = json.loads(ledger_out.read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(ledger["entries"]), ledger["targetMin"])
            self.assertFalse(any(e.get("status") == "todo" for e in ledger["entries"]))


if __name__ == "__main__":
    unittest.main()
