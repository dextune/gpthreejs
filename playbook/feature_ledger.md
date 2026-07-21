# Feature Ledger

Evidence-linked micro features. Prose-only details are invalid under `--strict`.

## Kinds

`gloss` `bevel` `fastener` `linework` `contour` `seam` `stitch` `stain` `scratch` `chip` `decal` `emissive` `hole` `groove` `ridge`

## Entry shape

```json
{
  "id": "lid-bevel-gloss",
  "kind": "gloss",
  "description": "bright rim along upper chamfer under key light",
  "region": { "x": 0.2, "y": 0.1, "w": 0.6, "h": 0.1, "units": "normalized" },
  "scale": "meso",
  "affects": "material",
  "mapsTo": { "type": "override", "ref": "mat_primary/top-gloss" },
  "confidence": 0.8,
  "status": "filled"
}
```

## Mapping rules

- `gloss` → low roughness / clearcoat override  
- `bevel` → real geometry edge treatment, not only a normal map  
- `fastener` → instanced meso parts  
- `linework` → groove geometry **or** decal — pick from evidence  
- every `mapsTo.ref` must exist on the blueprint  

Scaffold: `python3 -m engine ledger <img> --sense work/sense --out work/ledger.json`
