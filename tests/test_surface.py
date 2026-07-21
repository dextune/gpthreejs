"""Tests for generic surface stack."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.cast.surface.bake_maps import SURFACE_PRESETS, bake_surface_stack
from engine.cast.surface.schema import default_surface_stack, merge_surface_into_blueprint
from engine.shared.pngio import read_png


class SurfaceStackTests(unittest.TestCase):
    def test_presets_cover_roles(self) -> None:
        for role in ("metal", "cloth", "leather", "brass", "default"):
            self.assertIn(role, SURFACE_PRESETS)

    def test_default_stack_levels(self) -> None:
        low = default_surface_stack(detail_level="low")
        high = default_surface_stack(detail_level="high")
        self.assertFalse(low["bands"]["micro"])
        self.assertTrue(high["bands"]["micro"])
        self.assertGreaterEqual(high["resolution"], low["resolution"])

    def test_merge_assigns_roles(self) -> None:
        bp = {
            "seed": 1,
            "qualityMode": "sharp",
            "materials": [
                {"id": "mat_steel", "baseColor": "#888", "metalness": 0.9, "roughness": 0.3},
                {"id": "mat_cloth", "baseColor": "#a00", "metalness": 0.0, "roughness": 0.8},
            ],
        }
        merge_surface_into_blueprint(bp)
        self.assertIn("surfaceStack", bp)
        roles = {m["id"]: m["surfaceRole"] for m in bp["materials"]}
        self.assertEqual(roles["mat_steel"], "metal")
        self.assertEqual(roles["mat_cloth"], "cloth")

    def test_bake_writes_pngs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            man = bake_surface_stack(td, roles=["metal", "cloth"], detail_level="medium", resolution=64, seed=7)
            self.assertIn("baked", man)
            metal_n = Path(man["baked"]["metal"]["paths"]["normal"])
            self.assertTrue(metal_n.exists())
            im = read_png(metal_n)
            self.assertEqual(im.width, 64)
            # normal map should not be flat gray only — variance check
            vals = [im.rgba[i] for i in range(0, min(4000, len(im.rgba)), 4)]
            self.assertGreater(max(vals) - min(vals), 5)


if __name__ == "__main__":
    unittest.main()
