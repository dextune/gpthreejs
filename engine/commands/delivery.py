"""Delivery export CLI."""

from __future__ import annotations

import argparse

from engine.commands._shared import bind, print_json


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "delivery-export",
        help="Run hard delivery gates and package a portable delivery bundle",
    )
    p.add_argument("project", help="Project JSON path")
    p.add_argument("--out", required=True, help="Output directory for delivery package")
    p.add_argument("--max-iterations", type=int, default=0)
    p.add_argument(
        "--skip-run",
        action="store_true",
        help="Reuse existing run artifacts under --run-out or <out>/_run",
    )
    p.add_argument("--run-out", help="Directory of prior run artifacts")
    bind(p, run_delivery_export)


def run_delivery_export(args: argparse.Namespace) -> int:
    from engine.delivery.export import delivery_export

    result = delivery_export(
        args.project,
        out_dir=args.out,
        max_iterations=args.max_iterations,
        skip_run=args.skip_run,
        run_out=args.run_out,
    )
    print_json(result)
    return 0 if result.get("ok") else 2
