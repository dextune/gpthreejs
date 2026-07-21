"""Central compute budget and stage profiling."""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

from engine.shared.artifacts import content_hash


@dataclass
class ComputeBudget:
    max_parallel_stages: int = 2
    max_wall_seconds: float = 600.0
    max_rss_bytes: int | None = None
    active_stages: int = 0
    wall_seconds: float = 0.0

    def acquire(self) -> None:
        if self.active_stages >= self.max_parallel_stages:
            raise RuntimeError("compute budget oversubscribed: stage semaphore exhausted")
        self.active_stages += 1

    def release(self) -> None:
        self.active_stages = max(0, self.active_stages - 1)

    @contextmanager
    def stage(self, name: str) -> Iterator["StageProfile"]:
        self.acquire()
        profile = StageProfile(name=name)
        profile.start()
        try:
            yield profile
        finally:
            profile.stop()
            self.wall_seconds += profile.wall_seconds
            self.release()

    def to_dict(self) -> dict[str, Any]:
        return {
            "maxParallelStages": self.max_parallel_stages,
            "maxWallSeconds": self.max_wall_seconds,
            "activeStages": self.active_stages,
            "wallSeconds": self.wall_seconds,
        }


@dataclass
class StageProfile:
    name: str
    wall_seconds: float = 0.0
    cpu_seconds: float = 0.0
    rss_bytes: int | None = None
    render_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    _t0: float = 0.0
    _cpu0: float = 0.0

    def start(self) -> None:
        self._t0 = time.perf_counter()
        self._cpu0 = time.process_time()

    def stop(self) -> None:
        self.wall_seconds = time.perf_counter() - self._t0
        self.cpu_seconds = time.process_time() - self._cpu0
        try:
            import resource

            self.rss_bytes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        except Exception:
            self.rss_bytes = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "wallSeconds": self.wall_seconds,
            "cpuSeconds": self.cpu_seconds,
            "rssBytes": self.rss_bytes,
            "renderCount": self.render_count,
            "cacheHits": self.cache_hits,
            "cacheMisses": self.cache_misses,
        }


@dataclass
class ProfileReport:
    stages: list[dict[str, Any]] = field(default_factory=list)

    def add(self, profile: StageProfile) -> None:
        self.stages.append(profile.to_dict())

    def to_dict(self) -> dict[str, Any]:
        payload = {"schemaVersion": 1, "stages": self.stages}
        payload["reportHash"] = content_hash(payload, ignored_paths=(("reportHash",),))
        return payload


def promote_coarse_to_fine(
    candidates: list[dict[str, Any]],
    *,
    score_key: str = "score",
    keep: int = 2,
) -> list[dict[str, Any]]:
    ordered = sorted(candidates, key=lambda c: float(c.get(score_key) or 0), reverse=True)
    return ordered[:keep]
