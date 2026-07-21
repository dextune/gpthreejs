import * as THREE from "three";
import type { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

export interface FormHandles {
  nodes: Record<string, THREE.Object3D>;
  pivots?: { id: string; part: string }[];
  sockets?: { id: string; part: string }[];
}

export interface AnimationRuntime {
  stop: () => void;
}

export function startAnimationLoop(args: {
  renderer: THREE.WebGLRenderer;
  scene: THREE.Scene;
  camera: THREE.Camera;
  controls: OrbitControls;
  handles: FormHandles;
}): AnimationRuntime {
  const clock = new THREE.Clock();
  let frame = 0;
  let running = true;

  const tick = () => {
    if (!running) return;
    const t = clock.getElapsedTime();
    const torso = args.handles.nodes?.torso;
    const cape = args.handles.nodes?.cape;
    const capeBody = args.handles.nodes?.cape_body;
    if (torso) torso.rotation.y = Math.sin(t * 0.7) * 0.035;
    if (cape) cape.rotation.y = Math.sin(t * 0.9) * 0.03;
    if (capeBody) capeBody.rotation.x = 0.25 + Math.sin(t * 1.4) * 0.04;
    args.controls.update();
    args.renderer.render(args.scene, args.camera);
    frame = requestAnimationFrame(tick);
  };

  tick();
  return {
    stop: () => {
      running = false;
      cancelAnimationFrame(frame);
    },
  };
}
