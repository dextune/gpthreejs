import { startAnimationLoop, type FormHandles } from "./src/app/animation";
import { mountReferenceStrip } from "./src/app/references";
import { createRenderer, bindResize } from "./src/app/renderer";
import { RuntimeResources } from "./src/app/resources";
import { createViewerScene } from "./src/app/scene";
import { createKnightForm } from "./src/createKnightForm";

const app = document.getElementById("app");
if (!app) throw new Error("Missing #app root");

const resources = new RuntimeResources();
const renderer = createRenderer(app);
const { scene, camera, controls } = createViewerScene(renderer.domElement);
resources.add(bindResize(renderer, camera));

const knight = createKnightForm({}, { seed: 42 });
scene.add(knight);

const handles = knight.userData.formHandles as FormHandles;
console.info("[gpthreejs] formHandles", {
  nodes: Object.keys(handles.nodes || {}),
  pivots: handles.pivots,
  sockets: handles.sockets,
});

mountReferenceStrip(document.getElementById("refs"));

const animation = startAnimationLoop({ renderer, scene, camera, controls, handles });

window.addEventListener(
  "beforeunload",
  () => {
    animation.stop();
    resources.disposeObject(scene);
    resources.dispose(renderer, controls);
  },
  { once: true },
);
