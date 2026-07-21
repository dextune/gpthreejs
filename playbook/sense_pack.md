# Sense Pack

CPU-derived perception bundle consumed **before** authoring a Form Blueprint.

## Maps

| File | Meaning | Use |
|------|---------|-----|
| `matte.png` | Foreground alpha | Silhouette, bbox, mask IoU |
| `edges.png` | Sobel magnitude | Panel lines, bevel budget |
| `depth_proxy.png` | Relative near/far | Mass stacking, occlusion order |
| `sense_pack.json` | Metadata + palette + part grid | Proportions, materials |

## Rules

1. Run `python3 -m engine sense <img> --out work/sense --mode sharp` for default quality.
2. Do not invent proportions that contradict the matte bbox aspect.
3. Map top palette colors to `materials[].baseColor`.
4. Use `part_grid` zones when filling the Feature Ledger.
5. `depth_proxy` is **relative**, not metric meters. Optional ONNX depth can replace it later.

## Modes

- `draft` — metadata only  
- `solid` — matte + edges + palette  
- `sharp` / `razor` / `hybrid` — full pack including depth proxy  
