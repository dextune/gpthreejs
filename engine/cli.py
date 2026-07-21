"""gpthreejs command entry: python -m engine <cmd> ..."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _print(data) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gpthreejs", description="gpthreejs pipeline CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("probe", help="Probe image metadata")
    p.add_argument("image")

    p = sub.add_parser("caps", help="Probe host capabilities")

    p = sub.add_parser("sense", help="Build Sense Pack")
    p.add_argument("image")
    p.add_argument("--out", required=True)
    p.add_argument("--mode", default="sharp", choices=["draft", "solid", "sharp", "razor", "hybrid"])

    p = sub.add_parser("brief", help="Draft Intake Brief")
    p.add_argument("name")
    p.add_argument("--image")
    p.add_argument("--sense")
    p.add_argument("--complexity", default="moderate")
    p.add_argument("--domain", default="object", choices=["object", "character", "hybrid"])
    p.add_argument("--mode", dest="quality_mode", default="sharp")
    p.add_argument("--out", required=True)

    p = sub.add_parser("ledger", help="Scaffold Feature Ledger")
    p.add_argument("image")
    p.add_argument("--sense", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--grid", type=int, default=3)

    p = sub.add_parser("blueprint", help="Draft Form Blueprint")
    p.add_argument("name")
    p.add_argument("--brief", required=True)
    p.add_argument("--ledger")
    p.add_argument("--sense")
    p.add_argument("--out", required=True)

    p = sub.add_parser("validate", help="Validate blueprint")
    p.add_argument("blueprint")
    p.add_argument("--strict", action="store_true")

    p = sub.add_parser("layers", help="Layer state")
    p.add_argument("action", choices=["status", "check", "sync"])
    p.add_argument("blueprint")
    p.add_argument("--layer")
    p.add_argument("--in-place", action="store_true")

    p = sub.add_parser("cast", help="Emit TypeScript factory")
    p.add_argument("blueprint")
    p.add_argument("--out", required=True)

    p = sub.add_parser("fit", help="CPU parameter fit vs matte")
    p.add_argument("blueprint")
    p.add_argument("--sense", required=True)
    p.add_argument("--budget-sec", type=float, default=60)
    p.add_argument("--workers", type=int, default=0)
    p.add_argument("--in-place", action="store_true")

    p = sub.add_parser("sheet", help="Side-by-side comparison sheet")
    p.add_argument("--reference", required=True)
    p.add_argument("--render", required=True)
    p.add_argument("--out", required=True)

    p = sub.add_parser("grid", help="Multi-view grid")
    p.add_argument("--reference", required=True)
    p.add_argument("--renders", required=True)
    p.add_argument("--out", required=True)

    p = sub.add_parser("metrics", help="Compute metrics")
    p.add_argument("--reference", required=True)
    p.add_argument("--render", required=True)
    p.add_argument("--matte")
    p.add_argument("--edges")
    p.add_argument("--out")

    p = sub.add_parser("journal", help="Append critique journal entry")
    p.add_argument("blueprint")
    p.add_argument("--layer", required=True)
    p.add_argument("--fidelity", type=float, required=True)
    p.add_argument("--decision", required=True)
    p.add_argument("--vision", type=float, required=True)
    p.add_argument("--summary", required=True)
    p.add_argument("--metrics")
    p.add_argument("--render")
    p.add_argument("--sheet")
    p.add_argument("--in-place", action="store_true")

    p = sub.add_parser(
        "surface-bake",
        help="Bake generic procedural PBR maps (normal/roughness/ao) for surface roles",
    )
    p.add_argument("--out", required=True, help="Output directory for maps + manifest")
    p.add_argument(
        "--level",
        default="high",
        choices=["low", "medium", "high", "ultra"],
        help="Detail level (map res + which maps)",
    )
    p.add_argument("--resolution", type=int, default=0, help="Override map resolution")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--roles",
        default="metal,brass,cloth,leather,plastic,default",
        help="Comma-separated surface roles to bake",
    )

    p = sub.add_parser(
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

    p = sub.add_parser(
        "surface-annotate",
        help="Attach surfaceStack + surfaceRole to a Form Blueprint (in-place optional)",
    )
    p.add_argument("blueprint")
    p.add_argument("--level", default="high", choices=["low", "medium", "high", "ultra"])
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--in-place", action="store_true")
    p.add_argument("--out", help="Write annotated blueprint here (if not --in-place)")

    args = parser.parse_args(argv)

    if args.cmd == "probe":
        from engine.sense.probe import probe_image

        _print(probe_image(args.image))
        return 0

    if args.cmd == "caps":
        from engine.sense.probe import probe_capabilities

        _print(probe_capabilities())
        return 0

    if args.cmd == "sense":
        from engine.sense.pack import build_sense_pack

        _print(build_sense_pack(args.image, args.out, mode=args.mode))
        return 0

    if args.cmd == "brief":
        from engine.blueprint.draft import draft_brief

        _print(
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

    if args.cmd == "ledger":
        from engine.blueprint.draft import draft_ledger

        _print(draft_ledger(args.image, args.sense, args.out, grid=args.grid))
        return 0

    if args.cmd == "blueprint":
        from engine.blueprint.draft import draft_blueprint

        _print(
            draft_blueprint(
                args.name,
                brief_path=args.brief,
                ledger_path=args.ledger,
                sense_path=args.sense,
                out=args.out,
            )
        )
        return 0

    if args.cmd == "validate":
        from engine.blueprint.validate import validate_blueprint

        res = validate_blueprint(args.blueprint, strict=args.strict)
        _print(res.to_dict())
        return 0 if res.ok else 2

    if args.cmd == "layers":
        from engine.cast import layers as L

        if args.action == "status":
            _print(L.status(args.blueprint))
        elif args.action == "check":
            if not args.layer:
                print("--layer required", file=sys.stderr)
                return 2
            _print(L.check(args.blueprint, args.layer))
        else:
            _print(L.sync(args.blueprint, in_place=args.in_place or True))
        return 0

    if args.cmd == "cast":
        from engine.cast.emit_factory import emit_factory
        from engine.shared.jsonutil import load_json

        path = emit_factory(load_json(args.blueprint), args.out)
        _print({"out": path})
        return 0

    if args.cmd == "fit":
        from engine.cast.fit_params import fit_root_mass

        _print(
            fit_root_mass(
                args.blueprint,
                args.sense,
                budget_sec=args.budget_sec,
                workers=args.workers or None,
                in_place=args.in_place or True,
            )
        )
        return 0

    if args.cmd == "sheet":
        from engine.critique.sheet import make_sheet

        _print({"out": make_sheet(args.reference, args.render, args.out)})
        return 0

    if args.cmd == "grid":
        from engine.critique.sheet import make_grid

        _print({"out": make_grid(args.reference, args.renders, args.out)})
        return 0

    if args.cmd == "metrics":
        from engine.critique.metrics import compute_metrics

        _print(
            compute_metrics(
                args.reference,
                args.render,
                matte=args.matte,
                edges=args.edges,
                out=args.out,
            )
        )
        return 0

    if args.cmd == "journal":
        from engine.critique.journal import append_journal

        _print(
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
                in_place=args.in_place or True,
            )
        )
        return 0

    if args.cmd == "surface-bake":
        from engine.cast.surface.bake_maps import bake_surface_stack

        roles = [r.strip() for r in args.roles.split(",") if r.strip()]
        _print(
            bake_surface_stack(
                args.out,
                roles=roles,
                detail_level=args.level,
                resolution=args.resolution or None,
                seed=args.seed,
            )
        )
        return 0

    if args.cmd == "sufficiency":
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
        _print(report)
        if args.strict and not report.get("sufficient"):
            return 2
        if report.get("verdict") == "reject":
            return 3
        return 0

    if args.cmd == "surface-annotate":
        from engine.cast.surface.schema import default_surface_stack, merge_surface_into_blueprint
        from engine.shared.jsonutil import dump_json, load_json

        bp = load_json(args.blueprint)
        seed = args.seed or int(bp.get("seed") or 42)
        stack = default_surface_stack(detail_level=args.level, seed=seed)
        merge_surface_into_blueprint(bp, stack)
        out = args.blueprint if args.in_place or not args.out else args.out
        if not args.in_place and not args.out:
            out = args.blueprint
            args.in_place = True
        dump_json(out, bp)
        _print({"out": out, "surfaceStack": bp.get("surfaceStack"), "materials": [
            {"id": m.get("id"), "surfaceRole": m.get("surfaceRole")}
            for m in (bp.get("materials") or [])
        ]})
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
