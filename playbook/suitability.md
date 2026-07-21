# Suitability & Sufficiency

Evaluate two layers.

1. **Suitability** — whether this image can be used as a 3D reconstruction subject.  
2. **Sufficiency** — whether the current inputs are enough for a sharp cast. Use **`engine sufficiency`**.

Detailed routine: [sufficiency.md](./sufficiency.md)

## Suitability

### Prefer

- Single clear subject  
- Reasonable lighting  
- Distinct silhouette  
- Minimal heavy occlusion  

### Conditional

- Busy background → rely on matte / request crop  
- Extreme motion blur → `abort` or `ask` for sharper frame  
- Character hair/cloth → route `domain=character`, accept stylization  

### Reject

- No readable subject  
- Pure texture swatch without form  
- Unreadable resolution  

Verdicts: `pass` | `conditional` | `reject`  
Implementation decisions should align with the sufficiency report verdict.

## Agent order

```text
image received
  → probe (optional)
  → sense (recommended)
  → sufficiency  ← report missing information or specs through userMessage
  → if abort: stop
  → if ask: request remedies, wait
  → if continue: brief → ledger → blueprint → …
```
