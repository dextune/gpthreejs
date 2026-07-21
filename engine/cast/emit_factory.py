"""Emit a TypeScript Three.js factory from a Form Blueprint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from engine.blueprint.migrate import blueprint_for_v1_cast
from engine.geometry.schema import UnsupportedGeometryError


def _ts_name(name: str) -> str:
    parts = "".join(c if c.isalnum() else " " for c in name).split()
    return "".join(p[:1].upper() + p[1:] for p in parts) or "Object"


def _geom_key(g: dict) -> str:
    return json.dumps(g or {"kind": "box", "size": [1, 1, 1]}, sort_keys=True, separators=(",", ":"))


def _js_num_list(values: list[Any]) -> str:
    return "[" + ", ".join(str(float(v)) for v in values) + "]"


def _geom_js(g: dict) -> str:
    """Emit real Three.js geometry constructors (named-arg helpers where multi-param)."""

    kind = g.get("kind", "box")
    if kind == "box":
        s = g.get("size", [1, 1, 1])
        return f"geomHelpers.box({{ size: {_js_num_list(s)} }})"
    if kind == "sphere":
        r = g.get("radius", 0.5)
        return f"geomHelpers.sphere({{ radius: {float(r)} }})"
    if kind == "ellipsoid":
        radii = g.get("radii", [0.5, 0.5, 0.5])
        return f"geomHelpers.ellipsoid({{ radii: {_js_num_list(radii)} }})"
    if kind == "cylinder":
        rt = g.get("radiusTop", 0.5)
        rb = g.get("radiusBottom", 0.5)
        h = g.get("height", 1)
        return (
            f"geomHelpers.cylinder({{ radiusTop: {float(rt)}, radiusBottom: {float(rb)}, "
            f"height: {float(h)} }})"
        )
    if kind == "cone":
        r = g.get("radius", 0.5)
        h = g.get("height", 1)
        return f"geomHelpers.cone({{ radius: {float(r)}, height: {float(h)} }})"
    if kind == "capsule":
        r = g.get("radius", 0.2)
        length = g.get("length", 0.8)
        return f"geomHelpers.capsule({{ radius: {float(r)}, length: {float(length)} }})"
    if kind == "torus":
        r = g.get("radius", 0.5)
        t = g.get("tube", 0.1)
        return f"geomHelpers.torus({{ radius: {float(r)}, tube: {float(t)} }})"
    if kind == "rounded-box":
        s = g.get("size", [1, 1, 1])
        radius = g.get("radius", 0.05)
        return (
            f"geomHelpers.roundedBox({{ size: {_js_num_list(s)}, radius: {float(radius)} }})"
        )
    if kind == "shape-extrude":
        shape = g.get("shape") or [[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]]
        depth = g.get("depth", 0.1)
        bevel = g.get("bevel", 0.0)
        pts = ", ".join(f"[{float(p[0])}, {float(p[1])}]" for p in shape)
        return (
            f"geomHelpers.shapeExtrude({{ shape: [{pts}], depth: {float(depth)}, "
            f"bevel: {float(bevel)} }})"
        )
    if kind == "lathe":
        profile = g.get("profile") or [[0.0, 0.0], [0.5, 1.0]]
        segments = int(g.get("segments", 24))
        pts = ", ".join(f"[{float(p[0])}, {float(p[1])}]" for p in profile)
        return f"geomHelpers.lathe({{ profile: [{pts}], segments: {segments} }})"
    if kind == "tube":
        path = g.get("path") or [[0, 0, 0], [0, 1, 0]]
        radius = g.get("radius", 0.05)
        tubular = int(g.get("tubularSegments", 32))
        pts = ", ".join(f"[{float(p[0])}, {float(p[1])}, {float(p[2])}]" for p in path)
        return (
            f"geomHelpers.tube({{ path: [{pts}], radius: {float(radius)}, "
            f"tubularSegments: {tubular} }})"
        )
    if kind == "beveled-plate":
        outline = g.get("outline") or [[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]]
        thickness = g.get("thickness", 0.05)
        bevel = g.get("bevel", 0.01)
        pts = ", ".join(f"[{float(p[0])}, {float(p[1])}]" for p in outline)
        return (
            f"geomHelpers.beveledPlate({{ outline: [{pts}], thickness: {float(thickness)}, "
            f"bevel: {float(bevel)} }})"
        )
    if kind == "curve-blade":
        length = g.get("length", 0.5)
        width = g.get("width", 0.08)
        curve = g.get("curve", 0.0)
        return (
            f"geomHelpers.curveBlade({{ length: {float(length)}, width: {float(width)}, "
            f"curve: {float(curve)} }})"
        )
    if kind == "feather":
        length = g.get("length", 0.2)
        width = g.get("width", 0.05)
        barb = int(g.get("barbCount", 5))
        return (
            f"geomHelpers.feather({{ length: {float(length)}, width: {float(width)}, "
            f"barbCount: {barb} }})"
        )
    if kind == "cloth-patch":
        width = g.get("width", 0.3)
        height = g.get("height", 0.4)
        drape = g.get("drape", 0.1)
        return (
            f"geomHelpers.clothPatch({{ width: {float(width)}, height: {float(height)}, "
            f"drape: {float(drape)} }})"
        )
    if kind == "instance-set":
        proto = g.get("prototype") or {"kind": "sphere", "radius": 0.01}
        count = int(g.get("count", 1))
        return f"geomHelpers.instanceSet({{ prototype: () => {_geom_js(proto)}, count: {count} }})"
    if kind == "shield":
        width = g.get("width", 0.55)
        height = g.get("height", 0.7)
        depth = g.get("depth", 0.08)
        return (
            f"geomHelpers.shield({{ width: {float(width)}, height: {float(height)}, "
            f"depth: {float(depth)} }})"
        )
    raise UnsupportedGeometryError(f"unsupported geometry kind {kind!r}")


def _geom_helpers_ts() -> str:
    """Named-object geometry helpers (DX-120): arg-shift becomes a type/runtime error surface."""

    return r'''
const geomHelpers = {
  box({ size }: { size: number[] }) {
    return new THREE.BoxGeometry(size[0], size[1], size[2]);
  },
  sphere({ radius }: { radius: number }) {
    return new THREE.SphereGeometry(radius, 32, 16);
  },
  ellipsoid({ radii }: { radii: number[] }) {
    const g = new THREE.SphereGeometry(1, 32, 16);
    g.scale(radii[0], radii[1], radii[2]);
    return g;
  },
  cylinder({ radiusTop, radiusBottom, height }: { radiusTop: number; radiusBottom: number; height: number }) {
    return new THREE.CylinderGeometry(radiusTop, radiusBottom, height, 24);
  },
  cone({ radius, height }: { radius: number; height: number }) {
    return new THREE.ConeGeometry(radius, height, 24);
  },
  capsule({ radius, length }: { radius: number; length: number }) {
    return new THREE.CapsuleGeometry(radius, length, 4, 8);
  },
  torus({ radius, tube }: { radius: number; tube: number }) {
    return new THREE.TorusGeometry(radius, tube, 12, 24);
  },
  roundedBox({ size, radius }: { size: number[]; radius: number }) {
    // Approximate rounded box with standard box; radius reserved for future BevelGeometry.
    void radius;
    return new THREE.BoxGeometry(size[0], size[1], size[2], 2, 2, 2);
  },
  shapeExtrude({ shape, depth, bevel = 0 }: { shape: number[][]; depth: number; bevel?: number }) {
    const s = new THREE.Shape();
    if (shape.length) {
      s.moveTo(shape[0][0], shape[0][1]);
      for (let i = 1; i < shape.length; i++) s.lineTo(shape[i][0], shape[i][1]);
      s.closePath();
    }
    return new THREE.ExtrudeGeometry(s, {
      depth,
      bevelEnabled: bevel > 0,
      bevelThickness: bevel,
      bevelSize: bevel,
      bevelSegments: 2,
    });
  },
  lathe({ profile, segments = 24 }: { profile: number[][]; segments?: number }) {
    const pts = profile.map((p) => new THREE.Vector2(Math.abs(p[0]), p[1]));
    return new THREE.LatheGeometry(pts, segments);
  },
  tube({ path, radius, tubularSegments = 32 }: { path: number[][]; radius: number; tubularSegments?: number }) {
    const curve = new THREE.CatmullRomCurve3(path.map((p) => new THREE.Vector3(p[0], p[1], p[2])));
    return new THREE.TubeGeometry(curve, tubularSegments, radius, 8, false);
  },
  beveledPlate({ outline, thickness, bevel }: { outline: number[][]; thickness: number; bevel: number }) {
    return geomHelpers.shapeExtrude({ shape: outline, depth: thickness, bevel });
  },
  curveBlade({ length, width, curve }: { length: number; width: number; curve: number }) {
    const shape = new THREE.Shape();
    shape.moveTo(-width / 2, 0);
    shape.quadraticCurveTo(curve, length * 0.5, 0, length);
    shape.quadraticCurveTo(-curve, length * 0.5, width / 2, 0);
    shape.lineTo(-width / 2, 0);
    return new THREE.ExtrudeGeometry(shape, { depth: 0.02, bevelEnabled: false });
  },
  feather({ length, width, barbCount }: { length: number; width: number; barbCount: number }) {
    void barbCount;
    return new THREE.ConeGeometry(width / 2, length, 8);
  },
  clothPatch({ width, height, drape }: { width: number; height: number; drape: number }) {
    const g = new THREE.PlaneGeometry(width, height, 6, 6);
    const pos = g.attributes.position as THREE.BufferAttribute;
    for (let i = 0; i < pos.count; i++) {
      const y = pos.getY(i);
      const x = pos.getX(i);
      pos.setZ(i, Math.sin((y / Math.max(height, 1e-6)) * Math.PI) * drape * 0.5 + x * 0.01);
    }
    pos.needsUpdate = true;
    g.computeVertexNormals();
    return g;
  },
  instanceSet({ prototype, count }: { prototype: () => THREE.BufferGeometry; count: number }) {
    void count;
    return prototype();
  },
  shield({ width, height, depth }: { width: number; height: number; depth: number }) {
    const shape: number[][] = [
      [-width / 2, height / 2],
      [width / 2, height / 2],
      [width / 2, -height / 4],
      [0, -height / 2],
      [-width / 2, -height / 4],
    ];
    return geomHelpers.shapeExtrude({ shape, depth, bevel: 0.01 });
  },
};
'''


def _emit_part(materials_map: str, p: dict, parent_expr: str, indent: int = 2) -> str:
    """Emit mesh and parent it under parent_expr (group or another mesh)."""
    pad = " " * indent
    pid = p["id"]
    safe = "".join(c if c.isalnum() else "_" for c in pid)
    t = p.get("transform") or {}
    pos = t.get("position") or t.get("translation") or [0, 0, 0]
    rot = t.get("rotation") or [0, 0, 0]
    scl = t.get("scale") or [1, 1, 1]
    mid = p.get("materialId", "mat_primary")
    lines = [
        f"{pad}{{",
        f"{pad}  const g_{safe} = getGeometry({json.dumps(_geom_key(p.get('geometry') or {}))}, () => {_geom_js(p.get('geometry') or {})});",
        f"{pad}  const m_{safe} = {materials_map}[{json.dumps(mid)}] ?? {materials_map}[Object.keys({materials_map})[0]];",
        f"{pad}  const mesh_{safe} = new THREE.Mesh(g_{safe}, m_{safe});",
        f"{pad}  mesh_{safe}.name = {json.dumps(pid)};",
        f"{pad}  mesh_{safe}.position.set({pos[0]}, {pos[1]}, {pos[2]});",
        f"{pad}  mesh_{safe}.rotation.set({rot[0]}, {rot[1]}, {rot[2]});",
        f"{pad}  mesh_{safe}.scale.set({scl[0]}, {scl[1]}, {scl[2]});",
        f"{pad}  mesh_{safe}.castShadow = true;",
        f"{pad}  mesh_{safe}.receiveShadow = true;",
        f"{pad}  owned.geometries.add(g_{safe});",
        f"{pad}  {parent_expr}.add(mesh_{safe});",
        f"{pad}  nodes[{json.dumps(pid)}] = mesh_{safe}];",
    ]
    # fix typo - nodes assignment
    lines[-1] = f"{pad}  nodes[{json.dumps(pid)}] = mesh_{safe};"
    for ch in p.get("children") or []:
        lines.append(_emit_part(materials_map, ch, f"mesh_{safe}", indent + 2))
    lines.append(f"{pad}}}")
    return "\n".join(lines)


def emit_factory(blueprint: dict[str, Any], out_path: str | Path) -> str:
    blueprint = blueprint_for_v1_cast(blueprint)
    name = _ts_name(blueprint.get("name") or "Form")
    seed = blueprint.get("seed", 42)
    mats = blueprint.get("materials") or []
    mat_entries = []
    for m in mats:
        channels = m.get("channels") or {}
        col = m.get("baseColor") or channels.get("baseColor", "#888888")
        rough = m.get("roughness", channels.get("roughness", 0.5))
        metal = m.get("metalness", channels.get("metalness", 0.0))
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
        _emit_part("materialRegistry", p, "group") for p in blueprint.get("parts") or []
    )

    handles = blueprint.get("handles") or {}
    handles_json = json.dumps(handles, indent=2)
    helpers = _geom_helpers_ts()

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

/** Plan FormRuntime contract (RES-101 / DX-120). */
export interface FormRuntime {{
  group: THREE.Group;
  nodes: Record<string, THREE.Object3D>;
  handles: Record<string, unknown>;
  dispose(): void;
}}

{helpers}

export function create{name}Form(
  blueprint: FormBlueprint = {{}},
  options: Create{name}FormOptions = {{}},
): FormRuntime {{
  const seed = options.seed ?? {seed};
  void seed;
  void blueprint;

  const group = new THREE.Group();
  group.name = {json.dumps(blueprint.get("name") or name)};

  const materialRegistry: Record<string, THREE.Material> = {{
{mat_block}
  }};

  if (options.wireframe) {{
    for (const m of Object.values(materialRegistry)) {{
      if ("wireframe" in m) (m as THREE.MeshStandardMaterial).wireframe = true;
    }}
  }}

  const geometryRegistry = new Map<string, THREE.BufferGeometry>();
  const owned = {{
    geometries: new Set<THREE.BufferGeometry>(),
    materials: new Set<THREE.Material>(Object.values(materialRegistry)),
    textures: new Set<THREE.Texture>(),
    disposed: false,
  }};

  const getGeometry = (key: string, create: () => THREE.BufferGeometry): THREE.BufferGeometry => {{
    let geometry = geometryRegistry.get(key);
    if (!geometry) {{
      geometry = create();
      geometryRegistry.set(key, geometry);
      owned.geometries.add(geometry);
    }}
    return geometry;
  }};

  const nodes: Record<string, THREE.Object3D> = {{}};

{parts_code}

  const handles = {{
    nodes,
    ...({handles_json} as object),
    blueprintName: {json.dumps(blueprint.get("name"))},
    bodySource: {json.dumps(blueprint.get("bodySource", "procedural"))},
  }};

  group.userData.formHandles = handles;

  const dispose = () => {{
    if (owned.disposed) return;
    owned.disposed = true;
    for (const g of owned.geometries) g.dispose();
    for (const m of owned.materials) m.dispose();
    for (const t of owned.textures) t.dispose();
    owned.geometries.clear();
    owned.materials.clear();
    owned.textures.clear();
    geometryRegistry.clear();
    group.clear();
  }};

  return {{ group, nodes, handles, dispose }};
}}

/** Legacy wrapper: returns the THREE.Group only. */
export function create{name}Group(
  blueprint: FormBlueprint = {{}},
  options: Create{name}FormOptions = {{}},
): THREE.Group {{
  return create{name}Form(blueprint, options).group;
}}

export default create{name}Form;
'''
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return str(path)
