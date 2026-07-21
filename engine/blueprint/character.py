"""Stylized character vertical slice: knight proportions, identity parts, polish order."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from engine.blueprint.attachments import assess_attachment_contacts, validate_attachment_schema
from engine.blueprint.materials_profile import apply_role_to_material, assess_material_readability
from engine.blueprint.profiles import (
    apply_pose_to_parts,
    build_pose_profile,
    default_character_landmarks,
    default_proportion_profile,
    modeling_profile_rules,
    validate_landmarks,
    validate_proportion_profile,
)
from engine.shared.artifacts import blueprint_revision_content_hash, content_hash


def build_stylized_character_blueprint(
    name: str = "BluePlumeKnight",
    *,
    pose_id: str = "source-34",
    include_polish: bool = False,
    handedness: str = "right",
) -> dict[str, Any]:
    """
    Build a character-depth Blueprint v2 vertical slice without micro texture first.

    Gates:
      A/B camera + mass/stance (CHAR-101)
      C identity geometry helmet/pauldron/shield/sword/plume (CHAR-110)
      D torso layers / scarf / straps / cape / lower armor (CHAR-120)
      polish only after geometry gates when include_polish (CHAR-130)
    """

    proportion = default_proportion_profile("stylized-character")
    pose = build_pose_profile(pose_id, mirrored=(handedness == "left"))
    landmarks = default_character_landmarks()
    if handedness == "left":
        for landmark in landmarks:
            if landmark["id"] in ("shield-center", "sword-grip", "sword-tip", "wrist-left", "wrist-right"):
                landmark["position"][0] = -landmark["position"][0]

    def _mat(mid: str, name: str, role: str, **overrides: Any) -> dict[str, Any]:
        base = apply_role_to_material({"id": mid, "name": name, "type": "physical"}, role)
        base.update(overrides)
        # Blueprint v2 requires channels object.
        base["channels"] = {
            "baseColor": base.get("baseColor", "#888888"),
            "roughness": base.get("roughness", 0.5),
            "metalness": base.get("metalness", 0.0),
        }
        base["role"] = role
        return base

    materials = [
        _mat("mat_steel", "Steel", "steel"),
        _mat("mat_brass", "Brass", "brass"),
        _mat("mat_cloth", "Cloth", "cloth"),
        _mat("mat_leather", "Leather", "leather"),
        _mat("mat_plume", "Plume", "cloth", baseColor="#2f5bd8"),
    ]

    shield_side = -1.0 if handedness == "right" else 1.0
    sword_side = -shield_side

    parts = [
        {
            "id": "pelvis",
            "name": "Pelvis",
            "role": "pelvis",
            "joint": "pelvis",
            "poseDriven": True,
            "geometry": {"kind": "rounded-box", "size": [0.28, 0.16, 0.18], "radius": 0.03},
            "materialId": "mat_steel",
            "transform": {"position": [0, 0.9, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
            "children": [
                {
                    "id": "torso",
                    "name": "Torso",
                    "role": "torso",
                    "joint": "spine",
                    "geometry": {"kind": "rounded-box", "size": [0.36, 0.34, 0.22], "radius": 0.04},
                    "materialId": "mat_steel",
                    "transform": {"position": [0, 0.18, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
                    "children": [
                        {
                            "id": "chest_plate",
                            "name": "Chest Plate",
                            "role": "armor",
                            "geometry": {
                                "kind": "beveled-plate",
                                "outline": [[-0.16, 0.12], [0.16, 0.12], [0.14, -0.12], [-0.14, -0.12]],
                                "thickness": 0.04,
                                "bevel": 0.01,
                            },
                            "materialId": "mat_steel",
                            "transform": {"position": [0, 0.02, 0.1], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
                            "children": [],
                        },
                        {
                            "id": "scarf",
                            "name": "Scarf",
                            "role": "cloth",
                            "geometry": {"kind": "cloth-patch", "width": 0.28, "height": 0.22, "drape": 0.06},
                            "materialId": "mat_cloth",
                            "transform": {"position": [0, 0.1, 0.08], "rotation": [0.2, 0, 0], "scale": [1, 1, 1]},
                            "children": [],
                        },
                        {
                            "id": "strap_cross",
                            "name": "Cross Strap",
                            "role": "strap",
                            "geometry": {"kind": "tube", "path": [[-0.12, 0.12, 0.08], [0.12, -0.1, 0.08]], "radius": 0.015},
                            "materialId": "mat_leather",
                            "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
                            "children": [],
                        },
                        {
                            "id": "brooch",
                            "name": "Brooch",
                            "role": "trim",
                            "geometry": {"kind": "sphere", "radius": 0.03},
                            "materialId": "mat_brass",
                            "transform": {"position": [0, 0.08, 0.12], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
                            "children": [],
                        },
                        {
                            "id": "cape",
                            "name": "Cape",
                            "role": "cloth",
                            "geometry": {"kind": "cloth-patch", "width": 0.4, "height": 0.55, "drape": 0.12},
                            "materialId": "mat_cloth",
                            "transform": {"position": [0, 0.05, -0.12], "rotation": [0.15, 0, 0], "scale": [1, 1, 1]},
                            "children": [],
                        },
                        {
                            "id": "neck",
                            "name": "Neck",
                            "role": "limb",
                            "joint": "neck",
                            "geometry": {"kind": "cylinder", "radiusTop": 0.05, "radiusBottom": 0.06, "height": 0.08},
                            "materialId": "mat_steel",
                            "transform": {"position": [0, 0.2, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
                            "children": [
                                {
                                    "id": "head",
                                    "name": "Head",
                                    "role": "head",
                                    "joint": "head",
                                    "geometry": {"kind": "ellipsoid", "radii": [0.11, 0.13, 0.11]},
                                    "materialId": "mat_steel",
                                    "transform": {"position": [0, 0.14, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
                                    "children": [
                                        {
                                            "id": "helmet",
                                            "name": "Helmet",
                                            "role": "armor",
                                            "geometry": {
                                                "kind": "lathe",
                                                "profile": [[0.0, 0.0], [0.12, 0.0], [0.13, 0.08], [0.08, 0.16], [0.0, 0.18]],
                                            },
                                            "materialId": "mat_steel",
                                            "transform": {"position": [0, 0.02, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
                                            "children": [
                                                {
                                                    "id": "plume",
                                                    "name": "Blue Plume",
                                                    "role": "equipment",
                                                    "geometry": {
                                                        "kind": "feather",
                                                        "length": 0.28,
                                                        "width": 0.08,
                                                        "barbCount": 7,
                                                    },
                                                    "materialId": "mat_plume",
                                                    "transform": {
                                                        "position": [0, 0.16, -0.02],
                                                        "rotation": [-0.4, 0, 0],
                                                        "scale": [1, 1, 1],
                                                    },
                                                    "children": [],
                                                }
                                            ],
                                        }
                                    ],
                                }
                            ],
                        },
                        {
                            "id": "pauldron_l",
                            "name": "Pauldron L",
                            "role": "armor",
                            "geometry": {"kind": "ellipsoid", "radii": [0.1, 0.08, 0.1]},
                            "materialId": "mat_steel",
                            "transform": {"position": [-0.22, 0.12, 0.02], "rotation": [0, 0, 0.2], "scale": [1, 1, 1]},
                            "children": [],
                        },
                        {
                            "id": "pauldron_r",
                            "name": "Pauldron R",
                            "role": "armor",
                            "geometry": {"kind": "ellipsoid", "radii": [0.1, 0.08, 0.1]},
                            "materialId": "mat_steel",
                            "transform": {"position": [0.22, 0.12, 0.02], "rotation": [0, 0, -0.2], "scale": [1, 1, 1]},
                            "children": [],
                        },
                        {
                            "id": "upper_arm_l",
                            "name": "Upper Arm L",
                            "role": "limb",
                            "joint": "shoulder-l",
                            "geometry": {"kind": "capsule", "radius": 0.05, "length": 0.16},
                            "materialId": "mat_steel",
                            "transform": {"position": [-0.22, 0.05, 0.02], "rotation": [0, 0, 0.3], "scale": [1, 1, 1]},
                            "children": [
                                {
                                    "id": "forearm_l",
                                    "name": "Forearm L",
                                    "role": "limb",
                                    "joint": "elbow-l",
                                    "geometry": {"kind": "capsule", "radius": 0.045, "length": 0.14},
                                    "materialId": "mat_steel",
                                    "transform": {"position": [0, -0.16, 0], "rotation": [0.2, 0, 0], "scale": [1, 1, 1]},
                                    "children": [
                                        {
                                            "id": "hand_l",
                                            "name": "Hand L",
                                            "role": "limb",
                                            "joint": "wrist-l",
                                            "geometry": {"kind": "rounded-box", "size": [0.07, 0.08, 0.05], "radius": 0.01},
                                            "materialId": "mat_leather",
                                            "transform": {
                                                "position": [0, -0.12, 0],
                                                "rotation": [0, 0, 0],
                                                "scale": [1, 1, 1],
                                            },
                                            "children": [
                                                {
                                                    "id": "shield",
                                                    "name": "Sun Shield",
                                                    "role": "equipment",
                                                    "geometry": {
                                                        "kind": "shape-extrude",
                                                        "shape": [
                                                            [-0.22, 0.28],
                                                            [0.22, 0.28],
                                                            [0.2, -0.05],
                                                            [0.0, -0.32],
                                                            [-0.2, -0.05],
                                                        ],
                                                        "depth": 0.06,
                                                    },
                                                    "materialId": "mat_steel",
                                                    "transform": {
                                                        "position": [shield_side * 0.12, 0.05, 0.08],
                                                        "rotation": [0, 0.4 * shield_side, 0],
                                                        "scale": [1, 1, 1],
                                                    },
                                                    "attachment": {
                                                        "parentSocket": "socket-hand-l",
                                                        "childSocket": "socket-shield",
                                                        "contact": "grip",
                                                        "maxGap": 0.45,
                                                        "maxPenetration": 0.12,
                                                        "required": True,
                                                    },
                                                    "children": [],
                                                }
                                            ],
                                        }
                                    ],
                                }
                            ],
                        },
                        {
                            "id": "upper_arm_r",
                            "name": "Upper Arm R",
                            "role": "limb",
                            "joint": "shoulder-r",
                            "geometry": {"kind": "capsule", "radius": 0.05, "length": 0.16},
                            "materialId": "mat_steel",
                            "transform": {"position": [0.22, 0.05, 0.02], "rotation": [0, 0, -0.45], "scale": [1, 1, 1]},
                            "children": [
                                {
                                    "id": "forearm_r",
                                    "name": "Forearm R",
                                    "role": "limb",
                                    "joint": "elbow-r",
                                    "geometry": {"kind": "capsule", "radius": 0.045, "length": 0.14},
                                    "materialId": "mat_steel",
                                    "transform": {"position": [0, -0.16, 0], "rotation": [0.35, 0, 0], "scale": [1, 1, 1]},
                                    "children": [
                                        {
                                            "id": "hand_r",
                                            "name": "Hand R",
                                            "role": "limb",
                                            "joint": "wrist-r",
                                            "geometry": {"kind": "rounded-box", "size": [0.07, 0.08, 0.05], "radius": 0.01},
                                            "materialId": "mat_leather",
                                            "transform": {
                                                "position": [0, -0.12, 0],
                                                "rotation": [0, 0, 0],
                                                "scale": [1, 1, 1],
                                            },
                                            "children": [
                                                {
                                                    "id": "sword",
                                                    "name": "Broad Sword",
                                                    "role": "equipment",
                                                    "geometry": {
                                                        "kind": "curve-blade",
                                                        "length": 0.55,
                                                        "width": 0.08,
                                                        "curve": 0.04,
                                                    },
                                                    "materialId": "mat_steel",
                                                    "transform": {
                                                        "position": [sword_side * 0.05, 0.2, 0.02],
                                                        "rotation": [0, 0, -0.4 * sword_side],
                                                        "scale": [1, 1, 1],
                                                    },
                                                    "attachment": {
                                                        "parentSocket": "socket-hand-r",
                                                        "childSocket": "socket-sword",
                                                        "contact": "grip",
                                                        "maxGap": 0.45,
                                                        "maxPenetration": 0.12,
                                                        "required": True,
                                                    },
                                                    "children": [],
                                                }
                                            ],
                                        }
                                    ],
                                }
                            ],
                        },
                    ],
                },
                {
                    "id": "belt",
                    "name": "Belt",
                    "role": "strap",
                    "geometry": {"kind": "torus", "radius": 0.14, "tube": 0.02},
                    "materialId": "mat_leather",
                    "transform": {"position": [0, 0.02, 0], "rotation": [1.5708, 0, 0], "scale": [1, 1, 1]},
                    "children": [],
                },
                {
                    "id": "upper_leg_l",
                    "name": "Upper Leg L",
                    "role": "limb",
                    "joint": "hip-l",
                    "geometry": {"kind": "capsule", "radius": 0.06, "length": 0.2},
                    "materialId": "mat_steel",
                    "transform": {"position": [-0.1, -0.12, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
                    "children": [
                        {
                            "id": "lower_leg_l",
                            "name": "Lower Leg L",
                            "role": "limb",
                            "joint": "knee-l",
                            "geometry": {"kind": "capsule", "radius": 0.05, "length": 0.18},
                            "materialId": "mat_steel",
                            "transform": {"position": [0, -0.2, 0], "rotation": [0.1, 0, 0], "scale": [1, 1, 1]},
                            "children": [
                                {
                                    "id": "boot_l",
                                    "name": "Boot L",
                                    "role": "armor",
                                    "joint": "ankle-l",
                                    "geometry": {"kind": "rounded-box", "size": [0.1, 0.08, 0.16], "radius": 0.02},
                                    "materialId": "mat_leather",
                                    "transform": {
                                        "position": [0, -0.14, 0.03],
                                        "rotation": [0, 0, 0],
                                        "scale": [1, 1, 1],
                                    },
                                    "children": [],
                                }
                            ],
                        }
                    ],
                },
                {
                    "id": "upper_leg_r",
                    "name": "Upper Leg R",
                    "role": "limb",
                    "joint": "hip-r",
                    "geometry": {"kind": "capsule", "radius": 0.06, "length": 0.2},
                    "materialId": "mat_steel",
                    "transform": {"position": [0.1, -0.12, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
                    "children": [
                        {
                            "id": "lower_leg_r",
                            "name": "Lower Leg R",
                            "role": "limb",
                            "joint": "knee-r",
                            "geometry": {"kind": "capsule", "radius": 0.05, "length": 0.18},
                            "materialId": "mat_steel",
                            "transform": {"position": [0, -0.2, 0], "rotation": [0.15, 0, 0], "scale": [1, 1, 1]},
                            "children": [
                                {
                                    "id": "boot_r",
                                    "name": "Boot R",
                                    "role": "armor",
                                    "joint": "ankle-r",
                                    "geometry": {"kind": "rounded-box", "size": [0.1, 0.08, 0.16], "radius": 0.02},
                                    "materialId": "mat_leather",
                                    "transform": {
                                        "position": [0, -0.14, 0.03],
                                        "rotation": [0, 0, 0],
                                        "scale": [1, 1, 1],
                                    },
                                    "children": [],
                                }
                            ],
                        }
                    ],
                },
            ],
        }
    ]

    if include_polish:
        parts = _apply_surface_polish(parts)

    parts = apply_pose_to_parts(parts, pose)

    # Blueprint v2 handles are a dict keyed by handle id (socket ids used by attachments).
    handles = {
        "socket-hand-l": {
            "id": "socket-hand-l",
            "partId": "hand_l",
            "type": "socket",
            "kind": "grip",
            "radius": 0.04,
            "transform": {
                "translation": [0, 0, 0.02],
                "position": [0, 0, 0.02],
                "rotation": [0, 0, 0],
                "scale": [1, 1, 1],
            },
        },
        "socket-hand-r": {
            "id": "socket-hand-r",
            "partId": "hand_r",
            "type": "socket",
            "kind": "grip",
            "radius": 0.04,
            "transform": {
                "translation": [0, 0, 0.02],
                "position": [0, 0, 0.02],
                "rotation": [0, 0, 0],
                "scale": [1, 1, 1],
            },
        },
        "socket-shield": {
            "id": "socket-shield",
            "partId": "shield",
            "type": "socket",
            "kind": "grip",
            "radius": 0.04,
            "transform": {
                "translation": [0, 0, -0.02],
                "position": [0, 0, -0.02],
                "rotation": [0, 0, 0],
                "scale": [1, 1, 1],
            },
        },
        "socket-sword": {
            "id": "socket-sword",
            "partId": "sword",
            "type": "socket",
            "kind": "grip",
            "radius": 0.035,
            "transform": {
                "translation": [0, 0.05, 0],
                "position": [0, 0.05, 0],
                "rotation": [0, 0, 0],
                "scale": [1, 1, 1],
            },
        },
        "origin": {
            "id": "origin",
            "partId": "pelvis",
            "type": "pivot",
            "transform": {
                "translation": [0, 0, 0],
                "position": [0, 0, 0],
                "rotation": [0, 0, 0],
                "scale": [1, 1, 1],
            },
        },
    }

    render_profiles = [
        {
            "id": "source-34",
            "view": "source-34",
            "camera": {"position": [0.9, 1.15, 2.2], "lookAt": [0, 1.0, 0], "fov": 32},
            "purpose": "source-aligned",
        },
        {
            "id": "front",
            "view": "front",
            "camera": {"position": [0, 1.05, 2.4], "lookAt": [0, 1.0, 0], "fov": 32},
            "purpose": "turnaround",
        },
        {
            "id": "left",
            "view": "left",
            "camera": {"position": [-2.4, 1.05, 0], "lookAt": [0, 1.0, 0], "fov": 32},
            "purpose": "turnaround",
        },
        {
            "id": "right",
            "view": "right",
            "camera": {"position": [2.4, 1.05, 0], "lookAt": [0, 1.0, 0], "fov": 32},
            "purpose": "turnaround",
        },
        {
            "id": "back",
            "view": "back",
            "camera": {"position": [0, 1.05, -2.4], "lookAt": [0, 1.0, 0], "fov": 32},
            "purpose": "turnaround",
        },
        {
            "id": "top-34",
            "view": "top-34",
            "camera": {"position": [1.0, 2.6, 1.4], "lookAt": [0, 1.0, 0], "fov": 32},
            "purpose": "inspection",
        },
    ]

    critical = [
        {
            "id": "silhouette",
            "layer": "mass",
            "floor": 0.75,
            "description": "Overall mass matches reference",
            "partIds": ["pelvis", "torso"],
            "targetViews": ["source-34", "front"],
        },
        {
            "id": "helmet_identity",
            "layer": "secondary",
            "floor": 0.7,
            "description": "Helmet dome readable",
            "partIds": ["helmet"],
            "targetViews": ["source-34", "front"],
        },
        {
            "id": "shield_identity",
            "layer": "secondary",
            "floor": 0.7,
            "description": "Shield silhouette readable",
            "partIds": ["shield"],
            "targetViews": ["source-34", "left"],
        },
        {
            "id": "sword_identity",
            "layer": "secondary",
            "floor": 0.7,
            "description": "Sword blade readable",
            "partIds": ["sword"],
            "targetViews": ["source-34", "right"],
        },
        {
            "id": "plume_identity",
            "layer": "secondary",
            "floor": 0.7,
            "description": "Blue plume readable",
            "partIds": ["plume"],
            "targetViews": ["source-34", "front"],
        },
        {
            "id": "handedness",
            "layer": "mass",
            "floor": 0.8,
            "description": "Shield/sword hands match source",
            "partIds": ["shield", "sword", "hand_l", "hand_r"],
            "targetViews": ["source-34"],
        },
    ]

    # Production ledger with character category coverage (PD-2 / DG-03)
    from engine.blueprint.ledger_validation import CHARACTER_LEDGER_CATEGORIES

    category_part = {
        "silhouette-proportion": "pelvis",
        "head-face-helmet": "helmet",
        "torso-layering": "torso",
        "limb-asymmetry": "upper_arm_l",
        "held-worn-equipment": "shield",
        "lower-body-feet": "boot_l",
        "material-roles": "torso",
        "attachment-relationships": "sword",
    }
    ledger_entries = []
    for cat in CHARACTER_LEDGER_CATEGORIES:
        part_ref = category_part.get(cat, "pelvis")
        ledger_entries.append(
            {
                "id": f"ledger-{cat}",
                "kind": "identity",
                "description": f"Character coverage: {cat}",
                "region": {"x": 0, "y": 0, "w": 1, "h": 1, "units": "normalized"},
                "scale": "meso",
                "affects": "geometry",
                "category": cat,
                "mapsTo": {"type": "part", "ref": part_ref},
                "confidence": 0.6,
                "status": "draft",
                "evidenceRefs": ["character-slice", f"category:{cat}", f"part:{part_ref}"],
            }
        )
    while len(ledger_entries) < 8:
        i = len(ledger_entries)
        cat = CHARACTER_LEDGER_CATEGORIES[i % len(CHARACTER_LEDGER_CATEGORIES)]
        part_ref = category_part.get(cat, "pelvis")
        ledger_entries.append(
            {
                "id": f"ledger-extra-{i}",
                "kind": "contour",
                "description": f"Additional coverage {i}",
                "region": {"x": 0, "y": 0, "w": 1, "h": 1, "units": "normalized"},
                "scale": "meso",
                "affects": "geometry",
                "category": cat,
                "mapsTo": {"type": "part", "ref": part_ref},
                "confidence": 0.5,
                "status": "draft",
                "evidenceRefs": ["character-slice", f"part:{part_ref}"],
            }
        )

    bp: dict[str, Any] = {
        "schemaVersion": 2,
        "name": name,
        "qualityMode": "sharp",
        "modelingProfile": "stylized-character",
        "intent": "game",
        "deliveryGrade": "delivery",
        "enforceCharacterDepth": True,
        "handedness": handedness,
        "revision": {"id": "rev-char-001", "parent": None, "contentHash": ""},
        "proportionProfile": proportion,
        "poseProfile": pose,
        "landmarks": landmarks,
        "parts": parts,
        "materials": materials,
        "handles": handles,
        "renderProfiles": render_profiles,
        "criticalFeatures": critical,
        "ledger": {
            "version": 1,
            "mode": "production",
            "modelingProfile": "stylized-character",
            "targetMin": 8,
            "entries": ledger_entries,
            "agentAction": "continue",
        },
        "bodySource": "procedural",
        "domain": "character",
        "complexity": "complex",
        "environment": {
            "id": "neutral-studio",
            "exposure": 1.0,
            "ambientIntensity": 0.45,
            "keyIntensity": 1.1,
            "fillIntensity": 0.4,
            "rimIntensity": 0.25,
        },
        "polishApplied": include_polish,
        "seed": 42,
    }
    bp["revision"]["contentHash"] = blueprint_revision_content_hash(bp)
    return bp


def _apply_surface_polish(parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add trim/rivet/seam polish only after geometry gates (CHAR-130)."""

    cloned = deepcopy(parts)

    def add_polish(part: dict[str, Any]) -> None:
        if part.get("id") == "chest_plate":
            part.setdefault("children", []).append(
                {
                    "id": "chest_rivets",
                    "name": "Chest Rivets",
                    "role": "trim",
                    "geometry": {
                        "kind": "instance-set",
                        "prototype": {"kind": "sphere", "radius": 0.008},
                        "count": 6,
                        "distribution": "grid",
                    },
                    "materialId": "mat_brass",
                    "transform": {"position": [0, 0, 0.025], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
                    "children": [],
                }
            )
        if part.get("id") == "helmet":
            part.setdefault("children", []).append(
                {
                    "id": "helmet_seam",
                    "name": "Helmet Seam",
                    "role": "trim",
                    "geometry": {"kind": "tube", "path": [[-0.1, 0.05, 0.08], [0.1, 0.05, 0.08]], "radius": 0.006},
                    "materialId": "mat_brass",
                    "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
                    "children": [],
                }
            )
        for child in part.get("children") or []:
            add_polish(child)

    for part in cloned:
        add_polish(part)
    return cloned


def validate_character_slice(blueprint: dict[str, Any]) -> dict[str, Any]:
    """Run M3 automatic checks for proportion/pose/attachments/materials/roles."""

    errors: list[str] = []
    profile = blueprint.get("modelingProfile") or "stylized-character"
    rules = modeling_profile_rules(profile)
    errors.extend(validate_proportion_profile(blueprint.get("proportionProfile") or {}))
    if rules.get("requireLandmarks"):
        errors.extend(
            validate_landmarks(
                blueprint.get("landmarks") or [],
                required=tuple(rules.get("requiredLandmarks") or ()),
            )
        )

    roles = set()
    identity_ids = set()

    def walk(part: dict[str, Any], depth: int) -> int:
        roles.add(part.get("role"))
        identity_ids.add(part.get("id"))
        max_depth = depth
        for child in part.get("children") or []:
            max_depth = max(max_depth, walk(child, depth + 1))
        return max_depth

    depth = 0
    for part in blueprint.get("parts") or []:
        depth = max(depth, walk(part, 1))

    for role in rules.get("requiredRoles") or ():
        if role not in roles:
            errors.append(f"$.parts: missing required role {role!r}")
    if depth < int(rules.get("minHierarchyDepth") or 1):
        errors.append(f"$.parts: hierarchy depth {depth} below minimum {rules['minHierarchyDepth']}")

    for required_id in ("helmet", "shield", "sword", "plume", "pauldron_l", "pauldron_r"):
        if required_id not in identity_ids:
            errors.append(f"$.parts: missing identity part {required_id!r}")

    attach_errors = validate_attachment_schema(
        blueprint.get("parts") or [],
        blueprint.get("handles"),
    )
    errors.extend(attach_errors)
    contacts = assess_attachment_contacts(blueprint.get("parts") or [], blueprint.get("handles"))
    if not contacts["passed"]:
        errors.extend(i["message"] for i in contacts["issues"] if i.get("severity") == "error")

    readability = assess_material_readability(blueprint.get("materials") or [])
    if not readability["passed"]:
        errors.extend(i["message"] for i in readability["issues"] if i.get("severity") == "error")

    return {
        "ok": not errors,
        "errors": errors,
        "contacts": contacts,
        "readability": readability,
        "hierarchyDepth": depth,
        "roles": sorted(r for r in roles if r),
        "contentHash": content_hash(
            {
                "parts": blueprint.get("parts"),
                "pose": blueprint.get("poseProfile"),
                "proportion": blueprint.get("proportionProfile"),
            }
        ),
    }


def character_gate_report(blueprint: dict[str, Any]) -> dict[str, Any]:
    """Gate A-E style summary for the character vertical slice."""

    validation = validate_character_slice(blueprint)
    identity = {"helmet", "shield", "sword", "plume", "pauldron_l", "pauldron_r"}
    present = set()

    def walk(part: dict[str, Any]) -> None:
        if part.get("id") in identity:
            present.add(part["id"])
        for child in part.get("children") or []:
            walk(child)

    for part in blueprint.get("parts") or []:
        walk(part)

    torso_roles = {"cloth", "strap", "armor"}
    roles = set(validation.get("roles") or [])
    gates = {
        "A_camera_profiles": bool(blueprint.get("renderProfiles")),
        "B_mass_stance": bool(blueprint.get("proportionProfile") and blueprint.get("poseProfile")),
        "C_identity_geometry": identity.issubset(present),
        "D_torso_layers": bool(torso_roles & roles) and "cape" in {
            p for p in _all_ids(blueprint.get("parts") or [])
        },
        "E_attachments_materials": validation["contacts"]["passed"] and validation["readability"]["passed"],
    }
    return {
        "schemaVersion": 1,
        "gates": gates,
        "passed": all(gates.values()) and validation["ok"],
        "validation": validation,
        "polishApplied": bool(blueprint.get("polishApplied")),
    }


def _all_ids(parts: list[dict[str, Any]]) -> set[str]:
    ids: set[str] = set()

    def walk(part: dict[str, Any]) -> None:
        if part.get("id"):
            ids.add(part["id"])
        for child in part.get("children") or []:
            walk(child)

    for part in parts:
        walk(part)
    return ids
