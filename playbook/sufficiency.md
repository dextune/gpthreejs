# Sufficiency Gate

Evaluate whether the reference image or specification artifacts are sufficient
to run gpthreejs. When they are not, return issue codes, remedies, and the
required agent action.

## When

Run this immediately after the Sense Pack, or after the brief, ledger, and
blueprint exist. It must run before code generation.

```bash
python3 -m engine sufficiency <image> \
  --sense work/sense \
  --domain character \
  --intent game \
  --view-count 1 \
  --out work/sufficiency.json

# CI / hard gate
python3 -m engine sufficiency <image> --sense work/sense --strict
# exit 2 = not sufficient, exit 3 = reject (blocker)
```

Options:

| Flag | Meaning |
|--------|------|
| `--sense` | `sense_pack.json` or its directory |
| `--brief` / `--ledger` / `--blueprint` | specification artifacts |
| `--domain` | object \| character \| hybrid |
| `--intent` | realtime-prop, game, playable, animation, hero, likeness… |
| `--view-count` | number of available reference views |
| `--has-side` / `--has-back` | whether side or back views exist |
| `--strict` | exit 2 when `sufficient=false` |

## Verdict

| verdict | sufficient | agentAction | Meaning |
|---------|------------|-------------|------|
| `pass` | true | `continue` | safe to proceed |
| `conditional` | false/true* | `ask` or `continue` | major issues ask; minor-only issues can continue |
| `reject` | false | `abort` | blocker; casting is forbidden |

\* Minor or info-only issues can be promoted to `pass`.

## Issue severity

| severity | Examples |
|----------|-----|
| **blocker** | missing file, unreadable resolution, tiny subject, all ledger rows are todo, no parts |
| **major** | dark exposure, character single view, sparse ledger, missing anatomy |
| **minor** | JPEG to PNG recommended, missing surface stack for a high-quality mode |
| **info** | Sense Pack not run, heuristic matte |

Each issue includes `code`, `message`, `remedy`, and optional `evidence`. The
runtime may localize `message` or `userMessage`, but this playbook remains in
English.

## Reference Prep handoff

On `abort` / `ask`, the engine attaches a **GenerationBrief** (inline and, when
`--out` is set, `generation-brief.json` next to the report). User messages include
a capture/gen checklist (resolution, transparent or solid neutral background,
front/side views, pose). Do not cast until prep + re-sufficiency succeed.

Full prep loop: `playbook/reference_prep.md`.

## Agent routine

1. Run `sufficiency` immediately after image intake, then rerun after sense when possible.  
2. Deliver `userMessage` to the user verbatim or as a faithful summary.  
3. `agentAction`:
   - **abort**: do not cast or generate code; request the blocker remedy.  
   - **ask**: request more views, a crop, better exposure, or ledger completion; wait.  
   - **continue**: record minor issues in the journal and proceed.  
4. For a character with a single view, explicitly state that side views are
   needed or that the result is stylized with lower confidence.

## Representative codes

| code | Summary |
|------|------|
| `FILE_MISSING` / `FILE_UNREADABLE` | path or decode failure |
| `RES_TOO_LOW` / `RES_MARGINAL` | resolution |
| `EXPOSURE_DARK` / `EXPOSURE_BRIGHT` | exposure |
| `SUBJECT_TOO_SMALL` / `SUBJECT_SMALL` | foreground ratio |
| `EDGE_TOO_FEW` | insufficient form information, such as a flat swatch |
| `CHAR_SINGLE_VIEW` / `CHAR_NO_SIDE` | missing character views |
| `LEDGER_ALL_TODO` / `LEDGER_SPARSE` / `LEDGER_UNMAPPED` | detail specification |
| `BP_NO_ANATOMY` / `BP_SHALLOW_TREE` | character or complex-object specification |

## Output shape

```json
{
  "verdict": "conditional",
  "sufficient": false,
  "score": 0.64,
  "agentAction": "ask",
  "issues": [ { "code": "CHAR_NO_SIDE", "severity": "major", "message": "...", "remedy": "..." } ],
  "userMessage": "...",
  "nextSteps": [ "Request side turnaround images." ]
}
```
