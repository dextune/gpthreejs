# Metrics

Scripts compute numbers. Agents still write vision scores and feature critiques.

| Metric | Script | Meaning |
|--------|--------|---------|
| `maskIoU` | matte vs render | Silhouette overlap |
| `ssim` | ref vs render | Structural luminance similarity |
| `edgeF1` | edge map vs render edges | Contour agreement |

```bash
python3 -m engine metrics --reference ref.png --render view.png \
  --matte work/sense/matte.png --edges work/sense/edges.png --out work/metrics.json
```

## Accept policy (`solid+`)

1. Vision ≥ pact floor  
2. All critical features ≥ floors  
3. Metric floors pass  
4. Sheet or grid path recorded in journal  

Never auto-accept from metrics alone.
