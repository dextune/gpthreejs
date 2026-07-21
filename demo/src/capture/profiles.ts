export type CapturePassId = "beauty" | "alpha";

export interface CaptureProfile {
  id: "knight-source-34-m0";
  viewport: {
    width: number;
    height: number;
    deviceScaleFactor: number;
  };
  camera: {
    fov: number;
    position: [number, number, number];
    target: [number, number, number];
    near: number;
    far: number;
  };
  lightRigId: "m0-neutral-key-fill-rim";
}

import m0Profile from "./m0-profile.json";

export const m0CaptureProfile = m0Profile as CaptureProfile;
