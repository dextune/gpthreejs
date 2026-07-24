---
name: gpthreejs
description: >
  Lock a reference photo or prepared concept views into a fidelity-gated,
  multi-view-checked, CPU-assisted procedural Three.js form written as
  TypeScript. Use for image-to-3D code, product props, hard-surface rebuilds,
  stylized characters, perception packs, parameter search, generation briefs,
  and reference-matched camera/material/light reconstruction. Triggers:
  /gpthreejs, photo to Three.js, reconstruct object as code, image to 3D factory,
  reference-locked mesh code, text-only character turnaround prep.
license: MIT
version: 0.2.0
metadata:
  short-description: "Photo → gated procedural Three.js form"
---

# gpthreejs

Turn reference evidence into an editable procedural `THREE.Group` factory. The
result is source code, not a downloaded mesh pack, photogrammetry result, or
one-shot primitive approximation.

The skill combines:

- CPU-derived image evidence
- a sufficiency gate and Reference Prep route
- an evidence-linked Form Blueprint
- strict cast layers
- demo-derived likeness construction patterns
- deterministic multi-view critique

Host-agnostic: use native image reading, a browser MCP, project preview, or a
user screenshot wherever this document says to look, render, or capture.

## When to run

Run this skill when the user provides an object/character reference, or only a
concept that needs prepared reference views, and wants:

- a TypeScript Three.js factory
- a Form Blueprint and Feature Ledger
- a procedural product, prop, vehicle, scene, or stylized character
- reference-matched silhouette, materials, markings, camera, and lighting
- multi-view metrics and a recorded critique loop
- an explicitly labeled hybrid GLB body with in-repo materials and handles

## Non-goals

- photogrammetry, NeRF, or Gaussian splat as the primary deliverable
- silent use of downloaded or externally generated meshes
- claiming hidden-side or 360-degree truth from one photo
- masking weak geometry with dramatic lighting or texture noise

## Required inputs

Start with either an intent sentence or at least one image.

Collect when available:

1. image path, attachment, URL, or concept sentence
2. intended use, defaulting to a real-time browser prop
3. domain: `object` | `character` | `hybrid`
4. `qualityMode`: `draft` | `solid` | `sharp` | `razor` | `hybrid`
5. must-have identity features or redesign constraints

Do not block indefinitely on minor missing details. Use Reference Prep when the
evidence is too weak to cast safely.

## Quality modes

| Mode | Evidence and review | Intended use |
| --- | --- | --- |
| `draft` | metadata, one view, no fit | fast form sketch |
| `solid` | matte, edges, palette, four views | everyday props |
| `sharp` | full Sense Pack, 8–16 views, silhouette fit | default high fidelity |
| `razor` | full pack, 16+ views, larger search budget | hero assets |
| `hybrid` | full pack, user-approved GLB body | complex body with procedural finish/rig |

Record the mode in the blueprint. Never silently switch to `hybrid`.

## Vocabulary

Use these terms in artifacts and summaries:

| Term | Meaning |
| --- | --- |
| **Sense Pack** | matte, depth proxy, edges, palette, and part evidence |
| **Intake Brief** | class, complexity, domain, and Fidelity Pact |
| **Feature Ledger** | evidence-linked details mapped to implementation |
| **Form Blueprint** | hierarchy, materials, attachments, handles, search spaces, journal |
| **Reference Frame** | normalized dimensions, landmarks, projection, and camera lock |
| **Cast layers** | ordered implementation strata |
| **Critique Journal** | per-layer evidence, scores, metrics, and decision |
| **FormHandles** | pivots, sockets, colliders, and break groups on `root.userData.formHandles` |
| **Decision** | `accept` \| `replan` \| `recode` \| `ask` \| `abort` |

## Mandatory decision path

```text
Usable high-resolution or multi-view evidence?
  yes -> sense -> sufficiency -> brief -> ledger -> blueprint -> strict validate
         -> cast layers -> likeness synthesis -> render/metrics -> journal
  no  -> Reference Prep -> generate/capture views -> register -> sufficiency-set
         -> continue only after the gate permits it
```

A low-resolution single image may support a limited stylized interpretation,
but it does not support a claim of exact hidden geometry or human likeness.

## Working directory

Run commands from the skill/repository root:

```bash
python3 -m engine <command> ...
```

Keep generated JSON and review images under `work/`.

## Operating loop

### 1. Probe and build the Sense Pack

```bash
python3 -m engine probe <image>
python3 -m engine sense <image> --out work/sense --mode sharp
```

Read `work/sense/sense_pack.json` and its PNG maps before planning geometry.
Rules: `playbook/sense_pack.md`.

### 2. Run the sufficiency gate

Do not cast first and rationalize weak evidence later.

```bash
python3 -m engine sufficiency <image> \
  --sense work/sense \
  --domain object|character|hybrid \
  --intent realtime-prop|game|hero|likeness \
  --view-count <N> [--has-side] [--has-back] \
  --out work/sufficiency.json
```

Optional strict rerun after artifacts exist:

```bash
python3 -m engine sufficiency <image> --sense work/sense \
  --brief work/brief.json --ledger work/ledger.json \
  --blueprint work/blueprint.json --domain character --strict
```

Interpretation:

- `agentAction=continue`: proceed and record minor limitations
- `agentAction=ask`: obtain a view, crop, exposure, or missing evidence
- `agentAction=abort`: do not cast; return remedies or use Reference Prep

Full rules: `playbook/sufficiency.md` and `playbook/suitability.md`.

### 3. Reference Prep when evidence is thin

Do not stop at “need better images.” Emit a concrete GenerationBrief.

```bash
# Concept-first
python3 -m engine intake "modern fantasy knight" \
  --domain character --route concept-first \
  --out work/request-spec.json --brief-out work/generation-brief.json

# Existing weak reference plus sufficiency issues
python3 -m engine reference-prep work/request-spec.json \
  --issues work/sufficiency.json --seed-image <image> \
  --out work/generation-brief.json

# Register generated or captured views
python3 -m engine reference-register work/generation-brief.json \
  --images work/gen/front.png work/gen/side.png \
  --out work/reference-set.json
python3 -m engine sufficiency-set work/reference-set.json \
  --request work/request-spec.json --out work/sufficiency.json
```

Generated views are `design-intent` or `design-hypothesis`, never silently
`observed`. Reference defaults: `playbook/reference_prep.md`.

### 4. Author the Intake Brief and Fidelity Pact

```bash
python3 -m engine brief "SubjectName" --image <image> \
  --sense work/sense/sense_pack.json \
  --complexity moderate --domain object --out work/brief.json
```

Define the visible identity systems and acceptance floors before implementation.
Rules: `playbook/fidelity_pact.md`.

### 5. Build the Feature Ledger

```bash
python3 -m engine ledger <image> --sense work/sense \
  --out work/ledger.json --grid 3
```

Each entry must later map to real geometry, a material override, a decal, or a
runtime structure. Taxonomy: `playbook/feature_ledger.md`.

### 6. Author and validate the Form Blueprint

```bash
python3 -m engine blueprint "SubjectName" \
  --brief work/brief.json --ledger work/ledger.json \
  --sense work/sense/sense_pack.json --out work/blueprint.json
python3 -m engine validate work/blueprint.json
python3 -m engine validate work/blueprint.json --strict
```

A compound object needs a real part tree. Strict validation must reject a
single-root placeholder, unlinked ledger entries, missing attachments, and
undefined critical identity systems.

## Cast layers

Only modify and review the currently open layer:

1. `mass`: global silhouette, occupancy, and proportions
2. `skeleton`: connected hierarchy and attachments
3. `contour`: profiles, cutouts, bevels, rims, edge bands
4. `proportion`: character head units and pose, when applicable
5. `landmarks`: face/body placement, when applicable
6. `skin`: material regions, PBR channels, decals, local effects
7. `light`: camera-approved look-development rig
8. `handle`: pivots, sockets, colliders, break groups
9. `polish`: instancing, deterministic noise, LOD and performance

```bash
python3 -m engine layers status work/blueprint.json
python3 -m engine layers check work/blueprint.json --layer mass
python3 -m engine cast work/blueprint.json --out src/createSubjectForm.ts
```

Optional fit for `sharp` and `razor`:

```bash
python3 -m engine fit work/blueprint.json \
  --sense work/sense/sense_pack.json \
  --budget-sec 90 --workers 8 --in-place
```

Layer rules: `playbook/cast_layers.md`.

## Demo-derived likeness synthesis

For `sharp` and `razor`, this section is mandatory. Read
`playbook/demo_fidelity_patterns.md` before finalizing `mass`, `contour`,
`skin`, or `light`.

The strongest reference-matched showcase models repeatedly use these methods:

1. **Lock a normalized Reference Frame.** Store dominant dimension, bounds,
   landmarks, part extents, and attachment locations as ratios.
2. **Lock camera before detail.** Match projection, FOV, yaw, pitch, roll,
   target, crop, and object occupancy. Freeze the evaluation camera.
3. **Trace identity-carrying profiles.** Use `Shape` plus `ExtrudeGeometry`,
   lathed profiles, custom curves, or compound shells instead of generic boxes.
4. **Create true negative space.** Use `Shape.holes` or equivalent topology for
   wells, slots, vents, and cutouts that affect silhouette or orbit views.
5. **Keep continuous products continuous.** Prefer one outer shell with
   intentional parting lines over stacked rounded boxes and visible seams.
6. **Split contour treatments into geometry.** Edge grinds, sharpened bands,
   rims, trim, lips, and inlays need their own highlight-producing surfaces.
7. **Build ergonomic forms as compounds.** Combine scaled spheres,
   hemispheres, tubes, torus seams, pads, and transitions; do not ship one blob.
8. **Use curve tubes for ropes, hoses, wires, and wraps.** Add only low-amplitude,
   deterministic irregularity supported by the reference.
9. **Separate macro, meso, and micro evidence.** Macro is hierarchy, meso is
   geometry/instancing, micro is independent PBR maps and decals.
10. **Treat markings as identity.** Logos, labels, sidewall text, serials,
    warnings, L/R marks, and emblems must be implemented and scored.
11. **Localize wear and procedural variation.** Patina, dirt, marble, scratches,
    and glow appear only in evidence-defined regions.
12. **Use one subject-specific light rig.** Never stack default lights with a
    bespoke rig. Record tone mapping, exposure, environment intensity, and
    background with the blueprint.
13. **Validate volume with orbit views.** The primary view may match while a
    fake plane, dark-overlay hole, or floating attachment collapses off-axis.

Correct defects in this order: camera, silhouette, proportions, negative space,
attachments, contour bands, material regions, micro finish, markings, lighting.
Do not adjust a later category to conceal an earlier error.

## Surface detail stack

When primitives and clean contour geometry are insufficient:

```bash
python3 -m engine surface-annotate work/blueprint.json \
  --level high --in-place
python3 -m engine surface-bake --out work/surfaces \
  --level high --seed 42
```

Use maps for micro detail and shared/instanced geometry for meso repetition.
Runtime helpers include `physical`, `rivetRing`, and `edgeBand` in
`detail/surfaceKit.ts`. Rules: `playbook/surface_detail.md` and
`playbook/materials.md`.

## Render and multi-view critique

Capture a deterministic primary view and volume-check views.

```bash
python3 -m engine sheet --reference <image> --render <shot> \
  --out work/cmp.png
python3 -m engine grid --reference <image> --renders work/views \
  --sense work/sense --out work/grid.png --metrics work/metrics.json
python3 -m engine metrics --reference <image> --render <shot> \
  --matte work/sense/matte.png --out work/metrics.json
```

Evaluation mode should use a fixed camera, stable exposure, no animation, and a
background/contact-shadow setup compatible with the reference matte. Orbit views
check volume, attachment, and true cutouts; they are not evidence for unseen-side
likeness.

## Record the Critique Journal decision

```bash
python3 -m engine journal work/blueprint.json --layer mass \
  --fidelity 0.82 --decision accept --vision 0.8 \
  --metrics work/metrics.json --summary "..." \
  --render <shot> --sheet work/cmp.png --in-place
python3 -m engine layers sync work/blueprint.json --in-place
```

Accept only when:

- a comparison sheet or grid exists
- the global vision score meets the Fidelity Pact
- every critical identity system meets its own floor
- required metric floors pass for `solid+`
- non-planar forms survive at least two orbit views
- the current layer is correct without compensation from later layers

After each layer choose exactly one:

- `accept`: advance
- `replan`: blueprint/evidence interpretation is wrong
- `recode`: blueprint is sound but implementation is wrong
- `ask`: more evidence or explicit permission is required
- `abort`: requested fidelity is not feasible

Rules: `playbook/critique.md`.

## Implementation rules

- TypeScript and plain Three.js unless the host project already has a wrapper
- factory signature: `create<Name>Form(blueprint, options?) => THREE.Group`
- expose `root.userData.formHandles`
- keep reconstruction ratios/data separate from renderer objects
- deterministic seeds for every procedural pattern and jitter source
- prefer primitives, `Shape` extrusion, lathe/custom profiles, curve tubes,
  shared geometry, instancing, and canvas textures
- use true geometry for silhouette-critical holes and cutouts
- use separate surfaces for strong edge/rim/grind highlight breaks
- use `SRGBColorSpace` only for color textures and decals
- keep roughness, normal/bump, AO, emissive, and albedo independent
- localize procedural wear/noise to evidence-defined regions
- child parts declare parent socket, contact, embed/overlap, and tolerance
- use one approved light rig and a deterministic evaluation camera
- do not add animation until still fidelity passes
- hybrid bodies set `bodySource: "hybrid-glb"` and remain explicit

## Required reading

| Topic | Document |
| --- | --- |
| Demo-derived likeness construction | `playbook/demo_fidelity_patterns.md` |
| Reference Prep | `playbook/reference_prep.md` |
| Sufficiency codes | `playbook/sufficiency.md` |
| Suitability | `playbook/suitability.md` |
| Fidelity Pact | `playbook/fidelity_pact.md` |
| Feature Ledger | `playbook/feature_ledger.md` |
| Cast layers | `playbook/cast_layers.md` |
| Surface detail | `playbook/surface_detail.md` |
| Materials | `playbook/materials.md` |
| Metrics | `playbook/metrics.md` |
| Critique decisions | `playbook/critique.md` |

## Outputs

- **Analysis only:** suitability, evidence limits, Intake Brief, Feature Ledger,
  normalized Reference Frame, geometry/material/camera plan, and risks
- **Implementation:** blueprint JSON, factory TypeScript, renders, metrics, and
  Critique Journal
- **Not feasible:** explicit blocker and the exact additional views, mode, or
  accepted stylization needed to continue

## Honesty

One image cannot prove hidden geometry or exact micromesh. Report approximation,
stylization, low-poly choices, and per-region character confidence openly. A
primary-view match is not permission to claim 360-degree likeness. Hybrid is
never the silent default.
