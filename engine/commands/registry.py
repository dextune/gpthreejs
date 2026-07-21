"""CLI parser and dispatcher registry."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gpthreejs", description="gpthreejs pipeline CLI")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    from engine.commands import blueprint, cast, critique, delivery, reference, run, sense

    for register in (
        sense.register,
        blueprint.register,
        cast.register,
        critique.register,
        reference.register,
        run.register,
        delivery.register,
    ):
        register(subparsers)

    return parser


def dispatch(args: argparse.Namespace) -> int:
    handler = getattr(args, "handler", None)
    if handler is None:
        return 1
    return handler(args)
