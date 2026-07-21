# Game Asset Brief

`GameAssetBrief` specializes `UseContextBrief` for game-ready assets.

## Fields

- `schemaVersion`
- `subjectType`: `rigid-character`, `skinned-character`, `creature`, or `prop`
- `rigMode`: `rigid-rig`, `skinned-rig`, or `hybrid-rigged-glb`
- `targetRuntime`
- `targetProfile`
- `worldScale`
- `upAxis`
- `forwardAxis`
- `unit`
- `cameraStyle`
- `skeletonProfile`
- `rootMotionPolicy`
- `motionStyle`
- `weaponProfile`
- `handedness`
- `requestedActions`
- `performanceBudget`
- `referencePolicy`

## Required R1 Defaults

- `targetRuntime`: `threejs`
- `targetProfile`: `web-desktop` unless the user specifies mobile.
- `unit`: meters.
- `rootMotionPolicy`: `in-place` unless the user requests root motion.
- `rigMode`: `rigid-rig` for segmented characters.

Defaults must be recorded in `defaultedFields`.

## Rejection Cases

- The user requests production organic auto-rigging from one image.
- Required runtime or deliverable constraints conflict.
- Performance budget is impossible for the requested fidelity and actor count.
