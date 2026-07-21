"""Production run CLI."""

from __future__ import annotations

import argparse

from engine.commands._shared import bind, print_json


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "run",
        help="Production path: reference→validate→cast→render→metrics→review",
    )
    p.add_argument("project", help="Project JSON path")
    p.add_argument("--max-iterations", type=int, default=0)
    p.add_argument("--out", dest="out_dir")
    bind(p, run_run)


def run_run(args: argparse.Namespace) -> int:
    from engine.orchestration.run import run_production

    result = run_production(
        args.project,
        max_iterations=args.max_iterations,
        out_dir=args.out_dir,
    )
    print_json(result)
    return 0 if result.get("ok") else 2
