"""Shared command helpers."""

from __future__ import annotations

import argparse
import json
from typing import Callable

CommandHandler = Callable[[argparse.Namespace], int]


def print_json(data) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def bind(parser: argparse.ArgumentParser, handler: CommandHandler) -> None:
    parser.set_defaults(handler=handler)
