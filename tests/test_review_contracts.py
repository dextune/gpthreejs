"""Render/review artifact schema contract tests."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.critique.contracts import (  # noqa: E402
    METRIC_ENTRY_REQUIRED_FIELDS,
    METRIC_REPORT_REQUIRED_FIELDS,
    REQUIRED_RENDER_PASSES,
    RENDER_PASS_REQUIRED_FIELDS,
    RENDER_SET_REQUIRED_FIELDS,
    RENDER_VIEW_REQUIRED_FIELDS,
    REVIEW_ISSUE_REQUIRED_FIELDS,
    REVIEW_REPORT_REQUIRED_FIELDS,
    metric_report_schema,
    render_set_schema,
    review_report_schema,
    validate_metric_report,
    validate_metric_report_freshness,
    validate_render_set,
    validate_render_set_freshness,
    validate_review_report,
    validate_review_report_freshness,
    artifact_content_hash_value,
)
from engine.shared.artifacts import artifact_content_hash  # noqa: E402


class ReviewContractTests(unittest.TestCase):
    def test_render_metric_review_schemas_expose_required_fields(self) -> None:
        self.assertEqual(tuple(render_set_schema()["required"]), RENDER_SET_REQUIRED_FIELDS)
        self.assertEqual(tuple(render_set_schema()["properties"]["views"]["items"]["required"]), RENDER_VIEW_REQUIRED_FIELDS)
        self.assertEqual(tuple(metric_report_schema()["required"]), METRIC_REPORT_REQUIRED_FIELDS)
        self.assertEqual(
            tuple(metric_report_schema()["properties"]["metrics"]["items"]["required"]),
            METRIC_ENTRY_REQUIRED_FIELDS,
        )
        self.assertEqual(tuple(review_report_schema()["required"]), REVIEW_REPORT_REQUIRED_FIELDS)
        self.assertEqual(
            tuple(review_report_schema()["properties"]["issues"]["items"]["required"]),
            REVIEW_ISSUE_REQUIRED_FIELDS,
        )

    def test_valid_render_set_metric_report_and_review_report_pass(self) -> None:
        self.assertEqual(validate_render_set(_valid_render_set()), [])
        self.assertEqual(validate_metric_report(_valid_metric_report()), [])
        self.assertEqual(validate_review_report(_valid_review_report()), [])

    def test_invalid_render_set_reports_missing_pass_path(self) -> None:
        render_set = _valid_render_set()
        del render_set["views"][0]["passes"]["partId"]

        errors = validate_render_set(render_set)

        self.assertIn("$.views[0].passes.partId: missing required render pass", errors)
        for pass_name in REQUIRED_RENDER_PASSES:
            self.assertIn(pass_name, ("beauty", "alpha", "partId"))
        self.assertEqual(RENDER_PASS_REQUIRED_FIELDS, ("path", "hash"))

    def test_invalid_metric_report_reports_missing_metric_field(self) -> None:
        metric_report = _valid_metric_report()
        del metric_report["metrics"][0]["threshold"]

        errors = validate_metric_report(metric_report)

        self.assertIn("$.metrics[0].threshold: missing required field", errors)

    def test_invalid_review_report_rejects_unknown_recommendation_and_issue_shape(self) -> None:
        review_report = _valid_review_report()
        review_report["recommendation"] = "ship-it"
        del review_report["issues"][0]["rootCause"]

        errors = validate_review_report(review_report)

        self.assertIn("$.recommendation: unsupported decision 'ship-it'", errors)
        self.assertIn("$.issues[0].rootCause: missing required field", errors)

    def test_stale_downstream_artifacts_report_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            blueprint_path = root / "blueprint.json"
            factory_path = root / "factory.ts"
            blueprint_path.write_text('{"name":"Fresh","schemaVersion":2}\n', encoding="utf-8")
            factory_path.write_text("export const fresh = true;\n", encoding="utf-8")

            render_set = _valid_render_set()
            render_set["blueprintHash"] = artifact_content_hash(blueprint_path)
            render_set["factoryHash"] = _sha256(factory_path)
            self.assertEqual(
                validate_render_set_freshness(
                    render_set,
                    blueprint_path=blueprint_path,
                    factory_path=factory_path,
                ),
                [],
            )

            blueprint_path.write_text('{"name":"Changed","schemaVersion":2}\n', encoding="utf-8")
            self.assertIn(
                "$.blueprintHash: stale Blueprint hash",
                validate_render_set_freshness(
                    render_set,
                    blueprint_path=blueprint_path,
                    factory_path=factory_path,
                ),
            )

            metric_report = _valid_metric_report()
            metric_report["renderSetHash"] = artifact_content_hash_value(render_set)
            self.assertEqual(validate_metric_report_freshness(metric_report, render_set=render_set), [])

            changed_render_set = dict(render_set, rendererVersion="changed")
            self.assertEqual(
                validate_metric_report_freshness(metric_report, render_set=changed_render_set),
                ["$.renderSetHash: stale RenderSet hash"],
            )

            review_report = _valid_review_report()
            review_report["renderSetHash"] = artifact_content_hash_value(render_set)
            review_report["metricReportHash"] = artifact_content_hash_value(metric_report)
            self.assertEqual(
                validate_review_report_freshness(
                    review_report,
                    render_set=render_set,
                    metric_report=metric_report,
                ),
                [],
            )

            changed_metric_report = dict(metric_report, metricConfigHash="changed")
            self.assertIn(
                "$.metricReportHash: stale MetricReport hash",
                validate_review_report_freshness(
                    review_report,
                    render_set=render_set,
                    metric_report=changed_metric_report,
                ),
            )


def _valid_render_set() -> dict:
    return {
        "schemaVersion": 1,
        "revisionId": "rev-0001",
        "blueprintHash": "b" * 64,
        "factoryHash": "f" * 64,
        "rendererVersion": "three-0.172.0+harness-1",
        "renderProfileHash": "r" * 64,
        "views": [
            {
                "id": "source-34",
                "cameraProfileHash": "c" * 64,
                "lightProfileHash": "l" * 64,
                "passes": {
                    "beauty": {"path": "renders/source-34-beauty.png", "hash": "1" * 64},
                    "alpha": {"path": "renders/source-34-alpha.png", "hash": "2" * 64},
                    "partId": {"path": "renders/source-34-part-id.png", "hash": "3" * 64},
                },
            }
        ],
    }


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _valid_metric_report() -> dict:
    return {
        "schemaVersion": 1,
        "revisionId": "rev-0001",
        "renderSetHash": "r" * 64,
        "metricConfigHash": "m" * 64,
        "metrics": [
            {
                "id": "silhouette-iou",
                "target": "silhouette",
                "viewId": "source-34",
                "pass": "alpha",
                "value": 0.91,
                "threshold": 0.86,
                "passed": True,
            }
        ],
    }


def _valid_review_report() -> dict:
    return {
        "schemaVersion": 1,
        "revisionId": "rev-0001",
        "renderSetHash": "r" * 64,
        "metricReportHash": "m" * 64,
        "reviewerConfigHash": "v" * 64,
        "recommendation": "replan",
        "issues": [
            {
                "severity": "critical",
                "criterionId": "large-sun-shield",
                "viewId": "source-34",
                "evidence": "shield area is below the reference range",
                "rootCause": "part-scale-and-pose",
                "action": "increase shield width and move forearm pivot forward",
                "confidence": 0.94,
            }
        ],
    }


if __name__ == "__main__":
    unittest.main()
