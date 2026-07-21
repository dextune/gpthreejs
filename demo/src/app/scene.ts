import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

export interface ViewerScene {
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  controls: OrbitControls;
}

export function createViewerScene(rendererElement: HTMLElement): ViewerScene {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x12161c);
  scene.fog = new THREE.Fog(0x12161c, 8, 28);

  const camera = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 0.1, 100);
  camera.position.set(2.6, 1.7, 3.4);

  const controls = new OrbitControls(camera, rendererElement);
  controls.target.set(0, 1.0, 0);
  controls.enableDamping = true;
  controls.minDistance = 1.2;
  controls.maxDistance = 12;

  addLights(scene);
  addGround(scene);

  return { scene, camera, controls };
}

function addLights(scene: THREE.Scene): void {
  scene.add(new THREE.AmbientLight(0xb0c0d8, 0.45));
  scene.add(new THREE.HemisphereLight(0xdde8ff, 0x2a2018, 0.55));

  const key = new THREE.DirectionalLight(0xfff2e0, 1.55);
  key.position.set(4, 7, 3);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.camera.near = 0.5;
  key.shadow.camera.far = 30;
  key.shadow.camera.left = -5;
  key.shadow.camera.right = 5;
  key.shadow.camera.top = 6;
  key.shadow.camera.bottom = -2;
  scene.add(key);

  const fill = new THREE.DirectionalLight(0x88aaff, 0.45);
  fill.position.set(-3, 2, -2);
  scene.add(fill);

  const rim = new THREE.DirectionalLight(0xffccaa, 0.55);
  rim.position.set(-2, 3, -4);
  scene.add(rim);
}

function addGround(scene: THREE.Scene): void {
  const ground = new THREE.Mesh(
    new THREE.CircleGeometry(6, 64),
    new THREE.MeshStandardMaterial({ color: 0x1a1f28, roughness: 0.95, metalness: 0.05 }),
  );
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  scene.add(ground);

  const grid = new THREE.GridHelper(8, 16, 0x3a4558, 0x252b36);
  (grid.material as THREE.Material).opacity = 0.45;
  (grid.material as THREE.Material).transparent = true;
  scene.add(grid);
}
