"""Regression contracts for refactoring work."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import statistics
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
from engine.cast.layers import sync as sync_layers
from engine.critique.journal import append_journal
from engine.sense.pack import build_sense_pack
from engine.shared.jsonutil import load_json
from engine.shared.pngio import Image, write_png
from tests.benchmark_sense_performance import (
    SOURCE_STATE_FILES,
    build_sense_pack_wall_run,
    build_sense_pack_with_traced_peak,
    capture as capture_sense_performance,
    dependency_versions,
    main as benchmark_sense_main,
    source_state_fingerprint,
    write_box_png as write_sense_benchmark_png,
)

SENSE_PERFORMANCE_BASELINE = ROOT / "tests/golden/knight/baselines/sense-performance-baseline.json"
EXPECTED_SENSE_SOURCE_FILES = [
    "engine/__init__.py",
    "engine/contracts/__init__.py",
    "engine/contracts/modes.py",
    "engine/sense/__init__.py",
    "engine/sense/depth_proxy.py",
    "engine/sense/edges.py",
    "engine/sense/matte.py",
    "engine/sense/pack.py",
    "engine/sense/palette.py",
    "engine/sense/probe.py",
    "engine/shared/__init__.py",
    "engine/shared/jsonutil.py",
    "engine/shared/pngio.py",
    "tests/benchmark_sense_performance.py",
]


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
                "journal": [
                    {
                        "layer": "mass",
                        "decision": "accept",
                        "policyTrace": {
                            "policyIssued": True,
                            "issuer": "review-policy",
                            "decision": "accept",
                        },
                    }
                ],
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


def _source_state_fingerprint(paths: list[str]) -> str:
    lines = []
    for rel_path in sorted(paths):
        lines.append(f"{rel_path}  {hashlib.sha256((ROOT / rel_path).read_bytes()).hexdigest()}")
    return hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()


def _matching_sense_benchmark_environment(baseline: dict) -> bool:
    import platform

    if tracemalloc.is_tracing():
        return False
    machine = baseline["machine"]
    dependencies = baseline["dependencies"]
    if machine["platform"] != platform.platform():
        return False
    if machine["pythonVersion"] != sys.version.split()[0]:
        return False
    if machine["implementation"] != platform.python_implementation():
        return False
    if machine["machine"] != platform.machine():
        return False
    if machine["processor"] != platform.processor():
        return False
    if machine["cpuCount"] != os.cpu_count():
        return False
    return dependencies == dependency_versions()


def _schema_shape(value):
    if isinstance(value, dict):
        return {key: _schema_shape(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        if not value:
            return []
        return [_schema_shape(value[0])]
    return type(value).__name__


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

    def test_accept_journal_requires_render_metrics_and_feature_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bp_path = root / "bp.json"
            render_path = root / "render.png"
            metrics_path = root / "metrics.json"
            _write_blueprint(bp_path)
            blueprint = load_json(bp_path)
            blueprint["criticalFeatures"] = [
                {"id": "silhouette", "layer": "mass", "floor": 0.7}
            ]
            bp_path.write_text(json.dumps(blueprint), encoding="utf-8")
            render_path.write_text("render placeholder", encoding="utf-8")
            metrics_path.write_text(json.dumps({"ssim": 0.9, "maskIoU": 0.9, "edgeF1": 0.9}), encoding="utf-8")

            common = {
                "layer": "mass",
                "fidelity": 0.9,
                "decision": "accept",
                "vision": 0.9,
                "summary": "accept",
            }
            policy_trace = {"policyIssued": True, "issuer": "review-policy", "decision": "accept"}
            with self.assertRaisesRegex(SystemExit, "decision was not issued by review-policy"):
                append_journal(
                    bp_path,
                    **common,
                    render=str(render_path),
                    metrics_path=metrics_path,
                    feature_scores={"silhouette": 0.9},
                    in_place=False,
                )
            with self.assertRaisesRegex(SystemExit, "missing render evidence"):
                append_journal(
                    bp_path,
                    **common,
                    metrics_path=metrics_path,
                    feature_scores={"silhouette": 0.9},
                    policy_trace=policy_trace,
                    in_place=False,
                )
            with self.assertRaisesRegex(SystemExit, "missing metrics evidence"):
                append_journal(
                    bp_path,
                    **common,
                    render=str(render_path),
                    feature_scores={"silhouette": 0.9},
                    policy_trace=policy_trace,
                    in_place=False,
                )
            with self.assertRaisesRegex(SystemExit, "feature silhouette missing render evidence"):
                append_journal(
                    bp_path,
                    **common,
                    render=str(render_path),
                    metrics_path=metrics_path,
                    policy_trace=policy_trace,
                    in_place=False,
                )

            entry = append_journal(
                bp_path,
                **common,
                render=str(render_path),
                metrics_path=metrics_path,
                feature_scores={"silhouette": 0.9},
                policy_trace=policy_trace,
                in_place=False,
            )
            self.assertEqual(entry["decision"], "accept")
            self.assertEqual(entry["policyTrace"], policy_trace)

    def test_layer_sync_ignores_arbitrary_accept_without_policy_trace(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bp_path = Path(td) / "bp.json"
            _write_blueprint(bp_path)
            blueprint = load_json(bp_path)
            blueprint["journal"] = [{"layer": "mass", "decision": "accept"}]
            bp_path.write_text(json.dumps(blueprint), encoding="utf-8")

            state = sync_layers(bp_path, in_place=False)

            self.assertIn("mass", state["open"])
            self.assertNotIn("mass", state["done"])

            blueprint["journal"] = [
                {
                    "layer": "mass",
                    "decision": "accept",
                    "policyTrace": {
                        "policyIssued": True,
                        "issuer": "review-policy",
                        "decision": "accept",
                    },
                }
            ]
            bp_path.write_text(json.dumps(blueprint), encoding="utf-8")

            state = sync_layers(bp_path, in_place=False)

            self.assertIn("mass", state["done"])

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
        baseline = load_json(SENSE_PERFORMANCE_BASELINE)
        policy = baseline["policy"]
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            image = root / "ref.png"
            write_sense_benchmark_png(image, 192, 192)
            with patch("engine.sense.matte.matte_optional_rembg", return_value=None):
                wall_runs = []
                fast_pack = None
                for index in range(policy["developerSmokeWallRunCount"]):
                    fast_pack, elapsed = build_sense_pack_wall_run(image, root / f"sense-fast-{index}")
                    wall_runs.append(elapsed)

                pack, traced_peak = build_sense_pack_with_traced_peak(image, root / "sense-memory")

            self.assertIn("maps", fast_pack)
            self.assertIn("maps", pack)
            expected_maps = baseline["backend"]["maps"]
            self.assertEqual(sorted((fast_pack.get("maps") or {}).keys()), expected_maps)
            self.assertEqual(sorted((pack.get("maps") or {}).keys()), expected_maps)
            self.assertEqual(
                fast_pack["maps"]["matte"]["method"],
                baseline["backend"]["matteMethod"],
            )
            self.assertEqual(
                pack["maps"]["matte"]["method"],
                baseline["backend"]["matteMethod"],
            )
            if _matching_sense_benchmark_environment(baseline):
                self.assertLessEqual(
                    statistics.median(wall_runs),
                    policy["developerSmokeMedianCeilingSeconds"],
                )
                self.assertLessEqual(max(wall_runs), policy["developerSmokeMaxCeilingSeconds"])
            self.assertLess(traced_peak, policy["developerSmokeTracedAllocationCeilingBytes"])

    def test_sense_performance_baseline_records_repeated_metadata(self) -> None:
        baseline = load_json(SENSE_PERFORMANCE_BASELINE)
        self.assertEqual(baseline["status"], "baseline-captured")
        self.assertEqual(baseline["fixture"]["kind"], "generated-box-png")
        self.assertEqual(baseline["fixture"]["width"], 192)
        self.assertEqual(baseline["fixture"]["height"], 192)
        self.assertEqual(baseline["fixture"]["mode"], "sharp")
        fingerprint = baseline["sourceStateFingerprint"]
        self.assertEqual(SOURCE_STATE_FILES, EXPECTED_SENSE_SOURCE_FILES)
        self.assertEqual(fingerprint["files"], SOURCE_STATE_FILES)
        self.assertEqual(_source_state_fingerprint(fingerprint["files"]), fingerprint["value"])
        self.assertEqual(source_state_fingerprint(SOURCE_STATE_FILES), fingerprint)
        with tempfile.TemporaryDirectory() as td:
            fixture = Path(td) / "ref.png"
            write_sense_benchmark_png(fixture, 192, 192)
            self.assertEqual(
                hashlib.sha256(fixture.read_bytes()).hexdigest(),
                baseline["fixture"]["sha256"],
            )

        command = baseline["benchmarkCommand"]
        self.assertEqual(
            command["reproduce"],
            "python3 tests/benchmark_sense_performance.py --wall-runs 7 --traced-runs 3",
        )
        self.assertEqual(command["warmupRuns"], 0)
        self.assertEqual(command["wallRunCount"], baseline["wallClock"]["runCount"])
        self.assertEqual(
            command["tracedAllocationRunCount"],
            baseline["tracedPythonAllocations"]["runCount"],
        )
        self.assertIn("traced allocation", command["runOrder"])

        machine = baseline["machine"]
        for key in ("platform", "pythonVersion", "implementation", "machine", "processor"):
            self.assertTrue(machine[key], key)
        self.assertGreaterEqual(machine["cpuCount"], 1)

        dependencies = baseline["dependencies"]
        for key in ("pillow", "rembg", "numpy"):
            self.assertTrue(dependencies[key], key)

        backend = baseline["backend"]
        self.assertEqual(backend["matteOptionalRembg"], "patched-return-none")
        self.assertEqual(backend["matteMethod"], "corner-distance")
        self.assertEqual(backend["maps"], ["depth_proxy", "edges", "matte"])

        wall = baseline["wallClock"]
        self.assertEqual(wall["unit"], "seconds")
        self.assertEqual(wall["runCount"], 7)
        self.assertEqual(len(wall["runs"]), wall["runCount"])
        self.assertEqual(wall["min"], min(wall["runs"]))
        self.assertEqual(wall["max"], max(wall["runs"]))
        self.assertEqual(wall["median"], sorted(wall["runs"])[len(wall["runs"]) // 2])

        traced = baseline["tracedPythonAllocations"]
        self.assertEqual(traced["unit"], "bytes")
        self.assertEqual(traced["runCount"], 3)
        self.assertEqual(len(traced["peakBytes"]), traced["runCount"])
        self.assertEqual(traced["min"], min(traced["peakBytes"]))
        self.assertEqual(traced["max"], max(traced["peakBytes"]))
        self.assertEqual(traced["median"], sorted(traced["peakBytes"])[len(traced["peakBytes"]) // 2])
        self.assertLess(traced["max"], baseline["policy"]["developerSmokeTracedAllocationCeilingBytes"])

        policy = baseline["policy"]
        self.assertEqual(policy["historicalSingleRunBudgetSeconds"], 0.75)
        self.assertEqual(policy["developerSmokeWallRunCount"], 3)
        self.assertEqual(policy["developerSmokeMedianMultiplier"], 4.0)
        self.assertEqual(policy["developerSmokeMaxMultiplier"], 6.0)
        self.assertEqual(
            policy["developerSmokeMedianCeilingSeconds"],
            round(wall["median"] * policy["developerSmokeMedianMultiplier"], 6),
        )
        self.assertEqual(
            policy["developerSmokeMaxCeilingSeconds"],
            round(wall["max"] * policy["developerSmokeMaxMultiplier"], 6),
        )
        self.assertEqual(policy["rssGate"], "deferred-to-PERF-110")
        self.assertEqual(policy["releaseGate"], "deferred-to-PERF-110-after-representative-fixtures")

    def test_sense_performance_benchmark_command_schema_and_argparse(self) -> None:
        generated = capture_sense_performance(wall_runs=1, traced_runs=1)
        baseline = load_json(SENSE_PERFORMANCE_BASELINE)
        self.assertEqual(_schema_shape(generated), _schema_shape(baseline))
        self.assertEqual(generated["schemaVersion"], 1)
        self.assertEqual(generated["reportId"], "m0-sense-small-fixture-performance-baseline")
        self.assertEqual(generated["status"], "baseline-captured")
        self.assertRegex(generated["created"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertIn("single 0.75 second Sense smoke datapoint", generated["purpose"])
        self.assertEqual(generated["benchmarkCommand"]["wallRunCount"], 1)
        self.assertEqual(generated["benchmarkCommand"]["tracedAllocationRunCount"], 1)
        self.assertEqual(generated["wallClock"]["runCount"], 1)
        self.assertEqual(generated["tracedPythonAllocations"]["runCount"], 1)
        self.assertEqual(generated["sourceStateFingerprint"], source_state_fingerprint(SOURCE_STATE_FILES))
        self.assertEqual(generated["fixture"]["sha256"], baseline["fixture"]["sha256"])
        self.assertEqual(generated["backend"]["maps"], ["depth_proxy", "edges", "matte"])
        self.assertEqual(generated["backend"]["matteMethod"], "corner-distance")
        self.assertEqual(generated["dependencies"], dependency_versions())

        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as wall_run_error:
            benchmark_sense_main(["--wall-runs", "0", "--traced-runs", "1"])
        self.assertEqual(wall_run_error.exception.code, 2)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as traced_run_error:
            benchmark_sense_main(["--wall-runs", "1", "--traced-runs", "0"])
        self.assertEqual(traced_run_error.exception.code, 2)

    def test_sense_traced_peak_is_isolated_from_external_tracing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "ref.png"
            write_sense_benchmark_png(image, 192, 192)

            script = f"""
from pathlib import Path
from unittest.mock import patch
from tests.benchmark_sense_performance import build_sense_pack_with_traced_peak
import tracemalloc

with patch("tests.benchmark_sense_performance.build_sense_pack", side_effect=RuntimeError("boom")):
    try:
        build_sense_pack_with_traced_peak(Path({str(image)!r}), Path({str(Path(td) / "owned")!r}))
    except RuntimeError:
        pass
    else:
        raise SystemExit("expected RuntimeError")
if tracemalloc.is_tracing():
    raise SystemExit("owned tracing was not restored")
"""
            untraced_env = os.environ.copy()
            untraced_env.pop("PYTHONTRACEMALLOC", None)
            subprocess.run(
                [sys.executable, "-c", script],
                cwd=ROOT,
                env=untraced_env,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            started_tracing = not tracemalloc.is_tracing()
            if started_tracing:
                tracemalloc.start()
            try:
                _external_allocation = bytearray(10 * 1024 * 1024)
                pack, traced_peak = build_sense_pack_with_traced_peak(image, Path(td) / "borrowed")
                self.assertTrue(tracemalloc.is_tracing())
                self.assertIn("maps", pack)
                self.assertLess(traced_peak, load_json(SENSE_PERFORMANCE_BASELINE)["policy"]["developerSmokeTracedAllocationCeilingBytes"])
            finally:
                if started_tracing:
                    tracemalloc.stop()

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
