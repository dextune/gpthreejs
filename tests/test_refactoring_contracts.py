"""Regression contracts for refactoring work."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import tracemalloc
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.cli import main as cli_main
from engine.cast.emit_factory import emit_factory
from engine.cast.fit_params import fit_root_mass
from engine.sense.pack import build_sense_pack
from engine.shared.jsonutil import load_json
from engine.shared.pngio import Image, write_png


def _write_blueprint(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "name": "RefactorBox",
                "qualityMode": "sharp",
                "layers": {
                    "mass": {"status": "open"},
                    "skeleton": {"status": "locked"},
                },
                "journal": [{"layer": "mass", "decision": "accept"}],
                "fidelityPact": {"metricFloors": {"vision": 0.7}},
            }
        ),
        encoding="utf-8",
    )


def _run_cli(argv: list[str]) -> int:
    with contextlib.redirect_stdout(io.StringIO()):
        return cli_main(argv)


def _surface_normal_hash(out_dir: Path, hash_seed: str) -> str:
    script = """
from pathlib import Path
import sys
from engine.cast.surface.bake_maps import bake_role
bake_role("metal", Path(sys.argv[1]), size=32, seed=11, maps={"normal": True, "roughness": False, "ao": False})
"""
    env = os.environ.copy()
    env["PYTHONHASHSEED"] = hash_seed
    subprocess.run(
        [sys.executable, "-c", script, str(out_dir)],
        cwd=ROOT,
        env=env,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return hashlib.sha256((out_dir / "metal_normal.png").read_bytes()).hexdigest()


def _write_box_png(path: Path, w: int = 192, h: int = 192) -> None:
    img = Image(w, h, bytearray(w * h * 4))
    for y in range(h):
        for x in range(w):
            if w // 4 <= x < (w * 3) // 4 and h // 4 <= y < (h * 3) // 4:
                img.set_pixel(x, y, (180, 60, 60, 255))
            else:
                img.set_pixel(x, y, (220, 220, 220, 255))
    write_png(path, img)


def _write_fit_fixture(td: Path) -> tuple[Path, Path]:
    td.mkdir(parents=True, exist_ok=True)
    matte = td / "matte.png"
    img = Image(96, 96, bytearray(96 * 96 * 4))
    for y in range(96):
        for x in range(96):
            alpha = 255 if 26 <= x < 70 and 22 <= y < 74 else 0
            img.set_pixel(x, y, (alpha, alpha, alpha, alpha))
    write_png(matte, img)

    sense = td / "sense.json"
    sense.write_text(json.dumps({"maps": {"matte": {"path": str(matte)}}}), encoding="utf-8")

    blueprint = td / "bp.json"
    blueprint.write_text(
        json.dumps(
            {
                "version": 1,
                "name": "FitBox",
                "seed": 99,
                "parts": [
                    {
                        "id": "root_mass",
                        "geometry": {"kind": "box", "size": [1, 1, 1]},
                        "searchSpace": {"size": {"min": [0.4, 0.4, 0.4], "max": [1.7, 1.7, 1.7]}},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return blueprint, sense


class RefactoringContractTests(unittest.TestCase):
    def test_layer_sync_cli_is_dry_run_unless_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bp_path = Path(td) / "bp.json"
            _write_blueprint(bp_path)

            self.assertEqual(_run_cli(["layers", "sync", str(bp_path)]), 0)
            after_dry_run = load_json(bp_path)
            self.assertEqual(after_dry_run["layers"]["mass"]["status"], "open")
            self.assertEqual(after_dry_run["layers"]["skeleton"]["status"], "locked")

            self.assertEqual(_run_cli(["layers", "sync", str(bp_path), "--in-place"]), 0)
            after_in_place = load_json(bp_path)
            self.assertEqual(after_in_place["layers"]["mass"]["status"], "done")
            self.assertEqual(after_in_place["layers"]["skeleton"]["status"], "open")

    def test_journal_cli_is_dry_run_unless_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bp_path = Path(td) / "bp.json"
            _write_blueprint(bp_path)

            argv = [
                "journal",
                str(bp_path),
                "--layer",
                "mass",
                "--fidelity",
                "0.4",
                "--decision",
                "replan",
                "--vision",
                "0.4",
                "--summary",
                "dry run",
            ]
            self.assertEqual(_run_cli(argv), 0)
            self.assertEqual(len(load_json(bp_path)["journal"]), 1)

            self.assertEqual(_run_cli([*argv, "--in-place"]), 0)
            self.assertEqual(len(load_json(bp_path)["journal"]), 2)

    def test_surface_bake_seed_is_stable_across_python_hash_seeds(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            first = _surface_normal_hash(Path(td) / "a", "1")
            second = _surface_normal_hash(Path(td) / "b", "2")
            self.assertEqual(first, second)

    def test_emitted_factory_reuses_materials_and_geometry(self) -> None:
        blueprint = {
            "name": "ReuseBox",
            "materials": [
                {
                    "id": "mat_primary",
                    "baseColor": "#777777",
                    "roughness": 0.5,
                    "metalness": 0.0,
                }
            ],
            "parts": [
                {
                    "id": "a",
                    "materialId": "mat_primary",
                    "geometry": {"kind": "box", "size": [1, 1, 1]},
                },
                {
                    "id": "b",
                    "materialId": "mat_primary",
                    "geometry": {"kind": "box", "size": [1, 1, 1]},
                },
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "createReuseBoxForm.ts"
            emit_factory(blueprint, out)
            text = out.read_text(encoding="utf-8")
            self.assertIn("const geometryRegistry", text)
            self.assertIn("getGeometry(", text)
            self.assertIn("const materialRegistry", text)
            self.assertNotIn(".clone()", text)

    def test_fit_workers_are_real_and_deterministic_for_fixed_trials(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bp1, sense = _write_fit_fixture(Path(td) / "one")
            bp2 = Path(td) / "two" / "bp.json"
            bp2.parent.mkdir(parents=True, exist_ok=True)
            bp2.write_text(bp1.read_text(encoding="utf-8"), encoding="utf-8")

            single = fit_root_mass(
                bp1,
                sense,
                budget_sec=10,
                workers=1,
                in_place=False,
                seed=123,
                max_trials=64,
            )
            multi = fit_root_mass(
                bp2,
                sense,
                budget_sec=10,
                workers=2,
                in_place=False,
                seed=123,
                max_trials=64,
            )

            self.assertEqual(single["trials"], 64)
            self.assertEqual(multi["trials"], 64)
            self.assertEqual(single["size"], multi["size"])
            self.assertEqual(single["bestIoU"], multi["bestIoU"])
            self.assertEqual(single["workersUsed"], 1)
            self.assertEqual(multi["workersUsed"], 2)

    def test_sense_pack_stays_within_small_fixture_budget(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            image = root / "ref.png"
            _write_box_png(image, 192, 192)
            with patch("engine.sense.matte.matte_optional_rembg", return_value=None):
                t0 = time.perf_counter()
                fast_pack = build_sense_pack(image, root / "sense-fast", mode="sharp")
                elapsed = time.perf_counter() - t0

                tracemalloc.start()
                pack = build_sense_pack(image, root / "sense-memory", mode="sharp")
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()

            self.assertIn("maps", fast_pack)
            self.assertIn("maps", pack)
            self.assertLess(elapsed, 0.75)
            self.assertLess(peak, 8 * 1024 * 1024)

    def test_sufficiency_orchestrator_stays_split_from_policy_modules(self) -> None:
        text = (ROOT / "engine/sense/sufficiency.py").read_text(encoding="utf-8")
        self.assertLess(len(text.splitlines()), 180)
        self.assertIn("from engine.sense.sufficiency_checks import", text)
        self.assertIn("from engine.sense.sufficiency_messages import", text)
        self.assertIn("from engine.sense.sufficiency_policy import", text)
        self.assertNotIn("MIN_SHORT_SIDE =", text)
        self.assertNotIn("def user_message(", text)


if __name__ == "__main__":
    unittest.main()
