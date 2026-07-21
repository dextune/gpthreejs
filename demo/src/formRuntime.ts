/**
 * Shared FormRuntime contract (RES-101).
 * Production factories should return this shape and call dispose() once.
 */
import type * as THREE from "three";

export interface FormRuntime {
  group: THREE.Group;
  nodes: Record<string, THREE.Object3D>;
  handles: Record<string, unknown>;
  dispose(): void;
}

export function createFormRuntime(args: {
  group: THREE.Group;
  nodes: Record<string, THREE.Object3D>;
  handles?: Record<string, unknown>;
  geometries?: Iterable<THREE.BufferGeometry>;
  materials?: Iterable<THREE.Material>;
  textures?: Iterable<THREE.Texture>;
}): FormRuntime {
  const geometries = new Set(args.geometries ?? []);
  const materials = new Set(args.materials ?? []);
  const textures = new Set(args.textures ?? []);
  let disposed = false;
  return {
    group: args.group,
    nodes: args.nodes,
    handles: args.handles ?? { nodes: args.nodes },
    dispose() {
      if (disposed) return;
      disposed = true;
      for (const g of geometries) g.dispose();
      for (const m of materials) m.dispose();
      for (const t of textures) t.dispose();
      geometries.clear();
      materials.clear();
      textures.clear();
      args.group.clear();
    },
  };
}
