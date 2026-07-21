# Fidelity Pact

The pact is the contract between intake and accept gates.

## Fields

- `targetFidelity` — overall bar 0–1 by complexity  
- `metricFloors` — hard numeric floors for `solid+` modes  
- `mustCapture` — identity non-negotiables  
- `mayApproximate` — allowed fudge (usually unseen faces)  
- `ledgerMin` — minimum filled Feature Ledger rows  

## Defaults (`sharp`)

| Key | Floor |
|-----|-------|
| maskIoU_front | 0.85 |
| ssim_front | 0.50 |
| edgeF1 | 0.25 |
| vision | 0.70 |

Metrics are **necessary but not sufficient**. Critical features still need agent scores.
