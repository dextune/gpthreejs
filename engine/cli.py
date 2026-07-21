"""gpthreejs command entry: python -m engine <cmd> ..."""

from __future__ import annotations

from engine.commands import build_parser, dispatch


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return dispatch(args)


if __name__ == "__main__":
    raise SystemExit(main())
