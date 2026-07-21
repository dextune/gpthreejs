# gpthreejs 품질 고도화 실행 계획

## 문서 상태

- 상태: `planned`
- 기준일: 2026-07-21
- 적용 대상: gpthreejs v0.1 계열
- 실행 추적: [tasklist.md](./tasklist.md)
- 언어: 사용자 요청에 따라 이 계획 묶음은 한국어로 작성한다.

## 목적

이 문서 묶음은 외부 품질 검토서의 제안과 실제 기사 캐릭터 제작 과정에서 확인된 실패를 합쳐, 구현 순서와 검증 기준이 있는 작업 계획으로 바꾼 것이다. 목표는 “디테일이 많은 코드”가 아니라 다음 결과다.

> 참조 근거를 보존하면서, 형상·포즈·부착·재질이 읽히는 절차적 Three.js 결과를 만들고, 잘못된 결과는 자동 승인하지 않는다.

## 기준 자료

1. 외부 검토서
   - 파일: `C:\Users\User\Downloads\gpthreejs_quality_improvement_bundle_ko\gpthreejs_quality_review\gpthreejs_quality_improvement_master_plan_ko.md`
   - SHA-256: `210005DB82A8364E1FFC9AAC69A9216FDD66AA5A69234A83B92956911714891D`
   - 반영 항목: ReferenceSet, canonical renderer, fail-closed review, revision/hash, iteration controller, geometry vocabulary, CPU 예산, ChatGPT App 확장안
2. 실제 실행 관찰
   - 복잡한 배경과 화면을 가득 채운 피사체에서 matte 휴리스틱이 `SUBJECT_FILLS_FRAME`, `MATTE_HEURISTIC`을 발생시켰고 수동 padding이 필요했다.
   - 단일 캐릭터 입력은 `CHAR_SINGLE_VIEW`, `CHAR_NO_SIDE`, `GAME_VIEWS_THIN`으로 중단되어 front/side/back 보강이 필요했다.
   - `ledger`는 `targetMin=6`인데 TODO 3개만 생성해 수작업으로 항목을 채워야 했다.
   - `blueprint`는 캐릭터 입력에도 `root_mass`와 `accent_trim` 중심의 얕은 상자를 생성했다.
   - strict validation은 ledger 연결만 충족하면 캐릭터 의미 구조가 빈약해도 통과할 수 있었다.
   - 생성 데모를 다른 경로로 복사하면 `surfaceKit.ts`의 저장소 상대 import가 깨졌다.
   - Vite build는 통과했지만 잘못된 geometry helper 인자 때문에 런타임에서 `parent.add is not a function`이 발생했다.
   - 고해상도 surface map과 강한 AO가 금속의 검은 영역을 늘려 형상 판독성을 악화시켰다.
   - 검과 방패의 손 접촉, 좌우 배치, 포즈 관계가 `FormHandles` 존재만으로 보장되지 않았다.
   - 조명·노출을 수동으로 올려야 갑옷 형태가 읽혔고, 결과는 여전히 블록아웃 인상이 강했다.
3. 현재 저장소 코드
   - [`engine/blueprint/draft.py`](../../../engine/blueprint/draft.py)는 실제로 TODO 3개와 box 기반 기본 Blueprint를 만든다.
   - [`engine/blueprint/validate.py`](../../../engine/blueprint/validate.py)는 일부 ledger 참조를 검증하지만 캐릭터 필수 구조, 중복 ID, cycle, 수치 범위, 접촉 품질을 충분히 막지 않는다.
   - [`engine/cast/emit_factory.py`](../../../engine/cast/emit_factory.py)는 지원하지 않는 geometry를 box로 조용히 대체한다.
   - [`engine/cast/fit_params.py`](../../../engine/cast/fit_params.py)는 실제 Three.js 렌더가 아닌 96×96 matte 대리 목적함수로 `root_mass`만 탐색한다.
   - [`engine/critique/journal.py`](../../../engine/critique/journal.py)는 metrics나 feature score가 없을 때도 `accept` 경로가 열릴 수 있다.
   - [`demo/src/detail/surfaceKit.ts`](../../../demo/src/detail/surfaceKit.ts)는 `../../../engine/.../presets.json`에 결합되어 배포 경로가 취약하다.
   - [`demo/package.json`](../../../demo/package.json)은 build만 제공하고 typecheck와 브라우저 런타임 smoke test가 없다.

## 핵심 판단

기사 결과의 가장 큰 문제는 micro texture 부족이 아니다. 실패 순서는 다음과 같다.

```text
불완전한 입력 판독
  -> 빈약한 Feature Ledger
  -> 의미 부품이 없는 Blueprint
  -> 제한된 primitive emitter
  -> 경직된 비율/포즈와 잘못된 부착
  -> 환경광 없는 금속 + 강한 AO
  -> 단일 beauty 화면만 확인
  -> 수치·시각 게이트 없이 수동 accept
```

따라서 surface detail을 먼저 늘리는 작업은 금지한다. 다음 순서를 지킨다.

```text
M0 기준선·런타임 게이트
  -> M1 계약·fail-closed
  -> M2 참조·Ledger 품질
  -> M3 캐릭터 형상·포즈·부착
  -> M4 canonical render·review
  -> M5 자동 iteration
  -> M6 성능·배포성
  -> M7 ChatGPT App 연결
```

## 문서 지도

| 문서 | 범위 |
| --- | --- |
| [01-observed-failures-and-success-criteria.md](./01-observed-failures-and-success-criteria.md) | 실제 실패, 근본 원인, 기사 benchmark, 최종 성공 기준 |
| [02-reference-sense-and-sufficiency-plan.md](./02-reference-sense-and-sufficiency-plan.md) | ReferenceSet, matte, multi-view, Ledger 생성·검증 |
| [03-blueprint-character-and-geometry-plan.md](./03-blueprint-character-and-geometry-plan.md) | Blueprint v2, 캐릭터 비율·포즈·landmark·geometry·부착·재질 |
| [04-render-review-and-iteration-plan.md](./04-render-review-and-iteration-plan.md) | canonical render, multi-pass metrics, reviewer, fail-closed, 반복 수정 |
| [05-runtime-tooling-and-portability-plan.md](./05-runtime-tooling-and-portability-plan.md) | emitter/runtime 계약, typecheck, 브라우저 smoke, 경로·인코딩·리소스 해제 |
| [06-testing-benchmarks-and-release-gates.md](./06-testing-benchmarks-and-release-gates.md) | 테스트 계층, fixture, 실패 모드, 성능 및 릴리스 게이트 |
| [07-delivery-sequencing-and-parallelization.md](./07-delivery-sequencing-and-parallelization.md) | 마일스톤, 의존성, 병렬 작업 lane, 범위 제외 |
| [08-multi-agent-goal-prompt.md](./08-multi-agent-goal-prompt.md) | 고정 모델 배치, agent 역할, work packet, 리뷰 루프가 포함된 실행용 Goal 프롬프트 |
| [tasklist.md](./tasklist.md) | 안정적인 작업 ID, 체크박스, 상태·증거·진척 로그 |

## 유지하고 재사용할 것

| 현재 자산 | 결정 |
| --- | --- |
| Sense Pack, Intake Brief, Feature Ledger, Form Blueprint | 이름과 역할을 유지하고 schema를 확장한다. |
| Cast layer 순서 | 유지한다. 캐릭터의 `proportion`, `landmarks`를 실제 gate로 승격한다. |
| `engine/commands/` registry | 재사용해 production orchestration command를 추가한다. |
| shared quality/detail mode 계약 | 유지한다. `qualityMode`에 캐릭터 유형을 섞지 않는다. |
| Surface preset 단일 JSON | 유지하되 생성 결과가 저장소 상대 경로에 의존하지 않게 패키징한다. |
| deterministic seed와 bounded worker | 유지하고 실제 render objective에 연결한다. |
| demo runtime 분리와 `RuntimeResources` | canonical harness의 출발점으로 재사용한다. |
| 기존 unit/regression tests | 새 계약의 하위 호환 회귀 기준으로 유지한다. |
| [refactoring-opportunities.md](../refactoring-opportunities.md) | 완료된 리팩터링을 중복 구현하지 않고, 남은 배포·bundle 이슈만 이 계획에 연결한다. |

## 주요 계약 결정

1. `qualityMode`는 계산량과 fidelity 예산만 나타낸다.
2. 형상 전략은 새 `modelingProfile`로 분리한다. 초기값은 `generic-prop`, `stylized-character`, `hard-surface-hero`다.
3. 사용 목적은 `intent`로 유지한다. 예: `realtime-prop`, `game`, `hero-render`, `animation`, `likeness`.
4. Blueprint v1은 즉시 제거하지 않는다. v2 validator와 v1→v2 migration을 함께 제공한다.
5. 생성 factory는 최소한 Three.js 외 저장소 내부 상대 import 없이 복사·빌드 가능해야 한다.
6. reviewer는 추천만 생성하고 최종 `accept`는 deterministic policy가 결정한다.
7. 실제 렌더가 없는 fit은 production 경로에서 사용하지 않는다. 기존 fit은 `experimental-proxy`로 명시하거나 비활성화한다.

## NOT in scope

- photoreal face, 피부, 머리카락 재현: 이번 목표는 stylized hero character의 구조적 품질이다.
- 완전 자동 rigging과 cloth simulation: 정적 pose와 attachment 정확성이 먼저다.
- 기존 프랜차이즈 캐릭터의 1:1 복제: 시각 언어와 품질을 목표로 하되 특정 IP 동일성을 목표로 하지 않는다.
- neural mesh/NeRF/Gaussian splat을 기본 경로로 채택: `hybrid`는 명시적 opt-in으로 유지한다.
- Blueprint 전면 폐기 또는 Python 엔진 전체 재작성: v1 호환 migration을 둔 점진적 변경으로 진행한다.
- ONNX, CMA-ES, Wasm SIMD 선행 최적화: 실제 render 기반 품질 objective와 profiling이 준비된 뒤 시작한다.
- ChatGPT App 전체 UI를 품질 기반보다 먼저 구현: 앱은 검증된 production command의 consumer로 둔다.

## 프로그램 완료 조건

다음을 모두 만족해야 전체 고도화를 완료로 본다.

- 기존 얕은 캐릭터 Blueprint fixture가 strict v2 validation에서 실패한다.
- 기사 benchmark가 카메라/포즈, mass, identity geometry, layered detail, material readability 순으로 모든 gate를 통과한다.
- 검과 방패는 손/팔 socket과 접촉하고, float·관통·좌우 반전 문제가 없다.
- neutral light와 beauty light 양쪽에서 실루엣과 재질 역할이 읽힌다.
- source-aligned 및 front/left/right/back의 deterministic render set이 자동 생성된다.
- render, metrics, critical feature evidence, artifact hash 중 하나라도 없거나 stale이면 accept되지 않는다.
- 동일 seed/profile/renderer에서 허용 오차 내 재현된다.
- `python -m engine`의 production command, Python test, TypeScript typecheck, Vite build, headless runtime smoke가 CI에서 통과한다.
- 생성 factory를 임시 독립 프로젝트로 복사해도 저장소 상대 import 없이 build와 runtime smoke를 통과한다.
- 기사 외 두 번째 stylized character 또는 hard-surface prop fixture에서도 gate가 유효해 과적합을 피한다.

## 진척 업데이트 규칙

모든 구현 작업은 [tasklist.md](./tasklist.md)의 안정적인 ID를 사용한다.

- 시작: checkbox는 미완료로 두고 `Status`를 `in-progress`로 변경한다.
- 완료: checkbox를 체크하고 `Status=done`, `Evidence`에 PR/commit/test/artifact를 기록한다.
- 차단: `Status=blocked`로 변경하고 `Blocker`와 해제 조건을 기록한다.
- 범위 변경: task를 삭제하지 말고 `superseded`로 남긴 뒤 대체 task ID를 연결한다.
- 각 마일스톤 종료 시 progress snapshot과 benchmark 결과를 `Progress log`에 추가한다.
