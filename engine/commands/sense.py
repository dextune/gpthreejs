"""Sense-stage CLI commands."""

from __future__ import annotations

import argparse

from engine.commands._shared import bind, print_json
from engine.contracts.modes import QUALITY_MODES


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("probe", help="Probe image metadata")
    p.add_argument("image")
    bind(p, run_probe)

    p = subparsers.add_parser("caps", help="Probe host capabilities")
    bind(p, run_caps)

    p = subparsers.add_parser("sense", help="Build Sense Pack")
    p.add_argument("image")
    p.add_argument("--out", required=True)
    p.add_argument("--mode", default="sharp", choices=QUALITY_MODES)
    bind(p, run_sense)

    p = subparsers.add_parser(
        "sufficiency",
        help="Report if image/spec info is insufficient (verdict + remedies + agentAction)",
    )
    p.add_argument("image", help="Reference image path")
    p.add_argument("--sense", help="sense_pack.json or directory with sense_pack.json")
    p.add_argument("--brief", help="Intake brief JSON")
    p.add_argument("--ledger", help="Feature ledger JSON")
    p.add_argument("--blueprint", help="Form blueprint JSON")
    p.add_argument("--domain", choices=["object", "character", "hybrid"])
    p.add_argument(
        "--intent",
        default="realtime-prop",
        help="realtime-prop|game|playable|animation|hero|likeness|...",
    )
    p.add_argument("--view-count", type=int, default=1)
    p.add_argument("--has-side", action="store_true")
    p.add_argument("--has-back", action="store_true")
    p.add_argument("--out", help="Write full JSON report")
    p.add_argument(
        "--strict",
        action="store_true",
        help="Exit 2 when not sufficient (for CI / gates)",
    )
    bind(p, run_sufficiency)


def run_probe(args: argparse.Namespace) -> int:
    from engine.sense.probe import probe_image

    print_json(probe_image(args.image))
    return 0


def run_caps(args: argparse.Namespace) -> int:
    from engine.sense.probe import probe_capabilities

    print_json(probe_capabilities())
    return 0


def run_sense(args: argparse.Namespace) -> int:
    from engine.sense.pack import build_sense_pack

    print_json(build_sense_pack(args.image, args.out, mode=args.mode))
    return 0


def run_sufficiency(args: argparse.Namespace) -> int:
    from engine.sense.sufficiency import assess_sufficiency

    report = assess_sufficiency(
        args.image,
        sense_path=args.sense,
        brief_path=args.brief,
        ledger_path=args.ledger,
        blueprint_path=args.blueprint,
        domain=args.domain,
        intent=args.intent,
        view_count=args.view_count,
        has_side=args.has_side,
        has_back=args.has_back,
        out=args.out,
    )
    print_json(report)
    if args.strict and not report.get("sufficient"):
        return 2
    if report.get("verdict") == "reject":
        return 3
    return 0
