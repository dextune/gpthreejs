# Reference Prep

Reference Prep is the **input reinforcement** step between sufficiency
`abort` / `ask` / `generate_more` (or **no image**) and cast. It does **not**
relax gates: after prep, sufficiency and delivery-export still apply.

Related: `playbook/sufficiency.md`, `playbook/suitability.md`,
`docs/planning/intake-and-reference-prep-upgrade.md`.

## When

Run Reference Prep when any of the following is true:

- User provides **intent text only** (no image) → route `concept-first`
- Sufficiency returns `abort` or `ask` (resolution, single view, thin coverage)
- Agent would otherwise stop with only “need better images”

Do **not** skip prep and force cast on thin evidence.

## Operating loop

```text
1c) Reference Prep
    - emit GenerationBrief
    - if host can generate images: produce views under brief
    - register ReferenceSet with correct evidenceClass
    - re-run sufficiency-set
    - only then cast
```

CLI:

```bash
# Text-only / concept-first
python3 -m engine intake "modern fantasy knight" \
  --domain character --route concept-first \
  --out work/request-spec.json \
  --brief-out work/generation-brief.json

# From sufficiency issues or RequestSpec
python3 -m engine reference-prep work/request-spec.json \
  --issues work/sufficiency.json \
  --seed-image optional.png \
  --out work/generation-brief.json

# Register generated/captured views (honest evidence)
python3 -m engine reference-register work/generation-brief.json \
  --images work/gen/front.png work/gen/side.png \
  --out work/reference-set.json

python3 -m engine sufficiency-set work/reference-set.json \
  --request work/request-spec.json --out work/sufficiency.json
```

Engine constants live in `engine/reference/capture_defaults.py` (shared with
brief builders — do not duplicate magic numbers in prose-only forks).

## Capture / generation defaults (RP-002)

| Item | Default | Notes |
| --- | --- | --- |
| Short side | ≥ **512px** recommended (hard floor **256px**) | Aligns with `RES_*` policy |
| Background | transparent PNG or solid neutral (`#808080`) | Matte stability |
| Aspect | **1:1** recommended, free allowed | Short-side is truth |
| Views (character) | **front + side** required; **back** recommended | `CHAR_*`, delivery multi-view |
| Pose | A-pose / T-pose, camera-relative | Proportions & attachments |
| Lighting | Soft studio; avoid harsh rim | Edge / silhouette maps |
| Files | One view per file, PNG | Sense/ledger simplicity |

## GenerationBrief (machine)

Minimum fields: `schemaVersion`, `subject`, `route`, `evidenceClassDefault`,
`views[]`, `frame`, `pose`. See `engine/reference/generation_brief.py`.

| Route | Meaning |
| --- | --- |
| `photo-lock` | Enough real refs; normalize only |
| `redesign-from-ref` | Low-quality seed + new design-intent views |
| `concept-first` | Text only → full generated turnaround |
| `hybrid-body` | Existing hybrid policy |

### Evidence honesty (EV-001)

| Origin | Allowed `evidenceClass` |
| --- | --- |
| User upload / seed | `observed` |
| 2D gen from brief | `design-intent` or `design-hypothesis` |
| Symmetry pad | `inferred` only — never sole side for delivery |

**Never** label generated views as silent `observed`. Validators reject
`origin=generated|edited|provider` with `evidenceClass=observed`.

### redesign-from-ref

- Seed image: `observed`, role `identity-seed` (low-res matte ok, marked)
- New turnaround: `design-intent`
- Fidelity pact: `redesign: true`, `likenessFloor: stylized`, no pixel-match duty
- Do not claim original-sprite reconstruction

## Agent speech (SK-002)

When blocked, user-facing text must include:

1. **Why** (issue codes)
2. **Capture/gen checklist** (table above)
3. Choices: **(A)** host generates under brief **(B)** user uploads **(C)**
   explicit limited-info stylization waiver (default: discouraged)

Korean and English checklist strings are emitted by
`prep_checklist_message()` and attached to sufficiency `userMessage` /
`nextSteps` on abort/ask.

Example next steps:

1. Write GenerationBrief (`reference-prep`)
2. Generate or capture front/side under frame defaults
3. `reference-register` with `design-intent`
4. Re-run `sufficiency-set`; only then cast

## Required inputs (product)

1. **Intent sentence OR image** (either is enough to start)
2. Intended use
3. `qualityMode` (optional)

| Input | Route |
| --- | --- |
| No image | `concept-first` → prep → register → sufficiency → cast |
| Thin / low-res image | prep with seed → gen views → re-enter sufficiency |
| Sufficient multi-view | skip prep; existing pipeline |

## Non-goals

- Softening `RES_TOO_LOW` or multi-view delivery hard gates
- Auto aesthetic accept of gen images
- Claiming 360° likeness from one low-res sprite
- Vendor image SDK as engine core dependency
