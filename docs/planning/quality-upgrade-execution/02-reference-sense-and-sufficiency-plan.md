# Reference, Sense, Sufficiency 고도화 계획

## 목표

단일 이미지의 기술 품질만 검사하는 현재 gate를, 여러 이미지가 같은 대상을 일관되게 설명하는지 확인하는 `ReferenceSet` gate로 확장한다. 이미지가 부족할 때는 수동 padding 같은 우회 없이 `normalize`, `generate_more`, `ask`, `abort` 중 하나를 명시적으로 선택한다.

## 현재 재사용 자산

- [`engine/sense/pack.py`](../../../engine/sense/pack.py)의 Sense Pack orchestration
- [`engine/sense/sufficiency.py`](../../../engine/sense/sufficiency.py)의 issue/report 구조
- [`engine/sense/sufficiency_checks.py`](../../../engine/sense/sufficiency_checks.py)의 image/spec/view 검사
- [`engine/sense/sufficiency_policy.py`](../../../engine/sense/sufficiency_policy.py)의 verdict/action 분리
- [`engine/contracts/modes.py`](../../../engine/contracts/modes.py)의 중앙 mode 계약
- 기존 `pass | conditional | reject`, `continue | ask | abort` vocabulary

이 코드를 버리지 않고 입력 단위를 image에서 ReferenceSet으로 확장한다.

## 목표 데이터 흐름

```text
prompt + supplied images
          |
          v
      RequestSpec
          |
          v
    ReferencePlanner
      |       |
      |       +--> optional image provider
      |                |
      +----------------+
          |
          v
 ReferenceSet manifest
          |
          +--> decode/normalize once
          +--> per-view Sense Pack
          +--> view classification
          +--> feature visibility
          +--> cross-view consistency
          |
          v
 ReferenceSetSufficiencyReport
   pass | generate_more | regenerate | ask | abort
```

## 1. RequestSpec와 ReferenceSet 계약

초기 schema는 다음 필드를 포함한다.

```json
{
  "schemaVersion": 1,
  "subject": "stylized blue-plume knight",
  "intent": "game",
  "modelingProfile": "stylized-character",
  "qualityMode": "sharp",
  "mustHave": [
    {"id": "blue_feather_plume", "weight": 1.0},
    {"id": "large_sun_shield", "weight": 1.0},
    {"id": "broad_fantasy_sword", "weight": 1.0}
  ],
  "mustNotHave": [],
  "targetViews": ["source-34", "front", "left", "right", "back"]
}
```

```json
{
  "schemaVersion": 1,
  "references": [
    {
      "id": "ref-source-34",
      "path": "references/hero.png",
      "assetHash": "...",
      "declaredView": "source-34",
      "detectedView": "source-34",
      "evidenceClass": "observed",
      "visibleFeatures": ["blue_feather_plume", "large_sun_shield"],
      "sensePack": "sense/ref-source-34/sense-pack.json"
    }
  ]
}
```

허용 `evidenceClass`:

- `observed`: 사용자가 준 이미지에서 보이는 정보
- `design-intent`: 생성 디자인의 의도된 기준 뷰
- `design-hypothesis`: 보이지 않는 면을 보완한 생성 가설
- `inferred`: 대칭이나 일반적인 제작 규칙 기반 추론

생성 side/back을 `observed`로 올리는 행위는 validator에서 거부한다.

## 2. Matte와 입력 정규화

현재 corner-color matte는 단색 배경 product shot에는 유효하다. 이를 기본 fallback으로 유지하되 결과 품질을 점수화한다.

### 단계별 backend

1. 원본 alpha가 신뢰 가능한 경우 alpha를 사용한다.
2. corner-color heuristic을 실행하고 confidence를 계산한다.
3. foreground가 frame edge에 과도하게 닿거나 배경 분산이 높으면 OpenCV/segmentation provider로 승격한다.
4. 고급 backend가 없거나 실패하면 자동 padding/canvas normalization을 적용하고 다시 측정한다.
5. 여전히 낮은 confidence면 `ask`, cast는 시작하지 않는다.

자동 padding은 원본 픽셀을 변형하지 않고 manifest에 transform을 기록한다.

```json
{
  "normalization": {
    "operation": "pad",
    "sourceHash": "...",
    "canvas": [1536, 1536],
    "offset": [128, 64],
    "background": "estimated",
    "reversible": true
  }
}
```

### Matte confidence 신호

- foreground occupancy
- frame-edge contact ratio
- largest connected component ratio
- hole/noise ratio
- corner background variance
- alpha boundary roughness
- optional provider confidence

`SUBJECT_FILLS_FRAME`은 무조건 reject가 아니라 normalization 가능한지 먼저 판단한다.

## 3. View coverage와 cross-view consistency

`view_count`, `has_side`, `has_back` CLI flag는 하위 호환 입력으로만 남기고 manifest에서 계산한 값을 우선한다.

검사 항목:

- declared view와 detected view 일치
- 동일 subject embedding 또는 규칙 기반 visual signature
- 머리/몸 비율, 장비 개수, 주 색상, emblem 일치
- 좌우 비대칭 보존
- feature별 visibility와 occlusion
- 중복 각도 비율
- crop, exposure, blur, silhouette 완전성

Feature coverage:

```text
coverage = sum(feature.weight * max(view.visibility(feature)))
           --------------------------------------------------
                       sum(feature.weight)
```

고정 이미지 개수보다 coverage를 gate로 사용한다. 다만 캐릭터 `sharp+`는 side view가 없는 상태를 기본적으로 통과시키지 않는다.

## 4. Concept-only와 이미지 생성

이미지 provider는 core engine에 직접 결합하지 않고 port로 둔다. provider가 없으면 명확히 `ask`한다.

권장 순서:

1. prompt를 RequestSpec으로 구조화한다.
2. canonical hero image를 생성한다.
3. hero image를 기준으로 front/left/right/back을 edit 방식으로 만든다.
4. helmet/shield/sword/hand-grip detail crop을 만든다.
5. cross-view consistency를 검사한다.
6. 실패한 뷰만 재생성한다.
7. budget 소진 시 가장 불확실한 항목과 함께 `ask` 또는 `abort`한다.

각 뷰를 독립 text-to-image로 생성하는 경로는 기본값으로 두지 않는다.

## 5. Feature Ledger 생성

현재 `draft_ledger`의 TODO 3개는 실행 가능한 초안이 아니다. 다음 계약으로 변경한다.

### Ledger 생성 규칙

- `targetMin` 이상을 실제 entry로 생성하거나, 생성할 근거가 없으면 `agentAction=ask`를 반환한다.
- TODO entry는 interactive authoring mode에서만 허용하고 production path에서는 금지한다.
- 각 entry는 최소 `id`, `kind`, `description`, `region`, `scale`, `affects`, `confidence`, `evidenceRefs`, `status`를 가진다.
- Blueprint 이전에는 `mapsTo`가 `unresolved`일 수 있지만, strict cast 이전에는 실제 feature/override/part로 해소한다.
- character profile은 global/meso/micro를 분리한다. 비율·포즈·방패·검은 micro ledger에 묻히지 않는다.

권장 분류:

```text
global: silhouette, proportion, pose, handedness, camera cues
meso: helmet, pauldrons, torso layers, shield, sword, cape
micro: rivets, seams, scratches, weave, edge wear
```

### Character 최소 ledger gate

`stylized-character`는 단순 개수 외에 다음 category coverage를 요구한다.

- silhouette/proportion
- head/face or helmet
- torso layering
- left/right limb or armor asymmetry
- held/worn equipment
- lower body/feet
- material roles
- attachment relationships

## 6. CLI와 호환성

단계적 명령:

```bash
python -m engine reference-plan request-spec.json --out work/reference-plan.json
python -m engine sense-set work/reference-set.json --out work/sense
python -m engine sufficiency-set work/reference-set.json \
  --request work/request-spec.json --out work/sufficiency.json
python -m engine ledger-set work/reference-set.json \
  --sense work/sense --out work/ledger.json
```

기존 `sense`, `sufficiency`, `ledger` 명령은 single-image compatibility wrapper로 유지한다.

## 7. 구현 순서

1. REF-101: RequestSpec/ReferenceSet schema와 hash canonicalization
2. REF-102: 기존 single-image 입력의 manifest adapter
3. REF-110: matte quality report와 reversible normalization
4. REF-120: manifest-derived view coverage
5. REF-130: ledger가 `targetMin`과 category coverage를 지키도록 변경
6. REF-140: cross-view consistency 기본 규칙
7. REF-150: optional image provider port와 budget contract
8. REF-160: production command에 ReferenceSet gate 연결

## 8. 테스트

### Unit

- frame-filling subject가 padding 후 confidence를 회복한다.
- 복잡한 corner background는 heuristic을 과신하지 않는다.
- `targetMin=6`이면 entry가 6개 미만인 production ledger를 반환하지 않는다.
- generated back view가 `observed`로 선언되면 validation error다.
- CLI flags와 manifest가 충돌하면 manifest evidence를 사용하고 warning을 남긴다.

### Integration

- 기존 single-image sample이 adapter를 통해 동일 또는 더 보수적인 verdict를 낸다.
- knight front/side/back은 equipment handedness와 color consistency를 통과한다.
- side view에서 shield emblem이나 plume color를 바꾸면 consistency gate가 실패한다.

### Failure modes

| 실패 | 테스트 | 처리 | 사용자 가시성 |
| --- | --- | --- | --- |
| image provider 미설치 | contract test | `ask`, 설치/첨부 remedy | 명확한 메시지 |
| segmentation backend 초기화 실패 | injected failure | heuristic 결과를 낮은 confidence로 유지, 필요 시 `ask` | backend와 fallback 기록 |
| generated view 불일치 | inconsistent fixture | 해당 뷰만 `regenerate` | 실패 feature 표시 |
| reference hash 변경 | stale manifest test | 파생 Sense Pack 무효화 | stale artifact 목록 |
| 모든 view에서 critical feature 가림 | coverage test | `ask` 또는 detail crop 생성 | 누락 feature 목록 |

## 완료 기준

- 실제 입력 파일을 읽어 view coverage를 계산한다.
- 수동 padding 없이 frame-filling knight 입력을 normalize하거나 명확히 `ask`한다.
- production ledger에 TODO가 없고 최소 개수와 category coverage를 만족한다.
- ReferenceSet hash 변경 시 Sense Pack, ledger, Blueprint가 stale 처리된다.
- 단일 이미지 compatibility test가 유지된다.
