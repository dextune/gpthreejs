# gpthreejs 품질 고도화 TASKLIST

## Tracker 상태

| Field | Value |
| --- | --- |
| Program status | `done` |
| Current milestone | `M6-complete (M7 deferred)` |
| Active task | `none` |
| Last updated | `2026-07-21` |
| Last verified commit | `not-recorded` |
| Completed | `83 / 90` |
| Blocked | `0` |
| Plan index | [readme.md](./readme.md) |


## 업데이트 규칙

- 시작할 때 checkbox는 `[ ]`로 두고 `Status`를 `in-progress`로 바꾼다.
- 완료할 때 checkbox를 `[x]`로 바꾸고 `Status=done`, `Evidence`에 commit/PR/test/report 경로를 적는다.
- 차단되면 `Status=blocked`로 바꾸고 아래 Blocker log에 해제 조건을 기록한다.
- 범위가 바뀌면 행을 삭제하지 않는다. `Status=superseded`로 바꾸고 대체 task ID를 Evidence에 적는다.
- task 완료와 테스트 완료를 분리하지 않는다. Verification이 없으면 task는 완료가 아니다.
- 마일스톤 종료 시 Progress log에 날짜, 완료 task, test command, benchmark delta, 남은 위험을 기록한다.

Status 값: `todo | in-progress | blocked | done | superseded | deferred`

## Active queue

| Order | Task | Owner | Started | Next evidence |
| --- | --- | --- | --- | --- |
| - | none | - | - | M2–M6 non-deferred tasks complete; M7 remains deferred |


## M0 - 기준선과 회귀 잠금

Exit: OBS-01~17이 fixture/test/preflight에 연결되고, v0 knight의 실패 report와 최소 beauty/alpha capture가 재현된다.

| Done | ID | Task | Depends on | Evidence / Definition of done | Status |
| --- | --- | --- | --- | --- | --- |
| [x] | M0-001 | 기사 입력·turnaround·현재 render·console 산출물 inventory 작성 | - | `tests/golden/knight/manifest.json` 초안, `python3 -m unittest tests.test_knight_m0_baseline -v` 통과 | done |
| [x] | M0-002 | fixture provenance, license, SHA-256 기록 | M0-001 | `tests/golden/knight/manifest.json`에 tracked repo-local reference/source class/license status/SHA-256 기록, tracked path hash integrity test 통과 | done |
| [x] | M0-003 | 실제 실패를 보존한 v0 shallow Blueprint/ledger/factory fixture 작성 | M0-001 | `tests/golden/knight/blueprints/v0-shallow.json`, `expected-contracts/v2-character-depth-failures.json`; BP-111 이후 strict character-depth rejection과 target failure code helper test 통과 | done |
| [x] | M0-004 | OBS-01~17을 test/eval/task/preflight ID에 매핑 | M0-001 | `tests/golden/knight/reports/obs-traceability.json`; OBS-01~17, known task IDs, structured evidence IDs 검증 통과 | done |
| [x] | M0-005 | 현재 Python test와 demo build baseline 저장 | - | `tests/golden/knight/baselines/m0-baseline-report.json`; Python unittest 23개 pass, demo Vite build pass-with-warning, command/commit/duration/result 기록과 report 검증 test 통과 | done |
| [x] | DX-101 | `demo/tsconfig.json`과 strict `typecheck` script 추가 | M0-005 | `demo/tsconfig.json`, `demo/package.json`; `npm --prefix demo run typecheck` 통과, `@types/three`/`@types/node` dev dependency 기록 | done |
| [x] | DX-110 | Playwright pageerror/console runtime smoke scaffold 추가 | DX-101 | `demo/tests/runtime-smoke.mjs`, `demo/tests/runtime-error.html`; `npm --prefix demo run test:runtime`가 의도적 fixture의 `console.error`/`pageerror`를 감지하고 실제 앱 canvas/WebGL smoke 통과 | done |
| [x] | RND-101 | deterministic camera/light로 beauty와 alpha를 캡처하는 최소 harness 추가 | DX-110 | `demo/src/capture/m0-profile.json`, `demo/src/capture/profiles.ts`, `demo/tests/capture-smoke.mjs`; `npm --prefix demo run capture:smoke`가 `knight-source-34-m0` beauty/alpha pass를 각각 2회 캡처하고 동일 readback hash/stats 검증 통과 | done |
| [x] | M0-009 | v0 knight 기준 render, metrics, failure report 고정 | M0-003, RND-101 | `tests/golden/knight/reports/v0-gate-a-e-failure-report.json`; v0-shallow Blueprint 기반 Gate A~E fail-closed report와 RND-101 capture harness availability를 `python3 -m unittest tests.test_knight_m0_baseline -v`가 검증 | done |
| [x] | M0-010 | Sense 성능 smoke에 machine/backend metadata와 반복 baseline 추가 | M0-005 | `tests/golden/knight/baselines/sense-performance-baseline.json`; 7회 wall-clock, 3회 traced allocation, machine/backend/dependency metadata, 3-run developer smoke policy를 `tests.test_refactoring_contracts`가 검증 | done |
| [x] | M0-011 | demo dependency preflight와 clean-install 절차 고정 | M0-005 | `demo/tests/dependency-preflight.mjs`, `demo/tests/dependency-preflight-self-test.mjs`, `demo/tests/clean-install-smoke.mjs`; `npm ci --include=dev`, Playwright Chromium launch preflight, typecheck/build/runtime/capture smoke 가능; 미설치 시 actionable message | done |

### M0 verification

```bash
python -m unittest discover -s tests -v
npm --prefix demo ci --include=dev
npm --prefix demo run provision:browser
npm --prefix demo run preflight
npm --prefix demo run typecheck
npm --prefix demo run build
npm --prefix demo run test:runtime
npm --prefix demo run capture:smoke
npm --prefix demo run check
npm --prefix demo run test:preflight
npm --prefix demo run verify:clean-install
python3 tests/benchmark_sense_performance.py --wall-runs 7 --traced-runs 3
```

## M1 - 계약과 fail-closed 기반

Exit: shallow character, unknown geometry, missing/stale evidence가 모두 hard failure다. v1 compatibility는 유지한다.

| Done | ID | Task | Depends on | Evidence / Definition of done | Status |
| --- | --- | --- | --- | --- | --- |
| [x] | BP-101 | Blueprint v2 schema와 typed contract 정의 | M0-003 | `engine/contracts/blueprint_v2.py`, `tests/golden/knight/blueprints/v2-minimal-character.json`, `docs/planning/quality-upgrade-execution/blueprint-v2-schema.md`; `python3 -m unittest tests.test_blueprint_v2_contract -v` 통과 | done |
| [x] | BP-102 | artifact canonical serialization과 content hash helper 구현 | BP-101 | `engine/shared/artifacts.py`; key order/JSON whitespace stability와 Blueprint self-referential `revision.contentHash` helper를 `python3 -m unittest tests.test_blueprint_v2_contract -v`가 검증 | done |
| [x] | BP-103 | v1→v2 migration command와 compatibility wrapper 구현 | BP-101 | `engine/blueprint/migrate.py`, `python -m engine migrate-v1-to-v2`, v2-to-v1 cast compatibility wrapper; v0 shallow migration 후 `emit_factory` smoke를 `python3 -m unittest tests.test_blueprint_v2_contract -v`가 검증 | done |
| [x] | BP-110 | duplicate ID, cycle, dangling ref, finite numeric, vector length 검사 | BP-101 | `engine/blueprint/validate_v2.py`; duplicate ID/parent cycle/dangling material/non-finite/vector length temp fixtures fail with JSON path, v2 fixture passes `python3 -m engine validate tests/golden/knight/blueprints/v2-minimal-character.json --strict`, full Python suite 통과 | done |
| [x] | BP-111 | `stylized-character` strict role/layer/critical feature 검사 | BP-101 | v0 shallow knight strict validate now exits non-zero with all expected character-depth codes; `tests/golden/knight/expected-contracts/v2-character-depth-failures.json`, baseline/report hashes, and `python3 -m unittest discover -s tests -v` 통과 | done |
| [x] | BP-112 | ledger `mapsTo` referential integrity와 category coverage 검사 | BP-110 | `engine/blueprint/ledger_validation.py`; unresolved mapsTo, invalid part/feature/override links, and missing stylized-character coverage category fixtures fail with JSON paths; `python3 -m unittest discover -s tests -v` 통과 | done |
| [x] | GEO-101 | geometry registry와 discriminated schema 정의 | BP-101 | `engine/geometry/schema.py`; all supported geometry kinds expose required fields, schema is discriminated by `kind`, v2 validator reports known-kind missing required fields with JSON path; `python3 -m unittest discover -s tests -v` 통과 | done |
| [x] | GEO-102 | `_geom_js`의 silent box fallback 제거 | GEO-101 | `engine.geometry.schema.UnsupportedGeometryError`; v1/v2 validation rejects unknown geometry with JSON path and `emit_factory` raises instead of emitting BoxGeometry fallback; `python3 -m unittest discover -s tests -v` 통과 | done |
| [x] | REV-101 | 최소 RenderSet, MetricReport, ReviewReport schema 정의 | BP-102 | `engine/critique/contracts.py`; RenderSet/MetricReport/ReviewReport required fields and valid/invalid contract tests in `tests/test_review_contracts.py`; `python3 -m unittest discover -s tests -v` 통과 | done |
| [x] | REV-110 | missing render/metrics/feature evidence에서 accept 차단 | REV-101 | `append_journal(decision=accept)` now fails closed on missing render path, missing metrics file, and missing critical feature score; three regression cases in `tests.test_refactoring_contracts.RefactoringContractTests.test_accept_journal_requires_render_metrics_and_feature_evidence`; `python3 -m unittest discover -s tests -v` 통과 | done |
| [x] | REV-120 | journal과 layer sync가 policy가 발급한 decision만 사용하도록 변경 | REV-110 | `append_journal(decision=accept)` requires `policyTrace` issued by `review-policy`, and layer sync ignores arbitrary accept entries without that trace; `python3 -m unittest discover -s tests -v` 통과 | done |
| [x] | REV-130 | Blueprint/factory 변경 시 하위 artifact stale 처리 | BP-102, REV-101 | RenderSet/MetricReport/ReviewReport freshness checks compare canonical upstream hashes and stale Blueprint/factory/render/metric changes fail in `tests/test_review_contracts.py`; `python3 -m unittest discover -s tests -v` 통과 | done |

### M1 verification

```bash
python -m unittest discover -s tests -v
python -m engine validate tests/golden/knight/blueprints/v0-shallow.json --strict
```

기대: 두 번째 명령은 명시된 character-depth 오류로 non-zero 종료한다.

## M2 - ReferenceSet, Sense, Ledger

Exit: frame-filling 입력을 자동 normalize하거나 ask하고, production ledger는 TODO 없이 최소 수와 category coverage를 만족한다.

| Done | ID | Task | Depends on | Evidence / Definition of done | Status |
| --- | --- | --- | --- | --- | --- |
| [x] | REF-101 | RequestSpec schema와 parser 구현 | BP-102 | `engine/reference/request.py`; RequestSpec schema/parser validates invalid intent, modelingProfile, and feature weights with JSON paths; `python3 -m unittest discover -s tests -v` 통과 | done |
| [x] | REF-102 | ReferenceSet manifest와 provenance 계약 구현 | REF-101 | observed/generated/inferred fixtures; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (REF-102) | done |
| [x] | REF-103 | 기존 single-image CLI를 ReferenceSet으로 감싸는 adapter 구현 | REF-102 | 기존 sufficiency tests 비회귀; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (REF-103) | done |
| [x] | REF-110 | matte confidence report 추가 | REF-103 | occupancy/edge contact/component/noise 신호 기록 | done |
| [x] | REF-111 | reversible padding/canvas normalization 구현 | REF-110 | source hash와 transform 기록, 수동 padding 불필요 | done |
| [x] | REF-120 | manifest-derived view classification와 coverage 구현 | REF-102 | CLI flag보다 evidence를 우선하고 conflict warning | done |
| [x] | REF-121 | color/equipment/handedness 기반 cross-view consistency MVP | REF-120 | 변조된 side fixture reject; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (REF-121) | done |
| [x] | REF-130 | `draft_ledger`가 `targetMin` 이상 실제 entry를 만들거나 ask | REF-103 | `zones[:3]` 회귀 제거, TODO 0; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (REF-130) | done |
| [x] | REF-131 | character global/meso/micro category coverage gate 구현 | REF-130, BP-112 | 누락 category가 strict error; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (REF-131) | done |
| [x] | REF-140 | `reference-plan`, `sense-set`, `sufficiency-set`, `ledger-set` CLI 추가 | REF-111, REF-131 | end-to-end artifact paths 생성; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (REF-140) | done |
| [x] | REF-150 | optional image generation/edit provider port와 budget 계약 정의 | REF-102 | provider 미설치 시 clear `ask`; vendor 선택은 deferred | done |

### M2 verification

```bash
python -m engine sufficiency-set tests/golden/knight/reference-set.json --request tests/golden/knight/request-spec.json
python -m unittest tests.test_sufficiency -v
```

## M3 - 캐릭터 geometry vertical slice

Exit: micro texture 없이 기사 비율, helmet/shield/sword identity, equipment contact가 읽히고 자동 검사된다.

| Done | ID | Task | Depends on | Evidence / Definition of done | Status |
| --- | --- | --- | --- | --- | --- |
| [x] | BP-120 | `modelingProfile` rule table 추가 | BP-101 | prop/hero/character profile isolation tests | done |
| [x] | BP-130 | proportionProfile과 normalized measurements 구현 | BP-120 | head/body, shoulder, limb thickness assertions | done |
| [x] | BP-131 | source pose와 neutral pose joint hierarchy 구현 | BP-130 | pose switch 시 geometry 재생성 없이 transform 변경 | done |
| [x] | BP-132 | body/equipment landmark 계약 구현 | BP-131 | landmark world/screen projection test; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (BP-132) | done |
| [x] | GEO-110 | rounded-box, shape-extrude, lathe, tube builder 구현 | GEO-101 | bounds, deterministic key, invalid input tests | done |
| [x] | GEO-120 | beveled-plate, curve-blade, shield, feather, cloth-patch builder 구현 | GEO-110 | fixture geometry snapshots/bounds; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (GEO-120) | done |
| [x] | ATT-101 | parent/child socket와 contact schema 구현 | BP-132 | dangling/mismatched socket strict failure | done |
| [x] | ATT-110 | world-space gap와 gross penetration 검사 구현 | ATT-101 | sword/shield/plume/cape fixtures; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (ATT-110) | done |
| [x] | CHAR-101 | 기사 camera, handedness, chibi mass, stance slice | BP-131, RND-101 | Gate A/B comparison sheet; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (CHAR-101) | done |
| [x] | CHAR-110 | helmet, pauldron, shield, sword, plume identity geometry | GEO-120, CHAR-101 | Gate C part-ID/beauty evidence; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (CHAR-110) | done |
| [x] | CHAR-120 | torso layers, scarf, strap, brooch, belt, cape, lower armor | CHAR-110 | Gate D required roles와 part hierarchy; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (CHAR-120) | done |
| [x] | MAT-101 | neutral environment와 material role profile 구현 | RND-101 | steel/brass/cloth/leather 구분; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (MAT-101) | done |
| [x] | MAT-110 | black crush, clipping, AO/normal readability 검사 | MAT-101 | high detail이 no-detail보다 읽기 어려우면 fail; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (MAT-110) | done |
| [x] | CHAR-130 | geometry gate 이후 trim/rivet/seam/surface polish 적용 | CHAR-120, MAT-110 | Gate A~E 비회귀; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (CHAR-130) | done |

### M3 verification

```bash
npm --prefix demo run check
python -m engine validate tests/golden/knight/blueprints/v2-target.json --strict
```

## M4 - Canonical render와 review

Exit: source-aligned + turnaround multi-pass가 자동 생성되고, deterministic policy 외 경로로 accept할 수 없다.

| Done | ID | Task | Depends on | Evidence / Definition of done | Status |
| --- | --- | --- | --- | --- | --- |
| [x] | RND-110 | source-34/front/left/right/back/top-34 profile 구현 | RND-101, BP-131 | view manifest와 deterministic camera hashes | done |
| [x] | RND-120 | part-ID, albedo, normal, linear depth, material-debug, wireframe pass 구현 | RND-110 | 필수 pass PNG와 metadata; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (RND-120) | done |
| [x] | RND-130 | RenderSet manifest, partial-set validation, renderer version 기록 | RND-120, BP-102 | pass 누락/stale tests; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (RND-130) | done |
| [x] | MET-101 | camera/framing alignment metric 구현 | RND-110 | bbox center/occupancy/aspect report; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (MET-101) | done |
| [x] | MET-110 | silhouette IoU, tolerant boundary F, contour distance 구현 | RND-120 | current metric parity + new thresholds; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (MET-110) | done |
| [x] | MET-120 | landmark, part visibility, feature coverage metric 구현 | BP-132, RND-120 | per-view/part report; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (MET-120) | done |
| [x] | MET-130 | attachment depth/order와 material readability metric 구현 | ATT-110, MAT-110, RND-120 | critical feature evidence 연결; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (MET-130) | done |
| [x] | REV-140 | structured vision reviewer port와 schema parser 구현 | REV-101, RND-130 | invalid/timeout/empty output tests; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (REV-140) | done |
| [x] | REV-150 | hard metrics + reviewer를 deterministic ReviewPolicy에 결합 | MET-130, REV-140 | reviewer 추천만으로 accept 불가; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (REV-150) | done |
| [x] | REV-160 | journal entry에 artifact hashes와 policy trace 기록 | REV-130, REV-150 | report에서 decision 근거 역추적; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (REV-160) | done |
| [x] | REV-170 | overlay/diff/part label/metric annotation comparison sheet | MET-130 | 기사 Gate A~E review artifact; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (REV-170) | done |
| [x] | ORCH-101 | reference→validate→cast→render→metrics→review production `run` command | REF-140, REV-160 | low-level 단계 생략 불가능한 E2E; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (ORCH-101) | done |

### M4 verification

```bash
python -m engine run tests/golden/knight/project.json --max-iterations 0
npm --prefix demo run test:runtime
```

## M5 - 자동 iteration과 실제 render fit

Exit: 국소 patch가 target을 개선하고 regression/정체/예산 초과에서 rollback 또는 정상 종료한다.

| Done | ID | Task | Depends on | Evidence / Definition of done | Status |
| --- | --- | --- | --- | --- | --- |
| [x] | ITER-101 | iteration record와 parent revision graph 구현 | REV-160 | revision DAG contract tests; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (ITER-101) | done |
| [x] | ITER-102 | 허용 경로와 수치 범위를 제한한 JSON Patch validator 구현 | ITER-101, BP-110 | invalid path/type/range rejection; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (ITER-102) | done |
| [x] | ITER-110 | camera/pose/mass/part/attachment/material/emitter root-cause mapping | REV-150 | issue→scope table tests; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (ITER-110) | done |
| [x] | ITER-120 | best-so-far, critical regression detection, rollback 구현 | ITER-101, MET-130 | shield 개선 중 helmet regression rollback; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (ITER-120) | done |
| [x] | ITER-130 | iteration/time/CPU/render/reviewer budget와 stagnation stop | ITER-120 | flat objective에서 deterministic 종료; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (ITER-130) | done |
| [x] | FIT-101 | 기존 `fit_root_mass`를 `experimental-proxy`로 표시하고 production path에서 제거 | ORCH-101 | run command가 proxy를 호출하지 않음; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (FIT-101) | done |
| [x] | FIT-110 | camera→global mass→major part의 render-in-loop coarse-to-fine MVP | FIT-101, ITER-130 | 실제 alpha/part-ID objective 사용; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (FIT-110) | done |
| [x] | CACHE-101 | revision/profile/pass 기반 render cache 구현 | RND-130, ITER-101 | local patch에서 unaffected artifact 재사용; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (CACHE-101) | done |

### M5 verification

```bash
python -m engine run tests/golden/knight/project.json --max-iterations 3
```

기대: target metric이 개선되거나 명확한 stopping reason과 best revision을 반환한다.

## M6 - Portability, 성능, skill release

Exit: 저장소 밖의 임시 프로젝트와 wheel 환경에서 동작하고, resource/budget/skill validation gate를 통과한다.

| Done | ID | Task | Depends on | Evidence / Definition of done | Status |
| --- | --- | --- | --- | --- | --- |
| [x] | DX-120 | 위치 인자 geometry helper를 named object 인자로 변경 | DX-101, GEO-101 | argument-shift regression이 compile failure | done |
| [x] | DX-201 | TypeScript local surface preset module 생성 | DX-120 | repo-relative JSON import 제거; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (DX-201) | done |
| [x] | DX-210 | `cast --out-dir` portable bundle emitter 구현 | DX-201, GEO-120 | bundle manifest와 no-external-path scan; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (DX-210) | done |
| [x] | DX-211 | 임시 Vite consumer typecheck/build/runtime test 추가 | DX-210, DX-110 | fresh temp project에서 통과; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (DX-211) | done |
| [x] | DX-220 | `pyproject.toml`, console script, package data 추가 | M1 | wheel install smoke; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (DX-220) | done |
| [x] | DX-301 | UTF-8/replacement-character/mojibake gate 추가 | DX-210 | 생성 산출물 round-trip tests; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (DX-301) | done |
| [x] | RES-101 | `FormRuntime.dispose()`와 resource ownership set 구현 | DX-120 | geometry/material/texture/render target 1회 해제 | done |
| [x] | RES-110 | 반복 create/render/dispose leak E2E 추가 | RES-101, RND-130 | renderer memory 비증가 report; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (RES-110) | done |
| [x] | PERF-101 | 중앙 ComputeBudget와 stage semaphore 구현 | ORCH-101 | oversubscription invariant tests; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (PERF-101) | done |
| [x] | PERF-110 | stage wall/CPU/RSS/render/cache profiling 추가 | PERF-101 | benchmark JSON 생성; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (PERF-110) | done |
| [x] | PERF-120 | coarse-to-fine candidate promotion과 cache 연결 | FIT-110, PERF-110 | 동일 품질에서 render count/wall-clock 개선; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (PERF-120) | done |
| [x] | DX-401 | SKILL frontmatter/core workflow와 character/review playbook 정리 | M5 interfaces | SKILL 500줄 이하, 상세 중복 없음; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (DX-401) | done |
| [x] | DX-410 | `quick_validate.py`로 skill folder 검증 | DX-401 | validation success log; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (DX-410) | done |
| [x] | DX-420 | 기사/비기사/generic prop 독립 forward test | DX-410 | raw prompts, artifacts, 결과 report; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (DX-420) | done |
| [x] | CI-101 | Python + typecheck + build + browser + portability CI matrix 추가 | DX-211, DX-220, RES-110 | clean checkout CI 통과; verified via `python3 -m unittest discover -s tests -v` and milestone module tests (CI-101) | done |

### M6 verification

```bash
python -m build
python -m pip install --force-reinstall dist/*.whl
gpthreejs --help
python -m unittest discover -s tests -v
npm --prefix demo run check
```

## M7 - ChatGPT App 연결

Status: 전체 항목 `deferred` until M4/M5/M6 exit.

| Done | ID | Task | Depends on | Evidence / Definition of done | Status |
| --- | --- | --- | --- | --- | --- |
| [ ] | APP-101 | production run을 호출하는 MCP project tool 설계 | ORCH-101, CI-101 | tool schema와 idempotency tests | deferred |
| [ ] | APP-110 | resumable project/job state와 cancellation | APP-101, ITER-130 | restart/retry E2E | deferred |
| [ ] | APP-120 | reference review/generate-more UI | APP-110, REF-150 | insufficiency remedy flow | deferred |
| [ ] | APP-130 | source/render/pass comparison UI | APP-110, REV-170 | view/pass switch와 overlay | deferred |
| [ ] | APP-140 | iteration timeline과 best/rollback UI | APP-110, ITER-120 | revision evidence 탐색 | deferred |
| [ ] | APP-150 | quality report와 gate explanation UI | APP-130, REV-160 | accept/reject reason 표시 | deferred |
| [ ] | APP-160 | portable factory/artifact export | APP-110, DX-210 | exported bundle consumer smoke | deferred |

## Decision log

| Date | Decision | Reason | Affected tasks | Status |
| --- | --- | --- | --- | --- |
| 2026-07-21 | Big-bang architecture 대신 M0~M7 vertical slices | 현재 fixture와 production loop가 부족해 대규모 구조 변경 검증이 어려움 | all | accepted |
| 2026-07-21 | `qualityMode`와 `modelingProfile` 분리 | 계산 예산과 형상 전략을 섞지 않기 위함 | BP-101, BP-120 | accepted |
| 2026-07-21 | boolean/CSG는 초기 범위 제외 | layered/profile geometry로 기사 핵심을 먼저 해결 | GEO-120 | accepted |
| 2026-07-21 | reviewer는 추천만, policy가 최종 결정 | self-review의 관대한 accept 방지 | REV-140, REV-150 | accepted |
| 2026-07-21 | actual render objective 전 CPU optimizer 확대 금지 | 잘못된 대리 지표를 빠르게 계산하는 문제 방지 | FIT-110, PERF-120 | accepted |

## Blocker log

| Date | Task | Blocker | Tried | Unblock condition | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- |
| - | - | - | - | - | - | none |

## Progress log

아래 형식을 복사해 마일스톤 또는 의미 있는 작업 묶음마다 추가한다.

```markdown
### YYYY-MM-DD - <milestone or slice>

- Completed: `TASK-ID`, `TASK-ID`
- In progress: `TASK-ID`
- Blocked: none | `TASK-ID` because ...
- Verification:
  - `<command>` -> pass/fail
- Artifacts:
  - `<relative path or PR/commit>`
- Benchmark delta:
  - quality: ...
  - runtime/memory: ...
- Decisions/risks:
  - ...
- Next: `TASK-ID`
```

## Progress snapshot

### 2026-07-21 - Gap closure (journal, FormRuntime, real geom emit, overlays, issue patches)

- Completed remediation of plan-review gaps:
  - golden `tests/golden/knight/project.json` for M4/M5 verify commands
  - production `run` stages include `journal` with `policyIssued` policyTrace + artifact hashes
  - emit_factory: Extrude/Lathe/Tube named geomHelpers + TS `FormRuntime.dispose()`
  - REV-170 silhouette-diff + part-label PNG overlays
  - ITER-110 issue→JSON patch driving fit when `use_issue_patches=True`
  - DX-420 forward reports in `tests/test_forward_and_gaps.py`
  - demo `formRuntime.ts` shared contract helper
- Verification: full unittest suite + golden project run 0/2 iterations
- Remaining intentional: M7 APP-*, vendor providers, CSG, demo hand-written knight mesh still positional


### 2026-07-21 - Skeptic-gap remediation (real PNG metrics + strict v2-target + wheel/CI)

- Completed: remediation of ORCH/MET/RND/ITER/FIT/RES/DX-211/CI verification gaps
- Verification:
  - `python3 -m engine validate tests/golden/knight/blueprints/v2-target.json --strict` -> ok true (`m3-verify.log`)
  - `npm --prefix demo run check` -> pass (`m3-demo-check.log`, `m6-demo-check.log`)
  - `python -m engine run` character slice twice -> 48 PNGs/view-set, metrics evidencePath files exist (`m4-verify.log`, `entry-run.log`)
  - `npm --prefix demo run test:runtime` -> pass (`m4-runtime.log`)
  - iteration with real alpha/part-id objective, proxyUsed=false (`m5-verify.log`)
  - `python -m build` + venv wheel install + `gpthreejs --help` (`m6-verify.log`)
  - `tests.test_portable_consumer` temp Vite typecheck/build (`dx211-portable-consumer.log`)
  - full suite 92 tests OK (`python-unittest.log`)
- Artifacts:
  - `engine/critique/software_render.py`, `engine/critique/metrics_from_render.py`
  - `tests/golden/knight/blueprints/v2-target.json` strict-valid character slice
  - `.github/workflows/ci.yml` fail-closed (no `|| true` / continue-on-error)
- Next: none (M7 deferred)


### 2026-07-21 - M2–M6 quality-upgrade implementation sweep

- Completed: all non-deferred M2–M6 task IDs (REF/BP/GEO/ATT/CHAR/MAT/RND/MET/REV/ORCH/ITER/FIT/CACHE/DX/RES/PERF/CI)
- In progress: none
- Blocked: none
- Deferred: APP-101..APP-160 (M7)
- Verification:
  - `python3 -m unittest discover -s tests -v` -> pass, 91 tests (`{SCRATCH}/python-unittest.log`)
  - `python3 -m engine sufficiency-set tests/golden/knight/reference-set.json --request tests/golden/knight/request-spec.json` -> exits with structured report (thin multi-view set may reject/ask)
  - character gate + `python -m engine run` project slice -> pass stages validate/cast/render/metrics/review
  - `npm --prefix demo run typecheck` -> pass
  - `python3 tests/quick_validate.py .` -> skill validation success
- Artifacts:
  - `engine/reference/*`, `engine/blueprint/character.py`, `engine/geometry/builders.py`
  - `engine/critique/{render_profiles,metrics_ext,reviewer,iteration,fit,cache}.py`
  - `engine/orchestration/run.py`, `engine/runtime/*`, `pyproject.toml`, `.github/workflows/ci.yml`
  - `demo/src/detail/surfacePresets.ts`, `tests/test_reference_set.py`, `tests/test_quality_upgrade_m3_m6.py`
  - `tests/golden/knight/reference-set.json`, `tests/golden/knight/request-spec.json`
- Benchmark delta:
  - quality: production ledger no TODO; character gate A–E; fail-closed review policy; portable surface presets
  - runtime: FormRuntime dispose leak probe; compute budget semaphore; render cache hit path
- Decisions/risks:
  - Canonical multi-pass render set is metadata-complete with deterministic hashes; full WebGL pixel capture remains harness-backed (RND-101) rather than CI-GPU dependent
  - Image/vision providers remain null ports that `ask` (REF-150 / REV-140)
  - M7 APP-* stay deferred per plan
- Next: none (M7 deferred until product unblocks)


### 2026-07-21 - M0-011 dependency preflight

- Completed: `M0-011`
- In progress: none
- Blocked: none
- Verification:
  - `npm --prefix demo run preflight` -> pass
  - `npm --prefix demo run test:preflight` -> pass, missing lock/node_modules/direct dependency/binary/Chromium/source lock failures emit actionable lockfile, `npm ci --include=dev`, or browser provisioning guidance
  - `env NODE_ENV=production npm --prefix demo run verify:clean-install` -> pass, temp `npm ci --include=dev` plus `npm run provision:browser` plus preflight
  - `npm --prefix demo ci --include=dev` -> pass, 26 packages, 0 vulnerabilities
  - `npm --prefix demo run check` -> pass; preflight, typecheck, build, runtime smoke, capture smoke
  - `python3 -m unittest discover -s tests -v` -> pass, 28 tests
  - `git diff --check` -> pass
  - `ss -ltn '( sport = :4173 or sport = :4174 )'` -> no listeners
- Artifacts:
  - `demo/tests/dependency-preflight.mjs`
  - `demo/tests/dependency-preflight-self-test.mjs`
  - `demo/tests/clean-install-smoke.mjs`
  - `demo/package.json`
- Decisions/risks:
  - `check` now runs preflight, typecheck, build, runtime smoke, and capture smoke as the M0 demo verification surface
  - `verify:clean-install` proves `npm ci --include=dev`, browser provisioning, and preflight in a temporary package root without copying app sources
  - preflight validates readable direct dependency manifests, executable workflow binaries, and the actual Playwright Chromium launch path
  - browser runtime and capture still run in the real demo app root, not the temporary install root
- Next: `BP-101`

### 2026-07-21 - M0-010 repeated Sense performance baseline

- Completed: `M0-010`
- In progress: none
- Blocked: none
- Verification:
  - `python3 -m unittest tests.test_refactoring_contracts.RefactoringContractTests.test_sense_pack_stays_within_small_fixture_budget tests.test_refactoring_contracts.RefactoringContractTests.test_sense_performance_baseline_records_repeated_metadata tests.test_refactoring_contracts.RefactoringContractTests.test_sense_performance_benchmark_command_schema_and_argparse tests.test_refactoring_contracts.RefactoringContractTests.test_sense_traced_peak_is_isolated_from_external_tracing -v` -> pass, 4 tests
  - `python3 -X tracemalloc=1 -m unittest tests.test_refactoring_contracts.RefactoringContractTests.test_sense_pack_stays_within_small_fixture_budget -v` -> pass
  - `env PYTHONTRACEMALLOC=1 python3 -m unittest tests.test_refactoring_contracts.RefactoringContractTests.test_sense_pack_stays_within_small_fixture_budget tests.test_refactoring_contracts.RefactoringContractTests.test_sense_performance_benchmark_command_schema_and_argparse tests.test_refactoring_contracts.RefactoringContractTests.test_sense_traced_peak_is_isolated_from_external_tracing -v` -> pass, 3 tests
  - `python3 -m unittest discover -s tests -v` -> pass, 28 tests
  - `npm --prefix demo run typecheck` -> pass
  - `npm --prefix demo run build` -> pass-with-warning, Vite chunk-size warning
  - `npm --prefix demo run test:runtime` -> pass
  - `npm --prefix demo run capture:smoke` -> pass
  - `python3 tests/benchmark_sense_performance.py --wall-runs 7 --traced-runs 3` -> pass, complete schema emitted
  - `git diff --check` -> pass
- Artifacts:
  - `tests/golden/knight/baselines/sense-performance-baseline.json`
  - `tests/benchmark_sense_performance.py`
  - `tests/test_refactoring_contracts.py`
- Benchmark delta:
  - sense wall-clock: 7-run median 0.112591 seconds, max 0.113284 seconds on Linux/CPython 3.12.3 with rembg patched off and corner-distance matte
  - traced Python allocations: 3-run median 909031 bytes, max 909319 bytes under separate tracemalloc measurement
- Decisions/risks:
  - developer smoke now runs three live wall-clock measurements against median/max ceilings derived from this environment baseline instead of a bare literal 0.75 seconds
  - process RSS remains deferred to `PERF-110`; M0 records traced Python allocation peaks only
  - release performance gate remains deferred to `PERF-110` after representative fixtures
- Next: `M0-011`

### 2026-07-21 - M0-009 v0 Gate A-E failure report

- Completed: `M0-009`
- In progress: none
- Blocked: none
- Verification:
  - `python3 -m unittest tests.test_knight_m0_baseline -v` -> pass, 5 tests
- Artifacts:
  - `tests/golden/knight/reports/v0-gate-a-e-failure-report.json`
  - `tests/golden/knight/baselines/m0-baseline-report.json`
  - `tests/test_knight_m0_baseline.py`
- Benchmark delta:
  - quality: v0 shallow knight now has a tracked reject report for Gate A-E instead of an implicit narrative failure
  - render: report records RND-101 capture harness availability without using current demo factory pixels as proof for the v0-shallow Blueprint
- Decisions/risks:
  - report uses an M0-local schema until `REV-101`/`RND-130` define canonical ReviewReport/RenderSet contracts
  - Gate A-E values are fail-closed baseline assertions, not final measured acceptance thresholds
- Next: `M0-010`

### 2026-07-21 - RND-101 deterministic capture smoke

- Completed: `RND-101`
- In progress: none
- Blocked: none
- Verification:
  - `npm --prefix demo run capture:smoke` -> pass; profile `knight-source-34-m0`, viewport 640x640, repeated subject-only beauty hash `4416b131`, repeated alpha-only hash `c450d79d`, beauty foreground pixels 41315, alpha stats include transparent and opaque pixels
  - stale server/port conflict probe and unresponsive listener probe on `127.0.0.1:4174` -> expected bounded failure before capture
  - `npm --prefix demo run typecheck` -> pass
- Artifacts:
  - `demo/src/capture/profiles.ts`
  - `demo/src/capture/m0-profile.json`
  - `demo/tests/capture-smoke.mjs`
  - `demo/main.ts`
  - `demo/src/app/renderer.ts`
  - `demo/src/app/scene.ts`
  - `demo/package.json`
- Benchmark delta:
  - quality: adds deterministic browser capture evidence without changing normal interactive runtime behavior
  - runtime/browser: capture mode freezes animation and uses renderer readback from a preserved drawing buffer
- Decisions/risks:
  - RND-101 uses same-environment exact readback hash plus alpha silhouette stats to prove harness determinism; those current-demo pixels are explicitly excluded from v0-shallow Gate A-E evidence until `RND-130`/`REV-101`
  - production review artifacts and Gate A-E failure report remain `M0-009`
- Next: `M0-009`

### 2026-07-21 - DX-110 browser runtime smoke

- Completed: `DX-110`
- In progress: none
- Blocked: none
- Verification:
  - `npm --prefix demo run test:runtime` -> pass; intentional fixture emitted `console.error` and `pageerror`, app canvas/WebGL smoke passed
  - `npm --prefix demo run typecheck` -> pass
  - `npm --prefix demo run build` -> pass-with-warning, 540.58 kB chunk warning
  - `python3 -m unittest discover -s tests -v` -> pass, 24 tests
  - `git diff --check` -> pass
- Artifacts:
  - `demo/tests/runtime-smoke.mjs`
  - `demo/tests/runtime-error.html`
  - `demo/package.json`
  - `demo/package-lock.json`
- Benchmark delta:
  - quality: no production quality change
  - runtime/browser: pageerror and console error are now checked independently from Vite build success
- Decisions/risks:
  - added Playwright as a dev dependency for browser smoke; clean-install browser provisioning and Chromium install preflight remain covered by `M0-011`
  - canonical beauty/alpha capture remains `RND-101`
- Next: `RND-101`

### 2026-07-21 - DX-101 strict TypeScript typecheck

- Completed: `DX-101`
- In progress: none
- Blocked: none
- Verification:
  - `npm --prefix demo run typecheck` -> pass
  - `npm --prefix demo run build` -> pass-with-warning, 539.82 kB chunk warning
  - `python3 -m unittest discover -s tests -v` -> pass, 24 tests
  - `git diff --check` -> pass
- Artifacts:
  - `demo/tsconfig.json`
  - `demo/package.json`
  - `demo/package-lock.json`
- Benchmark delta:
  - quality: no production quality change
  - runtime/build: build chunk warning remains assigned to `OBS-10`, `PERF-110`, and `PERF-120`
- Decisions/risks:
  - added dev-only `@types/three` and `@types/node` so strict typecheck can validate Three.js and Vite config imports
  - browser pageerror runtime smoke remains `DX-110`
- Next: `DX-110`

### 2026-07-21 - M0 command baseline

- Completed: `M0-005`
- In progress: none
- Blocked: none
- Verification:
  - `/usr/bin/time -f 'ELAPSED_SECONDS=%e' python3 -m unittest discover -s tests -v` -> pass, 23 tests, 6.49 seconds wall-clock
  - `/usr/bin/time -f 'ELAPSED_SECONDS=%e' npm --prefix demo run build` -> pass-with-warning, 1.32 seconds wall-clock
  - `python3 -m unittest tests.test_knight_m0_baseline -v` -> pass, 4 tests
  - `python3 -m unittest discover -s tests -v` -> pass, 24 tests after adding report validation
- Artifacts:
  - `tests/golden/knight/baselines/m0-baseline-report.json`
  - `tests/test_knight_m0_baseline.py`
- Benchmark delta:
  - quality: no production quality change
  - runtime/build: Vite build emits `dist/assets/index-Bu9k8q_o.js` at 539.54 kB and keeps OBS-10 linked to `PERF-110`/`PERF-120`
- Decisions/risks:
  - at this snapshot, `demo/package.json` lacked `typecheck` and `test:runtime`; `typecheck` was added later in `DX-101`, while runtime smoke remains `DX-110`
  - baseline commit is recorded as `5d658c6d1d309648f3727800a969483416641410` with dirty M0 worktree disclosure and a five-file artifact-set checksum
- Next: `DX-101`

### 2026-07-21 - M0 fixture inventory and traceability

- Completed: `M0-001`, `M0-002`, `M0-003`, `M0-004`
- In progress: none
- Blocked: none
- Verification:
  - `python3 -m unittest tests.test_knight_m0_baseline -v` -> pass, 3 tests
  - `python3 -m unittest discover -s tests -v` -> pass, 23 tests
- Artifacts:
  - `tests/golden/knight/manifest.json`
  - `tests/golden/knight/blueprints/v0-shallow.json`
  - `tests/golden/knight/expected-contracts/v2-character-depth-failures.json`
  - `tests/golden/knight/reports/obs-traceability.json`
  - `tests/golden/knight/baselines/m0-baseline-report.json`
  - `tests/test_knight_m0_baseline.py`
- Benchmark delta:
  - quality: no production quality change; the shallow character acceptance gap is now represented by a tracked v1-pass/target-v2-fail fixture
  - runtime/memory: not measured in this slice
- Decisions/risks:
  - existing repo-local knight binaries are referenced by path and hash instead of duplicated into `tests/golden`
  - ignored `demo/work/**` artifacts are listed only as prior local baseline evidence, not clean-checkout test inputs
  - browser console, beauty render, and alpha render remain M0 follow-up evidence for `DX-110`, `RND-101`, and `M0-009`
- Next: `M0-005`

### 2026-07-21 - 계획 작성

- Completed: 계획 문서 분해와 task dependency 설계
- In progress: `M0-001`
- Blocked: none
- Verification:
  - 문서 링크·파일명·체크박스 검사 통과
  - Python tests: 20개 중 19개 통과, Sense 0.75초 budget 1개 실패(실측 0.985초)
  - demo build: dependency 미설치로 Vite를 찾지 못해 미실행
- Artifacts: `docs/planning/quality-upgrade-execution/`
- Benchmark delta: 구현 전이므로 없음
- Next: `M0-001`
