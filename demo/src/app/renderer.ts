import * as THREE from "three";

export interface RendererOptions {
  alpha?: boolean;
  preserveDrawingBuffer?: boolean;
  pixelRatio?: number;
  size?: {
    width: number;
    height: number;
  };
}

export function createRenderer(
  app: HTMLElement,
  options: RendererOptions = {},
): THREE.WebGLRenderer {
  const renderer = new THREE.WebGLRenderer({
    alpha: options.alpha ?? false,
    antialias: true,
    preserveDrawingBuffer: options.preserveDrawingBuffer ?? false,
  });
  renderer.setPixelRatio(options.pixelRatio ?? Math.min(window.devicePixelRatio, 2));
  renderer.setSize(options.size?.width ?? window.innerWidth, options.size?.height ?? window.innerHeight);
  if (options.alpha) {
    renderer.setClearAlpha(0);
  }
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  app.appendChild(renderer.domElement);
  return renderer;
}

export function bindResize(
  renderer: THREE.WebGLRenderer,
  camera: THREE.PerspectiveCamera,
): () => void {
  const onResize = () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  };
  window.addEventListener("resize", onResize);
  return () => window.removeEventListener("resize", onResize);
}
