# Demo-Derived Fidelity Patterns

This playbook distills the reconstruction methods repeatedly used by the strongest
procedural models in `hoainho/img2threejs-showcase`. It is not a catalog of subject-specific
assets. It is a reusable method for converting visible reference evidence into editable
Three.js geometry, materials, camera settings, and review constraints.

Use this playbook for `qualityMode=sharp` and `qualityMode=razor`. For `solid`, apply at
least the silhouette, true-negative-space, material-region, and camera-lock rules.

## Core rule

High likeness does not come from adding more generic primitives. It comes from locking the
reference in this order:

1. reference projection and camera
2. normalized silhouette and proportions
3. connected part hierarchy
4. contour bands, bevels, and true negative space
5. material-region segmentation
6. identity marks and repeated details
7. reference-specific lighting and tone response
8. primary-view comparison plus orbit validation

Do not tune material or lighting to hide incorrect geometry. Correct the earliest wrong
layer first.

## What the showcase demos teach

| Observed pattern | Reusable lesson |
| --- | --- |
| Sony earbud case uses one continuous rounded shell with real well openings | Preserve a continuous exterior as one primary body; create silhouette-critical holes as geometry rather than black decals or overlapping boxes |
| Gerber knife traces the blade profile and builds edge, grind, and apex as separate bands | Treat profile-dominant objects as 2D outlines extruded into depth; model visually distinct edge treatments as real contour geometry |
| Gerber cord uses a seeded curve and procedural weave maps | Use curve tubes for wrapped/cabled forms, with deterministic irregularity; reserve texture maps for fiber-scale detail |
| ISSACA shotgun separates receiver, barrel, handguard, sight, markings, and local finishes | Segment by visible function and material boundary, not by convenient primitive count |
| Doraemon house is assembled as a hierarchy of gabled masses and reference-colored sub-scenes | For scenes, lock the composition and overlap graph before detail; reproduce recognizable volume relationships, not merely object categories |
| War-Hauler applies patina, dirt, labels, glow, and wear only where evidence shows them | Localize surface effects by region; global random noise destroys likeness |
| Viewer entries specify camera, target, FOV, exposure, environment strength, tone mapping, and one light rig | Camera and look development are part of the reconstruction, not presentation added after modeling |

## 1. Build a reference coordinate system

Before creating geometry, convert the reference into normalized ratios.

1. Select the dominant visible dimension as `1.0`.
2. Record the visible bounding box, center, major axes, and ground/contact line.
3. Record identity landmarks as ratios relative to the dominant dimension.
4. Record every major part extent and attachment point in the same coordinate system.
5. Derive world-space dimensions from a single scale constant.

Recommended blueprint fragment:

```json
{
  "referenceFrame": {
    "dominantAxis": "x",
    "dominantLength": 1.0,
    "visibleBounds": [0.0, 0.0, 1.0, 0.42],
    "landmarks": {
      "tip": [0.98, 0.47],
      "gripStart": [0.39, 0.51],
      "pivot": [0.18, 0.56]
    }
  }
}
```

Avoid scattering unrelated world-space constants through factory code. Keep proportions in a
data block so CPU fit, critique, and later edits can change the form coherently.

## 2. Lock camera before detail

A correct model rendered through the wrong camera will fail likeness review.

For the primary reference view:

- match projection first: orthographic-like product plates usually need a narrow perspective
  FOV, commonly around 20–36 degrees, or an orthographic camera
- match yaw, pitch, roll, target, crop, and object occupancy
- freeze the evaluation camera and disable animation/damping during capture
- fit the object from its bounding box with a fixed margin
- preserve the same camera through all passes unless the camera itself is the diagnosed defect

Use two render modes:

### Evaluation mode

- neutral or reference-matched flat background
- deterministic camera
- no decorative floor if it contaminates the matte
- no animation
- stable exposure and tone mapping

### Look-development mode

- reference-matched background or gradient
- contact shadow when the source has grounding
- the approved material and lighting rig
- optional animation only after still fidelity passes

Never compare a shaded hero render against a clean product reference for silhouette metrics.

## 3. Choose geometry by visible topology

### Profile-dominant forms

Use `THREE.Shape` plus `ExtrudeGeometry` when identity is carried by a side outline: blades,
plates, signs, guards, receiver profiles, gables, and panel silhouettes.

- trace straight segments and curves from normalized landmarks
- use `Shape.holes` for slots, wells, thumb holes, vents, and cutouts that affect silhouette
- bevel only where the reference shows edge rounding
- create distinct face bands for grinds, sharpened edges, rims, lips, and inlays

A black plane placed over a solid mesh is not a hole. It fails orbit views, shadows, and edge
metrics.

### Continuous rounded housings

For cases, shells, capsules, and consumer products:

- prefer one continuous outer shell over stacked rounded boxes
- use a custom outline extrusion, lathed profile, rounded geometry, or merged body
- use hidden interior plugs only to close floors or support cavities
- keep parting lines intentional and reference-matched

### Compound organic or ergonomic forms

Do not use one sphere as a finished earbud, head, grip, or padded part. Build a compound form
from scaled spheres/hemispheres, short tubes, torus seams, nozzles, pads, and transition pieces.
Review the combined silhouette rather than each primitive in isolation.

### Curves, hoses, rope, wire, and wrapped parts

Use `CatmullRomCurve3` or another explicit path plus `TubeGeometry`.

- define the macro path from landmarks
- add only low-amplitude seeded jitter where handmade irregularity is visible
- model knots, tails, connectors, and clamps as separate connected structures
- use albedo/normal/roughness maps for weave, braid, rib, or corrugation frequencies

### Repeated structures

Use shared geometry or `InstancedMesh` for bolts, rivets, ribs, tread blocks, vents, roof seams,
spokes, pins, and jimping. Repetition spacing and count should come from the reference, not a
generic density preset.

## 4. Separate macro, meso, and micro evidence

| Frequency | Representation | Examples |
| --- | --- | --- |
| Macro | hierarchy and primary geometry | overall case, blade outline, cab, roof cluster, wheel positions |
| Meso | separate geometry, edge bands, panel lips, fasteners | bevel strip, grind facet, trim, vents, hinges, seams, bolts |
| Micro | independent PBR maps and decals | stonewash, scratches, weave, marble, dirt, lettering, warning marks |

Rules:

- use geometry when it changes silhouette, contact, occlusion, or a strong highlight break
- use a normal or bump map for relief too small to justify geometry
- use a roughness map for finish variation
- use decals for identity marks that do not alter silhouette
- never use the albedo texture as roughness, normal, or AO

## 5. Reconstruct material regions, not a single global material

Start by segmenting visible material regions. A single object may contain matte polymer,
painted metal, polished metal, rubber, glass, copper trim, gold contacts, emissive elements,
and printed markings.

For every region record:

- sampled or reference-estimated base color
- metalness
- roughness
- clearcoat and clearcoat roughness when applicable
- transmission/IOR/thickness for glass or translucent parts
- environment intensity sensitivity
- local map set and UV scale

Use procedural canvas maps only when their structure matches the evidence. Examples include:

- cloudy stonewash plus directional grinding scratches
- marbled Bakelite with broad color variation and fine grain
- woven cord with matching albedo and bump patterns
- localized grime, soot streaks, edge wear, and oxidation
- knurl, rib, tread, and corrugation patterns

All procedural noise must be deterministic and spatially constrained. Patina visible only on a
roof or armor top must not appear across the entire model.

## 6. Treat markings as identity geometry or decals

Logos, labels, serial numbers, warning symbols, sidewall text, panel markings, and L/R indicators
can carry more identity than hundreds of generic polygons.

Use a transparent `CanvasTexture` decal when the mark is flat:

- set color textures to `SRGBColorSpace`
- raise anisotropy for oblique viewing
- use `transparent: true` and `depthWrite: false`
- use polygon offset or a small surface offset to prevent z-fighting
- keep decal dimensions and placement in normalized reference ratios
- mirror only when the source truly has mirrored marks

Use shallow geometry when the mark is embossed, engraved deeply enough to affect highlights, or
changes the silhouette.

## 7. Build an identity budget before polish

Before entering `skin` or `polish`, select:

- up to five **critical** identity systems
- up to three **important** supporting systems

Each system must map to a concrete implementation target:

```json
{
  "id": "critical-edge-grind",
  "evidence": "bright lower blade band from choil to tip",
  "mapsTo": "parts.blade.localFeatures.edgeGrind",
  "implementation": "separate extruded contour band",
  "minimumScore": 0.82
}
```

Typical critical systems:

- exact outer silhouette
- signature cutout or negative space
- distinctive color/material boundary
- characteristic edge, rim, roofline, or wheel arrangement
- brand mark or emblem
- reference-defining local wear or glow placement

A global score cannot override a failed critical identity system.

## 8. Lock one reference-specific look-development rig

Use one approved light rig. Do not stack project default lights and a bespoke rig.

Recommended responsibilities:

- environment/IBL for broad reflection context
- key light for dominant reference direction
- restrained fill for readable shadow values
- optional rim/accent only when visible in the source
- contact shadow only when the reference is grounded

Record these per subject:

- tone-mapping operator
- exposure
- environment intensity
- background/background gradient
- key/fill/rim position, color, and intensity
- shadow softness and bias

Use AgX, ACES, or Neutral based on measured color behavior. Saturated red, copper, gold, and
emissive colors can shift substantially under the wrong tone mapping or excessive exposure.
Lighting cannot be accepted while geometry or camera is still being changed arbitrarily.

## 9. Review in the correct order

For every layer, diagnose in this order:

1. crop and projection
2. global silhouette and occupancy
3. major part proportions and overlap
4. negative spaces and attachment contacts
5. contour bands and bevel highlight breaks
6. material-region colors and values
7. roughness/metalness response
8. identity marks and local effects
9. background, exposure, and light direction

Then capture at least two orbit views for non-planar forms. Orbit views are not compared against
unseen reference geometry; they are used to detect collapsed planes, floating parts, invalid
attachments, and fake holes.

Correct one defect class per iteration:

- camera/crop defect -> camera settings
- silhouette/proportion defect -> blueprint or geometry
- missing connected structure -> hierarchy/attachment
- material segmentation defect -> material regions
- shading defect with sound materials -> light/look-development rig

Do not compensate for a geometry defect by changing exposure, or for a camera defect by scaling
unrelated parts.

## 10. Failure patterns to reject

Reject or recode when any of these appear:

- stacked-box approximation for a continuous designed shell
- generic primitive soup with no traced proportion system
- dark overlays pretending to be holes
- one material across visibly different finishes
- global noise applied uniformly across all parts
- labels omitted because they are "only texture"
- micro grain represented with excessive geometry
- floating tubes, limbs, handles, or trim
- default and custom light rigs active together
- camera/FOV changing between comparison passes without a recorded reason
- a primary-view plane that collapses under orbit
- decorative animation added before still fidelity is accepted

## 11. Minimum delivery checklist

For `sharp` and `razor`, do not declare completion until all are true:

- normalized reference frame and landmark ratios are stored
- primary camera and evaluation capture settings are fixed
- silhouette-critical holes are true geometry
- every critical identity system maps to geometry, material, or decal code
- material regions use independent PBR channels
- procedural noise is seeded and localized
- one reference-specific light rig is active
- primary comparison passes the Fidelity Pact
- at least two orbit views remain volumetric and attached
- runtime handles remain available after visual refinement

## Showcase sources reviewed

- `sony-wf1000xm3/createSonyWf1000xm3Model.ts`
- `gerber-knife/createGerberKnifeModel.ts`
- `issaca-shotgun/createIssacaShotgunModel.ts`
- `doraemon-house/createDoraemonHouseModel.ts`
- `warhauler/createWarHaulerModel.ts`
- `src/scene.ts` and `src/demos/registry.ts`

Repository: <https://github.com/hoainho/img2threejs-showcase>
