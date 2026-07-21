# Refactoring Opportunities

## Status

This plan reviews the codebase against the project values in `AGENTS.md`: code-first output, reusable modules, bounded memory use, fast processing, centralized contracts, and honest verification. It is a refactoring plan only. It does not propose a rewrite or a change in product direction.

The evidence map records the initial review snapshot. The progress log records implementation slices completed after that snapshot.

## Progress Log

2026-07-21 first pass:

- Added regression contracts for CLI dry-run behavior, deterministic surface baking, and emitted factory reuse.
- Split the CLI into a command registry under `engine/commands/`; `engine/cli.py` is now a thin entrypoint.
- Fixed `--in-place` semantics for `layers sync`, `fit`, `journal`, and `surface-annotate`.
- Centralized quality/detail mode contracts under `engine/contracts/`.
- Moved surface role presets to `engine/cast/surface/presets.json` and shared them between Python baking and the Three.js runtime.
- Replaced Python process-random `hash(role)` seed mixing with a stable role seed.
- Reduced surface bake height-field memory overhead by using a flat float buffer.
- Reused a loaded work image through Sense Pack matte, edge, depth, palette, and probe paths.
- Added geometry and material registries to emitted Three.js factories.
- Removed a swallowed surface-annotation failure from blueprint drafting.
- Removed dead fit-loop no-op code and split worker logging into requested versus used counts.
- Implemented real bounded fit worker evaluation with deterministic fixed-trial parity.
- Replaced fit candidate Image allocation with compact matte-mask IoU evaluation.
- Flattened hot pixel scans in Sense and Critique paths.
- Added Sense Pack time and peak-memory smoke gates for small fixtures.
- Split `demo/main.ts` into renderer, scene, references, animation, and resource modules.
- Split sufficiency thresholds/verdicts, user messages, and check groups into separate modules.

Remaining candidates:

- Add chunk-level code splitting for the demo bundle if the 500 kB Vite warning becomes a release gate.
- Expand memory/timing gates to larger real-world sample assets once representative fixtures are committed.

## Summary Verdict

The project already has a useful modular shape: `engine/sense`, `engine/blueprint`, `engine/cast`, `engine/critique`, and `engine/shared` separate the main pipeline stages, while the demo keeps Three.js runtime concerns in `demo/src`. The code also has some good reuse points, including shared PNG and JSON helpers, a `SurfaceLibrary` cache in the demo, and instanced rivet helpers.

The largest gaps are central management and memory-aware processing. Several rules and presets are duplicated across Python and TypeScript, the CLI is a single large dispatcher, image operations repeatedly decode or copy whole buffers, and some performance-facing options are exposed but not implemented. These issues are manageable with incremental refactoring.

## Initial Evidence Map

| Area | Evidence | Impact |
| --- | --- | --- |
| CLI centralization | `engine/cli.py:15-354` builds every parser and dispatches every command in one `main` function. `engine/cli.py:229`, `engine/cli.py:249`, and `engine/cli.py:294` use `args.in_place or True`, which forces in-place writes. | Harder to add or remove commands safely. CLI behavior can drift from command intent. |
| Contract duplication | `engine/blueprint/validate.py:72-76` duplicates the complexity ledger minimum instead of using `COMPLEXITY_LEDGER_MIN`. `engine/cast/surface/schema.py:70-77` maps quality mode to detail level with string replacement logic. | Central rules are not fully central. New modes or feature flags can require scattered edits. |
| Surface preset drift | `engine/cast/surface/bake_maps.py:19-130` and `demo/src/detail/surfaceKit.ts:23-116` carry parallel surface preset definitions. | Python baked maps and runtime generated maps can diverge. |
| Image memory pressure | `engine/shared/pngio.py:41-145` fully reads, inflates, stores rows, and writes whole PNG buffers. `engine/sense/pack.py:54-60` passes the same work image path to multiple builders that re-read it independently. | Repeated full-image allocations and decode passes slow processing and increase peak memory. |
| Pixel loop overhead | `engine/sense/edges.py:10-38`, `engine/sense/depth_proxy.py:10-35`, `engine/sense/matte.py:80-95`, and `engine/critique/fit_params.py:35-50` use repeated per-pixel helper calls. | Python call overhead becomes significant on larger reference images or candidate loops. |
| Monolithic policy module | `engine/sense/sufficiency.py` is 691 lines and mixes thresholds, issue creation, pack checks, spec checks, verdict logic, user messages, and next-step rendering. | Harder to add, remove, localize, or test policy rules independently. |
| Factory output reuse | `engine/cast/emit_factory.py:50-61` creates geometry per part and clones material per mesh in emitted TypeScript. | Generated assets can overuse memory when repeated forms share materials or geometries. |
| Fit worker gap | `engine/critique/fit_params.py:76` discards the `workers` parameter while the CLI exposes `--workers`. Candidate evaluation also allocates a new image per trial in `engine/critique/fit_params.py:16-32`. | Processing remains single-threaded and allocation-heavy despite user-facing performance controls. |
| Demo modularity | `demo/main.ts:1-120` owns renderer setup, scene setup, references, animation loop, and interaction in one file. | Runtime features are harder to add or delete without editing a central procedural file. |
| Verification gaps | Current tests cover core pipeline behavior, but not CLI non-in-place behavior, surface determinism across processes, worker execution, generated material reuse, or memory budgets. | Refactors can improve structure but still regress performance or determinism unless new gates are added. |

## Ranked Refactoring Plan

### P0 - Add Regression Gates Before Reshaping

Goal: protect current behavior before centralizing modules.

Actions:

- Add CLI tests for commands that support `--in-place` and output path behavior.
- Add a deterministic surface-bake test that runs the same role and seed in separate Python processes.
- Add a small generated-factory test that checks repeated material and geometry specs can be counted.
- Add lightweight memory and timing smoke checks around Sense Pack generation using the existing sample assets.

Acceptance:

- Existing tests still pass.
- New tests fail on at least one known current gap, such as forced in-place CLI behavior or nondeterministic `hash(role)` seeding.
- Performance tests use generous thresholds and are treated as regression smoke checks, not micro-benchmark truth.

### P1 - Split CLI Into a Command Registry

Goal: make feature add/remove operations centralized and low-risk.

Actions:

- Introduce `engine/commands/` with one module per command family: `sense`, `brief`, `ledger`, `blueprint`, `layers`, `cast`, `fit`, `critique`, and `journal`.
- Define a small command registration contract with `name`, `parser`, and `run(args)`.
- Keep `engine/cli.py` as a thin registry loader and dispatcher.
- Replace `args.in_place or True` with explicit defaults that preserve the documented command behavior.

Acceptance:

- Adding a command requires adding or removing one command module and one registry entry.
- No command implementation is nested inside `main`.
- CLI tests cover default behavior and explicit output paths.

### P1 - Create Central Contracts And Policy Registries

Goal: remove scattered constants and make feature toggles centrally managed.

Actions:

- Create `engine/contracts/` for stable registries: layers, decision kinds, ledger limits, quality modes, detail levels, issue codes, and sufficiency thresholds.
- Move sufficiency issue definitions and localized user-message templates out of `engine/sense/sufficiency.py`.
- Replace string replacement mode mapping with explicit maps.
- Add a contract validation test that scans known modes and confirms all stages can resolve them.

Acceptance:

- `engine/blueprint/validate.py` uses shared constants for ledger limits.
- Quality mode to detail level mapping is declared once.
- Sufficiency checks can be tested as independent policies without rendering user messages.

### P1 - Unify Surface Presets Across Python And TypeScript

Goal: prevent drift between baked Python maps and runtime Three.js materials.

Actions:

- Move surface role presets to a single data source, such as `engine/cast/surface/presets.json`.
- Generate or load the TypeScript preset table from the same source.
- Replace Python `hash(role)` seed mixing with a deterministic stable hash.
- Keep `SurfaceLibrary` caching, but make its preset input data shared.

Acceptance:

- Python and TypeScript use the same preset names, scales, colors, roughness, metalness, and bump values.
- Baked map output metadata is stable across separate process runs for the same seed.
- Runtime fallback behavior remains explicit when an unknown role is requested.

### P1 - Introduce An Image Workspace For Sense Pack Processing

Goal: avoid repeated image decoding and reduce peak memory.

Actions:

- Add a `SenseWorkspace` or `ImageWorkspace` object that owns the resized work image, dimensions, and optional derived grayscale buffer.
- Pass the workspace to matte, edge, depth, palette, and probe builders instead of passing only a file path.
- Keep file path APIs as compatibility wrappers while internals move to image objects or flat buffers.
- Record image size, downscale decisions, and generated artifact paths in one manifest.

Acceptance:

- Sense Pack generation reads the work PNG once in the main path.
- Derived steps share buffers where practical.
- Peak memory does not scale with unnecessary duplicate full RGBA images.

### P2 - Optimize Pixel Buffers And Hot Loops

Goal: reduce per-pixel Python overhead without adding heavy dependencies.

Actions:

- Add flat-buffer helpers in `engine/shared/pngio.py` for direct index operations.
- Replace repeated `pixel()` calls in edge, matte, depth, metrics, and fit loops with index arithmetic.
- Store surface height fields in flat `array` or `bytearray` structures instead of `list[list[float]]`.
- Avoid retaining intermediate row lists after PNG decode.

Acceptance:

- Image output parity tests pass against current fixtures.
- Sense Pack and fit smoke checks show equal or better runtime on the same sample inputs.
- Memory use is bounded by a small number of full-size buffers per stage.

### P2 - Reuse Geometry And Materials In Generated Factories

Goal: make emitted Three.js code memory-aware by default.

Actions:

- Emit a small geometry registry keyed by geometry type and parameters.
- Emit a material registry keyed by material signature.
- Share immutable materials by default and clone only when a part needs per-mesh mutation.
- Keep form handles and named parts stable for downstream animation or interaction.

Acceptance:

- Generated factories reuse identical geometry definitions.
- Generated factories do not clone identical material instances without a reason.
- Existing demo assets still render correctly.

### P2 - Make Fit Workers Real And Allocation Bounded

Goal: align the fitting command with its exposed performance controls.

Actions:

- Replace image allocation per candidate with a compact silhouette mask buffer.
- Evaluate candidates in chunks.
- Wire the `workers` parameter into a thread or process execution path only after deterministic single-worker parity is tested.
- Keep a single-worker default for reproducibility.

Acceptance:

- `--workers` changes execution strategy instead of becoming a ignored hint.
- Fixed seed and one worker produce stable results.
- Multi-worker mode returns the same best candidate set or a documented tie-equivalent result.

### P3 - Modularize The Demo Runtime

Goal: keep app-level feature additions isolated.

Actions:

- Split `demo/main.ts` into renderer/bootstrap, scene lighting, reference strip, asset loading, controls, and animation loop modules.
- Add a small runtime resource manager that owns disposal of generated textures, geometries, and materials.
- Keep `demo/src/detail/surfaceKit.ts` focused on material and detail generation.

Acceptance:

- `demo/main.ts` becomes orchestration only.
- Adding or removing a visual feature does not require editing renderer/bootstrap code.
- Demo build still passes and the generated sample still renders.

## Sequencing

1. Add P0 regression gates.
2. Refactor CLI registry and fix in-place semantics.
3. Create central contracts and move sufficiency policy data.
4. Unify surface presets and deterministic seeds.
5. Introduce image workspace and optimize hot loops.
6. Add emitted factory geometry and material registries.
7. Implement bounded fit workers.
8. Modularize demo runtime.

## Non-Goals

- Do not introduce new runtime dependencies unless a later benchmark proves the standard-library path is insufficient.
- Do not rewrite the pipeline around GLB or external modeling tools.
- Do not change public artifact formats without compatibility wrappers and migration notes.
- Do not optimize by hiding failures or weakening validation.

## Verification Strategy

Each refactoring slice should finish with:

- Targeted unit tests for changed contracts.
- Existing full test suite.
- A sample pipeline smoke run against `samples/`.
- A short before-and-after note for memory, runtime, or module-count impact when the slice claims performance or maintainability improvement.

Completion means the codebase has centralized command and policy registration, shared surface contracts, lower duplicate image-buffer pressure, deterministic surface baking, real worker behavior where exposed, and generated Three.js factories that reuse materials and geometries by default.
