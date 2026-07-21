"""Capture repeated Sense small-fixture performance metadata as JSON."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import statistics
import sys
import tempfile
import time
import tracemalloc
from datetime import date
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.sense.pack import build_sense_pack
from engine.shared.pngio import Image, write_png

SOURCE_STATE_FILES = [
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


def write_box_png(path: Path, width: int = 192, height: int = 192) -> None:
    img = Image(width, height, bytearray(width * height * 4))
    for y in range(height):
        for x in range(width):
            if width // 4 <= x < (width * 3) // 4 and height // 4 <= y < (height * 3) // 4:
                img.set_pixel(x, y, (180, 60, 60, 255))
            else:
                img.set_pixel(x, y, (220, 220, 220, 255))
    write_png(path, img)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_state_fingerprint(paths: list[str]) -> dict:
    lines = []
    for rel_path in sorted(paths):
        lines.append(f"{rel_path}  {sha256_file(ROOT / rel_path)}")
    return {
        "algorithm": "sha256(sorted '<relative-path>  <file-sha256>' lines joined with '\\n' and one terminal '\\n')",
        "value": hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest(),
        "files": paths,
    }


def dependency_versions() -> dict:
    versions = {}
    for package in ("pillow", "rembg", "numpy"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not-installed"
    return versions


def _build_sense_pack_in_subprocess(image: Path, output: Path, traced: bool) -> dict:
    script = """
import json
import sys
import time
import tracemalloc
from pathlib import Path
from unittest.mock import patch
from engine.sense.pack import build_sense_pack

if tracemalloc.is_tracing():
    tracemalloc.stop()
if bool(int(sys.argv[3])):
    tracemalloc.start()
started = time.perf_counter()
with patch("engine.sense.matte.matte_optional_rembg", return_value=None):
    pack = build_sense_pack(Path(sys.argv[1]), Path(sys.argv[2]), mode="sharp")
elapsed = time.perf_counter() - started
peak = 0
if tracemalloc.is_tracing():
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
print(json.dumps({"pack": pack, "elapsed": round(elapsed, 6), "peak": peak}))
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(image), str(output), "1" if traced else "0"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return json.loads(result.stdout)


def build_sense_pack_wall_run(image: Path, output: Path) -> tuple[dict, float]:
    if tracemalloc.is_tracing():
        measured = _build_sense_pack_in_subprocess(image, output, traced=False)
        return measured["pack"], measured["elapsed"]

    started = time.perf_counter()
    with patch("engine.sense.matte.matte_optional_rembg", return_value=None):
        pack = build_sense_pack(image, output, mode="sharp")
    return pack, round(time.perf_counter() - started, 6)


def build_sense_pack_with_traced_peak(image: Path, output: Path) -> tuple[dict, int]:
    if tracemalloc.is_tracing():
        measured = _build_sense_pack_in_subprocess(image, output, traced=True)
        return measured["pack"], measured["peak"]

    tracemalloc.start()
    try:
        with patch("engine.sense.matte.matte_optional_rembg", return_value=None):
            pack = build_sense_pack(image, output, mode="sharp")
        _, peak = tracemalloc.get_traced_memory()
        return pack, peak
    finally:
        tracemalloc.stop()


def repository_state() -> dict:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    ).stdout.strip()
    return {
        "commit": commit,
        "shortCommit": commit[:7],
        "worktreeState": "dirty" if dirty else "clean",
    }


def positive_int(raw: str) -> int:
    value = int(raw)
    if value <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return value


def capture(wall_runs: int, traced_runs: int) -> dict:
    wall = []
    traced = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        image = root / "ref.png"
        write_box_png(image)
        fixture_sha256 = sha256_file(image)
        with patch("engine.sense.matte.matte_optional_rembg", return_value=None):
            maps = []
            matte_method = None
            for index in range(wall_runs):
                pack, elapsed = build_sense_pack_wall_run(image, root / f"wall-{index}")
                wall.append(elapsed)
                maps = sorted((pack.get("maps") or {}).keys())
                matte_method = (pack.get("maps") or {}).get("matte", {}).get("method")
            for index in range(traced_runs):
                pack, peak = build_sense_pack_with_traced_peak(image, root / f"traced-{index}")
                traced.append(peak)
                maps = sorted((pack.get("maps") or {}).keys())
                matte_method = (pack.get("maps") or {}).get("matte", {}).get("method")

    return {
        "schemaVersion": 1,
        "reportId": "m0-sense-small-fixture-performance-baseline",
        "status": "baseline-captured",
        "created": date.today().isoformat(),
        "purpose": "Replace the single 0.75 second Sense smoke datapoint with repeated wall-clock, traced Python allocation, machine, and backend metadata for regression decisions.",
        "repository": repository_state(),
        "benchmarkCommand": {
            "summary": "Generate the fixture with tests/benchmark_sense_performance.py, patch engine.sense.matte.matte_optional_rembg to return None, run build_sense_pack(..., mode='sharp') repeatedly, measure wall runs without tracemalloc, then measure traced allocation runs separately.",
            "reproduce": f"python3 tests/benchmark_sense_performance.py --wall-runs {wall_runs} --traced-runs {traced_runs}",
            "warmupRuns": 0,
            "wallRunCount": wall_runs,
            "tracedAllocationRunCount": traced_runs,
            "runOrder": "all wall-clock runs first, then traced allocation runs",
        },
        "sourceStateFingerprint": source_state_fingerprint(SOURCE_STATE_FILES),
        "fixture": {
            "kind": "generated-box-png",
            "width": 192,
            "height": 192,
            "sha256": fixture_sha256,
            "foreground": "center rectangle from one quarter to three quarters of width and height",
            "mode": "sharp",
        },
        "machine": {
            "platform": platform.platform(),
            "pythonVersion": sys.version.split()[0],
            "implementation": platform.python_implementation(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpuCount": os.cpu_count(),
        },
        "dependencies": dependency_versions(),
        "backend": {
            "matteOptionalRembg": "patched-return-none",
            "matteMethod": matte_method,
            "maps": maps,
            "notes": "Wall-clock runs are measured without tracemalloc; traced allocation runs are measured separately because tracemalloc materially changes wall-clock timing.",
        },
        "wallClock": {
            "unit": "seconds",
            "runCount": wall_runs,
            "runs": wall,
            "min": min(wall),
            "median": statistics.median(wall),
            "max": max(wall),
        },
        "tracedPythonAllocations": {
            "unit": "bytes",
            "runCount": traced_runs,
            "peakBytes": traced,
            "min": min(traced),
            "median": int(statistics.median(traced)),
            "max": max(traced),
        },
        "policy": {
            "historicalSingleRunBudgetSeconds": 0.75,
            "developerSmokeWallRunCount": 3,
            "developerSmokeMedianMultiplier": 4.0,
            "developerSmokeMaxMultiplier": 6.0,
            "developerSmokeMedianCeilingSeconds": round(statistics.median(wall) * 4.0, 6),
            "developerSmokeMaxCeilingSeconds": round(max(wall) * 6.0, 6),
            "developerSmokeTracedAllocationCeilingBytes": 8388608,
            "releaseGate": "deferred-to-PERF-110-after-representative-fixtures",
            "rssGate": "deferred-to-PERF-110",
            "regressionBasis": "Compare median and max repeated wall-clock only on matching benchmark metadata before changing release budgets.",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wall-runs", type=positive_int, default=7)
    parser.add_argument("--traced-runs", type=positive_int, default=3)
    args = parser.parse_args(argv)
    print(json.dumps(capture(args.wall_runs, args.traced_runs), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
