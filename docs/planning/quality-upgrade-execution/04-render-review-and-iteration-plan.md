# Render, Review, Iteration 고도화 계획

## 목표

`cast` 이후 외부에서 임의 PNG와 점수를 넣는 현재 흐름을, 재현 가능한 render set과 fail-closed policy가 있는 폐루프로 바꾼다. reviewer가 결과를 좋다고 말해도 필수 artifact나 hard gate가 없으면 accept하지 않는다.

## 현재 재사용 자산

- [`engine/critique/metrics.py`](../../../engine/critique/metrics.py)의 IoU, approximate SSIM, edge F1
- [`engine/critique/sheet.py`](../../../engine/critique/sheet.py)의 비교 sheet
- [`engine/critique/journal.py`](../../../engine/critique/journal.py)의 layer history
- [`engine/cast/layers.py`](../../../engine/cast/layers.py)의 layer state
- [`demo/src/app/renderer.ts`](../../../demo/src/app/renderer.ts), [`scene.ts`](../../../demo/src/app/scene.ts)의 renderer/light bootstrap
- deterministic seed, geometry/material registry, worker contract

기존 metric은 smoke signal로 유지하고 최종 승인에는 pass별 evidence를 추가한다.

## 목표 흐름

```text
validated Blueprint revision
           |
           v
       cast/build
           |
           v
  canonical render harness
   | beauty | alpha | part-ID
   | albedo | normal | depth
   | material-debug | wireframe
           |
           v
      metric suite
           |
           +--> deterministic hard gates
           |
           v
   structured vision reviewer
           |
           v
  deterministic review policy
    | accept
    | replan + rootCause/action
    | recode + rootCause/action
    | ask
    + abort
```

## 1. Canonical render harness

### 최소 구현

초기 harness는 demo runtime을 재사용하되 interaction과 capture를 분리한다.

권장 모듈 경계:

```text
demo/src/capture/
├─ scene-harness.ts
├─ camera-profiles.ts
├─ render-passes.ts
├─ capture-runner.ts
└─ artifact-manifest.ts
```

두 번째 consumer가 생기기 전에는 별도 npm package로 추출하지 않는다. ChatGPT App이나 생성 프로젝트가 실제로 재사용할 때 `packages/runtime`로 이동한다.

### View profile

- `source-34`: 원본 camera/pose/framing과 정렬
- `front`, `left`, `right`, `back`: neutral turnaround
- `top-34`: volume inspection
- optional orbit preview: 사용자 탐색용, metric gate에는 사용하지 않음

source와 turnaround를 직접 비교하지 않는다.

### Pass

- beauty
- alpha/silhouette
- part-ID
- albedo
- normal
- linear depth
- roughness/metalness debug
- wireframe

모든 pass는 동일 Blueprint/factory/camera/light/renderer hash에 묶인다.

## 2. RenderSet 계약

```json
{
  "schemaVersion": 1,
  "revisionId": "rev-0003",
  "blueprintHash": "...",
  "factoryHash": "...",
  "rendererVersion": "three-0.172.0+harness-1",
  "renderProfileHash": "...",
  "views": [
    {
      "id": "source-34",
      "cameraProfileHash": "...",
      "lightProfileHash": "...",
      "passes": {
        "beauty": {"path": "...", "hash": "..."},
        "alpha": {"path": "...", "hash": "..."},
        "partId": {"path": "...", "hash": "..."}
      }
    }
  ]
}
```

partial render set은 debug artifact로 저장할 수 있지만 review input으로는 실패한다.

## 3. Camera와 pose 정렬

metric 전에 다음 순서로 정렬한다.

1. projection type
2. azimuth/elevation
3. FOV 또는 orthographic scale
4. translation, crop, frame occupancy
5. root pose와 joint pose
6. silhouette
7. part/landmark
8. material/beauty

camera fit과 geometry fit을 동시에 최적화하면 원인 분리가 어렵다. camera profile을 먼저 lock한다.

## 4. Metric suite

| 대상 | pass | 지표 |
| --- | --- | --- |
| framing | alpha bbox | center, occupancy, aspect error |
| silhouette | alpha | IoU, boundary F-score, distance transform |
| proportion | landmarks | normalized distances and angles |
| part existence | part-ID | area, visibility, per-view coverage |
| attachment | landmarks/part-ID/depth | socket gap, contact visibility, depth order |
| volume | depth/normal | region correlation, normal angular error |
| color | albedo | masked color distance |
| material readability | beauty/material debug | black crush, clipping, role contrast |
| request compliance | Blueprint + render evidence | mustHave/mustNotHave |

global SSIM 하나로 캐릭터 품질을 승인하지 않는다. style, lighting, background 차이에 과민하고 root cause를 알려주지 못한다.

## 5. Structured reviewer

reviewer 입력은 RequestSpec, ReferenceSet, Blueprint summary, RenderSet, MetricReport로 제한한다. builder의 자기설명과 이전 결론은 넣지 않는다.

```json
{
  "recommendation": "replan",
  "issues": [
    {
      "severity": "critical",
      "criterionId": "large-sun-shield",
      "viewId": "source-34",
      "partId": "shield-body",
      "evidence": "shield area is below the reference range",
      "rootCause": "part-scale-and-pose",
      "action": "increase shield width and move forearm pivot forward",
      "confidence": 0.94
    }
  ]
}
```

파싱 실패, schema mismatch, empty output은 accept가 아니라 `ask` 또는 `abort`다.

## 6. Fail-closed ReviewPolicy

`append_journal`이 decision을 신뢰하는 현재 구조를 다음 정책으로 바꾼다.

```text
ACCEPT only if
  required artifacts exist
  AND every artifact hash matches the current revision
  AND all critical views and passes exist
  AND all hard metric floors pass
  AND every critical feature has render evidence
  AND no mustNotHave violation exists
  AND reviewer has no critical issue
  AND no critical metric regresses from best-so-far
```

누락 값은 통과로 해석하지 않는다.

### 기존 decision vocabulary 유지

상태 이름을 무한히 늘리지 않는다. 기존 다섯 decision을 유지하고 세부 조치는 `rootCause`와 `action`으로 표현한다.

- `accept`
- `replan`: camera, pose, proportion, geometry, material, reference 변경
- `recode`: Blueprint는 맞지만 emitter/runtime 구현 오류
- `ask`: 추가 reference, user choice, provider 권한 필요
- `abort`: 현재 조건에서 불가능

## 7. Revision, hash, invalidation

각 report는 다음 hash를 기록한다.

- request spec
- reference set
- sense pack configuration and inputs
- ledger
- Blueprint
- factory/runtime support files
- render set
- metric configuration
- reviewer configuration

의존성:

```text
RequestSpec ----+
                +--> ReferenceSet --> Sense/Ledger --> Blueprint
References -----+                                  |
                                                    v
Factory/runtime --------------------------------> RenderSet
                                                    |
Metric config ------------------------------------> Metrics
                                                    |
Reviewer config ----------------------------------> ReviewReport
```

상위 artifact가 바뀌면 하위 artifact는 stale이다. 파일 timestamp가 아니라 canonical content hash를 사용한다.

## 8. Iteration controller

### 상태 머신

```text
REFERENCE_GATE -> PLAN -> VALIDATE -> CAST -> RENDER -> METRICS -> REVIEW -> POLICY
      ^             ^         ^         ^                              |
      |             |         |         +---------- recode ------------+
      |             |         +----------- replan material ------------+
      |             +--------------------- replan geometry/pose --------+
      +----------------------------------- ask/generate reference -------+
                                                                      |
                                                        accept -> FINAL
                                                        abort  -> REPORT
```

### 국소 수정

TypeScript 전체 재생성보다 Blueprint JSON Patch를 먼저 사용한다.

- camera-only issue: render profile patch
- global mass issue: proportion/root transform patch
- part silhouette issue: 해당 geometry spec patch
- attachment issue: socket/joint transform patch
- material issue: material override patch
- unsupported builder/runtime bug: `recode`

### Best-so-far와 rollback

각 iteration은 parent, patch, score delta, hard gate delta, regression을 기록한다. critical regression이 있거나 aggregate improvement가 `epsilon` 미만이면 candidate를 승격하지 않는다.

### 중단 조건

- max iterations
- wall-clock deadline
- CPU/render budget
- reviewer/provider budget
- 동일 root cause 반복 한도
- 연속 `N`회 개선 없음
- reference contradiction
- runtime 또는 renderer 반복 실패

## 9. Fit 교체 전략

현재 2D superellipse `fit_root_mass`는 production 품질 개선기로 사용하지 않는다.

1. 명령과 report에 `experimental-proxy`를 표시한다.
2. production orchestrator에서 호출하지 않는다.
3. canonical alpha pass가 준비되면 camera → global mass → major part → material 순서의 render-in-loop fit을 추가한다.
4. random search보다 먼저 deterministic grid/coarse-to-fine으로 objective를 검증한다.
5. objective가 실제 품질과 상관된다는 benchmark 후에만 DE/CMA-ES를 검토한다.

## 10. 구현 순서

1. RND-101: deterministic scene/camera/light profile
2. RND-110: beauty + alpha capture
3. RND-120: part-ID/albedo/normal/depth/material-debug pass
4. RND-130: RenderSet manifest와 hash
5. MET-101: framing/boundary/landmark/part metrics
6. REV-101: ReviewReport schema와 reviewer port
7. REV-110: fail-closed policy
8. REV-120: layer journal이 policy 결과만 기록하도록 변경
9. REV-130: dependency invalidation
10. ITER-101: iteration record와 JSON Patch
11. ITER-110: best-so-far, rollback, stopping
12. FIT-101: proxy fit 격리와 render-in-loop MVP

## 11. 테스트

### Contract

- pass 하나가 없으면 RenderSet validation 실패
- Blueprint hash가 바뀌면 이전 RenderSet/ReviewReport stale
- feature score가 없으면 accept 실패
- metrics가 없으면 accept 실패
- reviewer parsing 실패면 accept 실패

### E2E

- canonical view/pass가 실제 브라우저에서 생성된다.
- runtime console error가 있으면 capture job이 실패한다.
- 잘못된 shield scale fixture가 한 iteration 후 해당 metric을 개선한다.
- shield 수정이 helmet critical score를 떨어뜨리면 rollback한다.
- 동일 seed/profile의 render hash 또는 perceptual diff가 허용 범위 안에 든다.

### Failure modes

| 실패 | 테스트 | 처리 | 사용자 가시성 |
| --- | --- | --- | --- |
| renderer 초기화 실패 | browser launch failure | retry 한도 후 abort | stderr/console artifact |
| 일부 pass만 생성 | partial capture | review 금지 | missing pass 목록 |
| stale cache hit | hash mismatch | cache 무시, 재렌더 | invalidation reason |
| reviewer timeout | injected timeout | retry 또는 ask, accept 금지 | timeout과 budget |
| metric 계산 오류 | malformed PNG | 해당 revision 실패 | metric error report |
| iteration stagnation | flat objective | best revision 반환, conditional report | stopping reason |

## 완료 기준

- 사용자가 수동 screenshot을 넘기지 않아도 canonical render set이 생성된다.
- reviewer가 없어도 deterministic hard gate는 동작한다.
- hero-quality accept는 reviewer와 모든 evidence가 없으면 불가능하다.
- Blueprint 수정 후 이전 accept가 자동 무효화된다.
- proxy fit이 production path에서 제거된다.
- 기사 fixture에서 최소 한 번의 국소 patch가 목표 metric을 개선하고 비관련 critical feature를 보존한다.
