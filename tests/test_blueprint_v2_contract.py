"""Blueprint v2 contract regression tests."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.contracts.blueprint_v2 import (  # noqa: E402
    BLUEPRINT_V2_SCHEMA_VERSION,
    MODELING_PROFILES,
    TOP_LEVEL_REQUIRED_FIELDS,
    blueprint_v2_required_fields,
    blueprint_v2_schema,
)
from engine.blueprint.migrate import blueprint_for_v1_cast, migrate_v1_to_v2  # noqa: E402
from engine.blueprint.validate import validate_blueprint  # noqa: E402
from engine.cast.emit_factory import emit_factory  # noqa: E402
from engine.cli import main as cli_main  # noqa: E402
from engine.shared.artifacts import (  # noqa: E402
    CANONICAL_JSON_ALGORITHM,
    artifact_content_hash,
    blueprint_revision_content_hash,
    canonical_json_text,
    content_hash,
)
from engine.shared.jsonutil import load_json  # noqa: E402

FIXTURE = ROOT / "tests/golden/knight/blueprints/v2-minimal-character.json"
V1_SHALLOW = ROOT / "tests/golden/knight/blueprints/v0-shallow.json"
DOC = ROOT / "docs/planning/quality-upgrade-execution/blueprint-v2-schema.md"


class BlueprintV2ContractTests(unittest.TestCase):
    def test_schema_exposes_v2_profile_contract(self) -> None:
        schema = blueprint_v2_schema()

        self.assertEqual(schema["properties"]["schemaVersion"]["const"], BLUEPRINT_V2_SCHEMA_VERSION)
        self.assertEqual(tuple(schema["required"]), TOP_LEVEL_REQUIRED_FIELDS)
        self.assertEqual(
            tuple(schema["properties"]["modelingProfile"]["enum"]),
            MODELING_PROFILES,
        )
        self.assertIn("part", schema["$defs"])
        self.assertEqual(
            tuple(schema["$defs"]["part"]["required"]),
            blueprint_v2_required_fields()["part"],
        )

    def test_fixture_contains_every_required_contract_field(self) -> None:
        blueprint = load_json(FIXTURE)
        required = blueprint_v2_required_fields()

        self.assertEqual(blueprint["schemaVersion"], BLUEPRINT_V2_SCHEMA_VERSION)
        for field in required["topLevel"]:
            self.assertIn(field, blueprint)
        for field in required["revision"]:
            self.assertIn(field, blueprint["revision"])
        for field in required["proportionProfile"]:
            self.assertIn(field, blueprint["proportionProfile"])
        for field in required["poseProfile"]:
            self.assertIn(field, blueprint["poseProfile"])
        for field in required["landmark"]:
            self.assertIn(field, blueprint["landmarks"][0])
        for field in required["part"]:
            self.assertIn(field, blueprint["parts"][0])
        for field in required["material"]:
            self.assertIn(field, blueprint["materials"][0])
        for field in required["handle"]:
            self.assertIn(field, blueprint["handles"]["hand-l-grip"])
        for field in required["attachment"]:
            self.assertIn(field, blueprint["parts"][0]["children"][1]["attachment"])
        for field in required["renderProfile"]:
            self.assertIn(field, blueprint["renderProfiles"][0])
        for field in required["criticalFeature"]:
            self.assertIn(field, blueprint["criticalFeatures"][0])

    def test_field_documentation_tracks_required_contract_fields(self) -> None:
        text = DOC.read_text(encoding="utf-8")

        for fields in blueprint_v2_required_fields().values():
            for field in fields:
                self.assertIn(f"`{field}`", text)
        self.assertIn(str(FIXTURE.relative_to(ROOT)), text)

    def test_blueprint_v2_schema_is_a_copy(self) -> None:
        schema = blueprint_v2_schema()
        schema["required"].append("mutated")

        self.assertNotIn("mutated", blueprint_v2_schema()["required"])

    def test_artifact_hash_is_stable_across_key_order_and_json_whitespace(self) -> None:
        first = {"b": [2, {"d": "x"}], "a": {"c": True}}
        second = {"a": {"c": True}, "b": [2, {"d": "x"}]}

        self.assertEqual(CANONICAL_JSON_ALGORITHM, "json-v1:sort-keys,separators,no-nan,utf8,newline")
        self.assertEqual(canonical_json_text(first), canonical_json_text(second))
        self.assertEqual(content_hash(first), content_hash(second))

        with tempfile.TemporaryDirectory() as td:
            first_path = Path(td) / "first.json"
            second_path = Path(td) / "second.json"
            first_path.write_text('{\r\n  "b": [2, {"d": "x"}],\r\n  "a": {"c": true}\r\n}\r\n', encoding="utf-8")
            second_path.write_text('{"a":{"c":true},"b":[2,{"d":"x"}]}\n', encoding="utf-8")

            self.assertEqual(artifact_content_hash(first_path), artifact_content_hash(second_path))

    def test_blueprint_revision_hash_ignores_self_referential_hash_field(self) -> None:
        blueprint = load_json(FIXTURE)
        expected = blueprint["revision"]["contentHash"]

        self.assertEqual(blueprint_revision_content_hash(blueprint), expected)
        mutated = dict(blueprint)
        mutated["revision"] = dict(blueprint["revision"], contentHash="f" * 64)

        self.assertEqual(blueprint_revision_content_hash(mutated), expected)

    def test_v1_to_v2_migration_sets_contract_and_stable_revision_hash(self) -> None:
        migrated = migrate_v1_to_v2(load_json(V1_SHALLOW))

        self.assertEqual(migrated["schemaVersion"], BLUEPRINT_V2_SCHEMA_VERSION)
        self.assertEqual(migrated["modelingProfile"], "stylized-character")
        self.assertEqual(migrated["revision"]["contentHash"], blueprint_revision_content_hash(migrated))
        for field in blueprint_v2_required_fields()["topLevel"]:
            self.assertIn(field, migrated)
        for part in migrated["parts"]:
            self.assertIn("translation", part["transform"])
            self.assertIn("position", part["transform"])
        for material in migrated["materials"]:
            self.assertIn("channels", material)
            self.assertIn("baseColor", material["channels"])

    def test_migration_cli_output_casts_through_compatibility_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "migrated.json"
            factory = Path(td) / "createBluePlumeKnightForm.ts"

            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli_main(["migrate-v1-to-v2", str(V1_SHALLOW), "--out", str(out)]), 0)
            migrated = load_json(out)
            emit_factory(migrated, factory)

            cast_view = blueprint_for_v1_cast(migrated)
            self.assertTrue(factory.exists())
            self.assertEqual(cast_view["materials"][0]["baseColor"], migrated["materials"][0]["channels"]["baseColor"])
            self.assertIn("createKnightV0ShallowForm", factory.read_text(encoding="utf-8"))

    def test_blueprint_v2_valid_fixture_passes_structural_validation(self) -> None:
        result = validate_blueprint(FIXTURE, strict=True)

        self.assertTrue(result.ok, result.errors)

    def test_blueprint_v2_invalid_fixtures_fail_with_json_paths(self) -> None:
        base = load_json(FIXTURE)
        cases = []

        duplicate_part = json.loads(json.dumps(base))
        duplicate_part["parts"][0]["children"][0]["id"] = duplicate_part["parts"][0]["id"]
        cases.append(("duplicate-part-id", duplicate_part, "$.parts[0].children[0].id"))

        parent_cycle = json.loads(json.dumps(base))
        parent_cycle["parts"][0]["parentId"] = "shield"
        parent_cycle["parts"][0]["children"][1]["parentId"] = "torso"
        cases.append(("parent-cycle", parent_cycle, "$.parts[0].parentId"))

        dangling_material = json.loads(json.dumps(base))
        dangling_material["parts"][0]["materialId"] = "missing-material"
        cases.append(("dangling-material", dangling_material, "$.parts[0].materialId"))

        non_finite = json.loads(json.dumps(base))
        non_finite["materials"][0]["channels"]["roughness"] = float("nan")
        cases.append(("non-finite-number", non_finite, "$.materials[0].channels.roughness"))

        bad_vector = json.loads(json.dumps(base))
        bad_vector["parts"][0]["transform"]["translation"] = [0, 0]
        cases.append(("bad-vector-length", bad_vector, "$.parts[0].transform.translation"))

        with tempfile.TemporaryDirectory() as td:
            for name, blueprint, path_fragment in cases:
                fixture = Path(td) / f"{name}.json"
                fixture.write_text(json.dumps(blueprint), encoding="utf-8")

                result = validate_blueprint(fixture, strict=True)

                self.assertFalse(result.ok, name)
                self.assertTrue(
                    any(path_fragment in error for error in result.errors),
                    f"{name}: {result.errors}",
                )

    def test_ledger_maps_to_and_character_category_coverage_are_strict(self) -> None:
        base = load_json(FIXTURE)

        def add_ledger(blueprint: dict, categories: list[str]) -> dict:
            blueprint = json.loads(json.dumps(blueprint))
            blueprint["ledger"] = {
                "targetMin": len(categories),
                "entries": [
                    {
                        "id": f"entry-{index}",
                        "kind": "contour",
                        "description": category,
                        "region": {"units": "normalized", "x": 0, "y": 0, "w": 1, "h": 1},
                        "scale": "global" if index == 0 else "meso",
                        "affects": "geometry",
                        "confidence": 0.9,
                        "evidenceRefs": ["fixture:v2-minimal-character"],
                        "status": "filled",
                        "category": category,
                        "mapsTo": {"type": "part", "ref": "torso"},
                    }
                    for index, category in enumerate(
                        [
                            "silhouette-proportion",
                            "head-face-helmet",
                            "torso-layering",
                            "limb-asymmetry",
                            "held-worn-equipment",
                            "lower-body-feet",
                            "material-roles",
                            "attachment-relationships",
                        ][: len(categories)]
                    )
                ],
            }
            return blueprint

        valid = add_ledger(base, ["unused"] * 8)
        unresolved = add_ledger(base, ["unused"] * 8)
        unresolved["ledger"]["entries"][0]["mapsTo"] = "unresolved"
        invalid_ref = add_ledger(base, ["unused"] * 8)
        invalid_ref["ledger"]["entries"][1]["mapsTo"] = {"type": "part", "ref": "missing-part"}
        missing_coverage = add_ledger(base, ["unused"] * 7)

        with tempfile.TemporaryDirectory() as td:
            valid_path = Path(td) / "valid.json"
            valid_path.write_text(json.dumps(valid), encoding="utf-8")
            self.assertTrue(validate_blueprint(valid_path, strict=True).ok)

            cases = [
                ("unresolved.json", unresolved, "$.ledger.entries[0].mapsTo"),
                ("invalid-ref.json", invalid_ref, "$.ledger.entries[1].mapsTo.ref"),
                ("missing-coverage.json", missing_coverage, "$.ledger.entries[].category"),
            ]
            for name, blueprint, path_fragment in cases:
                path = Path(td) / name
                path.write_text(json.dumps(blueprint), encoding="utf-8")
                result = validate_blueprint(path, strict=True)
                self.assertFalse(result.ok, name)
                self.assertTrue(
                    any(path_fragment in error for error in result.errors),
                    f"{name}: {result.errors}",
                )


if __name__ == "__main__":
    unittest.main()
