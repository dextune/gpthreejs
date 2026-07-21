"""Emit a TypeScript Three.js factory from a Form Blueprint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _ts_name(name: str) -> str:
    parts = "".join(c if c.isalnum() else " " for c in name).split()
    return "".join(p[:1].upper() + p[1:] for p in parts) or "Object"


def _geom_js(g: dict) -> str:
    kind = g.get("kind", "box")
    if kind == "box":
        s = g.get("size", [1, 1, 1])
        return f"new THREE.BoxGeometry({s[0]}, {s[1]}, {s[2]})"
    if kind == "sphere":
        r = g.get("radius", 0.5)
        return f"new THREE.SphereGeometry({r}, 32, 16)"
    if kind == "cylinder":
        rt = g.get("radiusTop", 0.5)
        rb = g.get("radiusBottom", 0.5)
        h = g.get("height", 1)
        return f"new THREE.CylinderGeometry({rt}, {rb}, {h}, 24)"
    if kind == "capsule":
        r = g.get("radius", 0.2)
        l = g.get("length", 0.8)
        return f"new THREE.CapsuleGeometry({r}, {l}, 4, 8)"
    if kind == "torus":
        r = g.get("radius", 0.5)
        t = g.get("tube", 0.1)
        return f"new THREE.TorusGeometry({r}, {t}, 12, 24)"
    s = g.get("size", [1, 1, 1])
    return f"new THREE.BoxGeometry({s[0]}, {s[1]}, {s[2]})"


def _emit_part(p: dict, materials_map: str, parent_expr: str, indent: int = 2) -> str:
    """Emit mesh and parent it under parent_expr (group or another mesh)."""
    pad = " " * indent
    pid = p["id"]
    safe = "".join(c if c.isalnum() else "_" for c in pid)
    t = p.get("transform") or {}
    pos = t.get("position") or [0, 0, 0]
    rot = t.get("rotation") or [0, 0, 0]
    scl = t.get("scale") or [1, 1, 1]
    mid = p.get("materialId", "mat_primary")
    lines = [
        f"{pad}{{",
        f"{pad}  const g_{safe} = {_geom_js(p.get('geometry') or {})};",
        f"{pad}  const m_{safe} = {materials_map}[{json.dumps(mid)}] ?? {materials_map}[Object.keys({materials_map})[0]];",
        f"{pad}  const mesh_{safe} = new THREE.Mesh(g_{safe}, m_{safe}.clone());",
        f"{pad}  mesh_{safe}.name = {json.dumps(pid)};",
        f"{pad}  mesh_{safe}.position.set({pos[0]}, {pos[1]}, {pos[2]});",
        f"{pad}  mesh_{safe}.rotation.set({rot[0]}, {rot[1]}, {rot[2]});",
        f"{pad}  mesh_{safe}.scale.set({scl[0]}, {scl[1]}, {scl[2]});",
        f"{pad}  mesh_{safe}.castShadow = true;",
        f"{pad}  mesh_{safe}.receiveShadow = true;",
        f"{pad}  {parent_expr}.add(mesh_{safe});",
        f"{pad}  nodes[{json.dumps(pid)}] = mesh_{safe};",
    ]
    for ch in p.get("children") or []:
        lines.append(_emit_part(ch, materials_map, f"mesh_{safe}", indent + 2))
    lines.append(f"{pad}}}")
    return "\n".join(lines)


def emit_factory(blueprint: dict[str, Any], out_path: str | Path) -> str:
    name = _ts_name(blueprint.get("name") or "Form")
    seed = blueprint.get("seed", 42)
    mats = blueprint.get("materials") or []
    mat_entries = []
    for m in mats:
        col = m.get("baseColor", "#888888")
        rough = m.get("roughness", 0.5)
        metal = m.get("metalness", 0.0)
        mat_entries.append(
            f"  {json.dumps(m['id'])}: new THREE.MeshPhysicalMaterial({{"
            f" color: {json.dumps(col)}, roughness: {rough}, metalness: {metal},"
            f" clearcoat: {m.get('clearcoat', 0.0)} }})"
        )
    mat_block = (
        ",\n".join(mat_entries)
        if mat_entries
        else '  "default": new THREE.MeshStandardMaterial({ color: 0x888888 })'
    )

    parts_code = "\n".join(
        _emit_part(p, "materials", "group") for p in blueprint.get("parts") or []
    )

    handles = blueprint.get("handles") or {}
    handles_json = json.dumps(handles, indent=2)

    body = f'''/**
 * gpthreejs factory — emitted from a Form Blueprint.
 * bodySource: {blueprint.get("bodySource", "procedural")}
 * qualityMode: {blueprint.get("qualityMode", "sharp")}
 * Keep bodySource truthful if you swap in an external mesh shell.
 */
import * as THREE from "three";

export type FormBlueprint = Record<string, unknown>;

export interface Create{name}FormOptions {{
  seed?: number;
  wireframe?: boolean;
}}

export function create{name}Form(
  blueprint: FormBlueprint = {{}},
  options: Create{name}FormOptions = {{}},
): THREE.Group {{
  const seed = options.seed ?? {seed};
  void seed;

  const group = new THREE.Group();
  group.name = {json.dumps(blueprint.get("name") or name)};

  const materials: Record<string, THREE.MeshPhysicalMaterial> = {{
{mat_block}
  }};

  if (options.wireframe) {{
    for (const m of Object.values(materials)) {{
      m.wireframe = true;
    }}
  }}

  const nodes: Record<string, THREE.Object3D> = {{}};

{parts_code}

  group.userData.formHandles = {{
    nodes,
    ...({handles_json} as object),
    blueprintName: {json.dumps(blueprint.get("name"))},
    bodySource: {json.dumps(blueprint.get("bodySource", "procedural"))},
  }};

  return group;
}}

export default create{name}Form;
'''
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return str(path)
