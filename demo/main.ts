import { startAnimationLoop, type AnimationRuntime, type FormHandles } from "./src/app/animation";
import { mountReferenceStrip } from "./src/app/references";
import { createRenderer, bindResize } from "./src/app/renderer";
import { RuntimeResources } from "./src/app/resources";
import { createViewerScene } from "./src/app/scene";
import { m0CaptureProfile, type CapturePassId } from "./src/capture/profiles";
import { createKnightForm } from "./src/createKnightForm";
import type * as THREE from "three";

declare global {
  interface Window {
    __gpthreejsRuntimeSmoke?: {
      ready: boolean;
      nodeIds: string[];
      pivotIds: string[];
      socketIds: string[];
      rootChildren: number;
    };
    __gpthreejsCaptureReady?: {
      ready: boolean;
      mode: CapturePassId;
      profileId: string;
      width: number;
      height: number;
      pixelHash: string;
      hashKind: "rgba" | "alpha";
      stats: {
        minAlpha: number;
        maxAlpha: number;
        transparentPixels: number;
        opaquePixels: number;
        nonBackgroundPixels: number;
        foregroundPixels: number;
      };
      viewport: typeof m0CaptureProfile.viewport;
      nodeIds: string[];
      rootChildren: number;
    };
  }
}

const requiredRuntimeNodeIds = ["hips", "torso", "head", "hand_l", "hand_r", "weapon_hip"];
const requiredRuntimePivotIds = ["hips", "spine", "head", "leftHand", "rightHand"];
const requiredRuntimeSocketIds = ["weapon_r", "weapon_hip"];

function assertFormHandles(value: unknown): asserts value is FormHandles {
  const handles = value as Partial<FormHandles> | undefined;
  const nodeIds = Object.keys(handles?.nodes || {});
  const pivotIds = (handles?.pivots || []).map((pivot) => pivot.id);
  const socketIds = (handles?.sockets || []).map((socket) => socket.id);
  const missingNodeIds = requiredRuntimeNodeIds.filter((id) => !nodeIds.includes(id));
  const missingPivotIds = requiredRuntimePivotIds.filter((id) => !pivotIds.includes(id));
  const missingSocketIds = requiredRuntimeSocketIds.filter((id) => !socketIds.includes(id));
  if (!handles?.nodes || missingNodeIds.length || missingPivotIds.length || missingSocketIds.length) {
    throw new Error(
      `Invalid formHandles: ${JSON.stringify({
        missingNodeIds,
        missingPivotIds,
        missingSocketIds,
      })}`,
    );
  }
}

const app = document.getElementById("app");
if (!app) throw new Error("Missing #app root");

const captureMode = getCaptureMode(new URLSearchParams(window.location.search));
if (captureMode) {
  document.body.dataset.captureMode = captureMode;
}

const resources = new RuntimeResources();
const renderer = createRenderer(app, {
  alpha: captureMode === "alpha",
  pixelRatio: captureMode ? m0CaptureProfile.viewport.deviceScaleFactor : undefined,
  preserveDrawingBuffer: Boolean(captureMode),
  size: captureMode ? m0CaptureProfile.viewport : undefined,
});
const { scene, camera, controls } = createViewerScene(renderer.domElement, {
  captureProfile: captureMode ? m0CaptureProfile : undefined,
  showGround: !captureMode,
  transparentBackground: captureMode === "alpha",
});
if (!captureMode) {
  resources.add(bindResize(renderer, camera));
}

const knight = createKnightForm({}, { seed: 42 });
scene.add(knight);

const handles = knight.userData.formHandles;
assertFormHandles(handles);
window.__gpthreejsRuntimeSmoke = {
  ready: true,
  nodeIds: Object.keys(handles.nodes || {}),
  pivotIds: (handles.pivots || []).map((pivot) => pivot.id),
  socketIds: (handles.sockets || []).map((socket) => socket.id),
  rootChildren: knight.children.length,
};
console.info("[gpthreejs] formHandles", {
  nodes: Object.keys(handles.nodes || {}),
  pivots: handles.pivots,
  sockets: handles.sockets,
});

mountReferenceStrip(document.getElementById("refs"));

let animation: AnimationRuntime = { stop: () => undefined };
if (captureMode) {
  controls.update();
  renderer.render(scene, camera);
  const readback = readCanvasPixels(renderer, captureMode);
  window.__gpthreejsCaptureReady = {
    ready: true,
    mode: captureMode,
    profileId: m0CaptureProfile.id,
    width: renderer.domElement.width,
    height: renderer.domElement.height,
    pixelHash: readback.pixelHash,
    hashKind: readback.hashKind,
    stats: readback.stats,
    viewport: m0CaptureProfile.viewport,
    nodeIds: Object.keys(handles.nodes || {}),
    rootChildren: knight.children.length,
  };
} else {
  animation = startAnimationLoop({ renderer, scene, camera, controls, handles });
}

window.addEventListener(
  "beforeunload",
  () => {
    animation.stop();
    resources.disposeObject(scene);
    resources.dispose(renderer, controls);
  },
  { once: true },
);

function getCaptureMode(params: URLSearchParams): CapturePassId | undefined {
  const mode = params.get("capture");
  if (mode === "beauty" || mode === "alpha") return mode;
  return undefined;
}

function readCanvasPixels(renderer: THREE.WebGLRenderer, mode: CapturePassId): {
  pixelHash: string;
  hashKind: "rgba" | "alpha";
  stats: NonNullable<Window["__gpthreejsCaptureReady"]>["stats"];
} {
  const gl = renderer.getContext();
  const width = renderer.domElement.width;
  const height = renderer.domElement.height;
  const pixels = new Uint8Array(width * height * 4);
  gl.readPixels(0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
  let minAlpha = 255;
  let maxAlpha = 0;
  let transparentPixels = 0;
  let opaquePixels = 0;
  let nonBackgroundPixels = 0;
  let foregroundPixels = 0;
  let hash = 2166136261;
  const background = {
    red: pixels[0],
    green: pixels[1],
    blue: pixels[2],
    alpha: pixels[3],
  };
  for (let index = 0; index < pixels.length; index += 4) {
    const red = pixels[index];
    const green = pixels[index + 1];
    const blue = pixels[index + 2];
    const alpha = pixels[index + 3];
    if (mode === "alpha") {
      hash ^= alpha;
      hash = Math.imul(hash, 16777619) >>> 0;
    } else {
      hash ^= red;
      hash = Math.imul(hash, 16777619) >>> 0;
      hash ^= green;
      hash = Math.imul(hash, 16777619) >>> 0;
      hash ^= blue;
      hash = Math.imul(hash, 16777619) >>> 0;
      hash ^= alpha;
      hash = Math.imul(hash, 16777619) >>> 0;
    }
    minAlpha = Math.min(minAlpha, alpha);
    maxAlpha = Math.max(maxAlpha, alpha);
    if (alpha === 0) transparentPixels += 1;
    if (alpha === 255) opaquePixels += 1;
    const backgroundDistance = Math.abs(red - background.red)
      + Math.abs(green - background.green)
      + Math.abs(blue - background.blue)
      + Math.abs(alpha - background.alpha);
    if (backgroundDistance > 12) {
      nonBackgroundPixels += 1;
      foregroundPixels += 1;
    }
  }
  return {
    pixelHash: hash.toString(16).padStart(8, "0"),
    hashKind: mode === "alpha" ? "alpha" : "rgba",
    stats: {
      minAlpha,
      maxAlpha,
      transparentPixels,
      opaquePixels,
      nonBackgroundPixels,
      foregroundPixels,
    },
  };
}
