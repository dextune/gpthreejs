# 관찰된 실패와 성공 기준

## 목적

이 문서는 기사 캐릭터 실행 사례를 회귀 기준으로 고정한다. 문제를 “결과가 덜 예쁘다”로 기록하지 않고, 재현 가능한 증상과 코드 계약의 실패로 연결한다.

## 사용자에게 보인 결과

현재 렌더는 방패 문양과 파란 plume 덕분에 기사라는 범주는 읽히지만, stylized hero character보다 primitive 기반 마네킹에 가깝다.

잘된 부분:

- 방패의 파란색과 방사형 문양은 강한 identity cue다.
- plume은 상단 실루엣을 만들어 캐릭터를 구분한다.
- 검, 방패, 갑옷이라는 장비 범주는 존재한다.

보존하면서 개선할 부분:

| 영역 | 관찰 증상 | 사용자 영향 | 우선 근본 원인 |
| --- | --- | --- | --- |
| 전체 비율 | 길고 좁은 몸, 작은 머리, 곧은 팔다리 | chibi/hero 인상이 사라짐 | proportion profile 부재 |
| 포즈 | 완전 정면, 좌우 대칭, 팔과 다리가 일직선 | 생동감과 원본 인상 손실 | pose/camera 계약 부재 |
| 몸통 | 큰 청록 직사각형이 가슴과 허리를 덮음 | 갑옷 구조와 신체가 읽히지 않음 | 의미 부품 분해 부족 |
| 투구 | 얼굴이 검은 사각 그릴로 뭉침 | 시선과 캐릭터성이 사라짐 | visor/eye slit/cheek guard 분리 부족 |
| 어깨·팔 | 구형 견갑과 원통형 팔 | 장난감 관절처럼 보임 | character geometry profile 부족 |
| 검 | 손과의 grip이 약하고 다리 뒤에 떠 보임 | 무기를 들고 있다는 관계가 불명확 | socket/contact validation 부재 |
| 방패 | 강한 cue지만 팔과의 결합, 곡률, 몸 앞 배치가 약함 | 방어 자세와 중량감 손실 | convex profile 및 forearm attachment 부족 |
| 다리·발 | 블록과 뾰족한 cone 조합 | 장화/판금보다 임시 primitive로 보임 | tapered greave/sabaton builder 부재 |
| 재질 | 금속 하이라이트는 포화되고 그림자는 검게 뭉침 | 표면 디테일이 오히려 형상을 숨김 | environment/readability gate 부재 |
| 디테일 | rivet/map은 있으나 큰 형태가 틀림 | 디테일 작업 대비 품질 상승이 작음 | cast layer 순서 미준수 |

## 실행 중 확인된 파이프라인 실패

| ID | 재현된 문제 | 현재 근거 | 계획상 처리 |
| --- | --- | --- | --- |
| OBS-01 | 복잡한 배경과 높은 피사체 점유율에서 matte가 실패해 수동 padding 필요 | [`matte_heuristic`](../../../engine/sense/matte.py)은 모서리 배경색 거리만 사용 | REF-1xx |
| OBS-02 | 단일 캐릭터 입력이 side/back 부족으로 중단 | [`assess_intent_and_views`](../../../engine/sense/sufficiency_checks.py)는 외부 `view_count`, `has_side`, `has_back`을 신뢰 | REF-2xx |
| OBS-03 | `targetMin=6`인데 ledger skeleton은 TODO 3개뿐 | [`draft_ledger`](../../../engine/blueprint/draft.py)에서 `zones[:3]` 고정 | REF-3xx |
| OBS-04 | 캐릭터 Blueprint가 `root_mass` + `accent_trim` box로 시작 | [`draft_blueprint`](../../../engine/blueprint/draft.py)의 고정 scaffold | BP-1xx |
| OBS-05 | strict가 ledger 연결을 채운 얕은 캐릭터를 통과시킴 | [`validate_blueprint`](../../../engine/blueprint/validate.py)는 character structure를 warning으로만 처리 | BP-2xx |
| OBS-06 | emitter가 모르는 geometry를 box로 바꿈 | [`_geom_js`](../../../engine/cast/emit_factory.py)의 마지막 fallback | GEO-1xx |
| OBS-07 | factory helper 인자 오류가 Vite build에서 잡히지 않고 브라우저에서 `parent.add is not a function` 발생 | [`demo/package.json`](../../../demo/package.json)에 `tsc --noEmit`과 runtime smoke가 없음 | DX-1xx |
| OBS-08 | demo를 복사하면 surface preset import 경로가 깨짐 | [`surfaceKit.ts`](../../../demo/src/detail/surfaceKit.ts)의 `../../../engine/...` import | DX-2xx |
| OBS-09 | high surface detail이 metal을 더 어둡게 만들어 low로 낮춰야 했음 | AO 0.85, normal map, environment 부재 조합 | MAT-1xx |
| OBS-10 | build chunk가 500 kB 경고를 냄 | demo build 관찰 | PERF-2xx, release blocker는 아님 |
| OBS-11 | `FormHandles`가 있어도 sword/shield contact와 좌우 관계는 보장되지 않음 | handle metadata와 geometry validation이 분리됨 | ATT-1xx |
| OBS-12 | `python -m engine`과 demo 지원 파일이 저장소 배치에 의존 | Python package metadata 부재, TS 상대 import | DX-2xx |
| OBS-13 | 일부 생성 산출물에서 문자 인코딩이 깨짐 | 실제 복사/생성 과정 관찰 | DX-3xx |
| OBS-14 | 실제 3D 품질과 무관한 2D root mass fit에 CPU가 사용됨 | [`fit_root_mass`](../../../engine/cast/fit_params.py)의 96×96 proxy | REV-3xx |
| OBS-15 | metrics 또는 critical feature score가 없어도 accept 가능 | [`append_journal`](../../../engine/critique/journal.py)의 조건부 검사 | REV-2xx |
| OBS-16 | 현재 Windows 기준 작은 Sense fixture가 0.75초 고정 budget을 초과 | 2026-07-21 실행에서 0.985초, Python 20개 중 1개 실패 | M0-010, PERF-110 |
| OBS-17 | clean workspace에서 demo build 전제 조건이 불명확 | `npm --prefix demo run build`가 설치되지 않은 Vite 때문에 시작하지 못함 | M0-011, CI-101 |

## 근본 원인 분류

```text
입력 문제
├─ 단일 이미지 단위 sufficiency
├─ 배경 모서리 색 기반 matte
└─ 실제 feature coverage 미측정

설계 문제
├─ ledger skeleton이 최소 개수보다 작음
├─ 캐릭터 의미 구조 없는 Blueprint scaffold
├─ qualityMode와 모델링 전략의 혼재
└─ landmark/attachment/readability 계약 부재

생성 문제
├─ primitive vocabulary 제한
├─ unsupported geometry silent fallback
├─ 생성 factory가 blueprint를 사실상 사용하지 않음
└─ 저장소 상대 import와 타입 검증 부재

검수 문제
├─ canonical camera/render 부재
├─ beauty 중심 수동 확인
├─ global metric만 존재
├─ stale artifact를 구분하지 않음
└─ accept가 fail-open
```

## 기사 benchmark fixture

### 보존할 입력

- 사용자 원본 3/4 이미지
- 생성한 front/side/back turnaround
- 문제가 드러난 현재 렌더
- 실행 당시 Sense Pack, ledger, Blueprint, generated factory, 브라우저 console log
- 조명·detail level 변경 전후 render

권장 위치:

```text
tests/golden/knight/
├─ references/
├─ sense/
├─ blueprints/
│  ├─ v0-shallow.json
│  └─ v2-target.json
├─ renders/
├─ metrics/
├─ reviews/
└─ manifest.json
```

큰 PNG를 기본 Git history에 넣기 어렵다면 Git LFS 또는 릴리스 fixture archive를 사용하되, `manifest.json`과 hash는 저장소에 둔다.

### Gate A: 입력과 비교 조건

- source 3/4, front, side, back이 manifest에 선언된다.
- 각 reference의 `evidenceClass`와 visible feature가 기록된다.
- source-aligned camera/pose와 neutral turnaround camera가 분리된다.
- 좌우 장비 배치가 reference와 동일하다.

### Gate B: mass와 pose

- 머리는 전체 키의 초기 목표 22~25% 범위다. benchmark 조정 후 수치는 contract fixture로 고정한다.
- 어깨 폭, 몸통 taper, 팔·다리 굵기, 발 간격이 landmark로 측정된다.
- 정면 완전 대칭이 아닌 source pose가 존재한다.
- 실루엣 bbox 중심과 점유율이 reference별 허용 오차 안에 든다.

### Gate C: identity geometry

다음 feature는 part-ID와 beauty pass 양쪽에서 식별 가능해야 한다.

- helmet eye slit와 visor 경계
- blue plume과 겹친 feather silhouette
- asymmetric pauldrons
- convex sun shield와 rim
- broad fantasy sword profile
- scarf, strap, star brooch, tunic/tabard, belt, cape

### Gate D: attachment

- sword grip socket과 hand contact point의 거리가 tolerance 이하다.
- shield handle은 forearm/hand chain에 연결된다.
- plume root는 helmet crest에 접촉한다.
- cape upper attach는 torso/back anchor에 접촉한다.
- 주요 부품 사이에 화면상 floater가 없고 심한 관통이 없다.

### Gate E: material readability

- steel, brass, cloth, leather가 albedo와 beauty에서 구분된다.
- neutral light에서 black crush와 highlight clipping이 임계값을 넘지 않는다.
- metal material은 environment 또는 명시적 reflection fallback 없이 승인되지 않는다.
- AO/normal detail을 끈 render보다 켠 render의 landmark readability가 낮아지면 accept하지 않는다.

## 정량 성공 기준

초기 threshold는 benchmark 데이터를 모으며 조정한다. 수치 자체보다 fail-closed와 회귀 방지가 우선이다.

| 기준 | 초기 목표 |
| --- | --- |
| critical feature 평가 완료율 | 100% |
| mustHave 통과율 | 100% |
| critical view failure | 0 |
| stale artifact | 0 |
| source-aligned silhouette IoU | quality mode별 0.75~0.85 |
| boundary F-score | 0.75 이상 |
| landmark normalized error | feature별 threshold, 모두 기록 |
| socket/contact gap | part scale에 정규화한 tolerance 이하 |
| 동일 seed render 재현성 | 플랫폼별 허용 diff 이하 |
| 브라우저 console error | 0 |
| TypeScript type error | 0 |
| 이전 best critical regression | 0 |

## 과적합 방지 fixture

기사 하나만 통과하면 `knight-special-case generator`가 될 위험이 있다. 최소 두 fixture를 더 둔다.

1. 단순 대칭 hard-surface prop
   - generic-prop 경로가 캐릭터 규칙 때문에 불필요하게 실패하지 않는지 확인한다.
2. 비기사 stylized character
   - 다른 체형, 다른 장비, 비금속 재질에서도 proportion/landmark/attachment 계약이 작동하는지 확인한다.

## 완료 판정

이 문서의 작업은 다음 증거가 있을 때 완료다.

- 기사 v0 render와 개선 render의 동일 camera 비교 sheet
- Gate A~E report
- v0 shallow Blueprint를 거부하는 validator regression test
- typecheck/build/runtime smoke 결과
- 기사 외 fixture의 비회귀 결과
