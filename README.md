<p align="center">
  <img src="docs/assets/chatgpt-threejs-banner.png" alt="ChatGPT x Three.js banner" width="100%">
</p>

<h1 align="center">gpthreejs</h1>

<p align="center">
  <strong>Reference images into fidelity-gated procedural Three.js forms.</strong>
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-blue.svg"></a>
  <a href="SKILL.md"><img alt="Version 0.2.0" src="https://img.shields.io/badge/version-0.2.0-green.svg"></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-3776AB.svg">
  <img alt="Three.js" src="https://img.shields.io/badge/Three.js-procedural-8bc34a.svg">
</p>

gpthreejs is a code-first pipeline for turning reference evidence into an
editable TypeScript `THREE.Group` factory. It uses CPU perception, strict
blueprint validation, demo-derived reconstruction patterns, multi-view metrics,
and critique journals to keep generated geometry tied to visible evidence.

It is not photogrammetry and it does not silently download a mesh. The primary
deliverable is source code that remains inspectable, diffable, and editable.

## What you get

| Artifact | Purpose |
| --- | --- |
| `sense_pack.json` and maps | Matte, depth proxy, edges, palette, and part evidence |
| `brief.json` | Subject class, complexity, and Fidelity Pact |
| `ledger.json` | Evidence-linked identity and surface features |
| `blueprint.json` | Part hierarchy, Reference Frame, materials, handles, and journal |
| `createXxxForm.ts` | Procedural Three.js factory returning a `THREE.Group` |
| comparison sheets and metrics | Primary-view fidelity and orbit-volume checks |

## Install as a ChatGPT/Codex skill

Clone directly into the Codex skill directory:

```bash
git clone https://github.com/dextune/gpthreejs.git ~/.codex/skills/gpthreejs
```

For an existing checkout:

```bash
mkdir -p ~/.codex/skills
cp -a . ~/.codex/skills/gpthreejs
```

Requirements:

- Python 3.10 or newer
- standard library only for the core CLI
- optional CPU vision extras for richer local analysis

```bash
pip install -r engine/extras/requirements-cpu.txt
```

Invoke it with a reference image:

```text
/gpthreejs Rebuild this object as a Three.js form. qualityMode=sharp.
```

## Pipeline

```text
image or concept
  -> Sense Pack / Reference Prep
  -> sufficiency gate
  -> Intake Brief + Fidelity Pact
  -> Feature Ledger
  -> Form Blueprint + normalized Reference Frame
  -> strict validation
  -> cast layers
  -> demo-derived likeness synthesis
  -> deterministic primary render + orbit views
  -> metrics and critique
  -> accept | replan | recode | ask | abort
```

Example CLI flow:

```bash
python3 -m engine probe samples/demo.png
python3 -m engine sense samples/demo.png --out work/sense --mode sharp
python3 -m engine sufficiency samples/demo.png --sense work/sense \
  --domain object --intent realtime-prop --view-count 1 \
  --out work/sufficiency.json
python3 -m engine brief "FieldRadio" --image samples/demo.png \
  --sense work/sense/sense_pack.json --out work/brief.json
python3 -m engine ledger samples/demo.png --sense work/sense \
  --out work/ledger.json
python3 -m engine blueprint "FieldRadio" --brief work/brief.json \
  --ledger work/ledger.json --sense work/sense/sense_pack.json \
  --out work/blueprint.json
python3 -m engine validate work/blueprint.json --strict
python3 -m engine cast work/blueprint.json --out src/createFieldRadioForm.ts
python3 -m engine metrics --reference samples/demo.png \
  --render work/view.png --matte work/sense/matte.png \
  --out work/metrics.json
```

## Quality modes

| Mode | Use when |
| --- | --- |
| `draft` | A fast form sketch is enough |
| `solid` | An everyday prop needs basic evidence checks |
| `sharp` | Default high-quality reconstruction with CPU fit and multi-view review |
| `razor` | A hero asset justifies a larger search and review budget |
| `hybrid` | An external GLB body is explicitly approved |

## Demo-derived likeness reconstruction

Version 0.2 adds a mandatory high-fidelity synthesis stage based on recurring
methods observed in the strongest `img2threejs-showcase` demos:

- normalized landmark and proportion ratios
- camera/FOV/crop lock before detail
- custom profile extrusion instead of stacked primitive approximation
- real topology for holes, wells, slots, and vents
- continuous product shells and explicit contour bands
- compound ergonomic forms and curve-tube wraps
- macro/meso/micro evidence separation
- independent PBR channels and localized deterministic wear
- decals as scored identity features
- one reference-specific light rig with fixed tone mapping and exposure
- primary-view comparison plus orbit validation

See [playbook/demo_fidelity_patterns.md](playbook/demo_fidelity_patterns.md).

## Sufficiency and Reference Prep

Run sufficiency before production casting. If evidence is too weak, the agent
must return remedies or generate a concrete reference-capture brief rather than
producing shallow code.

```bash
python3 -m engine sufficiency samples/knight/knight_01_hero_34.png \
  --sense demo/work/sense --domain character --intent game \
  --view-count 1 --out work/sufficiency.json
```

Key fields:

- `verdict`: `pass`, `conditional`, or `reject`
- `agentAction`: `continue`, `ask`, or `abort`
- `issues[]`: reason and remedy
- `userMessage`: end-user summary

See [playbook/sufficiency.md](playbook/sufficiency.md) and
[playbook/reference_prep.md](playbook/reference_prep.md).

## Surface detail

Use the generic micro/meso detail stack only after silhouette and contour are
correct:

```bash
python3 -m engine surface-annotate work/blueprint.json --level high --in-place
python3 -m engine surface-bake --out work/surfaces --level high --seed 42
```

Runtime helpers live in `demo/src/detail/surfaceKit.ts`:

- `physical(role)`
- `rivetRing`
- `edgeBand`

Use maps for micro detail, shared/instanced geometry for meso repetition, and
real geometry for silhouette or strong highlight breaks. See
[playbook/surface_detail.md](playbook/surface_detail.md).

## Documentation

| Area | Document |
| --- | --- |
| Skill instructions | [SKILL.md](SKILL.md) |
| Demo-derived fidelity | [playbook/demo_fidelity_patterns.md](playbook/demo_fidelity_patterns.md) |
| Reference Prep | [playbook/reference_prep.md](playbook/reference_prep.md) |
| Sufficiency | [playbook/sufficiency.md](playbook/sufficiency.md) |
| Fidelity Pact | [playbook/fidelity_pact.md](playbook/fidelity_pact.md) |
| Cast layers | [playbook/cast_layers.md](playbook/cast_layers.md) |
| Surface detail | [playbook/surface_detail.md](playbook/surface_detail.md) |
| Documentation index | [docs/readme.md](docs/readme.md) |
| ChatGPT App | [docs/app/chatgpt-app.md](docs/app/chatgpt-app.md) |
| Security | [docs/app/security.md](docs/app/security.md) |
| Privacy | [docs/app/privacy.md](docs/app/privacy.md) |
| Runbook | [docs/app/runbook.md](docs/app/runbook.md) |

## Repository layout

```text
SKILL.md       Agent instructions
engine/        CLI and pure Python pipeline
playbook/      Runtime rubrics and reconstruction recipes
docs/          Project and application documentation
examples/      Sample blueprints
samples/       Reference images
demo/          Three.js preview project
tests/         Python smoke and regression tests
```

## Design principles

1. Lock camera and silhouette before material polish.
2. Use engine metrics as floors and agent judgment for identity.
3. Spend CPU on matte, edges, depth proxy, and fit before more code generation.
4. Build true cutouts and connected hierarchy instead of view-only cheats.
5. Use geometry for macro/meso identity and maps for micro finish.
6. Keep procedural variation deterministic and localized.
7. Ship editable source instead of opaque assets.
8. Admit blind sides; one photo does not prove hidden geometry.

## License

MIT. See [LICENSE](LICENSE).
