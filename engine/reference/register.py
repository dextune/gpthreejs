"""Register GenerationBrief outputs into a ReferenceSet (UX-001 / EV-001)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.reference.capture_defaults import (
    EVIDENCE_CLASS_GENERATED,
    EVIDENCE_CLASS_GENERATED_HYPOTHESIS,
    EVIDENCE_CLASS_SEED,
)
from engine.reference.generation_brief import parse_generation_brief
from engine.reference.reference_set import (
    ReferenceSetError,
    build_reference_entry,
    build_reference_set,
    validate_reference_set,
    write_reference_set,
)

ALLOWED_GENERATED_EVIDENCE = frozenset(
    {EVIDENCE_CLASS_GENERATED, EVIDENCE_CLASS_GENERATED_HYPOTHESIS}
)


def _view_from_path(path: Path, index: int, brief_views: list[dict[str, Any]]) -> str:
    stem = path.stem.lower()
    for view in brief_views:
        vid = str(view.get("id") or "").lower()
        if vid and vid in stem:
            return str(view["id"])
    if index < len(brief_views):
        return str(brief_views[index].get("id") or f"view-{index}")
    return f"view-{index}"


def register_from_brief(
    brief_path: str | Path,
    images: list[str | Path],
    *,
    out: str | Path,
    evidence_class: str | None = None,
    seed_image: str | Path | None = None,
    origin: str = "generated",
) -> dict[str, Any]:
    """Attach generated/captured images to a ReferenceSet with honest evidenceClass."""

    brief = parse_generation_brief(brief_path)
    default_evidence = evidence_class or str(
        brief.get("evidenceClassDefault") or EVIDENCE_CLASS_GENERATED
    )
    route = str(brief.get("route") or "concept-first")

    # Generated assets may never be labeled observed — always coerce on register.
    if origin in ("generated", "edited", "provider") and default_evidence == "observed":
        default_evidence = EVIDENCE_CLASS_GENERATED

    if origin in ("generated", "edited", "provider") and default_evidence not in ALLOWED_GENERATED_EVIDENCE:
        raise ReferenceSetError(
            [
                f"generated images require evidenceClass in "
                f"{sorted(ALLOWED_GENERATED_EVIDENCE)}, got {default_evidence!r}"
            ]
        )

    brief_views = list(brief.get("views") or [])
    refs: list[dict[str, Any]] = []

    if seed_image or brief.get("seedImage"):
        seed = Path(str(seed_image or brief.get("seedImage")))
        if seed.exists():
            refs.append(
                build_reference_entry(
                    ref_id="seed-identity",
                    path=seed,
                    declared_view="source-34",
                    evidence_class=EVIDENCE_CLASS_SEED,
                    origin="user-upload",
                    visible_features=list(brief.get("identityLocks") or []),
                )
            )

    for index, image in enumerate(images):
        path = Path(image)
        view_id = _view_from_path(path, index, brief_views)
        refs.append(
            build_reference_entry(
                ref_id=f"gen-{view_id}-{index}",
                path=path,
                declared_view=view_id,
                evidence_class=default_evidence,
                origin=origin,
                visible_features=list(brief.get("identityLocks") or []),
            )
        )

    if not refs:
        raise ReferenceSetError(["at least one image or seed is required to register"])

    reference_set = build_reference_set(refs)
    # Attach brief provenance on the set (non-schema-breaking extension).
    reference_set["generationBrief"] = {
        "subject": brief.get("subject"),
        "route": route,
        "evidenceClassDefault": default_evidence,
        "redesignPolicy": brief.get("redesignPolicy"),
    }
    errors = validate_reference_set(reference_set)
    if errors:
        raise ReferenceSetError(errors)
    write_reference_set(out, reference_set)
    return reference_set
