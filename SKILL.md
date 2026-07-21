---
name: gpthreejs
description: >
  Lock a reference photo into a fidelity-gated, multi-view-checked, CPU-assisted
  procedural Three.js form written as TypeScript. Use for image→3D code, product
  props, hard-surface rebuilds, stylized characters, multi-view metric review,
  perception packs, and parameter search. Triggers: /gpthreejs, photo to Three.js,
  reconstruct object as code, image to 3D factory, reference-locked mesh code.
license: MIT
version: 0.1.0
metadata:
  short-description: "Photo → gated procedural Three.js form"
---

# gpthreejs

Turn one reference image into a **procedural Three.js factory** that is locked
to the photo by **CPU perception**, **multi-view metrics**, and a **layered cast
loop**. Output is editable TypeScript — not a downloaded mesh pack and not a
one-shot chat blob.

Host-agnostic: use native image read, browser MCP, project preview, or a user
screenshot wherever this doc says “look” or “capture.”

## When to run

User attaches or points at an object/character image and wants:
- a Three.js `Group` factory in TypeScript
- a Form Blueprint + Feature Ledger before code
- multi-view fidelity checks (mask IoU, SSIM, edge F1)
- optional hybrid import of an external GLB as a draft body

## Non-goals

- Photogrammetry / NeRF / Gaussian splat as the primary deliverable
- Silent use of external mesh generators (hybrid is opt-in and labeled)
- Claiming photoreal 360° truth from a single photo

## Quality tiers (`qualityMode`)

| Mode | Sense pack | Views | Param fit | Neural body |
|------|------------|-------|-----------|-------------|
| `draft` | metadata only | 1 | no | no |
| `solid` | matte + edges + palette | 4 | no | no |
| `sharp` (default) | full pack | 8–16 | mass silhouette fit | no |
| `razor` | full pack | 16+ | full search | optional SDS notes |
| `hybrid` | full pack | 8–16 | materials | user/local GLB draft |

Record the mode on the blueprint. Never silently upgrade to `hybrid`.

## Vocabulary (use these terms only)

| Term | Meaning |
|------|---------|
| **Sense Pack** | CPU-derived maps: matte, depth proxy, edges, palette, part boxes |
| **Intake Brief** | Class, complexity, domain, Fidelity Pact |
| **Feature Ledger** | Evidence-linked micro features that must map to geometry/materials |
| **Form Blueprint** | Full hierarchy, materials, handles, search spaces, journal |
| **Cast layers** | Ordered build strata (see below) |
| **Critique Journal** | Per-layer scores, metrics, decision |
| **FormHandles** | Runtime pivots/sockets/colliders on `root.userData.formHandles` |
| **Decision** | `accept` \| `replan` \| `recode` \| `ask` \| `abort` |

Stick to this vocabulary in blueprints, journals, and user-facing summaries.

## Cast layers (strict order)

Only implement and review the **unlocked** layer:

1. `mass` — silhouette volumes, proportions  
2. `skeleton` — part hierarchy, attachments, handles  
3. `contour` — bevels, profiles, silhouettes per part  
4. `skin` — PBR materials, local overrides, ledgers  
5. `light` — real lights, env cues, no albedo-as-roughness  
6. `handle` — FormHandles: pivots, sockets, colliders, break groups  
7. `polish` — instancing, LOD hints, determinism, perf  

Characters/hybrids insert before `skin`:
- `proportion` — head-units + pose  
- `landmarks` — face/body feature placement  

## Operating loop

Numbers and gates come from the engine; visual identity judgments stay with you.
Run commands from the skill root:

```bash
python3 -m engine <command> ...
```

### 1) Probe + Sense Pack

```bash
python3 -m engine probe <image>
python3 -m engine sense <image> --out work/sense --mode sharp
```

Read `work/sense/sense_pack.json` and the PNG maps before drafting.  
Rules: `playbook/sense_pack.md`.

### 1b) Sufficiency gate — do not skip

After sense (or immediately if sense fails), **always** run:

```bash
python3 -m engine sufficiency <image> \
  --sense work/sense \
  --domain object|character|hybrid \
  --intent realtime-prop|game|hero|likeness \
  --view-count <N> [--has-side] [--has-back] \
  --out work/sufficiency.json
```

Optional after specs exist:

```bash
python3 -m engine sufficiency <image> --sense work/sense \
  --brief work/brief.json --ledger work/ledger.json --blueprint work/blueprint.json \
  --domain character --strict
```

| Report field | Meaning |
|--------------|---------|
| `verdict` | `pass` \| `conditional` \| `reject` |
| `sufficient` | bool — safe to cast? |
| `agentAction` | `continue` \| `ask` \| `abort` |
| `issues[]` | code, severity, message, **remedy** |
| `userMessage` | Korean end-user summary returned verbatim |

**Rules**

- `agentAction=abort` → **no cast/codegen**; show remedies.  
- `agentAction=ask` → request more views / crop / exposure / fill ledger; state stylization limits.  
- `agentAction=continue` → proceed; log minor issues in the journal.  
- Character + single view → treat `CHAR_*` majors seriously; never claim full likeness.

Full codes: `playbook/sufficiency.md`. Topic suitability: `playbook/suitability.md`.

### 2) Intake Brief + Fidelity Pact

```bash
python3 -m engine brief "SubjectName" --image <img> --sense work/sense/sense_pack.json \
  --complexity moderate --domain object --out work/brief.json
```

Fill domain: `object` | `character` | `hybrid`.  
Pact rules: `playbook/fidelity_pact.md`.

### 3) Feature Ledger

```bash
python3 -m engine ledger <image> --sense work/sense --out work/ledger.json --grid 3
```

Every ledger entry **must** later `mapsTo` a blueprint part feature or material
override. Taxonomy: `playbook/feature_ledger.md`.

### 4) Form Blueprint

```bash
python3 -m engine blueprint "SubjectName" --brief work/brief.json --ledger work/ledger.json \
  --sense work/sense/sense_pack.json --out work/blueprint.json
```

Author real parts (not a single root for compound objects). Use graphics terms
from `playbook/vocabulary.md`.

### 5) Validate

```bash
python3 -m engine validate work/blueprint.json
python3 -m engine validate work/blueprint.json --strict
```

`--strict` blocks shallow blueprints and unlinked ledger rows.

### 6) Cast current layer only

```bash
python3 -m engine layers status work/blueprint.json
python3 -m engine layers check work/blueprint.json --layer mass
python3 -m engine cast work/blueprint.json --out src/createSubjectForm.ts
```

Optional CPU fit (sharp/razor):

```bash
python3 -m engine fit work/blueprint.json --sense work/sense/sense_pack.json \
  --budget-sec 90 --workers 8 --in-place
```

Recipes: `playbook/cast_layers.md`, `playbook/materials.md`, `playbook/surface_detail.md`.

### 6b) Surface detail stack (generic — any subject)

Attach micro/meso stack and bake maps when fidelity needs more than primitives:

```bash
python3 -m engine surface-annotate work/blueprint.json --level high --in-place
python3 -m engine surface-bake --out work/surfaces --level high --seed 42
```

Runtime Three.js: use `detail/surfaceKit.ts` (`physical`, `rivetRing`, `edgeBand`).
Prefer maps for micro; InstancedMesh for fasteners. See `playbook/surface_detail.md`.


### 7) Render + multi-view critique

Capture renders (browser MCP or host preview). Package:

```bash
python3 -m engine sheet --reference <img> --render <shot> --out work/cmp.png
python3 -m engine grid --reference <img> --renders work/views --sense work/sense \
  --out work/grid.png --metrics work/metrics.json
python3 -m engine metrics --reference <img> --render <shot> --matte work/sense/matte.png \
  --out work/metrics.json
```

### 8) Journal decision

```bash
python3 -m engine journal work/blueprint.json --layer mass \
  --fidelity 0.82 --decision accept \
  --vision 0.8 --metrics work/metrics.json \
  --summary "..." --render <shot> --sheet work/cmp.png --in-place
python3 -m engine layers sync work/blueprint.json --in-place
```

**Accept** only if:
- comparison sheet (or grid) exists  
- vision score ≥ pact threshold (default 0.7)  
- every critical feature ≥ its floor  
- metric floors pass when `qualityMode` is `solid+` (see `playbook/metrics.md`)

## Decisions after each layer

Exactly one: `accept` | `replan` | `recode` | `ask` | `abort`.

- `replan` — blueprint wrong/shallow → edit blueprint, re-validate  
- `recode` — blueprint sound, implementation wrong  
- `ask` — need another view / cleaner crop / hybrid permission  
- `abort` — not feasible; say so clearly  

Guide: `playbook/critique.md`.

## Implementation rules

- TypeScript + plain Three.js unless the host project already wraps it  
- Factory signature: `create<Name>Form(blueprint, options?) => THREE.Group`  
- Expose `root.userData.formHandles`  
- Deterministic seeds for noise  
- Prefer primitives, Shape extrude, curve tubes, instancing, canvas textures  
- Independent PBR channels — never alias albedo into roughness  
- Child parts declare attachment (parent socket, contact, embed) — no floaters  
- Hybrid bodies: set `bodySource: "hybrid-glb"` and keep materials/handles in-repo  

## Required inputs

1. Image path / attachment / URL  
2. Intended use (default: real-time browser prop)  
3. `qualityMode` if user cares about fidelity vs speed  

If the image is unreadable or unsuitable, run suitability from
`playbook/suitability.md` and `ask` or `abort`.

## Outputs

- **Analysis only:** suitability, Intake Brief, ledger, plan, risks  
- **Implementation:** above + factory TS + blueprint JSON + critique journal  
- **Not feasible:** blocker + what extra views/mode would unlock progress  

## Honesty

One photo cannot guarantee hidden sides or exact micromesh. Report approximate /
stylized / low-poly openly. Per-region confidence for characters. Hybrid is never
the silent default.
