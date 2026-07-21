"""Cast-stage CLI commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from engine.commands._shared import bind, print_json
from engine.contracts.modes import DETAIL_LEVELS


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("cast", help="Emit TypeScript factory")
    p.add_argument("blueprint")
    p.add_argument("--out", required=True)
    p.add_argument(
        "--out-dir",
        dest="out_dir",
        help="Also emit a portable bundle directory (factory + surface presets + manifest)",
    )
    bind(p, run_cast)

    p = subparsers.add_parser("fit", help="CPU parameter fit vs matte")
    p.add_argument("blueprint")
    p.add_argument("--sense", required=True)
    p.add_argument("--budget-sec", type=float, default=60)
    p.add_argument("--workers", type=int, default=0)
    p.add_argument("--in-place", action="store_true")
    bind(p, run_fit)

    p = subparsers.add_parser(
        "surface-bake",
        help="Bake generic procedural PBR maps (normal/roughness/ao) for surface roles",
    )
    p.add_argument("--out", required=True, help="Output directory for maps + manifest")
    p.add_argument(
        "--level",
        default="high",
        choices=DETAIL_LEVELS,
        help="Detail level (map res + which maps)",
    )
    p.add_argument("--resolution", type=int, default=0, help="Override map resolution")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--roles",
        default="metal,brass,cloth,leather,plastic,default",
        help="Comma-separated surface roles to bake",
    )
    bind(p, run_surface_bake)

    p = subparsers.add_parser(
        "surface-annotate",
        help="Attach surfaceStack + surfaceRole to a Form Blueprint (in-place optional)",
    )
    p.add_argument("blueprint")
    p.add_argument("--level", default="high", choices=DETAIL_LEVELS)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--in-place", action="store_true")
    p.add_argument("--out", help="Write annotated blueprint here (if not --in-place)")
    bind(p, run_surface_annotate)


def run_cast(args: argparse.Namespace) -> int:
    from engine.cast.emit_factory import emit_factory
    from engine.runtime.portable import emit_portable_bundle
    from engine.shared.jsonutil import load_json

    path = emit_factory(load_json(args.blueprint), args.out)
    result: dict = {"out": path}
    if args.out_dir:
        factory_source = Path(path).read_text(encoding="utf-8")
        preset_path = Path(__file__).resolve().parents[2] / "demo" / "src" / "detail" / "surfacePresets.ts"
        surface_module = preset_path.read_text(encoding="utf-8") if preset_path.exists() else None
        manifest = emit_portable_bundle(
            factory_source=factory_source,
            out_dir=args.out_dir,
            surface_preset_module=surface_module,
        )
        result["bundle"] = {"outDir": args.out_dir, "manifest": manifest}
        if manifest.get("externalPathLeaks"):
            print_json(result)
            return 2
    print_json(result)
    return 0


def run_fit(args: argparse.Namespace) -> int:
    from engine.cast.fit_params import fit_root_mass

    print_json(
        fit_root_mass(
            args.blueprint,
            args.sense,
            budget_sec=args.budget_sec,
            workers=args.workers or None,
            in_place=args.in_place,
        )
    )
    return 0


def run_surface_bake(args: argparse.Namespace) -> int:
    from engine.cast.surface.bake_maps import bake_surface_stack

    roles = [role.strip() for role in args.roles.split(",") if role.strip()]
    print_json(
        bake_surface_stack(
            args.out,
            roles=roles,
            detail_level=args.level,
            resolution=args.resolution or None,
            seed=args.seed,
        )
    )
    return 0


def run_surface_annotate(args: argparse.Namespace) -> int:
    from engine.cast.surface.schema import default_surface_stack, merge_surface_into_blueprint
    from engine.shared.jsonutil import dump_json, load_json

    blueprint = load_json(args.blueprint)
    seed = args.seed or int(blueprint.get("seed") or 42)
    stack = default_surface_stack(detail_level=args.level, seed=seed)
    merge_surface_into_blueprint(blueprint, stack)

    out = args.blueprint if args.in_place else args.out
    if out:
        dump_json(out, blueprint)

    print_json(
        {
            "out": out,
            "surfaceStack": blueprint.get("surfaceStack"),
            "materials": [
                {"id": material.get("id"), "surfaceRole": material.get("surfaceRole")}
                for material in (blueprint.get("materials") or [])
            ],
        }
    )
    return 0
