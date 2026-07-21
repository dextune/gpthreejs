# Materials

Use independent PBR channels on `MeshPhysicalMaterial` / `MeshStandardMaterial`.

## Required fields

- `baseColor` (hex or rgb)  
- `roughness`  
- `metalness`  
- `overrides[]` for regional changes (maps to ledger)  

## Forbidden

- Encoding roughness by only darkening albedo  
- Fake metal with yellow albedo and metalness 0  
- Skipping bevels when the ledger lists gloss rims  

## Recipes (short)

| Look | Tips |
|------|------|
| Plastic | roughness 0.3–0.55, subtle clearcoat |
| Metal | metalness ≥ 0.7, roughness 0.15–0.4, edge wear |
| Paint enamel | clearcoat 0.4–0.8, color from palette |
| Cloth | high roughness, soft normal, stitch ledger |
