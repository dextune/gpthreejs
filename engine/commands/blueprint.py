"""Blueprint-stage CLI commands."""

from __future__ import annotations

import argparse
import sys

from engine.commands._shared import bind, print_json
from engine.contracts.modes import QUALITY_MODES


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("brief", help="Draft Intake Brief")
    p.add_argument("name")
    p.add_argument("--image")
    p.add_argument("--sense")
    p.add_argument("--complexity", default="moderate")
    p.add_argument("--domain", default="object", choices=["object", "character", "hybrid"])
    p.add_argument("--mode", dest="quality_mode", default="sharp", choices=QUALITY_MODES)
    p.add_argument("--out", required=True)
    bind(p, run_brief)

    p = subparsers.add_parser("ledger", help="Scaffold Feature Ledger")
    p.add_argument("image")
    p.add_argument("--sense", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--grid", type=int, default=3)
    bind(p, run_ledger)

    p = subparsers.add_parser("blueprint", help="Draft Form Blueprint")
    p.add_argument("name")
    p.add_argument("--brief", required=True)
    p.add_argument("--ledger")
    p.add_argument("--sense")
    p.add_argument("--out", required=True)
    bind(p, run_blueprint)

    p = subparsers.add_parser("validate", help="Validate blueprint")
    p.add_argument("blueprint")
    p.add_argument("--strict", action="store_true")
    bind(p, run_validate)

    p = subparsers.add_parser("layers", help="Layer state")
    p.add_argument("action", choices=["status", "check", "sync"])
    p.add_argument("blueprint")
    p.add_argument("--layer")
    p.add_argument("--in-place", action="store_true")
    bind(p, run_layers)


def run_brief(args: argparse.Namespace) -> int:
    from engine.blueprint.draft import draft_brief

    print_json(
        draft_brief(
            args.name,
            image=args.image,
            sense_path=args.sense,
            complexity=args.complexity,
            domain=args.domain,
            quality_mode=args.quality_mode,
            out=args.out,
        )
    )
    return 0


def run_ledger(args: argparse.Namespace) -> int:
    from engine.blueprint.draft import draft_ledger

    print_json(draft_ledger(args.image, args.sense, args.out, grid=args.grid))
    return 0


def run_blueprint(args: argparse.Namespace) -> int:
    from engine.blueprint.draft import draft_blueprint

    print_json(
        draft_blueprint(
            args.name,
            brief_path=args.brief,
            ledger_path=args.ledger,
            sense_path=args.sense,
            out=args.out,
        )
    )
    return 0


def run_validate(args: argparse.Namespace) -> int:
    from engine.blueprint.validate import validate_blueprint

    result = validate_blueprint(args.blueprint, strict=args.strict)
    print_json(result.to_dict())
    return 0 if result.ok else 2


def run_layers(args: argparse.Namespace) -> int:
    from engine.cast import layers as layer_state

    if args.action == "status":
        print_json(layer_state.status(args.blueprint))
    elif args.action == "check":
        if not args.layer:
            print("--layer required", file=sys.stderr)
            return 2
        print_json(layer_state.check(args.blueprint, args.layer))
    else:
        print_json(layer_state.sync(args.blueprint, in_place=args.in_place))
    return 0
