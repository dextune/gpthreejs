# Blueprint v2 Schema Contract

Blueprint v2 is the first typed contract for source-owned procedural form. It
does not replace v1 authoring yet; migration, compatibility validation, and
strict failure rules are separate M1 tasks.

## Top-Level Fields

| Field | Required | Purpose |
| --- | --- | --- |
| `schemaVersion` | yes | Contract version. Blueprint v2 uses the numeric value `2`. |
| `name` | yes | Stable human-readable object or character name. |
| `qualityMode` | yes | Rendering/detail target selected from the shared quality mode contract. |
| `modelingProfile` | yes | Declarative profile: `generic-prop`, `hard-surface-hero`, or `stylized-character`. |
| `intent` | yes | Intended use of the generated form, such as game or inspection. |
| `revision` | yes | Revision identity, optional parent, and canonical content hash. |
| `proportionProfile` | yes | Global size, body ratio, and thickness contract. |
| `poseProfile` | yes | Source or neutral pose identity, mirroring flag, and joint table. |
| `landmarks` | yes | Named 2D or 3D anchors for source comparison and later projection checks. |
| `parts` | yes | Semantic part hierarchy that drives geometry emission. |
| `materials` | yes | Material identities and channel data referenced by parts. |
| `handles` | yes | Sockets, pivots, colliders, and other animation or attachment handles. |
| `renderProfiles` | yes | Camera/view definitions for source-aligned and neutral inspection renders. |
| `criticalFeatures` | yes | Feature expectations mapped to parts and target views. |

## Nested Contracts

`revision` requires `id`, `parent`, and `contentHash`. The `contentHash` field is
a lowercase SHA-256 hex string once canonical serialization lands in BP-102.

`proportionProfile` requires `headUnits`, `headHeightRatio`,
`shoulderWidthRatio`, and `limbThickness`. These fields keep character mass and
scale relationships independent from absolute coordinates.

`poseProfile` requires `id`, `mirrored`, and `joints`. Geometry should not bake a
single source pose when a joint transform can carry that relationship.

Each `landmark` requires `id`, `semantic`, `space`, and `position`. Positions are
normalized 2D points or world 3D points.

Each `part` requires `id`, `name`, `role`, `geometry`, `materialId`,
`transform`, and `children`. The `children` field is always present so hierarchy
depth is explicit and deterministic.

Each `material` requires `id`, `name`, `role`, and `channels`. Roles are semantic
material categories; channel values carry renderer-specific parameters.

Each `handle` requires `id`, `partId`, `type`, and `transform`. Handles are not
proof of contact by themselves; attachment validation is a later gate.

Each `attachment` requires `parentSocket`, `childSocket`, `contact`, `maxGap`,
`maxPenetration`, and `required`. These fields are the minimum contact contract
for equipment, worn parts, and sockets.

Each `renderProfile` requires `id`, `view`, `camera`, and `purpose`. Source
alignment and neutral inspection must be representable as distinct profiles.

Each `criticalFeature` requires `id`, `description`, `partIds`, and
`targetViews`. A critical feature must point to concrete parts and views before a
review gate can accept it.

## Fixture

The minimal tracked fixture is
`tests/golden/knight/blueprints/v2-minimal-character.json`. It exists to keep
the BP-101 contract stable before BP-110 and BP-111 add strict runtime
validation.
