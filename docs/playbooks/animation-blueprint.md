# Animation Blueprint

`AnimationBlueprint` defines the clip, track, layer, source, and constraint
contract for generated or imported motion.

## Required Clip Set for R1

Locomotion:

- `idle`
- `walk`
- `run`
- `turn_left`
- `turn_right`
- `jump_start`
- `jump_loop`
- `jump_land`
- `fall`

Combat:

- `draw`
- `sheath`
- `attack_light_1`
- `attack_light_2`
- `attack_light_3`
- `attack_heavy`
- `block`
- `hit_front`
- `hit_back`
- `death`

Skill:

- `skill_cast`
- `skill_charge_loop`
- `skill_release`
- `skill_recovery`
- `skill_interrupt`

## Track Rules

- Runtime tracks use quaternions for rotation.
- Euler angles are allowed only as authoring input.
- Track targets must exist in the rig.
- Quaternion keys must be normalized.
- Loop clips must pass loop seam thresholds.
- Foot contact, ground penetration, joint limit, and hand-weapon drift metrics must be recorded.

## Runtime API

`CharacterAnimator` must expose:

- `playAction`
- `setLocomotion`
- `setAim`
- `update`
- `onEvent`
- `dispose`

Event delivery must be deterministic at 30 fps and 60 fps.
