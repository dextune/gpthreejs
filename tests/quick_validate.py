#!/usr/bin/env python3
"""DX-410: validate a skill folder (default: repo SKILL.md directory)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.runtime.skill_validate import quick_validate, validate_skill_folder


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate gpthreejs skill folder")
    parser.add_argument(
        "skill_dir",
        nargs="?",
        default=str(ROOT),
        help="Directory containing SKILL.md",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.json:
        import json

        print(json.dumps(validate_skill_folder(args.skill_dir), indent=2))
        report = validate_skill_folder(args.skill_dir)
        return 0 if report["ok"] else 2
    return quick_validate(args.skill_dir)


if __name__ == "__main__":
    raise SystemExit(main())
