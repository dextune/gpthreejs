# Use Context Brief

`UseContextBrief` is the top-level intent contract for every image-based build.
It prevents the pipeline from guessing the user's target use from image
appearance alone.

## Required Fields

- `schemaVersion`
- `projectGoal`
- `intendedUse`
- `applicationContext`
- `targetRuntime`
- `targetPlatform`
- `targetDevices`
- `interactionMode`
- `animationNeeds`
- `physicsNeeds`
- `deliverables`
- `worldScale`
- `units`
- `cameraDistance`
- `expectedActorCount`
- `fidelityPriority`
- `performanceBudget`
- `confirmedFields`
- `defaultedFields`
- `inferredFields`
- `unknownFields`
- `intentVerdict`
- `questionsAsked`
- `route`

## Verdicts

| Verdict | Meaning |
| --- | --- |
| `pass` | Critical fields are known and the route is stable. |
| `conditional` | Critical fields are known; remaining uncertainty is visible and acceptable. |
| `ask` | A critical field is missing; ask the next question before production build. |
| `reject` | The requested route is not supported or unsafe. |

## Provenance Rules

- User answers go into `confirmedFields`.
- Defaults go into `defaultedFields`.
- Image or text-derived guesses go into `inferredFields`.
- Missing or unresolved values go into `unknownFields`.
- Critical fields must not be silently defaulted.

## Route Rules

- `game-character` enables rig, animation, action, collider, performance, and package stages.
- `game-prop` enables interaction, collider, LOD, handles, and optional break groups.
- `web-3d` emphasizes loading budget, responsiveness, materials, and viewer API.
- `cinematic` emphasizes shot distance, camera, duration, and render quality.
- `ar-vr` emphasizes scale, anchors, interaction, device budget, and latency.
- `product-visualization` emphasizes material accuracy, variants, camera angles, and resolution.
- `3d-print` disables animation and requires physical scale, watertightness, wall thickness, and part separation.
- `static-preview` can skip rig and animation.

## Acceptance

- One image with no purpose returns `ask`.
- Complete purpose text routes without duplicate questions.
- Purpose changes invalidate only dependent downstream artifacts.
