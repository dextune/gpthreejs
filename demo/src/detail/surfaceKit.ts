/**
 * gpthreejs surfaceKit — domain-agnostic micro/meso detail for Three.js.
 *
 * Use for any prop/character:
 *   const lib = createSurfaceLibrary({ detailLevel: "high", seed: 42 });
 *   const steel = lib.physical("metal", { color: "#7a8fa3", metalness: 0.9 });
 *   lib.rivetRing(parent, { radius: 0.2, count: 12, material: brass });
 */
import * as THREE from "three";
import surfacePresetData from "./surfacePresets";

export type DetailLevel = "low" | "medium" | "high" | "ultra";

export type SurfaceRole =
  | "metal"
  | "painted_metal"
  | "brass"
  | "cloth"
  | "leather"
  | "rubber"
  | "plastic"
  | "wood"
  | "stone"
  | "skin"
  | "emissive"
  | "default";

export interface SurfaceLibraryOptions {
  detailLevel?: DetailLevel;
  seed?: number;
  /** Canvas map resolution (power-of-two friendly). */
  resolution?: number;
}

export interface PhysicalOpts {
  color: string | number;
  roughness?: number;
  metalness?: number;
  clearcoat?: number;
  clearcoatRoughness?: number;
  sheen?: number;
  sheenRoughness?: number;
  sheenColor?: string | number;
  emissive?: string | number;
  emissiveIntensity?: number;
  wireframe?: boolean;
  /** Override auto role. */
  role?: SurfaceRole;
}

interface RolePreset {
  roughness: number;
  roughVar: number;
  metalness: number;
  clearcoat: number;
  clearcoatRoughness: number;
  sheen?: number;
  normalScale: number;
  weave?: boolean;
  anisoGrain?: boolean;
  panel?: number;
  scratch?: number;
  grain?: number;
  aoEdge?: number;
}

interface SurfacePresetContract {
  base_rough?: number;
  rough_var?: number;
  scratch?: number;
  panel?: number;
  grain?: number;
  ao_edge?: number;
  normal_strength?: number;
  weave?: boolean;
  aniso_grain?: boolean;
  metalness?: number;
  clearcoat?: number;
  clearcoat_roughness?: number;
  sheen?: number;
}

const SURFACE_PRESET_DATA = surfacePresetData as Record<SurfaceRole, SurfacePresetContract>;

function toRolePreset(preset: SurfacePresetContract): RolePreset {
  return {
    roughness: preset.base_rough ?? 0.5,
    roughVar: preset.rough_var ?? 0.1,
    metalness: preset.metalness ?? 0.1,
    clearcoat: preset.clearcoat ?? 0.1,
    clearcoatRoughness: preset.clearcoat_roughness ?? 0.5,
    sheen: preset.sheen,
    normalScale: preset.normal_strength ?? 0.5,
    weave: preset.weave,
    anisoGrain: preset.aniso_grain,
    panel: preset.panel,
    scratch: preset.scratch,
    grain: preset.grain,
    aoEdge: preset.ao_edge,
  };
}

const ROLE_PRESETS = Object.fromEntries(
  Object.entries(SURFACE_PRESET_DATA).map(([role, preset]) => [role, toRolePreset(preset)]),
) as Record<SurfaceRole, RolePreset>;

function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function stableRoleSeed(role: string): number {
  let h = 2166136261;
  for (let i = 0; i < role.length; i++) {
    h ^= role.charCodeAt(i);
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h % 10000;
}

function hash2(x: number, y: number, seed: number): number {
  let n = x * 374761393 + y * 668265263 + seed * 362437;
  n = (n ^ (n >>> 13)) * 1274126177;
  return ((n ^ (n >>> 16)) >>> 0) / 4294967296;
}

function valueNoise(x: number, y: number, seed: number): number {
  const x0 = Math.floor(x);
  const y0 = Math.floor(y);
  const fx = x - x0;
  const fy = y - y0;
  const ux = fx * fx * (3 - 2 * fx);
  const uy = fy * fy * (3 - 2 * fy);
  const v00 = hash2(x0, y0, seed);
  const v10 = hash2(x0 + 1, y0, seed);
  const v01 = hash2(x0, y0 + 1, seed);
  const v11 = hash2(x0 + 1, y0 + 1, seed);
  return (
    v00 * (1 - ux) * (1 - uy) +
    v10 * ux * (1 - uy) +
    v01 * (1 - ux) * uy +
    v11 * ux * uy
  );
}

function fbm(x: number, y: number, seed: number, octaves = 4): number {
  let a = 0.5;
  let f = 1;
  let s = 0;
  let m = 0;
  for (let i = 0; i < octaves; i++) {
    s += a * valueNoise(x * f, y * f, seed + i * 19);
    m += a;
    a *= 0.5;
    f *= 2;
  }
  return s / (m || 1);
}

export interface BakedMaps {
  normal: THREE.CanvasTexture;
  roughness: THREE.CanvasTexture;
  ao: THREE.CanvasTexture;
}

/** Build procedural normal / roughness / AO textures for a surface role. */
export function bakeRoleMaps(
  role: SurfaceRole,
  resolution: number,
  seed: number,
): BakedMaps {
  const preset = ROLE_PRESETS[role] ?? ROLE_PRESETS.default;
  const size = Math.max(64, resolution);
  const height = new Float32Array(size * size);
  const ns = preset.normalScale;
  const grain = preset.grain ?? 0.3;
  const panel = preset.panel ?? 0;
  const scratch = preset.scratch ?? 0;

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const u = x / size;
      const v = y / size;
      let h = (fbm(u * 8, v * 8, seed) * 2 - 1) * 0.35 * grain;
      h += (fbm(u * 32, v * 32, seed + 3) * 2 - 1) * 0.2 * grain;
      if (preset.weave) {
        h += 0.15 * Math.sin(u * Math.PI * 64) * Math.sin(v * Math.PI * 64);
      }
      if (preset.anisoGrain) {
        h += 0.2 * Math.sin(v * Math.PI * 40 + h);
      }
      if (panel > 0) {
        const px = Math.abs(((u * 4) % 1) - 0.5);
        const py = Math.abs(((v * 4) % 1) - 0.5);
        const edge = Math.max(0, 0.04 - Math.min(px, py)) * 25;
        h -= edge * panel * 0.5;
      }
      if (scratch > 0 && hash2(Math.floor(x / 3), y, seed + 7) > 1 - scratch * 0.02) {
        h += (hash2(x, y, seed + 9) - 0.5) * scratch * 0.4;
      }
      const border = Math.min(u, v, 1 - u, 1 - v);
      if (border < 0.08) h -= (0.08 - border) * 2 * (preset.aoEdge ?? 0.25);
      height[y * size + x] = h * ns;
    }
  }

  const normalCanvas = document.createElement("canvas");
  normalCanvas.width = normalCanvas.height = size;
  const nctx = normalCanvas.getContext("2d")!;
  const nimg = nctx.createImageData(size, size);

  const roughCanvas = document.createElement("canvas");
  roughCanvas.width = roughCanvas.height = size;
  const rctx = roughCanvas.getContext("2d")!;
  const rimg = rctx.createImageData(size, size);

  const aoCanvas = document.createElement("canvas");
  aoCanvas.width = aoCanvas.height = size;
  const actx = aoCanvas.getContext("2d")!;
  const aimg = actx.createImageData(size, size);

  const baseR = preset.roughness;
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const i = y * size + x;
      const x0 = height[y * size + (x > 0 ? x - 1 : x)];
      const x1 = height[y * size + (x + 1 < size ? x + 1 : x)];
      const y0 = height[(y > 0 ? y - 1 : y) * size + x];
      const y1 = height[(y + 1 < size ? y + 1 : y) * size + x];
      let nx = -(x1 - x0) * 2.5;
      let ny = -(y1 - y0) * 2.5;
      let nz = 1;
      const inv = 1 / Math.hypot(nx, ny, nz);
      nx *= inv;
      ny *= inv;
      nz *= inv;
      const ni = i * 4;
      nimg.data[ni] = (nx * 0.5 + 0.5) * 255;
      nimg.data[ni + 1] = (ny * 0.5 + 0.5) * 255;
      nimg.data[ni + 2] = (nz * 0.5 + 0.5) * 255;
      nimg.data[ni + 3] = 255;

      const wear = Math.min(1, Math.abs(height[i]) * 0.8);
      const rn = fbm(x / size * 10, y / size * 10, seed + 11);
      const rough = Math.min(
        1,
        Math.max(0, baseR + (rn - 0.5) * 2 * preset.roughVar + wear * 0.15),
      );
      const rv = rough * 255;
      rimg.data[ni] = rimg.data[ni + 1] = rimg.data[ni + 2] = rv;
      rimg.data[ni + 3] = 255;

      const ao = Math.min(1, Math.max(0, 0.65 + height[i] * 0.5));
      const av = ao * 255;
      aimg.data[ni] = aimg.data[ni + 1] = aimg.data[ni + 2] = av;
      aimg.data[ni + 3] = 255;
    }
  }
  nctx.putImageData(nimg, 0, 0);
  rctx.putImageData(rimg, 0, 0);
  actx.putImageData(aimg, 0, 0);

  const mk = (c: HTMLCanvasElement) => {
    const t = new THREE.CanvasTexture(c);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.colorSpace = THREE.NoColorSpace;
    t.needsUpdate = true;
    return t;
  };
  const normal = mk(normalCanvas);
  // normal maps must not be sRGB
  normal.colorSpace = THREE.NoColorSpace;
  const roughness = mk(roughCanvas);
  const ao = mk(aoCanvas);
  return { normal, roughness, ao };
}

export class SurfaceLibrary {
  readonly detailLevel: DetailLevel;
  readonly seed: number;
  readonly resolution: number;
  private cache = new Map<string, BakedMaps>();
  private rivetGeo: THREE.BufferGeometry;
  private rng: () => number;

  constructor(opts: SurfaceLibraryOptions = {}) {
    this.detailLevel = opts.detailLevel ?? "high";
    this.seed = opts.seed ?? 42;
    const resMap: Record<DetailLevel, number> = {
      low: 128,
      medium: 256,
      high: 512,
      ultra: 1024,
    };
    this.resolution = opts.resolution ?? resMap[this.detailLevel];
    this.rng = mulberry32(this.seed);
    this.rivetGeo = new THREE.SphereGeometry(1, 8, 6);
  }

  mapsFor(role: SurfaceRole): BakedMaps {
    const key = `${role}@${this.resolution}`;
    let m = this.cache.get(key);
    if (!m) {
      m = bakeRoleMaps(role, this.resolution, this.seed + stableRoleSeed(role));
      // scale tiling slightly by role
      const rep = role === "cloth" || role === "leather" ? 3 : role === "metal" ? 2 : 1.5;
      m.normal.repeat.set(rep, rep);
      m.roughness.repeat.set(rep, rep);
      m.ao.repeat.set(rep, rep);
      this.cache.set(key, m);
    }
    return m;
  }

  /** Create a MeshPhysicalMaterial with procedural micro maps when detail ≥ medium. */
  physical(role: SurfaceRole, opts: PhysicalOpts): THREE.MeshPhysicalMaterial {
    const preset = ROLE_PRESETS[opts.role ?? role] ?? ROLE_PRESETS.default;
    const useMaps = this.detailLevel !== "low";
    const maps = useMaps ? this.mapsFor(opts.role ?? role) : null;
    const ns = this.detailLevel === "ultra" ? 1.15 : this.detailLevel === "high" ? 1.0 : 0.75;

    const mat = new THREE.MeshPhysicalMaterial({
      color: opts.color,
      roughness: opts.roughness ?? preset.roughness,
      metalness: opts.metalness ?? preset.metalness,
      clearcoat: opts.clearcoat ?? preset.clearcoat,
      clearcoatRoughness: opts.clearcoatRoughness ?? preset.clearcoatRoughness,
      sheen: opts.sheen ?? preset.sheen ?? 0,
      sheenRoughness: opts.sheenRoughness ?? 0.5,
      sheenColor: opts.sheenColor ?? opts.color,
      emissive: opts.emissive ?? 0x000000,
      emissiveIntensity: opts.emissiveIntensity ?? 0,
      wireframe: opts.wireframe ?? false,
      normalMap: maps?.normal,
      normalScale: new THREE.Vector2(preset.normalScale * ns, preset.normalScale * ns),
      roughnessMap: maps?.roughness,
      aoMap: maps?.ao,
      aoMapIntensity: this.detailLevel === "low" ? 0 : 0.85,
    });
    return mat;
  }

  /**
   * Instanced rivet ring (or partial arc) — generic meso detail.
   * Works on armor, machinery, furniture, vehicles, etc.
   */
  rivetRing(
    parent: THREE.Object3D,
    opts: {
      radius: number;
      count?: number;
      y?: number;
      size?: number;
      material: THREE.Material;
      axis?: "y" | "z" | "x";
      arc?: number;
      name?: string;
    },
  ): THREE.InstancedMesh | null {
    if (this.detailLevel === "low") return null;
    const max =
      this.detailLevel === "medium" ? 24 : this.detailLevel === "high" ? 48 : 96;
    const count = Math.min(opts.count ?? 12, max);
    if (count <= 0) return null;

    const mesh = new THREE.InstancedMesh(this.rivetGeo, opts.material, count);
    mesh.name = opts.name ?? "rivetRing";
    mesh.castShadow = true;
    const dummy = new THREE.Object3D();
    const size = opts.size ?? 0.012;
    const y = opts.y ?? 0;
    const arc = opts.arc ?? Math.PI * 2;
    const axis = opts.axis ?? "y";

    for (let i = 0; i < count; i++) {
      const t = (i / count) * arc;
      const c = Math.cos(t) * opts.radius;
      const s = Math.sin(t) * opts.radius;
      if (axis === "y") dummy.position.set(c, y, s);
      else if (axis === "z") dummy.position.set(c, s, y);
      else dummy.position.set(y, c, s);
      dummy.scale.setScalar(size);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
    }
    mesh.instanceMatrix.needsUpdate = true;
    parent.add(mesh);
    return mesh;
  }

  /** Scatter rivets in a rectangular region (local XZ plane). */
  rivetGrid(
    parent: THREE.Object3D,
    opts: {
      width: number;
      height: number;
      cols?: number;
      rows?: number;
      z?: number;
      size?: number;
      material: THREE.Material;
      name?: string;
    },
  ): THREE.InstancedMesh | null {
    if (this.detailLevel === "low" || this.detailLevel === "medium") return null;
    const cols = opts.cols ?? 4;
    const rows = opts.rows ?? 3;
    const count = cols * rows;
    const mesh = new THREE.InstancedMesh(this.rivetGeo, opts.material, count);
    mesh.name = opts.name ?? "rivetGrid";
    mesh.castShadow = true;
    const dummy = new THREE.Object3D();
    const size = opts.size ?? 0.01;
    const z = opts.z ?? 0;
    let i = 0;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const u = cols === 1 ? 0.5 : c / (cols - 1);
        const v = rows === 1 ? 0.5 : r / (rows - 1);
        dummy.position.set((u - 0.5) * opts.width, (v - 0.5) * opts.height, z);
        dummy.scale.setScalar(size * (0.9 + this.rng() * 0.2));
        dummy.updateMatrix();
        mesh.setMatrixAt(i++, dummy.matrix);
      }
    }
    mesh.instanceMatrix.needsUpdate = true;
    parent.add(mesh);
    return mesh;
  }

  /**
   * Thin edge trim as a box or torus — generic hard-surface meso cue.
   */
  edgeBand(
    parent: THREE.Object3D,
    opts: {
      kind?: "box" | "torus";
      material: THREE.Material;
      // box
      size?: [number, number, number];
      // torus
      radius?: number;
      tube?: number;
      position?: [number, number, number];
      rotation?: [number, number, number];
      name?: string;
    },
  ): THREE.Mesh | null {
    if (this.detailLevel === "low") return null;
    let geo: THREE.BufferGeometry;
    if (opts.kind === "torus") {
      geo = new THREE.TorusGeometry(opts.radius ?? 0.15, opts.tube ?? 0.012, 6, 20);
    } else {
      const s = opts.size ?? [0.4, 0.02, 0.28];
      geo = new THREE.BoxGeometry(s[0], s[1], s[2]);
    }
    const m = new THREE.Mesh(geo, opts.material);
    m.name = opts.name ?? "edgeBand";
    if (opts.position) m.position.set(...opts.position);
    if (opts.rotation) m.rotation.set(...opts.rotation);
    m.castShadow = true;
    m.receiveShadow = true;
    parent.add(m);
    return m;
  }

  dispose(): void {
    for (const m of this.cache.values()) {
      m.normal.dispose();
      m.roughness.dispose();
      m.ao.dispose();
    }
    this.cache.clear();
    this.rivetGeo.dispose();
  }
}

export function createSurfaceLibrary(opts?: SurfaceLibraryOptions): SurfaceLibrary {
  return new SurfaceLibrary(opts);
}

/** Map gpthreejs qualityMode → detail level. */
export function detailLevelFromQualityMode(mode?: string): DetailLevel {
  switch (mode) {
    case "draft":
      return "low";
    case "solid":
      return "medium";
    case "razor":
      return "ultra";
    case "hybrid":
    case "sharp":
    default:
      return "high";
  }
}
