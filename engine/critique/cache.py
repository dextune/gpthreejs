"""Render cache keyed by revision / profile / pass."""

from __future__ import annotations

from typing import Any

from engine.shared.artifacts import content_hash


class RenderCache:
    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self.hits = 0
        self.misses = 0

    def cache_key(self, *, revision_id: str, profile_id: str, pass_name: str, fingerprint: str) -> str:
        return content_hash(
            {
                "revisionId": revision_id,
                "profileId": profile_id,
                "pass": pass_name,
                "fingerprint": fingerprint,
            }
        )

    def get(self, key: str) -> dict[str, Any] | None:
        value = self._store.get(key)
        if value is None:
            self.misses += 1
            return None
        self.hits += 1
        return value

    def put(self, key: str, artifact: dict[str, Any]) -> None:
        self._store[key] = artifact

    def get_or_render(
        self,
        *,
        revision_id: str,
        profile_id: str,
        pass_name: str,
        fingerprint: str,
        render_fn,
    ) -> dict[str, Any]:
        key = self.cache_key(
            revision_id=revision_id,
            profile_id=profile_id,
            pass_name=pass_name,
            fingerprint=fingerprint,
        )
        cached = self.get(key)
        if cached is not None:
            return {**cached, "cache": "hit"}
        artifact = render_fn()
        payload = {**artifact, "cacheKey": key}
        self.put(key, payload)
        return {**payload, "cache": "miss"}

    def stats(self) -> dict[str, int]:
        return {"hits": self.hits, "misses": self.misses, "size": len(self._store)}
