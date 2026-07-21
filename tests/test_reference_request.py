"""RequestSpec contract tests."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.reference.request import (  # noqa: E402
    FEATURE_REQUIREMENT_REQUIRED_FIELDS,
    REQUEST_SPEC_REQUIRED_FIELDS,
    RequestSpecError,
    parse_request_spec,
    request_spec_schema,
    validate_request_spec,
)


class RequestSpecTests(unittest.TestCase):
    def test_request_spec_schema_exposes_required_fields(self) -> None:
        schema = request_spec_schema()

        self.assertEqual(tuple(schema["required"]), REQUEST_SPEC_REQUIRED_FIELDS)
        self.assertEqual(
            tuple(schema["$defs"]["featureRequirement"]["required"]),
            FEATURE_REQUIREMENT_REQUIRED_FIELDS,
        )

    def test_valid_request_spec_parses(self) -> None:
        spec = _valid_request_spec()

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "request-spec.json"
            path.write_text(json.dumps(spec), encoding="utf-8")

            parsed = parse_request_spec(path)

        self.assertEqual(parsed["subject"], "stylized blue-plume knight")
        self.assertEqual(validate_request_spec(parsed), [])

    def test_invalid_intent_profile_and_feature_weight_report_paths(self) -> None:
        spec = _valid_request_spec()
        spec["intent"] = "marketing"
        spec["modelingProfile"] = "photoreal-person"
        spec["mustHave"][0]["weight"] = 1.5

        errors = validate_request_spec(spec)

        self.assertIn("$.intent: unsupported intent 'marketing'", errors)
        self.assertIn("$.modelingProfile: unsupported profile 'photoreal-person'", errors)
        self.assertIn("$.mustHave[0].weight: expected number in range 0..1", errors)

    def test_parse_request_spec_raises_structured_errors(self) -> None:
        spec = _valid_request_spec()
        spec["mustNotHave"] = [{"id": "photo_background", "weight": -0.1}]

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad-request-spec.json"
            path.write_text(json.dumps(spec), encoding="utf-8")

            with self.assertRaises(RequestSpecError) as cm:
                parse_request_spec(path)

        self.assertEqual(
            cm.exception.errors,
            ["$.mustNotHave[0].weight: expected number in range 0..1"],
        )


def _valid_request_spec() -> dict:
    return {
        "schemaVersion": 1,
        "subject": "stylized blue-plume knight",
        "intent": "game",
        "modelingProfile": "stylized-character",
        "qualityMode": "sharp",
        "mustHave": [
            {"id": "blue_feather_plume", "weight": 1.0},
            {"id": "large_sun_shield", "weight": 1.0},
            {"id": "broad_fantasy_sword", "weight": 1.0},
        ],
        "mustNotHave": [],
        "targetViews": ["source-34", "front", "left", "right", "back"],
    }


if __name__ == "__main__":
    unittest.main()
