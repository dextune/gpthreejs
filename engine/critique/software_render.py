"""Deterministic CPU multi-pass renderer for production run metrics.

Renders real PNG files (beauty, alpha, partId, albedo, normal, linearDepth,
materialDebug, wireframe) from Blueprint part transforms and materials. This is
not a full GPU path, but metrics and review consume the written files — no
hardcoded pass scores.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

from engine.blueprint.attachments import part_world_positions
from engine.critique.render_profiles import REQUIRED_PASSES, VIEW_PROFILE_IDS, camera_profile, light_profile
from engine.geometry.builders import build_geometry
from engine.shared.artifacts import content_hash
from engine.shared.pngio import Image, read_png, write_png


def _hex_rgb(color: str | None) -> tuple[int, int, int]:
    if not color:
        return (136, 136, 136)
    c = str(color).lstrip("#")
    if len(c) >= 6:
        return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    return (136, 136, 136)


def _part_extent(geometry: dict[str, Any]) -> list[float]:
    """Half-extents estimate from geometry kind."""
    try:
        bounds = build_geometry(geometry)["bounds"]
        mn, mx = bounds["min"], bounds["max"]
        return [(mx[i] - mn[i]) / 2 for i in range(3)]
    except Exception:
        return [0.08, 0.08, 0.08]


def _project(
    world: list[float],
    camera: dict[str, Any],
    *,
    width: int,
    height: int,
) -> tuple[float, float, float]:
    cam = camera.get("position") or [0, 1, 2.5]
    look = camera.get("lookAt") or [0, 1, 0]
    # simple look-at basis (right-handed)
    forward = [look[0] - cam[0], look[1] - cam[1], look[2] - cam[2]]
    fl = math.sqrt(sum(v * v for v in forward)) or 1.0
    forward = [v / fl for v in forward]
    up = [0.0, 1.0, 0.0]
    right = [
        forward[1] * up[2] - forward[2] * up[1],
        forward[2] * up[0] - forward[0] * up[2],
        forward[0] * up[1] - forward[1] * up[0],
    ]
    rl = math.sqrt(sum(v * v for v in right)) or 1.0
    right = [v / rl for v in right]
    up = [
        right[1] * forward[2] - right[2] * forward[1],
        right[2] * forward[0] - right[0] * forward[2],
        right[0] * forward[1] - right[1] * forward[0],
    ]
    rel = [world[0] - cam[0], world[1] - cam[1], world[2] - cam[2]]
    x = rel[0] * right[0] + rel[1] * right[1] + rel[2] * right[2]
    y = rel[0] * up[0] + rel[1] * up[1] + rel[2] * up[2]
    z = rel[0] * forward[0] + rel[1] * forward[1] + rel[2] * forward[2]
    # perspective-ish
    fov = float(camera.get("fov") or 35.0)
    f = 1.0 / math.tan(math.radians(fov) / 2.0)
    depth = max(0.05, z)
    ndc_x = (x * f) / depth
    ndc_y = (y * f) / depth
    sx = (ndc_x * 0.5 + 0.5) * width
    sy = (-ndc_y * 0.5 + 0.5) * height
    return sx, sy, depth


def _collect_parts(parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []

    def walk(part: dict[str, Any]) -> None:
        flat.append(part)
        for child in part.get("children") or []:
            walk(child)

    for part in parts:
        walk(part)
    return flat


def _part_color_id(part_id: str) -> tuple[int, int, int]:
    digest = hashlib.sha256(part_id.encode("utf-8")).digest()
    # avoid near-black (reserved for background)
    return (32 + digest[0] % 224, 32 + digest[1] % 224, 32 + digest[2] % 224)


def render_view_passes(
    blueprint: dict[str, Any],
    *,
    view_id: str,
    out_dir: str | Path,
    width: int = 128,
    height: int = 128,
    camera: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write all required pass PNGs for one view; return pass metadata."""

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cam = camera or camera_profile(view_id)
    worlds = part_world_positions(blueprint.get("parts") or [])
    materials = {m["id"]: m for m in blueprint.get("materials") or [] if m.get("id")}
    parts = _collect_parts(blueprint.get("parts") or [])

    # z-buffer + layers
    zbuf = [1e9] * (width * height)
    beauty = Image(width, height, bytearray([40, 40, 44, 255] * (width * height)))
    alpha = Image(width, height, bytearray([0, 0, 0, 0] * (width * height)))
    part_id_img = Image(width, height, bytearray([0, 0, 0, 255] * (width * height)))
    albedo = Image(width, height, bytearray([40, 40, 44, 255] * (width * height)))
    normal = Image(width, height, bytearray([128, 128, 255, 255] * (width * height)))
    depth_img = Image(width, height, bytearray([0, 0, 0, 255] * (width * height)))
    mat_dbg = Image(width, height, bytearray([0, 0, 0, 255] * (width * height)))
    wire = Image(width, height, bytearray([20, 20, 24, 255] * (width * height)))

    # sort far-to-near for simple painter
    draw_list: list[tuple[float, dict[str, Any], list[float], list[float]]] = []
    for part in parts:
        pid = part.get("id")
        if not pid or pid not in worlds:
            continue
        pos = worlds[pid]
        _sx, _sy, depth = _project(pos, cam, width=width, height=height)
        extent = _part_extent(part.get("geometry") or {"kind": "box", "size": [0.1, 0.1, 0.1]})
        scale = (part.get("transform") or {}).get("scale") or [1, 1, 1]
        half = [extent[i] * float(scale[i]) for i in range(3)]
        draw_list.append((depth, part, pos, half))
    draw_list.sort(key=lambda item: -item[0])

    visible_parts: list[str] = []
    for depth, part, pos, half in draw_list:
        pid = str(part["id"])
        mat = materials.get(part.get("materialId"), {})
        base = mat.get("baseColor") or (mat.get("channels") or {}).get("baseColor")
        rgb = _hex_rgb(str(base) if base else None)
        pid_rgb = _part_color_id(pid)
        metal = float(mat.get("metalness") or (mat.get("channels") or {}).get("metalness") or 0)
        # project AABB corners to screen for filled ellipse/rect
        corners = []
        for dx in (-half[0], half[0]):
            for dy in (-half[1], half[1]):
                for dz in (-half[2], half[2]):
                    corners.append(_project([pos[0] + dx, pos[1] + dy, pos[2] + dz], cam, width=width, height=height))
        xs = [c[0] for c in corners]
        ys = [c[1] for c in corners]
        min_x = max(0, int(min(xs)))
        max_x = min(width - 1, int(max(xs)))
        min_y = max(0, int(min(ys)))
        max_y = min(height - 1, int(max(ys)))
        if max_x < min_x or max_y < min_y:
            continue
        cx = (min_x + max_x) / 2
        cy = (min_y + max_y) / 2
        rx = max(1.0, (max_x - min_x) / 2)
        ry = max(1.0, (max_y - min_y) / 2)
        painted = False
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                nx = (x - cx) / rx
                ny = (y - cy) / ry
                if nx * nx + ny * ny > 1.0:
                    continue
                idx = y * width + x
                if depth >= zbuf[idx]:
                    continue
                zbuf[idx] = depth
                painted = True
                beauty.set_pixel(x, y, (*rgb, 255))
                alpha.set_pixel(x, y, (255, 255, 255, 255))
                part_id_img.set_pixel(x, y, (*pid_rgb, 255))
                albedo.set_pixel(x, y, (*rgb, 255))
                # fake normal facing camera with slight gradient
                nr = int(128 + 40 * nx)
                ng = int(128 + 40 * ny)
                normal.set_pixel(x, y, (max(0, min(255, nr)), max(0, min(255, ng)), 220, 255))
                # linear depth encoded 0..255
                dval = int(max(0, min(255, 255 - depth * 40)))
                depth_img.set_pixel(x, y, (dval, dval, dval, 255))
                # material debug: metalness in red, roughness in green
                rough = float(mat.get("roughness") or (mat.get("channels") or {}).get("roughness") or 0.5)
                mat_dbg.set_pixel(x, y, (int(metal * 255), int(rough * 255), 64, 255))
        if painted:
            visible_parts.append(pid)
            # wireframe outline
            for x in range(min_x, max_x + 1):
                wire.set_pixel(x, min_y, (220, 220, 220, 255))
                wire.set_pixel(x, max_y, (220, 220, 220, 255))
            for y in range(min_y, max_y + 1):
                wire.set_pixel(min_x, y, (220, 220, 220, 255))
                wire.set_pixel(max_x, y, (220, 220, 220, 255))

    images = {
        "beauty": beauty,
        "alpha": alpha,
        "partId": part_id_img,
        "albedo": albedo,
        "normal": normal,
        "linearDepth": depth_img,
        "materialDebug": mat_dbg,
        "wireframe": wire,
    }
    passes: dict[str, Any] = {}
    for name, image in images.items():
        path = out / f"{name}.png"
        write_png(path, image)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        passes[name] = {"path": str(path), "hash": digest}

    return {
        "viewId": view_id,
        "cameraProfileHash": cam.get("hash") or content_hash(cam),
        "passes": passes,
        "visibleParts": visible_parts,
        "width": width,
        "height": height,
    }


def render_blueprint_set(
    blueprint: dict[str, Any],
    *,
    out_dir: str | Path,
    revision_id: str,
    blueprint_hash: str,
    factory_hash: str,
    views: tuple[str, ...] = VIEW_PROFILE_IDS,
    width: int = 128,
    height: int = 128,
) -> dict[str, Any]:
    """Render all views/passes to disk and return a RenderSet with real paths/hashes."""

    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    light = light_profile()
    render_views = []
    visibility: dict[str, list[str]] = {}
    for view in views:
        # prefer blueprint renderProfiles camera when present
        cam = None
        for profile in blueprint.get("renderProfiles") or []:
            if profile.get("id") == view or profile.get("view") == view:
                cam = dict(profile.get("camera") or {})
                cam["id"] = view
                break
        if cam is None:
            cam = camera_profile(view)
        else:
            cam["hash"] = content_hash(cam, ignored_paths=(("hash",),))
        view_out = root / view
        result = render_view_passes(
            blueprint,
            view_id=view,
            out_dir=view_out,
            width=width,
            height=height,
            camera=cam,
        )
        visibility[view] = result["visibleParts"]
        render_views.append(
            {
                "id": view,
                "cameraProfileHash": result["cameraProfileHash"],
                "lightProfileHash": light["hash"],
                "passes": result["passes"],
            }
        )

    # ensure every required pass exists as a file
    for view in render_views:
        for pass_name in REQUIRED_PASSES:
            meta = view["passes"].get(pass_name)
            if not meta or not Path(meta["path"]).is_file():
                raise RuntimeError(f"missing render pass PNG {view['id']}/{pass_name}")

    render_set = {
        "schemaVersion": 1,
        "revisionId": revision_id,
        "blueprintHash": blueprint_hash,
        "factoryHash": factory_hash,
        "rendererVersion": "gpthreejs-software/0.2",
        "renderProfileHash": content_hash({"views": list(views), "light": light["hash"]}),
        "views": render_views,
        "requiredPasses": list(REQUIRED_PASSES),
        "visibility": visibility,
    }
    return render_set


def alpha_bbox(alpha_path: str | Path) -> dict[str, float]:
    img = read_png(alpha_path)
    minx, miny, maxx, maxy = img.width, img.height, -1, -1
    opaque = 0
    for y in range(img.height):
        for x in range(img.width):
            if img.pixel(x, y)[3] > 128:
                opaque += 1
                minx, miny = min(minx, x), min(miny, y)
                maxx, maxy = max(maxx, x), max(maxy, y)
    area = img.width * img.height
    if opaque == 0:
        return {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0, "occupancy": 0.0}
    return {
        "x": minx / img.width,
        "y": miny / img.height,
        "w": (maxx - minx + 1) / img.width,
        "h": (maxy - miny + 1) / img.height,
        "occupancy": opaque / area,
    }


def silhouette_iou(alpha_a: str | Path, alpha_b: str | Path) -> float:
    a = read_png(alpha_a)
    b = read_png(alpha_b)
    if a.width != b.width or a.height != b.height:
        raise ValueError("alpha dimensions must match for IoU")
    inter = union = 0
    for y in range(a.height):
        for x in range(a.width):
            ma = a.pixel(x, y)[3] > 128
            mb = b.pixel(x, y)[3] > 128
            if ma and mb:
                inter += 1
            if ma or mb:
                union += 1
    return inter / union if union else 0.0


def boundary_f_score(alpha_a: str | Path, alpha_b: str | Path) -> float:
    """Boundary agreement via edge-pixel precision/recall F1."""

    a = read_png(alpha_a)
    b = read_png(alpha_b)

    def edges(img: Image) -> set[tuple[int, int]]:
        pts: set[tuple[int, int]] = set()
        for y in range(img.height):
            for x in range(img.width):
                on = img.pixel(x, y)[3] > 128
                if not on:
                    continue
                for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if nx < 0 or ny < 0 or nx >= img.width or ny >= img.height or img.pixel(nx, ny)[3] <= 128:
                        pts.add((x, y))
                        break
        return pts

    ea, eb = edges(a), edges(b)
    if not ea and not eb:
        return 1.0
    if not ea or not eb:
        return 0.0
    inter = len(ea & eb)
    precision = inter / len(ea)
    recall = inter / len(eb)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def contour_mean_distance(alpha_a: str | Path, alpha_b: str | Path) -> float:
    """Normalized mean nearest-edge distance (0 = perfect)."""

    a = read_png(alpha_a)
    b = read_png(alpha_b)

    def edges(img: Image) -> list[tuple[int, int]]:
        pts = []
        for y in range(img.height):
            for x in range(img.width):
                on = img.pixel(x, y)[3] > 128
                if not on:
                    continue
                for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if nx < 0 or ny < 0 or nx >= img.width or ny >= img.height or img.pixel(nx, ny)[3] <= 128:
                        pts.append((x, y))
                        break
        return pts

    ea, eb = edges(a), edges(b)
    if not ea or not eb:
        return 1.0
    total = 0.0
    for x, y in ea:
        best = min((x - u) ** 2 + (y - v) ** 2 for u, v in eb)
        total += math.sqrt(best)
    mean = total / len(ea)
    diag = math.sqrt(a.width ** 2 + a.height ** 2)
    return min(1.0, mean / diag)


def part_id_visible_set(part_id_path: str | Path, known_part_ids: list[str]) -> list[str]:
    img = read_png(part_id_path)
    present_colors = set()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = img.pixel(x, y)
            if a > 128 and (r, g, b) != (0, 0, 0):
                present_colors.add((r, g, b))
    visible = []
    for pid in known_part_ids:
        if _part_color_id(pid) in present_colors:
            visible.append(pid)
    return visible


def reference_alpha_from_blueprint(
    blueprint: dict[str, Any],
    *,
    view_id: str,
    out_path: str | Path,
    width: int = 128,
    height: int = 128,
) -> str:
    """Render a stable reference alpha for the current blueprint (self-consistency baseline).

    For production fit, candidates are compared against the parent revision's alpha
    (caller supplies parent path). When no parent exists, this writes the baseline.
    """

    result = render_view_passes(
        blueprint,
        view_id=view_id,
        out_dir=Path(out_path).parent / f"_ref_{view_id}",
        width=width,
        height=height,
    )
    src = Path(result["passes"]["alpha"]["path"])
    dest = Path(out_path)
    dest.write_bytes(src.read_bytes())
    return str(dest)
