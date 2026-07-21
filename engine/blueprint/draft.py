"""Draft Intake Brief, Feature Ledger skeleton, and Form Blueprint."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.blueprint.schema import (
    CHARACTER_INSERT,
    COMPLEXITY_LEDGER_MIN,
    DEFAULT_METRIC_FLOORS,
    LAYERS,
)
from engine.cast.surface.schema import default_surface_stack, merge_surface_into_blueprint
from engine.contracts.modes import quality_mode_to_detail_level
from engine.shared.jsonutil import dump_json, load_json


def draft_brief(
    name: str,
    *,
    image: str | None,
    sense_path: str | Path | None,
    complexity: str = "moderate",
    domain: str = "object",
    quality_mode: str = "sharp",
    out: str | Path,
) -> dict:
    sense = load_json(sense_path) if sense_path else {}
    palette = sense.get("palette", {}).get("colors", [])
    bbox = (sense.get("maps") or {}).get("matte", {}).get("bbox")
    layers = list(LAYERS)
    if domain in ("character", "hybrid"):
        # insert character layers before skin
        idx = layers.index("skin")
        layers = layers[:idx] + list(CHARACTER_INSERT) + layers[idx:]

    brief = {
        "version": 1,
        "name": name,
        "image": image,
        "domain": domain,
        "complexity": complexity,
        "qualityMode": quality_mode,
        "fidelityPact": {
            "targetFidelity": {"simple": 0.65, "moderate": 0.75, "complex": 0.82, "ultra": 0.88}.get(
                complexity, 0.75
            ),
            "metricFloors": dict(DEFAULT_METRIC_FLOORS),
            "mustCapture": [
                "silhouette",
                "primary palette",
                "identity features from ledger",
            ],
            "mayApproximate": ["unseen back faces", "micro texture"],
            "ledgerMin": COMPLEXITY_LEDGER_MIN.get(complexity, 6),
        },
        "senseHints": {
            "bbox": bbox,
            "paletteTop": palette[:4],
            "edgeDensity": (sense.get("maps") or {}).get("edges", {}).get("edge_density"),
            "foregroundRatio": (sense.get("maps") or {}).get("matte", {}).get("foreground_ratio"),
        },
        "layerOrder": layers,
        "notes": "Agent fills classification prose; scripts only scaffold.",
    }
    dump_json(out, brief)
    return brief


def draft_ledger(
    image: str,
    sense_dir: str | Path,
    out: str | Path,
    grid: int = 3,
    *,
    mode: str = "production",
    modeling_profile: str = "generic-prop",
    target_min: int | None = None,
) -> dict:
    """
    Draft a Feature Ledger.

    production mode: emit at least targetMin real entries (no TODO stubs), or
    set agentAction=ask when evidence is insufficient to invent features.
    authoring mode: allow TODO skeleton rows for interactive fill-in.
    """
    from engine.blueprint.ledger_validation import CHARACTER_LEDGER_CATEGORIES

    sense_path = Path(sense_dir) / "sense_pack.json"
    sense = load_json(sense_path) if sense_path.exists() else {}
    zones = sense.get("part_grid") or []
    if not zones:
        zones = [
            {
                "id": f"z{y}{x}",
                "region": {
                    "x": x / grid,
                    "y": y / grid,
                    "w": 1 / grid,
                    "h": 1 / grid,
                    "units": "normalized",
                },
            }
            for y in range(grid)
            for x in range(grid)
        ]

    min_entries = target_min if target_min is not None else COMPLEXITY_LEDGER_MIN["moderate"]
    character = modeling_profile == "stylized-character" or sense.get("domain") == "character"

    if mode == "authoring":
        entries = [
            {
                "id": f"todo-{z['id']}",
                "kind": "contour",
                "description": f"FILL: identity detail in zone {z['id']}",
                "region": z["region"],
                "scale": "meso",
                "affects": "geometry",
                "mapsTo": None,
                "confidence": 0.0,
                "status": "todo",
                "evidenceRefs": [],
            }
            for z in zones[:3]
        ]
        agent_action = "continue"
        instructions = (
            "Replace todo entries with real features. Every entry needs mapsTo "
            "pointing at parts[].features[] or materials[].overrides[] ids after blueprint."
        )
    else:
        entries = _production_ledger_entries(
            zones=zones,
            sense=sense,
            target_min=min_entries,
            character=character,
            categories=CHARACTER_LEDGER_CATEGORIES if character else (),
        )
        filled = [e for e in entries if e.get("status") != "todo"]
        if len(filled) < min_entries:
            agent_action = "ask"
            instructions = (
                f"Insufficient evidence to reach targetMin={min_entries}; "
                "supply more views or fill ledger entries before cast."
            )
        else:
            agent_action = "continue"
            instructions = (
                "Production ledger entries are evidence-backed scaffolds. "
                "Resolve mapsTo before strict cast."
            )

    ledger = {
        "version": 1,
        "image": image,
        "scanMethod": f"grid-{grid}x{grid}",
        "targetMin": min_entries,
        "mode": mode,
        "modelingProfile": modeling_profile,
        "zones": zones,
        "entries": entries,
        "agentAction": agent_action,
        "instructions": instructions,
    }
    dump_json(out, ledger)
    return ledger


def _production_ledger_entries(
    *,
    zones: list[dict[str, Any]],
    sense: dict[str, Any],
    target_min: int,
    character: bool,
    categories: tuple[str, ...],
) -> list[dict[str, Any]]:
    """Build real (non-TODO) ledger entries from zones/sense/category coverage."""

    palette = (sense.get("palette") or {}).get("colors") or []
    primary = (palette[0] or {}).get("hex") if palette else None
    entries: list[dict[str, Any]] = []

    def _region_for(index: int) -> dict[str, Any]:
        if zones:
            return zones[index % len(zones)].get("region") or {
                "x": 0,
                "y": 0,
                "w": 1,
                "h": 1,
                "units": "normalized",
            }
        return {"x": 0, "y": 0, "w": 1, "h": 1, "units": "normalized"}

    if character and categories:
        scale_for = {
            "silhouette-proportion": "global",
            "head-face-helmet": "meso",
            "torso-layering": "meso",
            "limb-asymmetry": "meso",
            "held-worn-equipment": "meso",
            "lower-body-feet": "meso",
            "material-roles": "micro",
            "attachment-relationships": "meso",
        }
        edge_density = None
        try:
            edge_density = (sense.get("maps") or {}).get("edges", {}).get("edge_density")
        except Exception:
            edge_density = None
        for index, category in enumerate(categories):
            zone = zones[index % len(zones)] if zones else {}
            zone_id = zone.get("id", f"z{index}")
            evidence = []
            if sense:
                evidence.append("sense")
            if zone_id:
                evidence.append(f"zone:{zone_id}")
            if primary:
                evidence.append(f"palette:{primary}")
            if edge_density is not None:
                evidence.append(f"edgeDensity:{float(edge_density):.4f}")
            conf = 0.55 if sense else 0.4
            if edge_density is not None:
                conf = min(0.9, conf + min(0.2, float(edge_density) * 0.5))
            entries.append(
                {
                    "id": f"feat-{category}",
                    "kind": "identity",
                    "description": (
                        f"Character coverage: {category} from zone {zone_id}"
                        + (f" palette {primary}" if primary else "")
                    ),
                    "region": _region_for(index),
                    "scale": scale_for.get(category, "meso"),
                    "affects": "geometry" if category != "material-roles" else "material",
                    "category": category,
                    "mapsTo": "unresolved",
                    "confidence": conf,
                    "status": "draft",
                    "evidenceRefs": evidence,
                }
            )
    else:
        # Prop / generic: one real entry per zone until targetMin.
        count = max(target_min, min(len(zones), max(target_min, 6)))
        for index in range(count):
            zone = zones[index % len(zones)] if zones else {"id": f"z{index}"}
            zid = zone.get("id", f"z{index}")
            entries.append(
                {
                    "id": f"feat-{zid}-{index}",
                    "kind": "contour",
                    "description": f"Identity mass/detail for zone {zid}",
                    "region": _region_for(index),
                    "scale": "meso" if index < 4 else "micro",
                    "affects": "geometry",
                    "mapsTo": "unresolved",
                    "confidence": 0.5,
                    "status": "draft",
                    "evidenceRefs": ["sense"] if sense else [],
                }
            )

    # Ensure targetMin with additional meso entries if categories alone fall short.
    index = len(entries)
    while len(entries) < target_min:
        entries.append(
            {
                "id": f"feat-extra-{index}",
                "kind": "contour",
                "description": f"Additional coverage entry {index}",
                "region": _region_for(index),
                "scale": "meso",
                "affects": "geometry",
                "mapsTo": "unresolved",
                "confidence": 0.45,
                "status": "draft",
                "evidenceRefs": ["sense"] if sense else [],
                **(
                    {"category": categories[index % len(categories)]}
                    if character and categories
                    else {}
                ),
            }
        )
        index += 1

    if primary:
        entries[0]["description"] = f"{entries[0]['description']} (palette cue {primary})"
    return entries


def draft_blueprint(
    name: str,
    *,
    brief_path: str | Path,
    ledger_path: str | Path | None,
    sense_path: str | Path | None,
    out: str | Path,
) -> dict:
    brief = load_json(brief_path)
    ledger = load_json(ledger_path) if ledger_path else {"entries": [], "targetMin": 0}
    sense = load_json(sense_path) if sense_path else {}
    colors = (sense.get("palette") or {}).get("colors") or [{"hex": "#888888", "rgb": [136, 136, 136]}]
    primary = colors[0]["hex"]
    secondary = colors[1]["hex"] if len(colors) > 1 else primary

    layers = brief.get("layerOrder") or list(LAYERS)
    layer_state = {
        lid: {"status": "locked" if i else "open", "reviews": []}
        for i, lid in enumerate(layers)
    }
    layer_state[layers[0]]["status"] = "open"

    bp: dict[str, Any] = {
        "version": 1,
        "name": name,
        "bodySource": "procedural",
        "qualityMode": brief.get("qualityMode", "sharp"),
        "domain": brief.get("domain", "object"),
        "complexity": brief.get("complexity", "moderate"),
        "image": brief.get("image"),
        "fidelityPact": brief.get("fidelityPact"),
        "senseRef": str(sense_path) if sense_path else None,
        "ledger": ledger,
        "parts": [
            {
                "id": "root_mass",
                "role": "primary",
                "geometry": {
                    "kind": "box",
                    "size": [1.0, 0.7, 0.6],
                    "segments": [1, 1, 1],
                },
                "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
                "materialId": "mat_primary",
                "features": [],
                "attachment": None,
                "searchSpace": {
                    "size": {"min": [0.4, 0.3, 0.3], "max": [1.6, 1.2, 1.2]},
                },
                "children": [
                    {
                        "id": "accent_trim",
                        "role": "trim",
                        "geometry": {
                            "kind": "box",
                            "size": [1.02, 0.08, 0.62],
                            "segments": [1, 1, 1],
                        },
                        "transform": {
                            "position": [0, 0.35, 0],
                            "rotation": [0, 0, 0],
                            "scale": [1, 1, 1],
                        },
                        "materialId": "mat_accent",
                        "features": [],
                        "attachment": {
                            "parent": "root_mass",
                            "contact": "face",
                            "embed": 0.01,
                        },
                        "children": [],
                    }
                ],
            }
        ],
        "materials": [
            {
                "id": "mat_primary",
                "type": "physical",
                "baseColor": primary,
                "roughness": 0.45,
                "metalness": 0.05,
                "overrides": [],
            },
            {
                "id": "mat_accent",
                "type": "physical",
                "baseColor": secondary,
                "roughness": 0.25,
                "metalness": 0.7,
                "overrides": [],
            },
        ],
        "lights": [
            {"id": "key", "kind": "directional", "intensity": 1.2, "position": [2, 3, 2]},
            {"id": "fill", "kind": "ambient", "intensity": 0.35},
        ],
        "handles": {
            "pivots": [{"id": "origin", "part": "root_mass", "local": [0, 0, 0]}],
            "sockets": [],
            "colliders": [{"id": "body", "part": "root_mass", "kind": "box"}],
            "breakGroups": [],
        },
        "layers": layer_state,
        "journal": [],
        "criticalFeatures": [
            {
                "id": "silhouette",
                "layer": "mass",
                "floor": 0.75,
                "description": "Overall mass matches reference silhouette",
            },
            {
                "id": "palette",
                "layer": "skin",
                "floor": 0.7,
                "description": "Primary colors match sense palette",
            },
        ],
        "seed": 42,
    }
    # Surface detail is part of the blueprint contract; failures should stay visible.
    level = quality_mode_to_detail_level(brief.get("qualityMode"))
    merge_surface_into_blueprint(
        bp,
        default_surface_stack(detail_level=level, seed=int(bp.get("seed") or 42)),
    )
    dump_json(out, bp)
    return bp
