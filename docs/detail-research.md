# Raising Detail Fidelity — Research Notes (gpthreejs Knight)

**Audience:** maintainers improving procedural character quality  
**Date:** 2026-07  
**Scope:** How to make a single-image (or turnaround) knight look *much* more detailed in Three.js without abandoning code-first output.

---

## 1. Why the current model still feels “blocky”

Human perception of “detail” is multi-band:

| Band | What the eye reads | Current gpthreejs knight | Industry default |
|------|--------------------|-------------------------|------------------|
| **Macro** | Silhouette, proportion, major masses | Partially OK after hand factory | Blockout / A-pose |
| **Meso** | Panel splits, bevels, straps, folds | Sparse boxes/capsules | Separate mesh pieces + bevels |
| **Micro** | Scratches, rivet heads, cloth weave, metal grain | Almost none | Normal/roughness maps |
| **Shading** | Specular breaks, clearcoat, AO in cavities | Flat PhysicalMaterial constants | Layered PBR maps |
| **Identity** | Heraldry, visor grille pattern, cross shape | Simplified | Decals / projected albedo |

Game art consensus (PBR texturing guides): **do not grow triangle count alone**. Push micro into **maps**, keep meso as **real geometry only when it breaks silhouette**.

---

## 2. Method families (research map)

### A. Geometry density (real triangles)

**Ideas**

1. **Armor kit library** — reusable operators: `plate`, `lameStack`, `pauldronShell`, `sallet`, `greave`, `rivetRing`, `leatherStrap`.  
   Inspired by production procedural systems (Infinigen-style generators, Houdini kits) and **ProcGen3D** (arXiv 2511.07142): image → *procedural graph* → rich decode, not freehand mesh soup.

2. **CSG for hard surface** — cut breath holes, slots, undercuts with boolean ops.  
   Practical Three.js path: [three-bvh-csg](https://github.com/gkjohnson/three-bvh-csg) (BVH-accelerated CSG).

3. **Lathe / extrude / Shape** — sallet profile from side-view silhouette curve; tabard outline from front matte.

4. **Subdivision + edge crease** — hold silhouette, smooth only mid faces (optional offline bake to static BufferGeometry).

5. **Parameter search** — fit plate sizes to matte/edge maps (gpthreejs `fit` idea), or MCTS over discrete kit choices (ProcGen3D inference pattern).

**Pros:** orbit-stable, readable in wireframe, good for sockets/colliders.  
**Cons:** draw-call explosion if every rivet is a Mesh; need InstancedMesh / BatchedMesh.

**Perf rule (three.js community):** scene graph object count hurts before triangle count. Prefer one `InstancedMesh` of 200 rivets over 200 `Mesh` nodes.

---

### B. Shading density (fake geometry)

**Ideas**

1. **Procedural normal maps** (canvas / DataTexture)  
   - Panel lines, hammer marks, leather grain, cloth weave  
   - Generated at runtime with noise + edge masks from Sense Pack

2. **Roughness / metalness maps**  
   - Steel: low roughness + edge wear high roughness  
   - Brass trim: very low roughness  
   - Cloth: high roughness, slight color variation

3. **MeshPhysicalMaterial layers**  
   - `clearcoat` / `clearcoatRoughness` for lacquered plate  
   - `sheen` for cloth  
   - optional `anisotropy` for brushed steel (where supported)

4. **AO / cavity**  
   - Screen-space AO in renderer, or baked AO map from multi-light offline pass  
   - Darken plate seams in a cavity mask

5. **Decals**  
   - Heraldic cross, lion emblem, dirt as `DecalGeometry` or transparent planes  
   - Better than carving every symbol as solid boxes

**Pros:** huge visual jump at fixed poly budget; mobile-friendly.  
**Cons:** wrong under extreme close-up / grazing if normals are weak; UVs needed for persistent maps.

**Game texturing literature:** normal + roughness give more “expensive look” per ms than doubling plate mesh count.

---

### C. Image-driven detail (use the reference pixels)

**Ideas**

1. **Camera-matched projection**  
   - Solve rough camera for hero view  
   - Project de-lit reference onto torso/helmet as albedo  
   - Mirror / inpaint unseen sides  
   Classic likeness path (projection + delight); Three.js projective materials / custom ShaderMaterial.

2. **Frequency separation of reference**  
   - Low-freq → base color zones  
   - High-freq → detail normal / roughness boost  
   (Photoshop-style FS; also used in texture detail mapping pipelines.)

3. **Depth / normal priors (CPU or ONNX)**  
   - Depth Anything / Depth Pro → extrusion depths for plates  
   - Normal estimators → bend breastplate dome to match painting

4. **Multi-view consistency**  
   - Front / side / back sheets already in `samples/knight/`  
   - Score maskIoU + edgeF1 per view; refine only failing bands

5. **Hybrid neural draft**  
   - TRELLIS / InstantMesh / Unique3D → GLB base  
   - gpthreejs re-enters: materials, formHandles, game hierarchy  
   Research & community: best shape ceiling for organic folds; topology often messy for games → retopo or accept stylized cage.

**Pros:** captures illustrator intent (cross shape, metal lighting language).  
**Cons:** baked lighting fights scene lights unless de-lit; hybrid breaks pure procedural purity (must label `bodySource`).

---

### D. Structure / kit reasoning (LLM + graph)

**Ideas**

1. **Armor ontology**  
   Explicit graph: `Helmet → Visor → BreathGrid`, `Cuirass → Fauld → Tassets`, etc.  
   Agent fills graph from Feature Ledger; decoder expands kits.

2. **ProcGen3D-style loop**  
   Propose kit parameters → render → metric/MCTS → accept.  
   Domain would need a **knight armor generator** (like their cactus/tree generators).

3. **3D-GPT / Infinigen pattern**  
   LLM only chooses parameters of a fixed procedural API, never invents raw triangle soup.

**Pros:** scales detail without infinite freehand code; reproducible.  
**Cons:** needs kit authoring investment up front.

---

## 3. What works best for *this* knight (ranked)

Given: stylized plate armor, closed helmet, crimson surcoat, brass trim, game realtime.

| Priority | Method | Expected visual gain | Cost | Fits gpthreejs? |
|----------|--------|----------------------|------|----------------|
| **P0** | Procedural PBR maps (normal + roughness + panel mask) | ★★★★ | Low CPU, low risk | Yes — canvas bake in factory |
| **P0** | Kit expansion: sallet profile, layered lames, proper cross decal, belt stack | ★★★★ | Code time | Yes — hand factory / emitter ops |
| **P1** | Instanced rivets + brass edge curves (TubeGeometry) | ★★★ | Low if instanced | Yes |
| **P1** | Multi-view metric gate on edgeF1 (already Sense edges) | ★★★ process | Medium | Yes |
| **P2** | CSG breath holes / undercut pauldrons | ★★★ | Dep + bake time | Optional dep |
| **P2** | Project de-lit hero albedo on torso/helmet | ★★★★ frontal | Medium | Yes — hybrid-ish |
| **P3** | TRELLIS/InstantMesh GLB + gpthreejs handles | ★★★★ shape | GPU/API | `qualityMode=hybrid` |
| **P3** | Full UV unwrap + Substance-like AI maps | ★★★★ | Offline DCC | Out of pure skill loop |

**Key finding:** For armored characters, **P0 maps + meso kits** usually beat “add 50 more boxes” in perceived quality.

---

## 4. Recommended architecture upgrade (gpthreejs)

```
Sense Pack (matte, edges, palette, depth proxy)
        │
        ▼
Feature Ledger ──► Armor Kit Graph (typed parts)
        │
        ▼
Macro cast (proportions, hierarchy, formHandles)
        │
        ▼
Meso cast (plates, bevels, straps, cape folds)     ← real geometry
        │
        ▼
Micro bake (canvas normals/roughness/AO/decals)   ← maps
        │
        ▼
Optional: project reference albedo (front confidence)
        │
        ▼
Multi-view metrics + agent critique
```

### New artifacts (proposed)

| Artifact | Role |
|----------|------|
| `armorKit.json` | Discrete kit IDs + params (not free mesh) |
| `surfaceStack.json` | Which maps each material uses |
| `detailBudget` | max draw calls / instances / tex res |
| `confidenceByRegion` | front high, back low |

### New engine modules (proposed)

- `engine/cast/kits/armor_plate.py` — param → blueprint fragment  
- `engine/cast/bake_surface.py` — PNG normal/roughness writers (stdlib zlib PNG already exists)  
- `engine/cast/project_albedo.py` — optional delight + project  
- `engine/critique/band_scores.py` — macro/meso/micro scores separately  

---

## 5. Concrete techniques for knight parts

### Helmet
- Lathe side profile from `knight_03_side_ortho` silhouette  
- Visor as inset box + **instanced breath holes** (or normal-map dots for far LOD)  
- Brass rims = thin torus / tube along edge curves  
- Micro: brushed anisotropy + fine scratch normal  

### Breastplate
- Macro dome (sphere scale) + meso plate seams as **inset edge loops** (extra thin boxes or normal grooves)  
- Lion/crest: **decal texture** from bust crop, not geometry  
- Clearcoat slightly higher than limbs  

### Surcoat
- Cloth: high roughness, soft normal weave  
- Cross: 2-plane or canvas texture with alpha (cleaner than solid boxes at distance)  
- Edge fray: alpha mask or jagged plane (stylized)  

### Cape
- 3–5 bones/planes with gradient thickness; optional simple cloth vertex sway (already partially done)  
- Micro folds via normal map scrolling slowly  

### Rivets / straps
- `InstancedMesh` rivet sphere/hemisphere  
- Straps: flat boxes + normal stitching  

### Sword
- Blade: tapered box or extruded profile; fuller as dark roughness strip  
- Guard/pommel: brass PhysicalMaterial  

---

## 6. Hybrid neural path (when procedural plateaus)

| Step | Tool examples | gpthreejs role |
|------|---------------|---------------|
| 1. Image → mesh | TRELLIS, InstantMesh, Unique3D | Import GLB, set `bodySource: hybrid-glb` |
| 2. Clean | Mesh simplification, optional retopo | Keep game poly budget |
| 3. Re-shade | Project / re-PBR | De-light + independent roughness |
| 4. Re-rig hierarchy | Manual/agent segment | formHandles sockets |
| 5. Gate | Multi-view metrics | Same critique journal |

Community pattern: neural for **shape**, human/agent pipeline for **game readiness**.

---

## 7. Evaluation — how to know “more detail” worked

Do not rely only on “looks cooler.”

| Metric | Band |
|--------|------|
| maskIoU multi-view | Macro silhouette |
| edgeF1 vs Sense edges | Meso panel readability |
| Region crops: helmet, chest cross, pauldron | Identity features |
| Agent vision score per critical feature | Same as gpthreejs floors |
| Perf: draw calls, tris, FPS @ 1080p | Realtime budget |

**Accept policy idea:** micro pass can accept with lower edgeF1 if normal maps present and identity crops pass.

---

## 8. Implementation roadmap (practical)

### Sprint 1 — Shading first (1–2 days)
- Canvas-generated normal + roughness for steel/cloth/leather  
- Apply to existing high-detail factory  
- Heraldry as canvas texture (cross + optional bust crop)

### Sprint 2 — Meso kits (2–4 days)
- Sallet lathe, lame stacks, tube brass edges  
- Instanced rivets  
- LOD0 / LOD1 (strip rivets & breath holes at distance)

### Sprint 3 — Image lock (3–5 days)
- Front projection of de-lit hero onto torso/helmet  
- Side view proportion lock from ortho sheet  
- Metric floors wired into demo review page

### Sprint 4 — Optional hybrid (variable)
- Local TRELLIS/InstantMesh adapter  
- formHandles re-bind script  

---

## 9. Limits (honesty)

1. **One stylized illustration cannot yield photoreal AAA armor.**  
2. **Infinite boxes ≠ detail** — without maps and kit structure it stays toy-like.  
3. **Neural meshes** win organic folds but often lose clean pivots until retopo.  
4. **Token/CPU tradeoff:** more agent review cycles help less than one good surface bake.

---

## 10. Sources (anchors)

- ProcGen3D — neural procedural graphs + MCTS image alignment (arXiv 2511.07142, [project](https://xzhang-t.github.io/project/ProcGen3D/))  
- TRELLIS / InstantMesh / Unique3D — single-image mesh baselines  
- three-bvh-csg — realtime-capable CSG for hard surface  
- three.js InstancedMesh / BatchedMesh — draw-call discipline  
- PBR / frequency separation texturing practice — micro detail in maps  
- Infinigen / 3D-GPT — procedural API controlled by agents  
- gpthreejs playbook — Sense Pack, Feature Ledger, multi-view metrics  

---

## 11. Bottom line

**Yes, much more detail is possible.** The highest ROI path for the knight is not “more primitive spam,” but:

1. **Micro via procedural PBR maps**,  
2. **Meso via armor kits + instancing**,  
3. **Identity via decals / optional projection**,  
4. **Hybrid neural only when shape still fails gates.**

That stack matches both graphics research and game production practice, and stays compatible with gpthreejs’s code-first, gated philosophy.
