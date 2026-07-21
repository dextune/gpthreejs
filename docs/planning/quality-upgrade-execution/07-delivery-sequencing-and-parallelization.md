# 전달 순서와 병렬화 계획

## 범위 조정 결론

외부 마스터 플랜의 최종 아키텍처를 한 번에 구현하면 engine/application/ports/adapters/renderer/app을 동시에 신설하게 된다. 현재 저장소 크기와 검증 자산에 비해 큰 폭의 구조 변경이다.

이 계획은 기능을 줄이지 않고 순서를 바꾼다.

1. 잘못된 성공을 먼저 차단한다.
2. 기사 vertical slice로 형상 품질을 증명한다.
3. 실제 render evidence를 production gate에 연결한다.
4. 자동 반복을 연결한다.
5. 그 다음 CPU와 App을 확장한다.

새 top-level package, service, provider는 실제 두 번째 consumer가 생길 때 추출한다.

## 마일스톤

## M0 - 기준선과 회귀 잠금

목표: 현재 실패를 재현 가능한 fixture로 고정하고 “build는 통과했지만 브라우저에서 깨짐”을 더 이상 놓치지 않는다.

산출물:

- knight v0 references/Blueprint/render/console manifest
- shallow Blueprint rejection 예정 fixture
- TypeScript typecheck scaffold
- browser pageerror smoke scaffold
- minimal deterministic beauty/alpha capture
- baseline test/build/metric report

Exit:

- OBS-01~17이 fixture, preflight 또는 명시적 contract test로 연결된다.
- 현재 v0가 어떤 gate에서 실패하는지 report가 남는다.

## M1 - 계약과 fail-closed 기반

목표: schema가 얕은 결과, 알 수 없는 geometry, evidence 없는 accept를 차단한다.

산출물:

- Blueprint v2 + v1 migration
- common/character strict validation
- unknown geometry hard error
- ReviewReport/RenderSet 최소 schema
- missing/stale evidence accept 차단
- content hash와 invalidation primitive

Exit:

- v0 shallow knight는 strict v2 실패.
- metrics/render/feature evidence가 없으면 accept 실패.
- 기존 v1 sample은 migration 또는 compatibility path로 동작.

## M2 - ReferenceSet과 Ledger

목표: 수동 padding과 TODO ledger를 production workflow에서 제거한다.

산출물:

- RequestSpec/ReferenceSet
- matte confidence와 reversible normalization
- manifest-derived view coverage
- cross-view consistency 기본 gate
- `targetMin`과 category coverage를 지키는 Ledger

Exit:

- frame-filling knight를 자동 normalize하거나 명확히 ask.
- production ledger TODO 0개.
- single-view character는 coverage 근거와 remedy를 반환.

## M3 - 캐릭터 geometry vertical slice

목표: texture 없이도 기사 정체성과 장비 관계가 읽히게 한다.

산출물:

- `stylized-character` profile
- proportion/pose/landmarks
- rounded/profile/plate/blade/feather/cloth builders
- socket/contact validation
- 기사 camera/handedness/mass/identity/torso/lower-body slices
- material readability profile

Exit:

- 몸통이 단일 box가 아니다.
- helmet/shield/sword silhouette가 source identity를 보존한다.
- 검/방패 attachment가 자동 검사된다.
- micro maps off에서도 형상이 읽힌다.

## M4 - Canonical render와 review

목표: 실제 Three.js multi-view/multi-pass evidence로 품질을 판정한다.

산출물:

- deterministic view/light profiles
- beauty/alpha/part-ID/albedo/normal/depth/material-debug capture
- framing/silhouette/landmark/part/attachment/readability metrics
- structured reviewer port
- fail-closed ReviewPolicy와 journal 연결

Exit:

- 수동 screenshot 없이 RenderSet 생성.
- critical feature 100% evidence.
- stale/partial/reviewer failure에서 accept 불가.

## M5 - Iteration controller

목표: 실패 부품만 수정하고 best revision과 rollback을 관리한다.

산출물:

- root-cause/action 분류
- JSON Patch planner
- revision graph
- best-so-far/rollback/stopping
- render cache
- render-in-loop fit MVP

Exit:

- 잘못된 shield fixture가 한 iteration 후 개선.
- helmet regression이 생기면 rollback.
- 무개선/예산 소진에서 정상 종료.

## M6 - Portability, 성능, skill release

목표: 생성 결과와 CLI를 다른 환경에서 실행하고, 검증된 objective를 효율화한다.

산출물:

- portable TS bundle
- Python wheel/console script/package data
- integrated disposal and resource E2E
- ComputeBudget와 stage profiling
- coarse-to-fine candidate promotion
- SKILL/playbook 정리, quick validation, forward tests

Exit:

- 임시 consumer 프로젝트에서 typecheck/build/runtime smoke.
- wheel install 후 저장소 밖에서 CLI 동작.
- worker/resource/budget gate 통과.
- 기사와 비기사 forward test 통과.

## M7 - ChatGPT App 연결

목표: 검증된 production command를 resumable App workflow로 노출한다.

선행 조건: M4 production artifacts와 M5 iteration state가 안정적이어야 한다.

산출물:

- MCP tools
- resumable project/job state
- reference review, comparison, iteration timeline, quality report UI
- artifact export

M7은 기존 [chatgpt-app-game-animation-upgrade.md](../chatgpt-app-game-animation-upgrade.md)와 조정한다. App UI가 engine contract를 다시 정의하지 않는다.

## 의존성 표

| Step | Modules touched | Depends on |
| --- | --- | --- |
| M0 baseline | `tests/`, `demo/src/capture/` | 없음 |
| M1 contracts | `engine/contracts/`, `engine/blueprint/`, `engine/critique/` | M0 fixture |
| M2 references | `engine/sense/`, `engine/commands/` | M1 hash/schema primitives |
| M3 character | `engine/blueprint/`, `engine/cast/`, `demo/src/runtime/` | M1 contracts, M0 capture |
| M4 review | `demo/src/capture/`, `engine/critique/`, `engine/commands/` | M1, M3 |
| M5 iteration | `engine/application/` 또는 기존 engine modules, `engine/cast/` | M4 |
| M6 portability | packaging, `demo/`, `SKILL.md`, `playbook/` | M3~M5 interfaces 안정화 |
| M7 App | `app/`, `docs/app/` | M4, M5, M6 |

## 병렬 lane

### 첫 구간

M0는 fixture와 공통 계약을 고정하므로 순차 실행한다. 여러 작업자가 서로 다른 “기준선”을 만들지 않게 한다.

### M1 이후

- Lane A: Blueprint v2 → strict validator → migration, 순차, `engine/blueprint/`, `engine/contracts/`
- Lane B: TypeScript runtime typing → geometry registry/builders → portable bundle, 순차, `demo/src/runtime/`, `engine/cast/`
- Lane C: ReferenceSet → matte confidence → view/ledger gate, 순차, `engine/sense/`
- Lane D: browser harness → passes → runtime/resource smoke, 순차, `demo/src/capture/`, `demo/tests/`
- Lane E: golden fixtures와 policy tests, A/B/C/D와 조율, `tests/`

실행:

1. M0 완료.
2. Lane A의 v2 contract 최소판 완료.
3. Lane B + C + D를 별도 worktree에서 병렬 실행.
4. 각 lane은 자체 unit test를 포함해 merge.
5. Lane E가 통합 fixture를 새 contract에 맞춰 고정.
6. M4 policy integration은 A/B/C/D merge 후 순차 실행.
7. M5는 M4 위에서 순차 실행.
8. M6의 packaging과 skill docs는 interface freeze 후 병렬 실행 가능.

## 충돌 위험

- Lane A와 B가 Blueprint type/geometry schema를 동시에 수정할 수 있다. A에서 interface를 먼저 freeze하고 B는 generated fixture로 소비한다.
- Lane B와 D가 demo renderer/resource 파일을 공유할 수 있다. `runtime/`과 `capture/` ownership을 분리한다.
- 모든 lane이 `tests/`를 수정하면 merge conflict가 난다. lane-local test folder를 쓰고 E에서 golden manifest만 통합한다.
- M2와 M4가 artifact hash helper를 중복 구현할 수 있다. M1에서 canonical hashing API를 먼저 만든다.

## 단계별 PR 원칙

각 PR은 다음 중 하나만 한다.

- contract/schema + tests
- behavior implementation + tests
- fixture/baseline update + review evidence
- packaging/docs

구조 변경과 품질 threshold 변경을 같은 PR에 섞지 않는다. threshold 변화는 benchmark 근거를 별도 기록한다.

권장 PR 크기:

- 1~3 module directory
- 하나의 task group
- 독립 rollback 가능
- tasklist ID가 title/body에 포함

## 결정이 필요한 항목과 기본값

| 항목 | 기본 결정 | 재검토 시점 |
| --- | --- | --- |
| 이미지 생성 provider | port만 정의하고 특정 vendor 선택은 보류 | M2 concept-only 구현 직전 |
| golden binary 저장 | manifest/hash는 Git, 큰 PNG는 Git LFS 우선 | M0 fixture 크기 측정 후 |
| browser runner | Playwright Chromium | M0 CI 호환성 확인 후 |
| runtime npm package | demo 내부 모듈로 시작 | M7 또는 두 번째 consumer 발생 시 |
| actual render optimizer | deterministic coarse-to-fine 먼저 | M5 objective 상관성 검증 후 |
| boolean/CSG | 초기 제외 | layered geometry로 해결 불가한 fixture 발생 시 |
| ONNX/OpenCV 필수화 | optional provider | heuristic 품질 benchmark 후 |

## 위험과 완화

| 위험 | 영향 | 완화 |
| --- | --- | --- |
| 기사 fixture 과적합 | 다른 subject 품질 저하 | 비기사 character와 generic prop fixture 동시 gate |
| golden image 취약성 | CI noise | pass별 metric, 동일환경 hash, cross-platform tolerance 분리 |
| schema v2 범위 폭증 | 개발 지연 | v1 migration, 세 profile만 구현, rule table 우선 |
| geometry builder 폭증 | 유지보수 증가 | fixture에서 필요한 10개 내외 builder만 우선 |
| vision reviewer 편향 | 잘못된 accept | reviewer는 추천만, deterministic policy가 최종 결정 |
| browser/GPU 변동 | 재현성 저하 | renderer/profile/version 기록, software-rendered CI job |
| CPU oversubscription | 속도·안정성 악화 | 중앙 ComputeBudget와 stage semaphore |
| surface detail이 형상을 숨김 | 시각 품질 퇴행 | neutral/readability pass와 no-detail comparison |

## NOT in scope

- M0~M6 전에 ChatGPT App 전체 UI 구현
- general-purpose 3D modeling kernel 또는 DCC 대체
- 완전 자동 rig/animation/cloth simulation
- 모든 geometry kind 사전 구현
- 특정 IP를 그대로 복제하기 위한 likeness guarantee
- 실측 benchmark 없이 CPU worker 수만 확대

## Engineering review 요약

- Scope challenge: big-bang 구조를 7개 마일스톤의 vertical slice로 축소했다.
- Architecture: 입력 단위, Blueprint 의미 구조, runtime portability, render evidence, fail-closed policy, iteration ownership을 분리했다.
- Code quality: silent fallback, ignored Blueprint input, repository-relative import, 위치 인자 helper를 우선 제거한다.
- Tests: 15개 필수 E2E와 branch-level failure tests를 계획했다.
- Performance: objective 완성 전 최적화를 보류하고 budget/profiling부터 둔다.
- Critical gaps: 현재 구현에는 존재하지만 각 gap을 task ID와 테스트에 연결했다.
- Parallelization: M0/A 선행 후 B+C+D 병렬, M4/M5 순차.
- Outside voice: 이번 문서 작성에서는 별도 실행하지 않았다. 제공된 외부 마스터 플랜을 독립 검토 입력으로 사용했다.

## 전체 완료 정의

M0~M6 exit criteria와 [06-testing-benchmarks-and-release-gates.md](./06-testing-benchmarks-and-release-gates.md)의 Stable gate를 모두 통과해야 engine/skill 고도화를 완료로 본다. M7 App은 별도 release track이다.
