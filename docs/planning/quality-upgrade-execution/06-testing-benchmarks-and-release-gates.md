# 테스트, Benchmark, Release Gate 계획

## 목표

품질을 주관적 screenshot 감상에만 맡기지 않고, 계약·실제 브라우저 렌더·feature evidence·사람/vision review를 계층화한다. 테스트는 구현 후 추가하는 부록이 아니라 각 task의 완료 조건이다.

## 현재 기준선

현재 테스트 자산:

- [`tests/test_engine.py`](../../../tests/test_engine.py): sense → blueprint → cast와 layer sync smoke
- [`tests/test_sufficiency.py`](../../../tests/test_sufficiency.py): missing/tiny/single-view/TODO/user message
- [`tests/test_surface.py`](../../../tests/test_surface.py): surface schema와 baking
- [`tests/test_refactoring_contracts.py`](../../../tests/test_refactoring_contracts.py): CLI dry-run, deterministic seed, factory reuse, worker parity, timing/memory smoke
- [`demo/package.json`](../../../demo/package.json): Vite build만 존재

현재 Python 회귀 테스트는 유지한다. 부족한 부분은 Blueprint v2, canonical browser render, fail-closed policy, portability, visual benchmark다.

2026-07-21 로컬 기준선 실행 결과:

- `python -m unittest discover -s tests -v`: 20개 중 19개 통과, 1개 실패. `test_sense_pack_stays_within_small_fixture_budget`가 0.985초로 고정 기준 0.75초를 초과했다.
- `npm --prefix demo run build`: `vite`를 찾지 못해 시작하지 못했다. 문서 검증 단계에서는 dependency install을 수행하지 않았다.

성능 실패는 threshold를 즉시 느슨하게 바꾸지 않는다. machine/backend metadata와 반복 측정을 먼저 추가한 뒤 release budget과 developer smoke budget을 분리한다.

## 테스트 계층

```text
                 [EVAL] structured visual review
              /                                    \
      [E2E] production CLI -> browser -> report -> policy
         /                                             \
 [INTEGRATION] ReferenceSet / Blueprint / emitter / capture
       /                                                   \
 [UNIT] schema, math, hashes, metrics, geometry builders, policy
```

각 계층의 역할을 섞지 않는다.

- Unit: deterministic pure contract와 계산
- Integration: 모듈 간 artifact handoff
- E2E: 실제 CLI, Node/Vite, 브라우저/WebGL, 파일 산출물
- Eval: landmark metric으로 설명하기 어려운 style/readability 판단

## 코드 경로 커버리지 지도

```text
REFERENCE FLOW
  input missing ------------------------ [UNIT + E2E]
  input decode failure ----------------- [UNIT]
  matte heuristic pass ----------------- [UNIT]
  matte low confidence -> fallback ----- [INTEGRATION]
  normalize -> recover ----------------- [INTEGRATION]
  still insufficient -> ask/abort ------ [E2E]
  generated view inconsistency --------- [EVAL + INTEGRATION]

BLUEPRINT FLOW
  v1 -> migrate v2 --------------------- [UNIT]
  valid generic prop ------------------- [UNIT]
  shallow character -------------------- [REGRESSION, CRITICAL]
  duplicate/cycle/NaN/unknown kind ----- [UNIT]
  ledger map unresolved ---------------- [UNIT]
  attachment missing/gap/penetration ---- [UNIT + INTEGRATION]

RUNTIME FLOW
  emit portable bundle ----------------- [INTEGRATION]
  TypeScript strict check --------------- [INTEGRATION]
  Vite build ---------------------------- [INTEGRATION]
  browser load/WebGL -------------------- [E2E]
  console/page error -------------------- [REGRESSION, CRITICAL]
  create/dispose loop ------------------- [E2E]

REVIEW FLOW
  complete RenderSet -------------------- [E2E]
  missing pass -------------------------- [UNIT]
  stale hash ---------------------------- [REGRESSION, CRITICAL]
  metric hard fail ---------------------- [UNIT]
  reviewer timeout/invalid output ------- [INTEGRATION]
  accept with missing evidence ---------- [REGRESSION, CRITICAL]
  local patch improves target ----------- [E2E + EVAL]
  unrelated feature regresses -> rollback [E2E]
  stagnation/budget stop ---------------- [UNIT + E2E]
```

## Golden fixture 구조

```text
tests/golden/
├─ knight/
│  ├─ manifest.json
│  ├─ references/
│  ├─ blueprints/
│  ├─ expected-contracts/
│  └─ baselines/
├─ stylized-character-02/
└─ hard-surface-prop-01/
```

저장 원칙:

- source image license/provenance를 manifest에 기록한다.
- 큰 binary는 Git LFS 또는 versioned fixture archive를 사용한다.
- JSON contract와 hash는 저장소에 둔다.
- renderer/OS/GPU 차이 때문에 beauty PNG의 exact hash만 gate로 쓰지 않는다.
- 동일 환경에서는 exact hash, 다른 환경에서는 alpha/part-ID hash와 perceptual tolerance를 조합한다.

## 기사 benchmark gate

### A. Reference/camera

- declared/detected view 일치
- source 3/4 camera/framing 정렬
- sword/shield handedness 일치

### B. Mass/pose

- head/body ratio, shoulder width, stance, limb thickness
- source pose와 neutral pose를 분리

### C. Identity geometry

- helmet eye slit
- plume silhouette
- asymmetric pauldron
- convex sun shield
- broad sword profile

### D. Layered detail

- scarf, strap, brooch, belt, tunic flap, cape
- lower armor overlap

### E. Material/readability

- steel/brass/cloth/leather role separation
- black crush와 clipping threshold
- neutral light에서 silhouette/part boundary 확인

Gate는 순서대로 잠근다. A/B 실패 상태에서 D/E를 승인하지 않는다.

## 필수 E2E 시나리오

1. Concept-only
   - provider가 있으면 ReferenceSet 생성, 없으면 명확한 `ask`.
2. Insufficient references
   - single front character에서 side/back/detail 부족 탐지.
3. Cross-view inconsistency
   - side view의 방패 문양 또는 plume 색 변경 시 reject.
4. Frame-filling subject
   - reversible normalization 또는 low-confidence ask.
5. Actual capture
   - 모든 canonical view와 필수 pass 생성.
6. Runtime regression
   - 잘못된 helper call이 typecheck 또는 pageerror에서 실패.
7. Fail-closed review
   - render/metrics/feature evidence 중 하나 삭제 시 accept 금지.
8. Stale acceptance
   - Blueprint 변경 후 이전 review 무효화.
9. Automatic improvement
   - 잘못된 shield scale/pose가 iteration 후 개선.
10. Regression rollback
    - shield 개선 중 helmet score가 떨어지면 이전 best 유지.
11. Stopping
    - flat objective에서 patience/budget으로 종료.
12. Resource lifecycle
    - 반복 create/render/dispose 후 resource count가 누적되지 않음.
13. Determinism
    - 동일 seed/profile/renderer의 pass가 허용 범위 내 재현.
14. Portable output
    - 임시 Vite 프로젝트에서 generated bundle typecheck/build/smoke.
15. Profile isolation
    - generic prop이 character-only gate 때문에 실패하지 않음.

## 실패 모드 감사

| 코드 경로 | 실제 실패 | 테스트 | 오류 처리 | 사용자에게 보이는 것 | Critical gap |
| --- | --- | --- | --- | --- | --- |
| matte backend | foreground/background 분리 실패 | low-confidence fixture | fallback 후 ask | backend, confidence, remedy | 계획 후 없음 |
| ReferenceSet | 다른 대상/흔들린 장비 | inconsistent fixture | reject/regenerate | view와 feature diff | 계획 후 없음 |
| Ledger | TODO/최소 수 미달 | production ledger test | cast 차단 | 부족 category | 계획 후 없음 |
| Blueprint | shallow character | v0 knight regression | strict error | missing roles/layers | 계획 후 없음 |
| Geometry | unknown kind | schema test | no fallback | kind와 JSON path | 계획 후 없음 |
| Emitter | helper 인자 drift | typecheck fixture | build 차단 | compiler diagnostic | 계획 후 없음 |
| Browser | runtime exception | Playwright pageerror | capture 실패 | console + screenshot | 계획 후 없음 |
| Renderer | partial pass | capture fixture | review 차단 | missing pass list | 계획 후 없음 |
| Metrics | malformed artifact | unit/integration | revision 실패 | metric error | 계획 후 없음 |
| Reviewer | timeout/invalid JSON | injected adapter | retry/ask, accept 금지 | timeout/schema error | 계획 후 없음 |
| Policy | stale/missing evidence | policy regression | accept 금지 | gate report | 계획 후 없음 |
| Iteration | no improvement | stagnation fixture | stop, best 반환 | stopping reason | 계획 후 없음 |
| Resources | GPU object leak | repeated lifecycle | release 실패 | memory delta | 계획 후 없음 |

현재 구현에는 critical gap이 있지만, 위 각 gap은 tasklist의 대응 task와 테스트에 연결한다. 테스트 없이 예외 처리만 추가하거나, 사용자에게 보이지 않는 silent failure를 허용하지 않는다.

## 성능 benchmark

성능은 품질 objective가 실제 render에 연결된 뒤 측정한다.

### 기록 지표

- stage별 wall-clock과 CPU time
- process/thread/renderer worker 수
- peak RSS
- decode count와 buffer size
- render count/cache hit rate
- triangles, draw calls, texture memory
- browser startup/capture latency
- candidate promotion count

### ComputeBudget 불변조건

```text
process workers * native threads per process <= physical cores
renderer workers + metric workers <= configured concurrency
render count <= maxRenderCount
wall clock <= deadline
```

OpenCV, NumPy/BLAS, ONNX Runtime, Python process를 각각 최대치로 두지 않는다.

### 초기 성능 gate

정확한 수치는 representative fixtures를 확보한 후 baseline으로 고정한다. 그 전에는 다음만 hard gate다.

- unbounded worker/process 생성 금지
- 동일 입력의 decode 중복 횟수 증가 금지
- 반복 render에서 resource count 단조 증가 금지
- quality mode별 max render count 준수
- timeout과 cancellation 동작

## 실행 명령

현재 기준선:

```bash
python -m unittest discover -s tests -v
npm --prefix demo ci
npm --prefix demo run build
```

M0 이후 목표:

```bash
python -m unittest discover -s tests -v
python -m engine validate tests/golden/knight/blueprints/v0-shallow.json --strict
npm --prefix demo run typecheck
npm --prefix demo run build
npm --prefix demo run test:runtime
python -m engine run tests/golden/knight/project.json --max-iterations 1
```

릴리스 candidate:

```bash
python -m build
python -m pip install --force-reinstall dist/*.whl
gpthreejs --help
npm --prefix demo run check
python -m unittest discover -s tests -v
```

## Release gate

### Alpha

- M0~M3 완료
- v2 validator와 기사 geometry vertical slice
- typecheck/build/runtime smoke
- 자동 accept는 아직 비활성화 가능

### Beta

- M4~M5 완료
- canonical multi-pass와 fail-closed policy
- iteration/rollback E2E
- 기사 + 비기사 fixture

### Stable

- M6 완료
- wheel/portable TS bundle
- representative performance baseline
- resource leak gate
- skill validation과 독립 forward test

ChatGPT App UI는 Stable engine contract를 소비하는 별도 release track이다.

## 완료 기준

- 모든 새 branch와 error path에 unit/integration/E2E 중 적합한 test가 있다.
- v0 knight 회귀가 validator와 browser test에서 모두 재현된다.
- CI가 Python, TypeScript, browser runtime, portability를 검사한다.
- golden diff가 renderer 환경 차이 때문에 불필요하게 깨지지 않도록 pass별 전략을 사용한다.
- release report가 품질, 회귀, 성능, resource 결과를 한 번에 보여준다.
