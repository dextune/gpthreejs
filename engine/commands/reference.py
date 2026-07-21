"""ReferenceSet planning and multi-view pipeline CLI commands."""

from __future__ import annotations

import argparse

from engine.commands._shared import bind, print_json


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("reference-plan", help="Plan a ReferenceSet from RequestSpec")
    p.add_argument("request", help="RequestSpec JSON path")
    p.add_argument("--image", action="append", dest="images", default=[], help="Reference image (repeatable)")
    p.add_argument("--reference-set", dest="reference_set", help="Existing ReferenceSet JSON")
    p.add_argument("--out", required=True)
    bind(p, run_reference_plan)

    p = subparsers.add_parser("sense-set", help="Sense each image in a ReferenceSet")
    p.add_argument("reference_set", help="ReferenceSet JSON path")
    p.add_argument("--out", required=True)
    p.add_argument("--mode", default="sharp")
    p.add_argument("--no-normalize", action="store_true")
    bind(p, run_sense_set)

    p = subparsers.add_parser(
        "sufficiency-set",
        help="Assess ReferenceSet sufficiency against a RequestSpec",
    )
    p.add_argument("reference_set", help="ReferenceSet JSON path")
    p.add_argument("--request", required=True, help="RequestSpec JSON path")
    p.add_argument("--sense", dest="sense_dir", help="sense-set output directory")
    p.add_argument("--out", help="Write full JSON report")
    p.add_argument("--strict", action="store_true")
    bind(p, run_sufficiency_set)

    p = subparsers.add_parser("ledger-set", help="Draft production ledger from ReferenceSet")
    p.add_argument("reference_set", help="ReferenceSet JSON path")
    p.add_argument("--sense", required=True, dest="sense_dir")
    p.add_argument("--request", help="RequestSpec JSON path")
    p.add_argument("--out", required=True)
    p.add_argument("--mode", default="production", choices=["production", "authoring"])
    bind(p, run_ledger_set)

    p = subparsers.add_parser(
        "wrap-image",
        help="Wrap a single image into a ReferenceSet (compatibility adapter)",
    )
    p.add_argument("image")
    p.add_argument("--view", default="source-34")
    p.add_argument("--out", required=True)
    bind(p, run_wrap_image)


def run_reference_plan(args: argparse.Namespace) -> int:
    from engine.reference.pipeline import plan_reference_set

    print_json(
        plan_reference_set(
            args.request,
            images=args.images or None,
            reference_set_path=args.reference_set,
            out=args.out,
        )
    )
    return 0


def run_sense_set(args: argparse.Namespace) -> int:
    from engine.reference.pipeline import sense_reference_set

    print_json(
        sense_reference_set(
            args.reference_set,
            out_dir=args.out,
            mode=args.mode,
            normalize=not args.no_normalize,
        )
    )
    return 0


def run_sufficiency_set(args: argparse.Namespace) -> int:
    from engine.reference.pipeline import sufficiency_reference_set

    report = sufficiency_reference_set(
        args.reference_set,
        request_path=args.request,
        out=args.out,
        sense_dir=args.sense_dir,
    )
    print_json(report)
    if args.strict and not report.get("sufficient"):
        return 2
    if report.get("verdict") == "reject":
        return 3
    return 0


def run_ledger_set(args: argparse.Namespace) -> int:
    from engine.reference.pipeline import ledger_reference_set

    ledger = ledger_reference_set(
        args.reference_set,
        sense_dir=args.sense_dir,
        out=args.out,
        request_path=args.request,
        mode=args.mode,
    )
    print_json(ledger)
    if ledger.get("gateErrors"):
        return 2
    return 0


def run_wrap_image(args: argparse.Namespace) -> int:
    from engine.reference.adapter import single_image_to_reference_set

    print_json(
        single_image_to_reference_set(
            args.image,
            declared_view=args.view,
            out=args.out,
        )
    )
    return 0
