# Action Timeline

`ActionManifest` turns animation clips into gameplay-ready timing data.

## Normalized Time

All event windows use normalized clip time from `0.0` to `1.0`. Runtime code maps
normalized time to clip seconds.

## Required Windows

- anticipation start and end
- active hit start and end
- recovery start and end
- cancel windows
- combo windows
- interrupt windows
- invulnerability windows
- movement lock windows
- root motion curves

## Required Events

- weapon trail on and off
- projectile spawn
- VFX trigger
- SFX trigger
- camera shake
- hitbox activation and deactivation

## Validation

- Windows must be ordered.
- Active hit windows must reference valid hitbox ids.
- Cancel and combo windows must not contradict recovery policy.
- Events must fire once even if the runtime skips frames.
- Root motion policy must match the `GameAssetBrief`.
