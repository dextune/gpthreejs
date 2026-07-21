"""Lightweight process/thread helpers."""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import Callable, Iterable, TypeVar

T = TypeVar("T")
R = TypeVar("R")


def default_workers(cap: int = 14) -> int:
    n = os.cpu_count() or 2
    return max(1, min(cap, n - 1 if n > 2 else n))


def map_threads(fn: Callable[[T], R], items: Iterable[T], workers: int | None = None) -> list[R]:
    seq = list(items)
    if not seq:
        return []
    w = workers or default_workers()
    if w == 1 or len(seq) == 1:
        return [fn(x) for x in seq]
    out: list[R | None] = [None] * len(seq)
    with ThreadPoolExecutor(max_workers=w) as ex:
        futs = {ex.submit(fn, item): i for i, item in enumerate(seq)}
        for fut in as_completed(futs):
            out[futs[fut]] = fut.result()
    return [x for x in out if x is not None]  # type: ignore[misc]


def map_processes(fn: Callable[[T], R], items: Iterable[T], workers: int | None = None) -> list[R]:
    seq = list(items)
    if not seq:
        return []
    w = workers or default_workers()
    if w == 1 or len(seq) == 1:
        return [fn(x) for x in seq]
    with ProcessPoolExecutor(max_workers=w) as ex:
        return list(ex.map(fn, seq))
