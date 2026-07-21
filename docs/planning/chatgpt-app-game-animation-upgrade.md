# ChatGPT App Game Animation Upgrade Plan

## Status

- Date: 2026-07-21
- Mode: planning and documentation
- Scope: extend the reference-image-to-procedural-Three.js workflow into a ChatGPT App capable of producing game-oriented character assets.
- Completion condition: the implementation order, schemas, gates, and measurable acceptance criteria are documented for image intake, static form generation, rigging, animation, review, and package export.

## Decision

The existing `gpthreejs` engine is a static procedural form pipeline. It can
analyze an image, derive a Sense Pack, draft a Form Blueprint, and emit a
TypeScript `THREE.Group` factory. It is not yet a game character generator
because it lacks a purpose-intake contract, game asset schemas, real rig
contracts, animation clips, action timing, GLB package invariants, a ChatGPT App
MCP server, and an interactive inspection widget.

The upgrade must be delivered in layers:

1. Purpose discovery before production build.
2. Static form and fidelity gates preserved from the current engine.
3. Game asset contracts for rig, animation, actions, package metadata, and performance.
4. ChatGPT App tools and widget surfaces for file intake, project state, review, and export.

Release order:

1. Slice 0: Intent Gate.
2. Slice A: Contracts.
3. Slice B: Animated Rigid MVP.
4. Slice C: Runtime Package.
5. Slice D: Hybrid Skinned GLB.
6. Slice E: ChatGPT App Beta.
7. Slice F: Production Gate.
8. Slice G: Organic Auto-Rig Research.

Organic production auto-rigging is explicitly not part of the R1/R2 launch gate.

## Current Evidence

| Area | Current state | Impact |
| --- | --- | --- |
| Cast layers | Current layers are `mass`, `skeleton`, `contour`, `skin`, `light`, `handle`, `polish`. | The names `skeleton` and `skin` can be mistaken for bone rigging and skinning. |
| Emitter | The current emitter creates primitive `Mesh` and `Group` hierarchies. | Rigid character animation is feasible; organic deformation is not. |
| Runtime | The demo has a knight hierarchy and sockets. | It is a useful R1 fixture. |
| Motion | Demo motion is limited to simple loop-time transforms. | There are no `AnimationClip` packs or action windows. |
| Hybrid | Hybrid GLB is documented as a path but not implemented as a package contract. | R2 must focus on import, normalize, validate, retarget, and preserve metadata. |
| Gates | Sufficiency, validation, layer checks, cast, metrics, and journal are separate commands. | Production orchestration must prevent gate bypass. |
| Tests | Existing tests cover static engine smoke, sufficiency, and surface maps. | Rig, animation, package, app, and performance coverage is missing. |

## Target User Experience

1. The user uploads a generated or external reference image in ChatGPT.
2. The app extracts visible subject/style evidence without guessing final use.
3. The app builds or updates a `UseContextBrief`.
4. Missing critical purpose fields are collected one question at a time.
5. The app selects a pipeline route: static form, animated rigid, hybrid skinned, print-ready, or research-only.
6. The build runs as a resumable job with stage progress.
7. The widget previews geometry, rig overlays, sockets, colliders, clips, events, and quality reports.
8. The user revises purpose, parts, bones, clips, or timing without invalidating unrelated artifacts.
9. The final package returns TypeScript, GLB, rig JSON, animation JSON, action JSON, package manifest, and quality report.

## Core Contracts

### UseContextBrief

Top-level project intent contract:

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

Critical fields must never be silently defaulted.

### GameAssetBrief

Game-specific target contract:

- `subjectType`
- `rigMode`
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

### RigBlueprint

Rig representation:

- `rigMode`
- `bindPose`
- `skeletonProfile`
- `bones`
- `skin`
- `sockets`
- `ikTargets`
- `colliders`
- `constraints`
- `confidenceByRegion`

Validators must reject cycles, duplicate ids, missing parents, invalid transforms,
missing socket targets, non-normalized weights, and invalid bone references.

### AnimationBlueprint

Motion representation:

- `clips`
- `motionMode`
- `tracks`
- `layers`
- `constraints`
- `source`
- `sourceLicense`

Validators must check clip ids, durations, loop policy, track targets, quaternion
normalization, event order, and window overlap policy.

### ActionManifest

Gameplay timing contract using normalized time:

- anticipation windows
- active hit windows
- recovery windows
- cancel, combo, interrupt windows
- invulnerability windows
- movement lock and root motion curves
- weapon trail, projectile, VFX, SFX, and camera events
- hitbox ids connected to damage shapes

### GameAssetManifest

Package contract:

- file list, MIME type, hash, and schema version
- factory TypeScript
- runtime controller TypeScript
- GLB
- rig JSON
- animation JSON
- action JSON
- reference lineage and provider metadata
- fidelity, rig, animation, performance validation results
- known uncertainties and optional failed gates

## Release Slices

### Slice 0: Intent Gate

Add intent schema, profiles, sufficiency report, question ranking, routing, and
dependency invalidation.

Acceptance:

- A request with only one image returns an `ask` verdict and a purpose question.
- A complete game-character request routes without duplicate questions.
- A 3D-print request excludes rig and animation stages.
- Purpose changes reuse unaffected Sense Pack artifacts and invalidate only dependent stages.

### Slice A: Contracts

Clarify static terminology, preserve static behavior, and add game schemas and
strict validators.

Acceptance:

- Existing static object and knight fixtures preserve hierarchy, materials, and handles.
- Documentation no longer implies that static `skeleton` and material `skin` are game rigging features.
- Invalid rig and animation fixtures fail with issue codes and remedies.

### Slice B: Animated Rigid MVP

Generalize the knight hierarchy into rigid character rigs and procedural clips.

Required clips:

- locomotion: `idle`, `walk`, `run`, `turn_left`, `turn_right`, `jump_start`, `jump_loop`, `jump_land`, `fall`
- combat: `draw`, `sheath`, `attack_light_1`, `attack_light_2`, `attack_light_3`, `attack_heavy`, `block`, `hit_front`, `hit_back`, `death`
- skill: `skill_cast`, `skill_charge_loop`, `skill_release`, `skill_recovery`, `skill_interrupt`

Acceptance:

- Required humanoid-lite nodes exist with deterministic names and valid parent chains.
- Required clips parse and execute in a Three.js smoke test.
- Attack clips include ordered anticipation, active, and recovery windows with hitbox ids.
- 30 fps and 60 fps event delivery produce identical event order and counts.

### Slice C: Runtime Package

Export factory, GLB, manifests, runtime adapter, and quality report.

Acceptance:

- Re-imported GLB preserves node count, hierarchy, clip ids, durations, sockets, and colliders.
- The same action manifest runs against the procedural factory and imported GLB.
- Sandbox state transitions run without uncaught errors and dispose mixer resources.

### Slice D: Hybrid Skinned GLB

Support rigged GLB normalization and retargeting.

Acceptance:

- At least three humanoid rig fixtures use the common action API.
- Round trip preserves vertex count, skin joint count, normalized weights, and clips.
- Unsupported skeletons return explicit issue codes and remedies.

### Slice E: ChatGPT App Beta

Build MCP tools and a Three.js inspection widget.

Acceptance:

- ChatGPT can provide image file inputs to analysis and build tools.
- Missing purpose information returns the intent question before build starts.
- Complete requests route without unnecessary questions.
- Widget loads GLB inline and fullscreen, restores clip/overlay UI state, and has a text fallback.

### Slice F: Production Gate

Add quality, performance, security, privacy, observability, deployment, and submission readiness.

Acceptance:

- Every build produces a six-layer quality report: appearance, rig, animation, gameplay, performance, and app.
- Budget failures report measured values and remedies.
- Unauthorized project or file access is blocked.
- Logs identify project, tool call, job stage, duration, and failure code without secrets.

### Slice G: Organic Auto-Rig Research

Research organic topology, auto-skinning, corrective morphs, face rigs, cloth/hair
secondary motion, and provider adapters.

Entry requires stable R1/R2 contracts and at least 30 organic fixtures with an
approved evaluation rubric.

## Risks

| Risk | Mitigation |
| --- | --- |
| Inferring purpose from image appearance | Require `UseContextBrief` and provenance fields. |
| Overlong purpose interview | Ask only the highest-impact missing critical field. |
| Purpose changes during production | Use dependency hashes and stale only affected artifacts. |
| Overpromising organic rigging from one image | Separate R1 rigid, R2 hybrid, and R3 research. |
| Animation without gameplay timing | Require `ActionManifest` events and windows. |
| External provider dependency | Record provider, license, and lineage metadata. |
| Long-running tool calls | Use jobs, status polling, idempotency, quotas, and checkpoints. |
| Widget storing authoritative state | Keep business state on the server and UI state in the widget. |
| GLB metadata loss | Add round-trip invariant tests. |
| Performance drift | Gate triangles, bones, materials, draw calls, texture memory, and frame time. |

## Verification Plan

- Unit: intent completeness, question priority, routing, schema migration, rig validation, animation validation, event scheduling, file validation, idempotency.
- Integration: image to package, factory to GLB round trip, hybrid GLB normalize and retarget, MCP tool to job to artifact.
- E2E: single image asks for purpose, complete game-character request builds, purpose change invalidates affected stages, widget reviews walk/attack/skill, invalid GLB rejects.
- Visual and motion: multi-view sheets, overlay snapshots, pose strips, event timeline snapshots.
- Performance and observability: p50/p95 frame time, draw calls, triangles, texture memory, stage duration, retry count, failure rate.

## ADR

Keep the Python engine and add versioned contracts on top. Build the ChatGPT App
as an MCP server plus direct-rendered Three.js widget. Release intent gate,
rigid procedural characters, hybrid rigged GLB, and organic research in that
order.

Alternatives rejected:

- Rewriting the engine in TypeScript: high migration risk with little feature value.
- Shipping organic auto-rig in R1: too much quality uncertainty.
- Wrapping only an external image-to-3D service: loses editable procedural output and lineage control.
- Text-only ChatGPT tools: insufficient for rig and motion review.
