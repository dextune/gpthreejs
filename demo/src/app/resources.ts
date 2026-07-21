import * as THREE from "three";
import type { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

export class RuntimeResources {
  private cleanup: Array<() => void> = [];

  add(cleanup: () => void): void {
    this.cleanup.push(cleanup);
  }

  disposeObject(root: THREE.Object3D): void {
    root.traverse((obj) => {
      const mesh = obj as THREE.Mesh;
      mesh.geometry?.dispose();
      const material = mesh.material;
      if (Array.isArray(material)) {
        for (const m of material) m.dispose();
      } else {
        material?.dispose();
      }
    });
  }

  dispose(renderer: THREE.WebGLRenderer, controls: OrbitControls): void {
    for (const fn of this.cleanup.splice(0).reverse()) fn();
    controls.dispose();
    renderer.dispose();
  }
}
