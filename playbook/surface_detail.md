# Surface Detail Stack (generic)

Domain-agnostic micro / meso detail for **any** gpthreejs subject (props, hard-surface, characters).

## Principle

| Band | Prefer | Avoid |
|------|--------|--------|
| Macro | Hierarchy, proportions, formHandles | — |
| Meso | Edge bands, panel splits, **InstancedMesh** rivets | Hundreds of separate Mesh rivets |
| Micro | Procedural **normal + roughness (+ AO)** maps | Triangle spam for grain |

`preferMapsOverGeometry: true` is the default budget rule.

## Blueprint fields

After `surface-annotate` or default draft:

```json
{
  "surfaceStack": {
    "version": 1,
    "detailLevel": "high",
    "resolution": 512,
    "seed": 42,
    "bands": { "macro": true, "meso": true, "micro": true },
    "maps": { "normal": true, "roughness": true, "ao": true },
    "meso": { "instancedRivets": true, "edgeTrim": true, "panelLines": true }
  },
  "materials": [
    {
      "id": "mat_steel",
      "surfaceRole": "metal",
      "surface": { "useNormal": true, "useRoughness": true, "useAo": true }
    }
  ]
}
```

### `surfaceRole` presets

`metal` · `painted_metal` · `brass` · `cloth` · `leather` · `rubber` · `plastic` · `wood` · `stone` · `skin` · `emissive` · `default`

## CLI

```bash
# Bake offline PNG maps (stdlib)
python3 -m engine surface-bake --out work/surfaces --level high --seed 42

# Annotate any blueprint
python3 -m engine surface-annotate work/blueprint.json --level high --in-place
```

## Runtime (Three.js)

```ts
import { createSurfaceLibrary, detailLevelFromQualityMode } from "./detail/surfaceKit";

const lib = createSurfaceLibrary({
  detailLevel: detailLevelFromQualityMode("sharp"), // low|medium|high|ultra
  seed: 42,
});

const steel = lib.physical("metal", { color: "#7a8fa3", metalness: 0.9 });
const brass = lib.physical("brass", { color: "#c9a14a" });
const cloth = lib.physical("cloth", { color: "#9a1f2e", sheen: 0.2 });

lib.rivetRing(parent, { radius: 0.2, count: 12, material: brass });
lib.rivetGrid(parent, { width: 0.3, height: 0.4, cols: 3, rows: 4, z: 0.1, material: brass });
lib.edgeBand(parent, { material: brass, size: [0.4, 0.02, 0.28], position: [0, 0.2, 0] });
```

Ship `demo/src/detail/surfaceKit.ts` with any factory (knight, prop, vehicle).

## Detail levels

| Level | Maps | Rivets | Use |
|-------|------|--------|-----|
| `low` | none | off | draft blockout |
| `medium` | 256 | few | solid props |
| `high` | 512 + AO | rings + grids | default sharp |
| `ultra` | 1024 | denser | hero / razor |

## Quality modes → levels

| qualityMode | detailLevel |
|-------------|-------------|
| draft | low |
| solid | medium |
| sharp | high |
| razor | ultra |
| hybrid | high |

## Checklist for new subjects

1. Assign each material a `surfaceRole`.  
2. Run `surface-annotate` (or rely on draft).  
3. In factory code, build materials via `lib.physical(role, …)`.  
4. Add meso only where silhouette breaks: trims, fasteners, panel lips.  
5. Keep identity marks as **decals / simple meshes**, micro as **maps**.
