# Performance Budgets

Performance budgets determine whether a package can be called game-ready.

## Initial Profiles

| Profile | Actor target | p95 frame time | Triangles | Bones | Materials | Skin influences |
| --- | --- | --- | --- | --- | --- | --- |
| `web-mobile` | 1 hero actor | `<= 33.3 ms` | `<= 50k` | `<= 80` | `<= 8` | `<= 4` |
| `web-desktop` | 10 actors | `<= 16.7 ms` | `<= 100k` per actor | `<= 120` | `<= 12` | `<= 4` |

Budgets must record device, browser, resolution, actor count, renderer settings,
and measurement date.

## Metrics

- triangles
- vertices
- bones
- materials
- draw calls
- texture memory
- animation update cost
- p50 frame time
- p95 frame time

## Policy

- Exceeding a budget returns measured values and remedies.
- Do not silently lower LOD and still mark the package production-ready.
- LOD and animation update policy must be recorded in the package manifest.
