/**
 * gpthreejs knight factory — uses generic surfaceKit for micro/meso detail.
 * Geometry is character-specific; materials/rivets/trims are domain-agnostic.
 */
import * as THREE from "three";
import {
  createSurfaceLibrary,
  detailLevelFromQualityMode,
  type DetailLevel,
  type SurfaceLibrary,
} from "./detail/surfaceKit";

export type FormBlueprint = Record<string, unknown>;

export interface CreateKnightFormOptions {
  seed?: number;
  wireframe?: boolean;
  /** Override surface detail (default from qualityMode or "high"). */
  detailLevel?: DetailLevel;
  qualityMode?: string;
}

function mesh(
  geo: THREE.BufferGeometry,
  material: THREE.Material,
  name: string,
  parent: THREE.Object3D,
  nodes: Record<string, THREE.Object3D>,
  pos: [number, number, number] = [0, 0, 0],
  rot: [number, number, number] = [0, 0, 0],
  scl: [number, number, number] = [1, 1, 1],
): THREE.Mesh {
  const m = new THREE.Mesh(geo, material);
  m.name = name;
  m.position.set(...pos);
  m.rotation.set(...rot);
  m.scale.set(...scl);
  m.castShadow = true;
  m.receiveShadow = true;
  // aoMap needs uv2
  if ((material as THREE.MeshPhysicalMaterial).aoMap) {
    const g = m.geometry;
    if (!g.attributes.uv2 && g.attributes.uv) {
      g.setAttribute("uv2", g.attributes.uv);
    }
  }
  parent.add(m);
  nodes[name] = m;
  return m;
}

function grp(
  name: string,
  parent: THREE.Object3D,
  nodes: Record<string, THREE.Object3D>,
  pos: [number, number, number] = [0, 0, 0],
): THREE.Group {
  const g = new THREE.Group();
  g.name = name;
  g.position.set(...pos);
  parent.add(g);
  nodes[name] = g;
  return g;
}

export function createKnightForm(
  blueprint: FormBlueprint = {},
  options: CreateKnightFormOptions = {},
): THREE.Group {
  const seed = options.seed ?? Number(blueprint.seed ?? 42);
  const detailLevel =
    options.detailLevel ??
    detailLevelFromQualityMode(
      options.qualityMode ?? String(blueprint.qualityMode ?? "sharp"),
    );

  const surfaces: SurfaceLibrary = createSurfaceLibrary({ detailLevel, seed });
  const root = new THREE.Group();
  root.name = "Knight";
  const nodes: Record<string, THREE.Object3D> = {};

  const steel = surfaces.physical("metal", {
    color: "#7a8fa3",
    metalness: 0.92,
    roughness: 0.32,
    clearcoat: 0.35,
    wireframe: options.wireframe,
  });
  const steelDark = surfaces.physical("metal", {
    color: "#4e5d6c",
    metalness: 0.9,
    roughness: 0.42,
    clearcoat: 0.2,
    wireframe: options.wireframe,
  });
  const brass = surfaces.physical("brass", {
    color: "#c9a14a",
    wireframe: options.wireframe,
  });
  const crimson = surfaces.physical("cloth", {
    color: "#9a1f2e",
    roughness: 0.74,
    sheen: 0.2,
    wireframe: options.wireframe,
  });
  const crimsonDark = surfaces.physical("cloth", {
    color: "#6b1520",
    roughness: 0.8,
    wireframe: options.wireframe,
  });
  const white = surfaces.physical("painted_metal", {
    color: "#f0ebe3",
    metalness: 0.05,
    roughness: 0.55,
    wireframe: options.wireframe,
  });
  const leather = surfaces.physical("leather", {
    color: "#3d2a22",
    wireframe: options.wireframe,
  });
  const leatherLight = surfaces.physical("leather", {
    color: "#5c4033",
    wireframe: options.wireframe,
  });
  const black = surfaces.physical("default", {
    color: "#121418",
    metalness: 0.35,
    roughness: 0.55,
    wireframe: options.wireframe,
  });
  const chain = surfaces.physical("metal", {
    color: "#6a7380",
    metalness: 0.85,
    roughness: 0.55,
    wireframe: options.wireframe,
  });

  // ─── Body ───
  const hips = grp("hips", root, nodes, [0, 1.02, 0]);
  mesh(new THREE.BoxGeometry(0.34, 0.14, 0.22), steel, "pelvis", hips, nodes, [0, -0.02, 0]);
  mesh(new THREE.BoxGeometry(0.38, 0.1, 0.24), steelDark, "fauld", hips, nodes, [0, -0.1, 0.01]);
  mesh(new THREE.BoxGeometry(0.14, 0.18, 0.08), steel, "tasset_l", hips, nodes, [-0.16, -0.18, 0.04], [0.15, 0, 0.1]);
  mesh(new THREE.BoxGeometry(0.14, 0.18, 0.08), steel, "tasset_r", hips, nodes, [0.16, -0.18, 0.04], [0.15, 0, -0.1]);
  mesh(new THREE.TorusGeometry(0.17, 0.018, 8, 24), leather, "belt", hips, nodes, [0, -0.08, 0], [Math.PI / 2, 0, 0]);
  mesh(new THREE.BoxGeometry(0.06, 0.05, 0.03), brass, "belt_buckle", hips, nodes, [0, -0.08, 0.17]);
  mesh(new THREE.BoxGeometry(0.1, 0.1, 0.06), leatherLight, "pouch", hips, nodes, [-0.2, -0.12, 0.08], [0, 0.3, 0]);
  surfaces.rivetRing(hips, { radius: 0.16, y: -0.02, count: 10, size: 0.01, material: brass, name: "pelvis_rivets" });

  const torso = grp("torso", hips, nodes, [0, 0.28, 0]);
  mesh(new THREE.BoxGeometry(0.4, 0.48, 0.26, 2, 2, 2), steel, "breastplate", torso, nodes, [0, 0.06, 0.02]);
  mesh(new THREE.SphereGeometry(0.14, 20, 14), steel, "chest_dome", torso, nodes, [0, 0.1, 0.12], [0, 0, 0], [1.35, 1.1, 0.55]);
  mesh(new THREE.BoxGeometry(0.38, 0.46, 0.1), steelDark, "backplate", torso, nodes, [0, 0.05, -0.12]);

  // Generic edge bands (meso)
  surfaces.edgeBand(torso, { material: brass, size: [0.42, 0.025, 0.28], position: [0, 0.3, 0.02], name: "trim_top" });
  surfaces.edgeBand(torso, { material: brass, size: [0.42, 0.02, 0.28], position: [0, -0.16, 0.02], name: "trim_waist" });
  surfaces.edgeBand(torso, { material: brass, size: [0.03, 0.46, 0.28], position: [-0.2, 0.05, 0.02], name: "trim_side_l" });
  surfaces.edgeBand(torso, { material: brass, size: [0.03, 0.46, 0.28], position: [0.2, 0.05, 0.02], name: "trim_side_r" });
  surfaces.rivetRing(torso, { radius: 0.18, y: 0.28, count: 12, size: 0.011, material: brass, name: "cuirass_rivets" });
  surfaces.rivetGrid(torso, {
    width: 0.28,
    height: 0.32,
    cols: 3,
    rows: 4,
    z: 0.16,
    size: 0.009,
    material: brass,
    name: "chest_rivets",
  });

  mesh(new THREE.CylinderGeometry(0.11, 0.16, 0.12, 20), steel, "gorget", torso, nodes, [0, 0.34, 0.02]);
  surfaces.edgeBand(torso, {
    kind: "torus",
    material: brass,
    radius: 0.12,
    tube: 0.012,
    position: [0, 0.38, 0.02],
    rotation: [Math.PI / 2, 0, 0],
    name: "gorget_ring",
  });

  // Tabard + cross
  const tabard = grp("tabard", torso, nodes, [0, -0.02, 0.02]);
  mesh(new THREE.BoxGeometry(0.36, 0.52, 0.06), crimson, "tabard_body", tabard, nodes, [0, -0.02, 0.14]);
  mesh(new THREE.BoxGeometry(0.16, 0.28, 0.05), crimsonDark, "tabard_flap_l", tabard, nodes, [-0.1, -0.32, 0.12], [0.08, 0, 0]);
  mesh(new THREE.BoxGeometry(0.16, 0.28, 0.05), crimsonDark, "tabard_flap_r", tabard, nodes, [0.1, -0.32, 0.12], [0.08, 0, 0]);
  mesh(new THREE.BoxGeometry(0.045, 0.2, 0.02), white, "cross_v", tabard, nodes, [0, 0.06, 0.18]);
  mesh(new THREE.BoxGeometry(0.14, 0.045, 0.02), white, "cross_h", tabard, nodes, [0, 0.1, 0.18]);
  mesh(new THREE.BoxGeometry(0.02, 0.07, 0.015), white, "cross_fl_v", tabard, nodes, [-0.1, -0.28, 0.15]);
  mesh(new THREE.BoxGeometry(0.055, 0.02, 0.015), white, "cross_fl_h", tabard, nodes, [-0.1, -0.26, 0.15]);
  mesh(new THREE.BoxGeometry(0.02, 0.07, 0.015), white, "cross_fr_v", tabard, nodes, [0.1, -0.28, 0.15]);
  mesh(new THREE.BoxGeometry(0.055, 0.02, 0.015), white, "cross_fr_h", tabard, nodes, [0.1, -0.26, 0.15]);

  mesh(new THREE.BoxGeometry(0.04, 0.42, 0.02), leather, "strap_l", torso, nodes, [-0.12, 0.02, 0.16], [0, 0, 0.12]);
  mesh(new THREE.BoxGeometry(0.04, 0.42, 0.02), leather, "strap_r", torso, nodes, [0.12, 0.02, 0.16], [0, 0, -0.12]);

  // Cape
  const cape = grp("cape", torso, nodes, [0, 0.28, -0.12]);
  mesh(new THREE.BoxGeometry(0.55, 0.2, 0.08), crimson, "cape_yoke", cape, nodes, [0, 0, -0.02], [0.2, 0, 0]);
  mesh(new THREE.BoxGeometry(0.58, 0.55, 0.05), crimsonDark, "cape_body", cape, nodes, [0, -0.32, -0.08], [0.25, 0, 0]);
  mesh(new THREE.BoxGeometry(0.2, 0.5, 0.04), crimson, "cape_fold_l", cape, nodes, [-0.22, -0.28, -0.04], [0.2, 0.15, 0.1]);
  mesh(new THREE.BoxGeometry(0.2, 0.5, 0.04), crimson, "cape_fold_r", cape, nodes, [0.22, -0.28, -0.04], [0.2, -0.15, -0.1]);
  mesh(new THREE.BoxGeometry(0.025, 0.09, 0.015), white, "cape_cross_v", cape, nodes, [-0.22, -0.05, 0.02]);
  mesh(new THREE.BoxGeometry(0.07, 0.025, 0.015), white, "cape_cross_h", cape, nodes, [-0.22, -0.02, 0.02]);

  // Pauldrons
  for (const side of ["l", "r"] as const) {
    const s = side === "l" ? -1 : 1;
    const p = grp(`pauldron_${side}`, torso, nodes, [s * 0.28, 0.22, 0]);
    mesh(new THREE.SphereGeometry(0.13, 18, 14), steel, `pauldron_${side}_dome`, p, nodes, [0, 0, 0], [0, 0, 0], [1.15, 0.75, 1]);
    mesh(new THREE.BoxGeometry(0.16, 0.08, 0.18), steelDark, `pauldron_${side}_lame`, p, nodes, [s * 0.02, -0.08, 0.02]);
    surfaces.edgeBand(p, {
      kind: "torus",
      material: brass,
      radius: 0.1,
      tube: 0.012,
      position: [0, 0.02, 0],
      rotation: [Math.PI / 2, 0, 0.2 * s],
      name: `pauldron_${side}_rim`,
    });
    surfaces.rivetRing(p, { radius: 0.09, y: 0.02, count: 8, size: 0.009, material: brass, name: `pauldron_${side}_rivets` });
  }

  // Helmet
  const neck = grp("neck", torso, nodes, [0, 0.42, 0.02]);
  mesh(new THREE.CylinderGeometry(0.07, 0.08, 0.1, 14), chain, "neck_pad", neck, nodes, [0, 0, 0]);
  const head = grp("head", neck, nodes, [0, 0.16, 0.02]);
  mesh(new THREE.SphereGeometry(0.15, 28, 20), steel, "helm_bowl", head, nodes, [0, 0.04, 0], [0, 0, 0], [1.05, 1.1, 1.15]);
  mesh(new THREE.SphereGeometry(0.1, 16, 12), steelDark, "helm_tail", head, nodes, [0, -0.02, -0.1], [0.4, 0, 0], [1.1, 0.7, 1]);
  mesh(new THREE.BoxGeometry(0.18, 0.16, 0.1), steel, "visor_plate", head, nodes, [0, 0, 0.11]);
  surfaces.edgeBand(head, {
    kind: "torus",
    material: brass,
    radius: 0.11,
    tube: 0.014,
    position: [0, 0.06, 0.08],
    rotation: [0.2, 0, 0],
    name: "helm_brow",
  });
  surfaces.edgeBand(head, {
    kind: "torus",
    material: brass,
    radius: 0.1,
    tube: 0.012,
    position: [0, -0.08, 0.02],
    rotation: [Math.PI / 2, 0, 0],
    name: "helm_neck_rim",
  });
  const holeGeo = new THREE.BoxGeometry(0.016, 0.016, 0.02);
  for (let row = 0; row < 3; row++) {
    for (let col = 0; col < 4; col++) {
      mesh(holeGeo, black, `breath_${row}_${col}`, head, nodes, [(col - 1.5) * 0.028, 0.02 - row * 0.028, 0.16]);
    }
  }
  mesh(new THREE.BoxGeometry(0.14, 0.018, 0.03), black, "visor_slit", head, nodes, [0, 0.055, 0.155]);
  mesh(new THREE.BoxGeometry(0.03, 0.06, 0.22), brass, "helm_crest", head, nodes, [0, 0.14, -0.02], [0.15, 0, 0]);
  surfaces.rivetRing(head, { radius: 0.12, y: 0.02, count: 10, size: 0.008, material: brass, name: "helm_rivets" });

  // Arms
  for (const side of ["l", "r"] as const) {
    const s = side === "l" ? -1 : 1;
    const shoulder = grp(`upper_arm_${side}`, torso, nodes, [s * 0.3, 0.12, 0]);
    mesh(new THREE.CapsuleGeometry(0.065, 0.22, 6, 12), steel, `ua_${side}`, shoulder, nodes, [0, -0.14, 0], [0, 0, s * 0.12]);
    mesh(new THREE.SphereGeometry(0.06, 12, 10), steelDark, `elbow_${side}`, shoulder, nodes, [0, -0.28, 0.01]);
    surfaces.edgeBand(shoulder, {
      kind: "torus",
      material: brass,
      radius: 0.055,
      tube: 0.01,
      position: [0, -0.28, 0.01],
      rotation: [Math.PI / 2, 0, 0],
      name: `elbow_rim_${side}`,
    });
    const forearm = grp(`forearm_${side}`, shoulder, nodes, [0, -0.42, 0.02]);
    mesh(new THREE.CapsuleGeometry(0.055, 0.2, 6, 12), steel, `fa_${side}`, forearm, nodes, [0, -0.02, 0]);
    mesh(new THREE.BoxGeometry(0.09, 0.16, 0.08), steelDark, `vambrace_${side}`, forearm, nodes, [0, -0.02, 0.02]);
    surfaces.edgeBand(forearm, {
      material: brass,
      size: [0.1, 0.02, 0.09],
      position: [0, -0.12, 0.01],
      name: `wrist_trim_${side}`,
    });
    const hand = grp(`hand_${side}`, forearm, nodes, [0, -0.18, 0.01]);
    mesh(new THREE.BoxGeometry(0.08, 0.1, 0.05), leather, `gauntlet_${side}`, hand, nodes, [0, 0, 0]);
    mesh(new THREE.BoxGeometry(0.075, 0.06, 0.04), leatherLight, `fingers_${side}`, hand, nodes, [0, -0.07, 0.01], [0.2, 0, 0]);
    for (let i = 0; i < 4; i++) {
      mesh(new THREE.SphereGeometry(0.012, 6, 6), brass, `knuckle_${side}_${i}`, hand, nodes, [(i - 1.5) * 0.018, -0.03, 0.03]);
    }
  }

  // Legs
  for (const side of ["l", "r"] as const) {
    const s = side === "l" ? -1 : 1;
    const thigh = grp(`thigh_${side}`, hips, nodes, [s * 0.11, -0.22, 0]);
    mesh(new THREE.CapsuleGeometry(0.085, 0.28, 6, 12), steel, `th_${side}`, thigh, nodes, [0, -0.12, 0]);
    mesh(new THREE.BoxGeometry(0.14, 0.2, 0.12), steelDark, `cuisse_${side}`, thigh, nodes, [0, -0.1, 0.02]);
    mesh(new THREE.SphereGeometry(0.075, 14, 12), steel, `knee_${side}`, thigh, nodes, [0, -0.3, 0.03]);
    mesh(new THREE.BoxGeometry(0.1, 0.08, 0.06), brass, `knee_cop_${side}`, thigh, nodes, [0, -0.3, 0.08]);
    const shin = grp(`shin_${side}`, thigh, nodes, [0, -0.48, 0.01]);
    mesh(new THREE.CapsuleGeometry(0.07, 0.28, 6, 12), steel, `sh_${side}`, shin, nodes, [0, -0.08, 0]);
    mesh(new THREE.BoxGeometry(0.12, 0.26, 0.1), steelDark, `greave_${side}`, shin, nodes, [0, -0.06, 0.02]);
    surfaces.edgeBand(shin, {
      material: brass,
      size: [0.13, 0.02, 0.11],
      position: [0, 0.06, 0.02],
      name: `greave_trim_${side}`,
    });
    surfaces.rivetGrid(shin, {
      width: 0.08,
      height: 0.16,
      cols: 2,
      rows: 3,
      z: 0.06,
      size: 0.008,
      material: brass,
      name: `greave_rivets_${side}`,
    });
    const foot = grp(`foot_${side}`, shin, nodes, [0, -0.28, 0.04]);
    mesh(new THREE.BoxGeometry(0.11, 0.07, 0.18), steel, `sabaton_${side}`, foot, nodes, [0, 0, 0.02]);
    mesh(new THREE.ConeGeometry(0.05, 0.12, 8), steelDark, `toe_${side}`, foot, nodes, [0, -0.01, 0.14], [Math.PI / 2, 0, 0]);
    surfaces.edgeBand(foot, {
      material: brass,
      size: [0.12, 0.02, 0.08],
      position: [0, 0.035, 0],
      name: `sabaton_trim_${side}`,
    });
  }

  // Sword + scabbard
  const weapon = grp("weapon_hip", hips, nodes, [-0.22, -0.05, -0.05]);
  weapon.rotation.set(0.15, 0.4, 0.55);
  mesh(new THREE.BoxGeometry(0.05, 0.72, 0.05), leather, "scabbard", weapon, nodes, [0, -0.15, 0]);
  mesh(new THREE.BoxGeometry(0.06, 0.04, 0.06), brass, "scabbard_mouth", weapon, nodes, [0, 0.22, 0]);
  mesh(new THREE.BoxGeometry(0.04, 0.08, 0.04), brass, "scabbard_chape", weapon, nodes, [0, -0.52, 0]);
  mesh(new THREE.CylinderGeometry(0.018, 0.02, 0.14, 10), leatherLight, "grip", weapon, nodes, [0, 0.32, 0]);
  mesh(new THREE.BoxGeometry(0.18, 0.025, 0.035), brass, "guard", weapon, nodes, [0, 0.24, 0]);
  mesh(new THREE.SphereGeometry(0.028, 10, 8), brass, "pommel", weapon, nodes, [0, 0.4, 0]);
  mesh(new THREE.BoxGeometry(0.025, 0.12, 0.01), steel, "blade_tip", weapon, nodes, [0, -0.58, 0]);

  const handR = nodes["hand_r"];
  if (handR) {
    const swordR = grp("sword_r", handR, nodes, [0.02, -0.05, 0.08]);
    swordR.rotation.set(0.2, 0, 0.3);
    mesh(new THREE.BoxGeometry(0.03, 0.75, 0.012), steel, "blade_r", swordR, nodes, [0, -0.25, 0]);
    mesh(new THREE.BoxGeometry(0.16, 0.025, 0.03), brass, "guard_r", swordR, nodes, [0, 0.12, 0]);
    mesh(new THREE.CylinderGeometry(0.016, 0.018, 0.12, 8), leather, "grip_r", swordR, nodes, [0, 0.2, 0]);
    mesh(new THREE.SphereGeometry(0.025, 8, 8), brass, "pommel_r", swordR, nodes, [0, 0.28, 0]);
  }

  root.userData.formHandles = {
    nodes,
    pivots: [
      { id: "hips", part: "hips", local: [0, 0, 0] },
      { id: "spine", part: "torso", local: [0, 0, 0] },
      { id: "head", part: "head", local: [0, 0, 0] },
      { id: "leftHand", part: "hand_l", local: [0, 0, 0] },
      { id: "rightHand", part: "hand_r", local: [0, 0, 0] },
    ],
    sockets: [
      { id: "weapon_r", part: "hand_r", local: [0, 0, 0] },
      { id: "weapon_hip", part: "weapon_hip", local: [0, 0, 0] },
    ],
    colliders: [
      { id: "body", part: "torso", kind: "capsule" },
      { id: "feet", part: "hips", kind: "box" },
    ],
    breakGroups: [],
    blueprintName: "Knight",
    bodySource: "procedural",
    detailLevel,
    surfaceLibrary: true,
  };
  root.userData.surfaceLibrary = surfaces;

  return root;
}

export default createKnightForm;
