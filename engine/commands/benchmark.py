"""Benchmark CLI command."""

from __future__ import annotations

import argparse

from engine.commands._shared import bind, print_json


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "benchmark",
        help="Run benchmark fixtures and produce a quality report",
    )
    p.add_argument(
        "--manifest",
        required=True,
        help="Path to the benchmark manifest JSON",
    )
    p.add_argument(
        "--out",
        required=True,
        help="Output directory for benchmark report and artifacts",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Per-fixture timeout in seconds (default: 120)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate manifest and show plan without executing fixtures",
    )
    bind(p, run_benchmark_cmd)


def run_benchmark_cmd(args: argparse.Namespace) -> int:
    from engine.benchmark.runner import run_benchmark

    report = run_benchmark(
        args.manifest,
        out_dir=args.out,
        timeout_seconds=args.timeout,
        dry_run=args.dry_run,
    )
    print_json(report)
    if not report.get("ok"):
        return 1
    return 0
