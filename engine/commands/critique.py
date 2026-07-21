"""Critique-stage CLI commands."""

from __future__ import annotations

import argparse

from engine.commands._shared import bind, print_json


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("sheet", help="Side-by-side comparison sheet")
    p.add_argument("--reference", required=True)
    p.add_argument("--render", required=True)
    p.add_argument("--out", required=True)
    bind(p, run_sheet)

    p = subparsers.add_parser("grid", help="Multi-view grid")
    p.add_argument("--reference", required=True)
    p.add_argument("--renders", required=True)
    p.add_argument("--out", required=True)
    bind(p, run_grid)

    p = subparsers.add_parser("metrics", help="Compute metrics")
    p.add_argument("--reference", required=True)
    p.add_argument("--render", required=True)
    p.add_argument("--matte")
    p.add_argument("--edges")
    p.add_argument("--out")
    bind(p, run_metrics)

    p = subparsers.add_parser("journal", help="Append critique journal entry")
    p.add_argument("blueprint")
    p.add_argument("--layer", required=True)
    p.add_argument("--fidelity", type=float, required=True)
    p.add_argument("--decision", required=True)
    p.add_argument("--vision", type=float, required=True)
    p.add_argument("--summary", required=True)
    p.add_argument("--metrics")
    p.add_argument("--render")
    p.add_argument("--sheet")
    p.add_argument("--policy-trace")
    p.add_argument("--in-place", action="store_true")
    bind(p, run_journal)


def run_sheet(args: argparse.Namespace) -> int:
    from engine.critique.sheet import make_sheet

    print_json({"out": make_sheet(args.reference, args.render, args.out)})
    return 0


def run_grid(args: argparse.Namespace) -> int:
    from engine.critique.sheet import make_grid

    print_json({"out": make_grid(args.reference, args.renders, args.out)})
    return 0


def run_metrics(args: argparse.Namespace) -> int:
    from engine.critique.metrics import compute_metrics

    print_json(
        compute_metrics(
            args.reference,
            args.render,
            matte=args.matte,
            edges=args.edges,
            out=args.out,
        )
    )
    return 0


def run_journal(args: argparse.Namespace) -> int:
    from engine.critique.journal import append_journal
    from engine.shared.jsonutil import load_json

    print_json(
        append_journal(
            args.blueprint,
            layer=args.layer,
            fidelity=args.fidelity,
            decision=args.decision,
            vision=args.vision,
            summary=args.summary,
            metrics_path=args.metrics,
            render=args.render,
            sheet=args.sheet,
            policy_trace=load_json(args.policy_trace) if args.policy_trace else None,
            in_place=args.in_place,
        )
    )
    return 0
