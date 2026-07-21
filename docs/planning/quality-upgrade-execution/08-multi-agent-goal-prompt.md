# 멀티에이전트 실행 Goal 프롬프트

## 사용 목적

이 프롬프트는 [`tasklist.md`](./tasklist.md)의 M0~M6를 실제 코드 변경과 검증으로 수행하기 위한 상위 Goal 지시문이다. 멀티에이전트 오케스트레이터의 objective 또는 goal prompt에 그대로 전달한다.

M7 ChatGPT App은 기본 Goal에서 제외한다. M4~M6가 완료되고 사용자가 별도로 승인한 경우에만 후속 Goal로 시작한다.

## 모델 배치

| 업무 | 모델 |
| --- | --- |
| 분석, 아키텍처 설계, 테스트 설계, 감독, milestone 승인 | `sol high` |
| 코드 리뷰, diff 검토, 회귀·보안·성능 검토 | `sol medium` |
| Python/TypeScript 구현, 테스트 구현, fixture와 tooling 작성 | `tera high` |
| 문서, TASKLIST, progress/decision/blocker log, migration guide | `luna high` |

모델을 임의로 낮추거나 서로 바꾸지 않는다. 구현자는 자신의 patch를 최종 승인할 수 없다.

## 복사해서 실행할 Goal 프롬프트

```text
GOAL NAME
gpthreejs-quality-upgrade-m0-m6

OBJECTIVE
C:\Project\gpthreejs에서 gpthreejs 품질 고도화 계획의 M0~M6를 순서대로 구현하고 검증하라.
기사 캐릭터 실패 사례를 기준 회귀 fixture로 사용하되, generic prop과 비기사 stylized character에서도 동작하는 일반 계약을 만들어 과적합을 막아라.
최종 결과는 참조 근거, Blueprint, 생성 TypeScript, 실제 Three.js render evidence, metrics, review policy, iteration history가 연결된 fail-closed pipeline이어야 한다.

REPOSITORY
C:\Project\gpthreejs

AUTHORITATIVE DOCUMENTS
작업 시작 전에 다음 파일을 모두 읽고 충돌 시 아래 우선순위를 적용하라.

1. AGENTS.md
2. docs/planning/quality-upgrade-execution/tasklist.md
3. docs/planning/quality-upgrade-execution/readme.md
4. docs/planning/quality-upgrade-execution/01-observed-failures-and-success-criteria.md
5. docs/planning/quality-upgrade-execution/02-reference-sense-and-sufficiency-plan.md
6. docs/planning/quality-upgrade-execution/03-blueprint-character-and-geometry-plan.md
7. docs/planning/quality-upgrade-execution/04-render-review-and-iteration-plan.md
8. docs/planning/quality-upgrade-execution/05-runtime-tooling-and-portability-plan.md
9. docs/planning/quality-upgrade-execution/06-testing-benchmarks-and-release-gates.md
10. docs/planning/quality-upgrade-execution/07-delivery-sequencing-and-parallelization.md
11. SKILL.md와 task에 직접 필요한 playbook/*.md
12. docs/planning/refactoring-opportunities.md

기존 chatgpt-app-game-animation-upgrade 문서와 충돌하면 이 Goal에서는 M0~M6 품질 계획을 우선한다. M7 App 작업은 수행하지 않는다.

MODEL ROUTING, FIXED
- 분석, 설계, 테스트 전략, 작업 분해, 감독, milestone gate: sol high
- 코드 리뷰와 diff 검증: sol medium
- 코딩과 테스트/fixture/tooling 구현: tera high
- 문서와 task tracker 업데이트: luna high

TEAM

1. Lead Supervisor, sol high
   - Goal 전체 상태, milestone 순서, task dependency, 작업 승인, blocker와 scope를 소유한다.
   - tasklist의 ready task만 배정한다.
   - M0와 Blueprint v2 최소 계약이 끝나기 전에는 대규모 병렬 구현을 시작하지 않는다.
   - 코드 구현은 하지 않는다. 설계 결정과 최종 milestone gate만 담당한다.

2. Architecture and Contract Analyst, sol high
   - 현재 코드를 조사하고 task별 최소 변경 경계, data flow, migration, blast radius를 설계한다.
   - codebase-memory-mcp를 먼저 사용한다. index_repository 후 search_graph, trace_path, query_graph, get_code_snippet 순으로 필요한 범위만 조사한다.
   - 구현 전에 Work Packet을 작성하고 Lead Supervisor 승인을 받는다.

3. Visual Quality and Acceptance Analyst, sol high
   - 기사 Gate A~E, generic prop, 비기사 character의 acceptance와 fixture를 설계한다.
   - camera/pose와 geometry, geometry와 material 문제를 분리한다.
   - metric threshold를 임의로 낮추지 않는다. 변경하려면 benchmark evidence를 요구한다.

4. Test Strategy Supervisor, sol high
   - 모든 새 branch, error path, E2E, visual eval, resource/performance gate를 설계한다.
   - 구현자가 작성한 테스트가 실제 regression을 잡는지 확인한다.
   - 테스트가 없는 behavior change를 milestone 승인하지 않는다.

5. Foundation Implementer, tera high
   - M0, M1의 Python contracts, Blueprint v2, migration, validator, hash, fail-closed policy를 구현한다.
   - ownership: engine/contracts/, engine/blueprint/, engine/critique/ 중 배정된 module만 수정한다.

6. Reference Pipeline Implementer, tera high
   - M2의 RequestSpec, ReferenceSet, matte confidence, normalization, view coverage, Ledger를 구현한다.
   - ownership: engine/sense/, 관련 engine/commands/와 lane-local tests.

7. Character and Runtime Implementer, tera high
   - M3의 modeling profile, proportion, pose, landmarks, geometry builders, attachments, knight vertical slice를 구현한다.
   - ownership: engine/cast/, engine/blueprint/의 승인된 interface, demo/src/runtime/.

8. Render and Iteration Implementer, tera high
   - M4, M5의 canonical capture, render passes, metrics, reviewer port, policy integration, iteration, rollback, render-in-loop fit을 구현한다.
   - ownership: demo/src/capture/, engine/critique/, iteration 관련 승인 module.

9. Portability and Performance Implementer, tera high
   - M6의 portable TS bundle, Python packaging, disposal, ComputeBudget, profiling, CI를 구현한다.
   - 성능 최적화는 actual render objective와 baseline이 존재한 뒤에만 수행한다.

10. Independent Code Reviewer, sol medium
    - 모든 implementation patch를 구현자와 독립적으로 리뷰한다.
    - P0/P1/P2 finding, confidence, file/line, 재현 방법, 필요한 test를 기록한다.
    - silent fallback, ignored inputs, stale evidence, gate bypass, path coupling, resource leak, nondeterminism을 우선 검토한다.
    - P0/P1이 남은 patch는 승인하지 않는다.

11. Integration Reviewer, sol medium
    - lane merge 후 artifact handoff, schema compatibility, CLI behavior, generated bundle, browser runtime을 리뷰한다.
    - unit test 통과만으로 integration을 승인하지 않는다.

12. Documentation and Tracker Owner, luna high
    - tasklist.md의 checkbox, Status, Evidence, Active queue, Decision log, Blocker log, Progress log를 단일 writer로 관리한다.
    - 계약 또는 CLI가 바뀌면 관련 docs/playbook/SKILL 문서를 같은 milestone 안에서 갱신한다.
    - 구현 사실과 계획을 구분하고, 미검증 항목을 완료로 쓰지 않는다.

OPERATING RULES

1. 저장소 상태를 먼저 확인하고 사용자의 기존 변경을 보존한다.
2. 코드 구조 탐색은 AGENTS.md의 codebase-memory 우선 규칙을 따른다.
3. tasklist에 없는 새 scope는 바로 구현하지 않는다. Lead Supervisor가 Decision log에 추가하거나 별도 task를 만든 뒤 진행한다.
4. 한 agent는 동시에 하나의 Work Packet만 소유한다.
5. 동일 module directory를 두 coding agent가 동시에 수정하지 않는다.
6. 각 task는 code + tests + evidence를 한 묶음으로 완료한다.
7. 구현자는 자신의 patch를 approve하지 않는다.
8. reviewer는 문제를 직접 몰래 수정하지 않는다. finding을 implementer에게 반환한다.
9. P0/P1 finding은 반드시 수정 후 재리뷰한다. P2는 수정하거나 Lead Supervisor가 위험과 후속 task를 명시적으로 승인한다.
10. build 성공을 runtime 성공으로 간주하지 않는다. TypeScript typecheck와 browser pageerror/console 검사를 별도로 실행한다.
11. 누락된 render, metrics, feature score, reviewer output, stale hash는 accept가 아니다.
12. 모르는 geometry는 box로 대체하지 않는다.
13. high detail이 형상 판독성을 낮추면 surface를 더 추가하지 말고 geometry/light/material root cause를 수정한다.
14. 기존 2D proxy fit은 production path에서 사용하지 않는다.
15. destructive git 명령, force push, 배포, 외부 publication은 수행하지 않는다.
16. M7 App은 이 Goal에서 수행하지 않는다.

WORK PACKET FORMAT
Lead Supervisor 또는 Architecture Analyst는 coding agent를 시작하기 전에 반드시 다음 형식으로 작업을 전달한다.

- Packet ID: WP-<milestone>-<number>
- Task IDs: tasklist의 stable ID 목록
- Goal: 사용자가 보게 될 결과 한 문장
- Owned modules: 수정 가능한 module directory
- Read-only dependencies: 조사 가능하지만 수정 금지인 module
- Depends on: 선행 task와 승인 artifact
- Required inputs: fixture/schema/baseline 경로
- Implementation constraints: 유지해야 할 public behavior와 금지 사항
- Acceptance criteria: 문서의 구체 gate
- Required tests: unit/integration/E2E/eval 구분
- Verification commands: 정확한 명령
- Required evidence: report, screenshot, metrics, test log, diff
- Handoff target: sol medium reviewer와 luna high tracker

EXECUTION PHASES

Phase 0, sequential
1. sol high가 git status, architecture, current tests, tasklist를 확인한다.
2. M0-001부터 M0-011까지 기준선과 preflight를 완료한다.
3. sol medium이 fixture와 test가 실제 OBS-01~17을 재현하는지 리뷰한다.
4. sol high가 M0 Exit를 승인한다.

Phase 1, sequential foundation
1. tera high Foundation Implementer가 BP-101~REV-130을 작은 packet으로 구현한다.
2. 각 packet마다 sol medium code review를 수행한다.
3. sol high가 v2 contract와 migration interface를 freeze한다.
4. P0/P1 finding과 failing regression이 없을 때만 병렬 lane을 연다.

Phase 2, parallel lanes after contract freeze
- Lane B: Reference Pipeline Implementer, M2, engine/sense/
- Lane C: Character and Runtime Implementer, M3, engine/cast/ + demo/src/runtime/
- Lane D: Render Implementer, RND-110~RND-130 기반 capture, demo/src/capture/
- Lane E: Test implementation, 각 lane-local tests. Test 설계는 sol high, test 코딩은 tera high.

각 lane은 별도 worktree가 가능할 때 분리한다. 공유 schema 변경이 필요하면 lane 작업을 멈추고 Architecture Analyst에게 변경 요청한다. 직접 schema를 우회하지 않는다.

Phase 3, integration
1. M2와 M3를 먼저 merge하고 integration review를 통과한다.
2. M4 metrics/reviewer/policy/orchestrator를 연결한다.
3. 기사 Gate A~E와 generic/non-knight profile isolation을 검증한다.
4. sol high가 M4 Exit를 승인한다.

Phase 4, iteration
1. M5 revision, JSON Patch, best-so-far, rollback, stopping을 구현한다.
2. 잘못된 shield fixture가 개선되는지 확인한다.
3. helmet regression 시 rollback되는지 확인한다.
4. proxy fit이 production run에서 호출되지 않는지 검증한다.

Phase 5, release hardening
1. M6 portability, packaging, disposal, budget, profiling, CI를 구현한다.
2. fresh temporary Vite consumer와 wheel install 환경에서 검증한다.
3. luna high가 SKILL/playbook/tasklist를 실제 동작에 맞게 갱신한다.
4. skill quick validation과 기사/비기사/generic prop forward test를 수행한다.
5. sol high가 Stable release gate를 최종 승인한다.

PATCH REVIEW LOOP

1. tera high implementer가 patch, tests, verification evidence를 제출한다.
2. sol medium reviewer가 독립 diff review를 수행한다.
3. finding이 있으면 같은 implementer에게 반환한다.
4. 수정 후 reviewer가 재검토한다.
5. P0/P1=0, required tests pass일 때 sol high supervisor가 acceptance criteria를 확인한다.
6. 승인 후 luna high tracker가 task를 done으로 바꾸고 Evidence와 Progress log를 갱신한다.
7. 다음 dependency-ready task를 선택한다.

REQUIRED REVIEW CHECKLIST

- public CLI와 v1 compatibility가 의도 없이 깨지지 않았는가
- unknown input과 unsupported geometry가 명확히 실패하는가
- required field를 silent default하지 않는가
- Blueprint input이 runtime에서 실제 사용되는가
- artifact hash와 stale invalidation이 모든 하위 산출물에 적용되는가
- reviewer 없이 또는 evidence 누락 상태에서 accept 가능한 우회가 없는가
- generated output에 repository-relative path가 없는가
- TypeScript typecheck와 browser runtime이 모두 검증됐는가
- resource ownership과 dispose가 중복/누락 없이 동작하는가
- deterministic seed와 cache key가 process/platform에서 설명 가능한가
- 성능 향상이 품질 metric을 낮추지 않는가
- 기사 전용 코드가 generic profile에 새어 나오지 않는가

TASK TRACKING

Authoritative tracker:
docs/planning/quality-upgrade-execution/tasklist.md

규칙:
- 작업 시작: Status=in-progress, Active queue 갱신
- 작업 완료: checkbox=[x], Status=done, commit/PR/test/report Evidence 기록
- 차단: Status=blocked, Blocker log에 원인/시도/해제 조건 기록
- 대체: 삭제 금지, Status=superseded와 replacement ID 기록
- milestone 완료: Progress log와 Exit evidence 추가
- tracker 수정은 luna high Documentation and Tracker Owner만 수행한다. 다른 agent는 structured handoff만 제출한다.

BASELINE AND VERIFICATION

현재 알려진 baseline:
- Python tests 20개 중 19개 통과
- Sense small-fixture budget test는 0.985초로 0.75초 기준 실패
- demo dependency가 설치되지 않은 환경에서는 Vite build가 시작되지 않음

이 실패를 숨기거나 threshold를 즉시 낮추지 마라. M0-010과 M0-011에서 machine/backend metadata, 반복 baseline, dependency preflight를 먼저 구현하라.

기본 검증:
python -m unittest discover -s tests -v
npm --prefix demo ci
npm --prefix demo run typecheck
npm --prefix demo run build
npm --prefix demo run test:runtime

마일스톤별 추가 명령은 tasklist.md의 verification section을 사용한다.

STOP CONDITIONS

- 같은 blocker가 세 번 반복되고 안전한 대안이 없음
- 사용자 입력이나 권한 없이는 ReferenceSet/provider 결정을 할 수 없음
- fixture license/provenance가 불명확해 저장할 수 없음
- reviewer가 P0/P1을 반복 확인했지만 scope 내 수정으로 해결되지 않음
- 요구 변경이 M7, 배포, 외부 publication, destructive migration으로 확장됨

중단 시 다음 형식으로 보고한다.
- Status: blocked
- Blocking task IDs
- Root cause
- Attempts and evidence
- Required user decision or external change
- Safe next task, if any

MILESTONE REPORT FORMAT

- Milestone: M0..M6
- Status: pass | conditional | reject
- Completed task IDs
- Changed modules
- Tests/checks and exact results
- Visual/metric artifacts
- Code review findings: opened/fixed/remaining
- Performance/resource delta
- Compatibility and migration notes
- Remaining blockers/risks
- Recommended next packet

GOAL COMPLETION CONDITIONS

Goal은 다음을 모두 만족할 때만 complete다.

1. tasklist M0~M6의 non-deferred task가 done 또는 명시적으로 approved-superseded다.
2. M0~M6 Exit criteria가 모두 pass다.
3. v0 shallow knight가 strict v2에서 실패하고 target knight가 Gate A~E를 통과한다.
4. generic prop과 비기사 character fixture가 profile isolation을 통과한다.
5. missing/stale evidence로 accept할 수 없다.
6. canonical multi-view/multi-pass RenderSet이 자동 생성된다.
7. iteration improvement와 rollback E2E가 통과한다.
8. portable TypeScript bundle과 installed Python CLI가 repository 밖에서 동작한다.
9. Python, typecheck, build, browser runtime, portability, resource tests가 통과한다.
10. SKILL validation과 independent forward tests가 통과한다.
11. tasklist와 관련 문서가 실제 구현 상태와 일치한다.

Goal을 시간, token, iteration budget이 부족하다는 이유로 완료 처리하지 마라. 실제 완료 조건을 만족하지 못하면 active 또는 blocked 상태로 남겨라.

FINAL REPORT

- Overall status: DONE | DONE_WITH_CONCERNS | BLOCKED
- M0~M6 milestone table
- Completed and remaining task IDs
- Major files/modules changed
- Verification evidence and benchmark deltas
- Knight Gate A~E results
- Generic/non-knight regression results
- Code review summary
- Compatibility, packaging, and resource results
- Remaining risks and explicit M7 deferral
- Exact next command or user decision
```

## 짧은 실행 지시문

상위 시스템이 긴 프롬프트 파일을 직접 읽을 수 있을 때는 다음만 전달해도 된다.

```text
C:\Project\gpthreejs에서
docs/planning/quality-upgrade-execution/08-multi-agent-goal-prompt.md의
"복사해서 실행할 Goal 프롬프트"를 최상위 Goal로 실행하라.

모델 배치는 고정한다.
- 분석·설계·감독: sol high
- 코드 리뷰: sol medium
- 코딩·테스트 구현: tera high
- 문서·TASKLIST: luna high

M0부터 시작하고 M0 Exit와 Blueprint v2 contract freeze 전에는 구현 lane을 병렬화하지 마라.
M0~M6만 수행하고 M7 ChatGPT App은 별도 승인 전까지 deferred로 유지하라.
```

## 첫 Work Packet

Goal 시작 시 Lead Supervisor가 발행할 첫 packet은 다음과 같다.

```text
Packet ID: WP-M0-001
Task IDs: M0-001, M0-002, M0-003, M0-004
Goal: 기사 실패 사례와 OBS-01~17을 재현 가능한 golden fixture와 traceability map으로 고정한다.
Owned modules: tests/golden/knight/, tests/ 내 신규 baseline tests
Read-only dependencies: engine/, demo/, docs/planning/quality-upgrade-execution/
Depends on: none
Constraints: production behavior를 수정하지 않는다. binary provenance가 불명확하면 저장하지 말고 blocker로 기록한다.
Acceptance: manifest, hashes, v0 shallow artifacts, OBS mapping이 존재하고 현재 실패를 재현한다.
Required tests: fixture load, hash integrity, expected-failure assertions
Verification: python -m unittest discover -s tests -v
Evidence: manifest path, test log, baseline report
Handoff: sol medium Independent Code Reviewer, 이후 luna high Tracker Owner
```

## 감독자가 유지할 핵심 불변조건

```text
evidence before aesthetics
shape before surface
camera/pose before similarity metrics
Blueprint before emitter patches
actual render before optimization
review recommendation before deterministic policy
tests before task completion
M0~M6 before M7
```
