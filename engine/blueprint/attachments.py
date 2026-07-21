"""Attachment sockets, contact schema, and gross penetration checks."""

from __future__ import annotations

import math
from typing import Any


def validate_attachment_schema(
    parts: list[dict[str, Any]],
    handles: dict[str, Any] | list[dict[str, Any]] | None,
    *,
    path: str = "$",
) -> list[str]:
    """Validate parent/child socket references and attachment fields."""

    errors: list[str] = []
    part_ids = _collect_part_ids(parts)
    sockets = _socket_index(handles)

    def walk(part: dict[str, Any], part_path: str) -> None:
        attachment = part.get("attachment")
        if not attachment:
            for child in part.get("children") or []:
                walk(child, f"{part_path}.children")
            return
        ap = f"{part_path}.attachment"
        for field in ("parentSocket", "childSocket", "contact", "maxGap", "maxPenetration", "required"):
            # Accept legacy v1 attachment shape (parent/contact/embed) as soft compatibility.
            if field not in attachment and field not in ("parentSocket", "childSocket", "maxGap", "maxPenetration", "required"):
                continue
        if "parentSocket" in attachment or "childSocket" in attachment:
            parent_socket = attachment.get("parentSocket")
            child_socket = attachment.get("childSocket")
            if parent_socket not in sockets:
                errors.append(f"{ap}.parentSocket: dangling socket {parent_socket!r}")
            if child_socket not in sockets:
                errors.append(f"{ap}.childSocket: dangling socket {child_socket!r}")
            if parent_socket in sockets and child_socket in sockets:
                parent = sockets[parent_socket]
                child = sockets[child_socket]
                if parent.get("partId") == child.get("partId"):
                    errors.append(f"{ap}: parent and child sockets resolve to the same part")
                # Optional semantic match: socket kinds should pair.
                if parent.get("kind") and child.get("kind") and parent.get("kind") != child.get("kind"):
                    if parent.get("kind") not in ("generic",) and child.get("kind") not in ("generic",):
                        errors.append(
                            f"{ap}: mismatched socket kinds {parent.get('kind')!r} vs {child.get('kind')!r}"
                        )
        elif "parent" in attachment:
            parent = attachment.get("parent")
            if parent not in part_ids:
                errors.append(f"{ap}.parent: dangling parent part {parent!r}")
        for child in part.get("children") or []:
            walk(child, f"{part_path}.children")

    for index, part in enumerate(parts):
        walk(part, f"{path}.parts[{index}]")
    return errors


def _collect_part_ids(parts: list[dict[str, Any]]) -> set[str]:
    ids: set[str] = set()

    def walk(part: dict[str, Any]) -> None:
        if part.get("id"):
            ids.add(part["id"])
        for child in part.get("children") or []:
            walk(child)

    for part in parts:
        walk(part)
    return ids


def _socket_index(handles: dict[str, Any] | list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    if handles is None:
        return {}
    if isinstance(handles, list):
        return {h["id"]: h for h in handles if isinstance(h, dict) and h.get("id")}
    index: dict[str, dict[str, Any]] = {}
    # v1 shape: {sockets: [...]}
    for socket in handles.get("sockets") or []:
        if isinstance(socket, dict) and socket.get("id"):
            index[socket["id"]] = socket
    for handle in handles.get("handles") or []:
        if isinstance(handle, dict) and handle.get("type") == "socket" and handle.get("id"):
            index[handle["id"]] = handle
    # v2 shape: dict keyed by handle id
    for key, handle in handles.items():
        if key in ("sockets", "handles", "pivots", "colliders", "breakGroups"):
            continue
        if isinstance(handle, dict) and (handle.get("type") in (None, "socket") or handle.get("kind")):
            entry = dict(handle)
            entry.setdefault("id", key)
            # normalize local offset from transform.position/translation
            if "local" not in entry:
                tf = entry.get("transform") or {}
                local = tf.get("position") or tf.get("translation")
                if local:
                    entry["local"] = list(local)
            index[str(entry.get("id") or key)] = entry
    return index


def _mat_mul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    out = [[0.0] * 4 for _ in range(4)]
    for i in range(4):
        for j in range(4):
            out[i][j] = sum(a[i][k] * b[k][j] for k in range(4))
    return out


def _mat_vec(m: list[list[float]], v: list[float]) -> list[float]:
    x, y, z = float(v[0]), float(v[1]), float(v[2])
    return [
        m[0][0] * x + m[0][1] * y + m[0][2] * z + m[0][3],
        m[1][0] * x + m[1][1] * y + m[1][2] * z + m[1][3],
        m[2][0] * x + m[2][1] * y + m[2][2] * z + m[2][3],
    ]


def _euler_matrix(rx: float, ry: float, rz: float) -> list[list[float]]:
    """XYZ Euler rotation matrix (radians)."""
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    # R = Rz * Ry * Rx
    return [
        [cy * cz, sx * sy * cz - cx * sz, cx * sy * cz + sx * sz, 0.0],
        [cy * sz, sx * sy * sz + cx * cz, cx * sy * sz - sx * cz, 0.0],
        [-sy, sx * cy, cx * cy, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _translation_matrix(t: list[float]) -> list[list[float]]:
    return [
        [1.0, 0.0, 0.0, float(t[0])],
        [0.0, 1.0, 0.0, float(t[1])],
        [0.0, 0.0, 1.0, float(t[2])],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _scale_matrix(s: list[float]) -> list[list[float]]:
    return [
        [float(s[0]), 0.0, 0.0, 0.0],
        [0.0, float(s[1]), 0.0, 0.0],
        [0.0, 0.0, float(s[2]), 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _local_matrix(transform: dict[str, Any] | None) -> list[list[float]]:
    t = transform or {}
    pos = list(t.get("position") or t.get("translation") or [0, 0, 0])
    rot = list(t.get("rotation") or [0, 0, 0])
    scl = list(t.get("scale") or [1, 1, 1])
    return _mat_mul(
        _translation_matrix(pos),
        _mat_mul(_euler_matrix(float(rot[0]), float(rot[1]), float(rot[2])), _scale_matrix(scl)),
    )


def part_world_transforms(parts: list[dict[str, Any]]) -> dict[str, list[list[float]]]:
    """World 4x4 transforms including rotation/scale (PD-3)."""

    worlds: dict[str, list[list[float]]] = {}
    identity = [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]

    def walk(part: dict[str, Any], parent: list[list[float]]) -> None:
        local = _local_matrix(part.get("transform"))
        world = _mat_mul(parent, local)
        if part.get("id"):
            worlds[str(part["id"])] = world
        for child in part.get("children") or []:
            walk(child, world)

    for part in parts:
        walk(part, identity)
    return worlds


def part_world_positions(parts: list[dict[str, Any]]) -> dict[str, list[float]]:
    """World positions derived from full transform chain."""

    transforms = part_world_transforms(parts)
    return {
        pid: [m[0][3], m[1][3], m[2][3]]
        for pid, m in transforms.items()
    }


def assess_attachment_contacts(
    parts: list[dict[str, Any]],
    handles: dict[str, Any] | list[dict[str, Any]] | None,
    *,
    path: str = "$",
) -> dict[str, Any]:
    """
    World-space gap and gross penetration checks for equipment attachments.
    Uses rotation-aware transform accumulation (PD-3).
    """

    sockets = _socket_index(handles)
    transforms = part_world_transforms(parts)
    issues: list[dict[str, Any]] = []

    def socket_world(socket: dict[str, Any], part_id: str | None) -> list[float] | None:
        if not part_id or part_id not in transforms:
            return None
        local = (
            socket.get("local")
            or (socket.get("transform") or {}).get("position")
            or (socket.get("transform") or {}).get("translation")
            or [0, 0, 0]
        )
        return _mat_vec(transforms[part_id], list(local))

    def walk(part: dict[str, Any]) -> None:
        attachment = part.get("attachment") or {}
        if attachment.get("parentSocket") and attachment.get("childSocket"):
            parent_socket = sockets.get(attachment["parentSocket"], {})
            child_socket = sockets.get(attachment["childSocket"], {})
            parent_part = parent_socket.get("partId")
            child_part = child_socket.get("partId") or part.get("id")
            a = socket_world(parent_socket, parent_part)
            b = socket_world(child_socket, str(child_part) if child_part else None)
            if a is not None and b is not None:
                gap = math.dist(a, b)
                max_gap = float(attachment.get("maxGap", 0.15))
                max_pen = float(attachment.get("maxPenetration", 0.05))
                if gap > max_gap:
                    issues.append(
                        {
                            "code": "ATTACHMENT_GAP",
                            "partId": part.get("id"),
                            "gap": gap,
                            "maxGap": max_gap,
                            "severity": "error" if attachment.get("required", True) else "warning",
                            "message": f"attachment gap {gap:.3f} exceeds maxGap {max_gap:.3f}",
                            "parentWorld": a,
                            "childWorld": b,
                        }
                    )
                parent_r = float(parent_socket.get("radius", 0.05))
                child_r = float(child_socket.get("radius", 0.05))
                penetration = (parent_r + child_r) - gap
                if penetration > max_pen:
                    issues.append(
                        {
                            "code": "ATTACHMENT_PENETRATION",
                            "partId": part.get("id"),
                            "penetration": penetration,
                            "maxPenetration": max_pen,
                            "severity": "error",
                            "message": f"gross penetration {penetration:.3f} exceeds max {max_pen:.3f}",
                        }
                    )
        for child in part.get("children") or []:
            walk(child)

    for part in parts:
        walk(part)

    return {
        "schemaVersion": 1,
        "passed": not any(i.get("severity") == "error" for i in issues),
        "issues": issues,
        "checkedParts": len(transforms),
        "rotationAware": True,
    }
