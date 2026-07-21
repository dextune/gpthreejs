# gpthreejs 품질 고도화 TASKLIST

## Tracker 상태

| Field | Value |
| --- | --- |
| Program status | `planned` |
| Current milestone | `M0` |
| Active task | `M0-001` |
| Last updated | `2026-07-21` |
| Last verified commit | `not-recorded` |
| Completed | `0 / 90` |
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
| 1 | `M0-001` | unassigned | - | fixture inventory |
| 2 | `M0-002` | unassigned | - | provenance + hashes |
| 3 | `M0-003` | unassigned | - | v0 shallow Blueprint fixture |

## M0 - 기준선과 회귀 잠금

Exit: OBS-01~17이 fixture/test/preflight에 연결되고, v0 knight의 실패 report와 최소 beauty/alpha capture가 재현된다.

| Done | ID | Task | Depends on | Evidence / Definition of done | Status |
| --- | --- | --- | --- | --- | --- |
| [ ] | M0-001 | 기사 입력·turnaround·현재 render·console 산출물 inventory 작성 | - | `tests/golden/knight/manifest.json` 초안 | todo |
| [ ] | M0-002 | fixture provenance, license, SHA-256 기록 | M0-001 | manifest에 모든 binary hash와 source class 존재 | todo |
| [ ] | M0-003 | 실제 실패를 보존한 v0 shallow Blueprint/ledger/factory fixture 작성 | M0-001 | strict v1은 통과 가능하고 v2 목표 gate는 실패하는 fixture | todo |
| [ ] | M0-004 | OBS-01~17을 test/eval/task/preflight ID에 매핑 | M0-001 | 누락 없는 traceability table | todo |
| [ ] | M0-005 | 현재 Python test와 demo build baseline 저장 | - | command, commit, duration, 결과가 baseline report에 기록 | todo |
| [ ] | DX-101 | `demo/tsconfig.json`과 strict `typecheck` script 추가 | M0-005 | `npm --prefix demo run typecheck` 실행 | todo |
| [ ] | DX-110 | Playwright pageerror/console runtime smoke scaffold 추가 | DX-101 | 의도적 runtime error fixture가 test를 실패시킴 | todo |
| [ ] | RND-101 | deterministic camera/light로 beauty와 alpha를 캡처하는 최소 harness 추가 | DX-110 | 동일 profile의 두 capture가 허용 오차 내 일치 | todo |
| [ ] | M0-009 | v0 knight 기준 render, metrics, failure report 고정 | M0-003, RND-101 | Gate A~E의 초기 실패가 report에 기록 | todo |
| [ ] | M0-010 | Sense 성능 smoke에 machine/backend metadata와 반복 baseline 추가 | M0-005 | 단일 0.75초 wall-clock 대신 환경별 회귀 판단 근거 | todo |
| [ ] | M0-011 | demo dependency preflight와 clean-install 절차 고정 | M0-005 | `npm ci` 후 build 가능, 미설치 시 actionable message | todo |

### M0 verification

```bash
python -m unittest discover -s tests -v
npm --prefix demo run typecheck
npm --prefix demo run build
npm --prefix demo run test:runtime
```

## M1 - 계약과 fail-closed 기반

Exit: shallow character, unknown geometry, missing/stale evidence가 모두 hard failure다. v1 compatibility는 유지한다.

| Done | ID | Task | Depends on | Evidence / Definition of done | Status |
| --- | --- | --- | --- | --- | --- |
| [ ] | BP-101 | Blueprint v2 schema와 typed contract 정의 | M0-003 | schema fixture와 field documentation | todo |
| [ ] | BP-102 | artifact canonical serialization과 content hash helper 구현 | BP-101 | key order/newline 차이에 hash가 안정적 | todo |
| [ ] | BP-103 | v1→v2 migration command와 compatibility wrapper 구현 | BP-101 | 기존 sample migration 후 cast smoke 통과 | todo |
| [ ] | BP-110 | duplicate ID, cycle, dangling ref, finite numeric, vector length 검사 | BP-101 | 각 invalid fixture가 JSON path와 함께 실패 | todo |
| [ ] | BP-111 | `stylized-character` strict role/layer/critical feature 검사 | BP-101 | v0 shallow knight가 실패 | todo |
| [ ] | BP-112 | ledger `mapsTo` referential integrity와 category coverage 검사 | BP-110 | unresolved/invalid link fixture 실패 | todo |
| [ ] | GEO-101 | geometry registry와 discriminated schema 정의 | BP-101 | 모든 지원 kind가 required fields를 가짐 | todo |
| [ ] | GEO-102 | `_geom_js`의 silent box fallback 제거 | GEO-101 | unknown kind regression test가 hard error | todo |
| [ ] | REV-101 | 최소 RenderSet, MetricReport, ReviewReport schema 정의 | BP-102 | valid/invalid contract tests | todo |
| [ ] | REV-110 | missing render/metrics/feature evidence에서 accept 차단 | REV-101 | 세 regression case 모두 실패 | todo |
| [ ] | REV-120 | journal과 layer sync가 policy가 발급한 decision만 사용하도록 변경 | REV-110 | 임의 `decision=accept` 입력이 거부됨 | todo |
| [ ] | REV-130 | Blueprint/factory 변경 시 하위 artifact stale 처리 | BP-102, REV-101 | stale acceptance regression test | todo |

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
| [ ] | REF-101 | RequestSpec schema와 parser 구현 | BP-102 | invalid intent/profile/feature weight tests | todo |
| [ ] | REF-102 | ReferenceSet manifest와 provenance 계약 구현 | REF-101 | observed/generated/inferred fixtures | todo |
| [ ] | REF-103 | 기존 single-image CLI를 ReferenceSet으로 감싸는 adapter 구현 | REF-102 | 기존 sufficiency tests 비회귀 | todo |
| [ ] | REF-110 | matte confidence report 추가 | REF-103 | occupancy/edge contact/component/noise 신호 기록 | todo |
| [ ] | REF-111 | reversible padding/canvas normalization 구현 | REF-110 | source hash와 transform 기록, 수동 padding 불필요 | todo |
| [ ] | REF-120 | manifest-derived view classification와 coverage 구현 | REF-102 | CLI flag보다 evidence를 우선하고 conflict warning | todo |
| [ ] | REF-121 | color/equipment/handedness 기반 cross-view consistency MVP | REF-120 | 변조된 side fixture reject | todo |
| [ ] | REF-130 | `draft_ledger`가 `targetMin` 이상 실제 entry를 만들거나 ask | REF-103 | `zones[:3]` 회귀 제거, TODO 0 | todo |
| [ ] | REF-131 | character global/meso/micro category coverage gate 구현 | REF-130, BP-112 | 누락 category가 strict error | todo |
| [ ] | REF-140 | `reference-plan`, `sense-set`, `sufficiency-set`, `ledger-set` CLI 추가 | REF-111, REF-131 | end-to-end artifact paths 생성 | todo |
| [ ] | REF-150 | optional image generation/edit provider port와 budget 계약 정의 | REF-102 | provider 미설치 시 clear `ask`; vendor 선택은 deferred | todo |

### M2 verification

```bash
python -m engine sufficiency-set tests/golden/knight/reference-set.json --request tests/golden/knight/request-spec.json
python -m unittest tests.test_sufficiency -v
```

## M3 - 캐릭터 geometry vertical slice

Exit: micro texture 없이 기사 비율, helmet/shield/sword identity, equipment contact가 읽히고 자동 검사된다.

| Done | ID | Task | Depends on | Evidence / Definition of done | Status |
| --- | --- | --- | --- | --- | --- |
| [ ] | BP-120 | `modelingProfile` rule table 추가 | BP-101 | prop/hero/character profile isolation tests | todo |
| [ ] | BP-130 | proportionProfile과 normalized measurements 구현 | BP-120 | head/body, shoulder, limb thickness assertions | todo |
| [ ] | BP-131 | source pose와 neutral pose joint hierarchy 구현 | BP-130 | pose switch 시 geometry 재생성 없이 transform 변경 | todo |
| [ ] | BP-132 | body/equipment landmark 계약 구현 | BP-131 | landmark world/screen projection test | todo |
| [ ] | GEO-110 | rounded-box, shape-extrude, lathe, tube builder 구현 | GEO-101 | bounds, deterministic key, invalid input tests | todo |
| [ ] | GEO-120 | beveled-plate, curve-blade, shield, feather, cloth-patch builder 구현 | GEO-110 | fixture geometry snapshots/bounds | todo |
| [ ] | ATT-101 | parent/child socket와 contact schema 구현 | BP-132 | dangling/mismatched socket strict failure | todo |
| [ ] | ATT-110 | world-space gap와 gross penetration 검사 구현 | ATT-101 | sword/shield/plume/cape fixtures | todo |
| [ ] | CHAR-101 | 기사 camera, handedness, chibi mass, stance slice | BP-131, RND-101 | Gate A/B comparison sheet | todo |
| [ ] | CHAR-110 | helmet, pauldron, shield, sword, plume identity geometry | GEO-120, CHAR-101 | Gate C part-ID/beauty evidence | todo |
| [ ] | CHAR-120 | torso layers, scarf, strap, brooch, belt, cape, lower armor | CHAR-110 | Gate D required roles와 part hierarchy | todo |
| [ ] | MAT-101 | neutral environment와 material role profile 구현 | RND-101 | steel/brass/cloth/leather 구분 | todo |
| [ ] | MAT-110 | black crush, clipping, AO/normal readability 검사 | MAT-101 | high detail이 no-detail보다 읽기 어려우면 fail | todo |
| [ ] | CHAR-130 | geometry gate 이후 trim/rivet/seam/surface polish 적용 | CHAR-120, MAT-110 | Gate A~E 비회귀 | todo |

### M3 verification

```bash
npm --prefix demo run check
python -m engine validate tests/golden/knight/blueprints/v2-target.json --strict
```

## M4 - Canonical render와 review

Exit: source-aligned + turnaround multi-pass가 자동 생성되고, deterministic policy 외 경로로 accept할 수 없다.

| Done | ID | Task | Depends on | Evidence / Definition of done | Status |
| --- | --- | --- | --- | --- | --- |
| [ ] | RND-110 | source-34/front/left/right/back/top-34 profile 구현 | RND-101, BP-131 | view manifest와 deterministic camera hashes | todo |
| [ ] | RND-120 | part-ID, albedo, normal, linear depth, material-debug, wireframe pass 구현 | RND-110 | 필수 pass PNG와 metadata | todo |
| [ ] | RND-130 | RenderSet manifest, partial-set validation, renderer version 기록 | RND-120, BP-102 | pass 누락/stale tests | todo |
| [ ] | MET-101 | camera/framing alignment metric 구현 | RND-110 | bbox center/occupancy/aspect report | todo |
| [ ] | MET-110 | silhouette IoU, tolerant boundary F, contour distance 구현 | RND-120 | current metric parity + new thresholds | todo |
| [ ] | MET-120 | landmark, part visibility, feature coverage metric 구현 | BP-132, RND-120 | per-view/part report | todo |
| [ ] | MET-130 | attachment depth/order와 material readability metric 구현 | ATT-110, MAT-110, RND-120 | critical feature evidence 연결 | todo |
| [ ] | REV-140 | structured vision reviewer port와 schema parser 구현 | REV-101, RND-130 | invalid/timeout/empty output tests | todo |
| [ ] | REV-150 | hard metrics + reviewer를 deterministic ReviewPolicy에 결합 | MET-130, REV-140 | reviewer 추천만으로 accept 불가 | todo |
| [ ] | REV-160 | journal entry에 artifact hashes와 policy trace 기록 | REV-130, REV-150 | report에서 decision 근거 역추적 | todo |
| [ ] | REV-170 | overlay/diff/part label/metric annotation comparison sheet | MET-130 | 기사 Gate A~E review artifact | todo |
| [ ] | ORCH-101 | reference→validate→cast→render→metrics→review production `run` command | REF-140, REV-160 | low-level 단계 생략 불가능한 E2E | todo |

### M4 verification

```bash
python -m engine run tests/golden/knight/project.json --max-iterations 0
npm --prefix demo run test:runtime
```

## M5 - 자동 iteration과 실제 render fit

Exit: 국소 patch가 target을 개선하고 regression/정체/예산 초과에서 rollback 또는 정상 종료한다.

| Done | ID | Task | Depends on | Evidence / Definition of done | Status |
| --- | --- | --- | --- | --- | --- |
| [ ] | ITER-101 | iteration record와 parent revision graph 구현 | REV-160 | revision DAG contract tests | todo |
| [ ] | ITER-102 | 허용 경로와 수치 범위를 제한한 JSON Patch validator 구현 | ITER-101, BP-110 | invalid path/type/range rejection | todo |
| [ ] | ITER-110 | camera/pose/mass/part/attachment/material/emitter root-cause mapping | REV-150 | issue→scope table tests | todo |
| [ ] | ITER-120 | best-so-far, critical regression detection, rollback 구현 | ITER-101, MET-130 | shield 개선 중 helmet regression rollback | todo |
| [ ] | ITER-130 | iteration/time/CPU/render/reviewer budget와 stagnation stop | ITER-120 | flat objective에서 deterministic 종료 | todo |
| [ ] | FIT-101 | 기존 `fit_root_mass`를 `experimental-proxy`로 표시하고 production path에서 제거 | ORCH-101 | run command가 proxy를 호출하지 않음 | todo |
| [ ] | FIT-110 | camera→global mass→major part의 render-in-loop coarse-to-fine MVP | FIT-101, ITER-130 | 실제 alpha/part-ID objective 사용 | todo |
| [ ] | CACHE-101 | revision/profile/pass 기반 render cache 구현 | RND-130, ITER-101 | local patch에서 unaffected artifact 재사용 | todo |

### M5 verification

```bash
python -m engine run tests/golden/knight/project.json --max-iterations 3
```

기대: target metric이 개선되거나 명확한 stopping reason과 best revision을 반환한다.

## M6 - Portability, 성능, skill release

Exit: 저장소 밖의 임시 프로젝트와 wheel 환경에서 동작하고, resource/budget/skill validation gate를 통과한다.

| Done | ID | Task | Depends on | Evidence / Definition of done | Status |
| --- | --- | --- | --- | --- | --- |
| [ ] | DX-120 | 위치 인자 geometry helper를 named object 인자로 변경 | DX-101, GEO-101 | argument-shift regression이 compile failure | todo |
| [ ] | DX-201 | TypeScript local surface preset module 생성 | DX-120 | repo-relative JSON import 제거 | todo |
| [ ] | DX-210 | `cast --out-dir` portable bundle emitter 구현 | DX-201, GEO-120 | bundle manifest와 no-external-path scan | todo |
| [ ] | DX-211 | 임시 Vite consumer typecheck/build/runtime test 추가 | DX-210, DX-110 | fresh temp project에서 통과 | todo |
| [ ] | DX-220 | `pyproject.toml`, console script, package data 추가 | M1 | wheel install smoke | todo |
| [ ] | DX-301 | UTF-8/replacement-character/mojibake gate 추가 | DX-210 | 생성 산출물 round-trip tests | todo |
| [ ] | RES-101 | `FormRuntime.dispose()`와 resource ownership set 구현 | DX-120 | geometry/material/texture/render target 1회 해제 | todo |
| [ ] | RES-110 | 반복 create/render/dispose leak E2E 추가 | RES-101, RND-130 | renderer memory 비증가 report | todo |
| [ ] | PERF-101 | 중앙 ComputeBudget와 stage semaphore 구현 | ORCH-101 | oversubscription invariant tests | todo |
| [ ] | PERF-110 | stage wall/CPU/RSS/render/cache profiling 추가 | PERF-101 | benchmark JSON 생성 | todo |
| [ ] | PERF-120 | coarse-to-fine candidate promotion과 cache 연결 | FIT-110, PERF-110 | 동일 품질에서 render count/wall-clock 개선 | todo |
| [ ] | DX-401 | SKILL frontmatter/core workflow와 character/review playbook 정리 | M5 interfaces | SKILL 500줄 이하, 상세 중복 없음 | todo |
| [ ] | DX-410 | `quick_validate.py`로 skill folder 검증 | DX-401 | validation success log | todo |
| [ ] | DX-420 | 기사/비기사/generic prop 독립 forward test | DX-410 | raw prompts, artifacts, 결과 report | todo |
| [ ] | CI-101 | Python + typecheck + build + browser + portability CI matrix 추가 | DX-211, DX-220, RES-110 | clean checkout CI 통과 | todo |

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
