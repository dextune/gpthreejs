# Rigging

Rigging converts a static form hierarchy into a stable game control contract.

## R1 Rigid Rig

Rigid rigs use `Group` and `Mesh` nodes with stable names and local transforms.
They do not require `SkinnedMesh` or vertex weights.

Required humanoid-lite chain:

- hips
- spine
- chest
- neck
- head
- left and right clavicle
- left and right upper arm
- left and right lower arm
- left and right hand
- left and right upper leg
- left and right lower leg
- left and right foot

## RigBlueprint Rules

- Bone and node ids are unique.
- Parent references exist.
- No cycles are allowed.
- Rest transforms are valid and deterministic.
- Joint limits are explicit.
- Sockets reference existing nodes or bones.
- Colliders reference existing nodes or bones.
- `formHandles` remains as a compatibility alias for existing callers.
- `rigHandles` is the preferred game-facing field.

## R2 Skinned or Hybrid Rig

Skinned rigs must validate:

- skin indices reference existing bones
- vertex weights sum to `1 +/- 1e-4`
- max influences are within budget
- inverse bind matrices are present and valid
- detached bones are rejected

Unsupported skeletons return explicit issue codes and remedies instead of
falling back silently.
