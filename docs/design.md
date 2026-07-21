# gpthreejs Design Notes

Maintainer-facing. Agent runtime rules live in `SKILL.md` + `playbook/`.

## Product surface

| Concept | gpthreejs term |
|---------|----------------|
| Perception | Sense Pack |
| Intake contract | Fidelity Pact |
| Spec | Form Blueprint |
| Micro features | Feature Ledger |
| Build order | Cast layers (`mass` … `polish`) |
| Review log | Critique Journal |
| Runtime hooks | `formHandles` |
| CLI | `python -m engine …` |

## Quality thesis

Spend wall-clock CPU on matte / edges / depth proxies and parameter fit.
Spend model tokens on judgment and TypeScript. Multi-view metrics block
accepts that look fine from one lucky camera angle.

## Isolation

This repository is self-contained. Do not import, re-export, or mirror directory
layouts, schema names, or CLI verbs from unrelated image-to-3D agent projects.
If a contributor pastes foreign schema fields into a blueprint, reject them in
review.

## Roadmap

| Version | Focus |
|---------|--------|
| 0.1.0 | Core CLI, sense, blueprint, cast, metrics |
| 0.2.0 | Multi-view capture helpers, CMA-ES fit, OpenCV path |
| 0.3.0 | Hybrid GLB normalize + materials re-entry |
| 0.4.0 | Character proportion / landmarks generators |
| 1.0.0 | Benchmark suite + measured token / CPU report |
