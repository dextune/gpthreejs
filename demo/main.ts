import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { createKnightForm } from "./src/createKnightForm";

const app = document.getElementById("app")!;
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
app.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x12161c);
scene.fog = new THREE.Fog(0x12161c, 8, 28);

const camera = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(2.6, 1.7, 3.4);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 1.0, 0);
controls.enableDamping = true;
controls.minDistance = 1.2;
controls.maxDistance = 12;

// lights
const amb = new THREE.AmbientLight(0xb0c0d8, 0.45);
scene.add(amb);
const hemi = new THREE.HemisphereLight(0xdde8ff, 0x2a2018, 0.55);
scene.add(hemi);

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

// ground
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

// gpthreejs knight
const knight = createKnightForm({}, { seed: 42 });
scene.add(knight);

// idle sway using formHandles
const handles = knight.userData.formHandles as {
  nodes: Record<string, THREE.Object3D>;
  pivots?: { id: string; part: string }[];
  sockets?: { id: string; part: string }[];
};
console.info("[gpthreejs] formHandles", {
  nodes: Object.keys(handles.nodes || {}),
  pivots: handles.pivots,
  sockets: handles.sockets,
});

// reference thumbnails
const refRoot = document.getElementById("refs");
if (refRoot) {
  for (const name of [
    "knight_01_hero_34.png",
    "knight_02_front_ortho.png",
    "knight_03_side_ortho.png",
    "knight_04_back_ortho.png",
    "knight_05_bust_detail.png",
  ]) {
    const img = document.createElement("img");
    img.src = `/refs/${name}`;
    img.alt = name;
    img.title = name;
    refRoot.appendChild(img);
  }
}

window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

const clock = new THREE.Clock();
function tick() {
  const t = clock.getElapsedTime();
  const torso = handles.nodes?.torso;
  const cape = handles.nodes?.cape;
  const capeBody = handles.nodes?.cape_body;
  if (torso) torso.rotation.y = Math.sin(t * 0.7) * 0.035;
  if (cape) cape.rotation.y = Math.sin(t * 0.9) * 0.03;
  if (capeBody) capeBody.rotation.x = 0.25 + Math.sin(t * 1.4) * 0.04;
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(tick);
}
tick();
