"""Geometry schema contract tests."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.blueprint.validate import validate_blueprint  # noqa: E402
from engine.cast.emit_factory import emit_factory  # noqa: E402
from engine.geometry.schema import (  # noqa: E402
    GEOMETRY_SPECS,
    SUPPORTED_GEOMETRY_KINDS,
    UnsupportedGeometryError,
    geometry_required_fields,
    geometry_schema,
    validate_geometry_required_fields,
)
from engine.shared.jsonutil import load_json  # noqa: E402

V2_FIXTURE = ROOT / "tests/golden/knight/blueprints/v2-minimal-character.json"


class GeometryContractTests(unittest.TestCase):
    def test_supported_geometry_kinds_have_required_fields(self) -> None:
        expected = (
            "box",
            "sphere",
            "ellipsoid",
            "capsule",
            "cylinder",
            "cone",
            "torus",
            "rounded-box",
            "shape-extrude",
            "lathe",
            "tube",
            "beveled-plate",
            "curve-blade",
            "feather",
            "cloth-patch",
            "instance-set",
        )

        self.assertEqual(SUPPORTED_GEOMETRY_KINDS, expected)
        for kind in SUPPORTED_GEOMETRY_KINDS:
            self.assertIn(kind, GEOMETRY_SPECS)
            self.assertTrue(geometry_required_fields(kind), kind)

    def test_geometry_schema_is_discriminated_by_kind(self) -> None:
        schema = geometry_schema()
        variants = {variant["properties"]["kind"]["const"]: variant for variant in schema["oneOf"]}

        self.assertEqual(tuple(variants), SUPPORTED_GEOMETRY_KINDS)
        for kind, variant in variants.items():
            self.assertEqual(variant["required"][0], "kind")
            self.assertEqual(tuple(variant["required"][1:]), geometry_required_fields(kind))

    def test_known_geometry_missing_required_field_reports_path(self) -> None:
        errors = validate_geometry_required_fields({"kind": "rounded-box", "size": [1, 1, 1]}, path="$.parts[0].geometry")

        self.assertEqual(
            errors,
            ["$.parts[0].geometry.radius: missing required field for geometry kind 'rounded-box'"],
        )

    def test_blueprint_v2_validator_uses_geometry_required_fields(self) -> None:
        blueprint = load_json(V2_FIXTURE)
        blueprint["parts"][0]["geometry"].pop("radius")

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "missing-radius.json"
            path.write_text(json.dumps(blueprint), encoding="utf-8")

            result = validate_blueprint(path, strict=True)

        self.assertFalse(result.ok)
        self.assertTrue(any("$.parts[0].geometry.radius" in error for error in result.errors), result.errors)

    def test_unknown_geometry_kind_fails_validation_with_path(self) -> None:
        blueprint = load_json(V2_FIXTURE)
        blueprint["parts"][0]["geometry"] = {"kind": "mystery-shape", "size": [1, 1, 1]}

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "unknown-kind.json"
            path.write_text(json.dumps(blueprint), encoding="utf-8")
            result = validate_blueprint(path, strict=True)

        self.assertFalse(result.ok)
        self.assertTrue(any("$.parts[0].geometry.kind" in error for error in result.errors), result.errors)

    def test_emitter_rejects_unknown_geometry_instead_of_falling_back_to_box(self) -> None:
        blueprint = {
            "version": 1,
            "name": "UnknownGeometry",
            "materials": [{"id": "mat_primary", "baseColor": "#ffffff"}],
            "parts": [
                {
                    "id": "unknown",
                    "geometry": {"kind": "mystery-shape", "size": [9, 9, 9]},
                    "materialId": "mat_primary",
                    "children": [],
                }
            ],
        }

        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(UnsupportedGeometryError, "mystery-shape"):
                emit_factory(blueprint, Path(td) / "factory.ts")


if __name__ == "__main__":
    unittest.main()
