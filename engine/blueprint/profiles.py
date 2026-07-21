"""Modeling profile rule tables, proportions, pose, and landmarks."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from engine.contracts.blueprint_v2 import LIMB_THICKNESS_PROFILES, MODELING_PROFILES

PROFILE_RULES: dict[str, dict[str, Any]] = {
    "generic-prop": {
        "requiredRoles": ("primary",),
        "requirePose": False,
        "requireLandmarks": False,
        "requireCharacterCoverage": False,
        "minHierarchyDepth": 1,
        "minParts": 1,
    },
    "hard-surface-hero": {
        "requiredRoles": ("primary", "trim"),
        "requirePose": False,
        "requireLandmarks": True,
        "requireCharacterCoverage": False,
        "minHierarchyDepth": 2,
        "minParts": 2,
    },
    "stylized-character": {
        "requiredRoles": (
            "pelvis",
            "torso",
            "head",
            "limb",
            "equipment",
        ),
        "requirePose": True,
        "requireLandmarks": True,
        "requireCharacterCoverage": True,
        "minHierarchyDepth": 3,
        "minParts": 8,
        "requiredLandmarks": (
            "crown",
            "chin",
            "shoulder-left",
            "shoulder-right",
            "pelvis",
            "wrist-left",
            "wrist-right",
            "shield-center",
            "sword-grip",
        ),
    },
}


DEFAULT_PROPORTIONS = {
    "generic-prop": {
        "headUnits": 1.0,
        "headHeightRatio": 0.0,
        "shoulderWidthRatio": 0.0,
        "limbThickness": "standard",
    },
    "hard-surface-hero": {
        "headUnits": 1.0,
        "headHeightRatio": 0.0,
        "shoulderWidthRatio": 0.5,
        "limbThickness": "standard",
    },
    "stylized-character": {
        "headUnits": 4.2,
        "headHeightRatio": 0.235,
        "shoulderWidthRatio": 0.42,
        "limbThickness": "chunky",
    },
}


DEFAULT_JOINTS_SOURCE_34 = {
    "pelvis": {"position": [0.0, 0.9, 0.0], "rotation": [0.0, 0.15, 0.0]},
    "spine": {"position": [0.0, 0.18, 0.0], "rotation": [0.05, 0.1, 0.0]},
    "chest": {"position": [0.0, 0.16, 0.0], "rotation": [0.0, 0.08, 0.0]},
    "neck": {"position": [0.0, 0.12, 0.0], "rotation": [0.0, 0.0, 0.0]},
    "head": {"position": [0.0, 0.14, 0.0], "rotation": [0.0, 0.12, 0.0]},
    "shoulder-l": {"position": [-0.22, 0.12, 0.02], "rotation": [0.1, 0.0, 0.35]},
    "elbow-l": {"position": [0.0, -0.18, 0.0], "rotation": [0.2, 0.0, 0.1]},
    "wrist-l": {"position": [0.0, -0.16, 0.0], "rotation": [0.0, 0.0, 0.0]},
    "shoulder-r": {"position": [0.22, 0.12, 0.02], "rotation": [0.15, 0.0, -0.55]},
    "elbow-r": {"position": [0.0, -0.18, 0.0], "rotation": [0.35, 0.0, -0.1]},
    "wrist-r": {"position": [0.0, -0.16, 0.0], "rotation": [0.1, 0.0, 0.0]},
    "hip-l": {"position": [-0.1, -0.05, 0.0], "rotation": [0.05, 0.0, 0.05]},
    "knee-l": {"position": [0.0, -0.22, 0.0], "rotation": [0.15, 0.0, 0.0]},
    "ankle-l": {"position": [0.0, -0.2, 0.0], "rotation": [0.0, 0.0, 0.0]},
    "hip-r": {"position": [0.1, -0.05, 0.0], "rotation": [0.1, 0.0, -0.08]},
    "knee-r": {"position": [0.0, -0.22, 0.0], "rotation": [0.25, 0.0, 0.0]},
    "ankle-r": {"position": [0.0, -0.2, 0.0], "rotation": [0.0, 0.0, 0.0]},
}


DEFAULT_JOINTS_NEUTRAL = {
    key: {
        "position": list(value["position"]),
        "rotation": [0.0, 0.0, 0.0],
    }
    for key, value in DEFAULT_JOINTS_SOURCE_34.items()
}


def modeling_profile_rules(profile: str) -> dict[str, Any]:
    if profile not in PROFILE_RULES:
        raise ValueError(f"unsupported modelingProfile {profile!r}; expected one of {MODELING_PROFILES}")
    return deepcopy(PROFILE_RULES[profile])


def default_proportion_profile(profile: str = "stylized-character") -> dict[str, Any]:
    base = deepcopy(DEFAULT_PROPORTIONS.get(profile) or DEFAULT_PROPORTIONS["generic-prop"])
    return base


def validate_proportion_profile(proportion: dict[str, Any], *, path: str = "$.proportionProfile") -> list[str]:
    errors: list[str] = []
    for field in ("headUnits", "headHeightRatio", "shoulderWidthRatio", "limbThickness"):
        if field not in proportion:
            errors.append(f"{path}.{field}: missing required field")
    head_units = proportion.get("headUnits")
    if isinstance(head_units, (int, float)) and not (1.5 <= float(head_units) <= 8.0):
        # props may use 1.0; only warn via range for character-like values when set high
        if float(head_units) < 0:
            errors.append(f"{path}.headUnits: expected non-negative")
    thickness = proportion.get("limbThickness")
    if thickness is not None and thickness not in LIMB_THICKNESS_PROFILES:
        errors.append(f"{path}.limbThickness: unsupported {thickness!r}")
    for ratio_name in ("headHeightRatio", "shoulderWidthRatio"):
        value = proportion.get(ratio_name)
        if value is None:
            continue
        if not isinstance(value, (int, float)) or not (0.0 <= float(value) <= 1.0):
            errors.append(f"{path}.{ratio_name}: expected number in 0..1")
    return errors


def build_pose_profile(
    pose_id: str = "source-34",
    *,
    mirrored: bool = False,
    joints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if joints is not None:
        joint_map = deepcopy(joints)
    elif pose_id == "neutral":
        joint_map = deepcopy(DEFAULT_JOINTS_NEUTRAL)
    else:
        joint_map = deepcopy(DEFAULT_JOINTS_SOURCE_34)
    if mirrored:
        joint_map = _mirror_joints(joint_map)
    return {
        "id": pose_id,
        "mirrored": mirrored,
        "joints": joint_map,
    }


def _mirror_joints(joints: dict[str, Any]) -> dict[str, Any]:
    mirrored: dict[str, Any] = {}
    swap = {
        "shoulder-l": "shoulder-r",
        "shoulder-r": "shoulder-l",
        "elbow-l": "elbow-r",
        "elbow-r": "elbow-l",
        "wrist-l": "wrist-r",
        "wrist-r": "wrist-l",
        "hip-l": "hip-r",
        "hip-r": "hip-l",
        "knee-l": "knee-r",
        "knee-r": "knee-l",
        "ankle-l": "ankle-r",
        "ankle-r": "ankle-l",
    }
    for key, value in joints.items():
        target = swap.get(key, key)
        pos = list(value.get("position") or [0, 0, 0])
        rot = list(value.get("rotation") or [0, 0, 0])
        pos[0] = -pos[0]
        rot[1] = -rot[1]
        rot[2] = -rot[2]
        mirrored[target] = {"position": pos, "rotation": rot}
    return mirrored


def apply_pose_to_parts(
    parts: list[dict[str, Any]],
    pose: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Return a deep-copied part tree with joint transforms applied.

    Geometry specs are left unchanged; only transform channels update so pose
    switches do not require geometry regeneration.
    """

    joint_map = pose.get("joints") or {}
    cloned = deepcopy(parts)

    def walk(part: dict[str, Any]) -> None:
        joint_id = part.get("joint") or part.get("id")
        if joint_id in joint_map:
            joint = joint_map[joint_id]
            transform = part.setdefault("transform", {})
            # Preserve authored local offsets by replacing joint channels only when marked.
            if part.get("poseDriven", True):
                if "position" in joint:
                    transform["position"] = list(joint["position"])
                if "rotation" in joint:
                    transform["rotation"] = list(joint["rotation"])
        for child in part.get("children") or []:
            walk(child)

    for part in cloned:
        walk(part)
    return cloned


def default_character_landmarks() -> list[dict[str, Any]]:
    return [
        {"id": "crown", "semantic": "crown", "space": "body", "position": [0.0, 1.55, 0.05]},
        {"id": "chin", "semantic": "chin", "space": "body", "position": [0.0, 1.28, 0.08]},
        {"id": "shoulder-left", "semantic": "shoulder", "space": "body", "position": [-0.22, 1.22, 0.02]},
        {"id": "shoulder-right", "semantic": "shoulder", "space": "body", "position": [0.22, 1.22, 0.02]},
        {"id": "sternum", "semantic": "sternum", "space": "body", "position": [0.0, 1.1, 0.06]},
        {"id": "pelvis", "semantic": "pelvis", "space": "body", "position": [0.0, 0.9, 0.0]},
        {"id": "elbow-left", "semantic": "elbow", "space": "body", "position": [-0.38, 1.0, 0.05]},
        {"id": "elbow-right", "semantic": "elbow", "space": "body", "position": [0.4, 0.95, 0.08]},
        {"id": "wrist-left", "semantic": "wrist", "space": "body", "position": [-0.42, 0.82, 0.1]},
        {"id": "wrist-right", "semantic": "wrist", "space": "body", "position": [0.48, 0.78, 0.12]},
        {"id": "knee-left", "semantic": "knee", "space": "body", "position": [-0.1, 0.48, 0.02]},
        {"id": "knee-right", "semantic": "knee", "space": "body", "position": [0.12, 0.45, 0.04]},
        {"id": "ankle-left", "semantic": "ankle", "space": "body", "position": [-0.1, 0.12, 0.04]},
        {"id": "ankle-right", "semantic": "ankle", "space": "body", "position": [0.12, 0.1, 0.05]},
        {"id": "shield-center", "semantic": "equipment", "space": "body", "position": [-0.5, 0.95, 0.12]},
        {"id": "sword-grip", "semantic": "equipment", "space": "body", "position": [0.52, 0.75, 0.1]},
        {"id": "sword-tip", "semantic": "equipment", "space": "body", "position": [0.7, 1.2, 0.05]},
    ]


def project_landmark_to_screen(
    landmark: dict[str, Any],
    *,
    camera: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Simple orthographic-ish projection for tests and metric hooks."""

    cam = camera or {"position": [0.0, 1.0, 2.5], "lookAt": [0.0, 1.0, 0.0], "fov": 35.0}
    pos = landmark.get("position") or [0, 0, 0]
    # NDC-like mapping relative to camera look target.
    look = cam.get("lookAt") or [0, 1, 0]
    cam_pos = cam.get("position") or [0, 1, 2.5]
    # Use x relative to look, y relative to look, ignore perspective depth for MVP.
    sx = 0.5 + (float(pos[0]) - float(look[0])) * 0.45
    sy = 0.5 - (float(pos[1]) - float(look[1])) * 0.45
    depth = float(cam_pos[2]) - float(pos[2])
    return {"x": sx, "y": sy, "depth": depth}


def validate_landmarks(
    landmarks: list[dict[str, Any]],
    *,
    required: tuple[str, ...] = (),
    path: str = "$.landmarks",
) -> list[str]:
    errors: list[str] = []
    ids = set()
    for index, landmark in enumerate(landmarks):
        lp = f"{path}[{index}]"
        for field in ("id", "semantic", "space", "position"):
            if field not in landmark:
                errors.append(f"{lp}.{field}: missing required field")
        lid = landmark.get("id")
        if lid in ids:
            errors.append(f"{lp}.id: duplicate landmark id {lid!r}")
        ids.add(lid)
        pos = landmark.get("position")
        if pos is not None and (not isinstance(pos, list) or len(pos) != 3):
            errors.append(f"{lp}.position: expected length-3 array")
    for req in required:
        if req not in ids:
            errors.append(f"{path}: missing required landmark {req!r}")
    return errors
