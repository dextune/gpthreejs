"""ReferenceSet planning and multi-view pipeline CLI commands."""

from __future__ import annotations

import argparse
from pathlib import Path

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

    p = subparsers.add_parser(
        "intake",
        help="Text-only / concept-first intake → RequestSpec + GenerationBrief",
    )
    p.add_argument("subject", help="Subject description (intent text)")
    p.add_argument("--domain", default="character", choices=["object", "character", "hybrid"])
    p.add_argument("--intent", default="game")
    p.add_argument("--quality-mode", default="sharp", dest="quality_mode")
    p.add_argument(
        "--route",
        default="concept-first",
        choices=["photo-lock", "redesign-from-ref", "concept-first", "hybrid-body"],
    )
    p.add_argument("--out", required=True, help="RequestSpec JSON path")
    p.add_argument(
        "--brief-out",
        dest="brief_out",
        help="GenerationBrief JSON path (default: sibling generation-brief.json)",
    )
    bind(p, run_intake)

    p = subparsers.add_parser(
        "reference-prep",
        help="Build GenerationBrief from RequestSpec and/or sufficiency issues",
    )
    p.add_argument("request", nargs="?", help="RequestSpec JSON path")
    p.add_argument("--issues", help="Sufficiency report JSON (issues source)")
    p.add_argument("--seed-image", dest="seed_image", help="Optional identity seed image")
    p.add_argument("--subject", help="Override subject")
    p.add_argument(
        "--route",
        choices=["photo-lock", "redesign-from-ref", "concept-first", "hybrid-body"],
    )
    p.add_argument("--out", required=True, help="GenerationBrief JSON path")
    bind(p, run_reference_prep)

    p = subparsers.add_parser(
        "reference-register",
        help="Register brief + images into ReferenceSet with honest evidenceClass",
    )
    p.add_argument("brief", help="GenerationBrief JSON path")
    p.add_argument(
        "--images",
        nargs="+",
        default=[],
        help="Generated or captured view PNGs",
    )
    p.add_argument("--seed-image", dest="seed_image", help="Optional observed seed image")
    p.add_argument(
        "--evidence-class",
        dest="evidence_class",
        choices=["design-intent", "design-hypothesis"],
        help="Override evidence class for generated views",
    )
    p.add_argument("--out", required=True, help="ReferenceSet JSON path")
    bind(p, run_reference_register)


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


def run_intake(args: argparse.Namespace) -> int:
    from engine.reference.intake import run_intake as _run_intake

    brief_out = args.brief_out
    if not brief_out:
        brief_out = str(Path(args.out).with_name("generation-brief.json"))
    result = _run_intake(
        args.subject,
        domain=args.domain,
        intent=args.intent,
        quality_mode=args.quality_mode,
        route=args.route,
        out=args.out,
        brief_out=brief_out,
    )
    print_json(result)
    return 0


def run_reference_prep(args: argparse.Namespace) -> int:
    from engine.reference.generation_brief import (
        build_generation_brief_from_issues,
        write_generation_brief,
    )
    from engine.reference.request import parse_request_spec
    from engine.shared.jsonutil import load_json

    request = None
    if args.request:
        request = parse_request_spec(args.request)

    issues: list = []
    if args.issues:
        payload = load_json(args.issues)
        if isinstance(payload, dict):
            issues = list(payload.get("issues") or [])
        elif isinstance(payload, list):
            issues = payload

    if not issues and request:
        # Plan missing character views when no issue file provided.
        domain = (
            "character"
            if (request.get("modelingProfile") == "stylized-character"
                or request.get("domain") == "character")
            else "object"
        )
        if domain == "character":
            issues = [
                {
                    "code": "CHAR_NO_SIDE",
                    "severity": "major",
                    "message": "side view required for character prep",
                    "remedy": "generate front+side under GenerationBrief",
                }
            ]

    brief = build_generation_brief_from_issues(
        issues,
        request=request,
        subject=args.subject,
        route=args.route,
        seed_image=args.seed_image,
    )
    write_generation_brief(args.out, brief)
    print_json(brief)
    return 0


def run_reference_register(args: argparse.Namespace) -> int:
    from engine.reference.register import register_from_brief

    result = register_from_brief(
        args.brief,
        list(args.images or []),
        out=args.out,
        evidence_class=args.evidence_class,
        seed_image=args.seed_image,
        origin="generated",
    )
    print_json(result)
    return 0
