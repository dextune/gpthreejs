# Cast Layers

Strict order. Only the **open** layer may be implemented and reviewed.

| Layer | Goal | Typical gates |
|-------|------|---------------|
| `mass` | Silhouette volumes | mask IoU, overall fidelity |
| `skeleton` | Hierarchy + attachments | no floaters |
| `contour` | Profiles, bevels | edge F1 |
| `skin` | PBR + ledger | palette, material realism |
| `light` | Real lights | shading, no baked albedo fights |
| `handle` | FormHandles | pivots/sockets present |
| `polish` | Perf, seeds, LOD hints | determinism |

Character/hybrid inserts before `skin`:

| Layer | Goal |
|-------|------|
| `proportion` | Head-units + pose |
| `landmarks` | Face/body placement |

## State

- `locked` — cannot touch  
- `open` — active  
- `done` — accepted  

`python3 -m engine layers sync work/blueprint.json --in-place` advances after journal `accept`.
