# Blueprint, 캐릭터, Geometry 고도화 계획

## 목표

캐릭터 입력을 box 두 개짜리 scaffold로 축약하지 않고, 비율·포즈·의미 부품·부착 관계를 Blueprint 계약에 담는다. strict validation은 “JSON 형태가 있음”이 아니라 “현재 modeling profile로 cast할 만큼 충분함”을 보장해야 한다.

## 설계 원칙

1. 큰 형태가 surface detail보다 먼저다.
2. `qualityMode`와 `modelingProfile`을 분리한다.
3. Blueprint가 source of truth다.
4. emitted TypeScript는 Blueprint를 컴파일한 읽기 가능한 산출물이다.
5. 모르는 geometry는 box로 대체하지 않고 명확히 실패한다.
6. handle metadata와 실제 접촉 geometry를 함께 검증한다.
7. 기사 전용 조건을 일반 character contract와 fixture-specific criteria로 분리한다.

## 1. Blueprint v2

v2는 v1을 즉시 폐기하지 않는다. `migrate-v1-to-v2`와 v1 compatibility validator를 함께 둔다.

### 핵심 필드

```json
{
  "schemaVersion": 2,
  "name": "BluePlumeKnight",
  "qualityMode": "sharp",
  "modelingProfile": "stylized-character",
  "intent": "game",
  "revision": {
    "id": "rev-0003",
    "parent": "rev-0002",
    "contentHash": "..."
  },
  "proportionProfile": {
    "headUnits": 4.2,
    "headHeightRatio": 0.235,
    "shoulderWidthRatio": 0.42,
    "limbThickness": "chunky"
  },
  "poseProfile": {
    "id": "source-34",
    "mirrored": false,
    "joints": {}
  },
  "landmarks": [],
  "parts": [],
  "materials": [],
  "handles": {},
  "renderProfiles": [],
  "criticalFeatures": []
}
```

### 역할 분리

- `proportionProfile`: 전체 체형과 비율
- `poseProfile`: joint/local transform과 handedness
- `landmarks`: 화면/3D 위치를 비교할 수 있는 기준점
- `parts`: 의미 부품과 hierarchy
- `handles`: 애니메이션/장비 교체용 pivot/socket/collider
- `attachments`: part 간 접촉과 embed 규칙
- `renderProfiles`: source-aligned와 neutral inspection 분리

## 2. Modeling profile

초기 profile은 세 개만 구현한다.

| profile | 용도 | 필수 gate |
| --- | --- | --- |
| `generic-prop` | 단순 소품 | mass, contour, material role |
| `hard-surface-hero` | 방패, 무기, 장치 | semantic part, profile geometry, bevel/trim |
| `stylized-character` | 기사 같은 캐릭터 | proportion, pose, landmarks, limb hierarchy, attachments |

profile을 class hierarchy로 과도하게 만들지 않는다. 초기에는 declarative rule table과 validator 함수로 구현한다.

## 3. Strict validation 확장

현재 validator의 ledger linkage는 유지하고 다음을 추가한다.

### 공통 구조

- schema version 지원 여부
- 모든 ID namespace의 uniqueness
- parent/child cycle
- dangling material, part, feature, override, landmark, socket 참조
- 모든 numeric 값의 finite 여부, 배열 길이, min/max 범위
- transform scale의 0/음수 정책
- geometry kind와 required parameter
- material role과 channel type
- attachment parent/child 일관성
- revision/content hash 형식

### Character strict

- `proportion`과 `landmarks` layer 둘 다 존재해야 한다. 현재 warning 조건을 strict error로 바꾼다.
- head, torso, pelvis, 좌우 upper/lower limb 또는 명시적 비대칭 구조가 있어야 한다.
- held equipment는 hand/forearm socket 또는 explicit wearable attachment를 가진다.
- critical feature는 최소 한 part/feature와 최소 한 target view에 연결된다.
- global/meso ledger category coverage를 만족한다.
- 완전 대칭 pose는 reference가 대칭일 때만 허용한다.
- `mirrored` 상태와 reference handedness가 충돌하면 오류다.

### Shallow blueprint rejection

단순 part 개수만 세면 meaningless subdivision으로 우회할 수 있다. 다음 조합을 사용한다.

```text
semantic depth
  = required role coverage
  + hierarchy depth
  + distinct silhouette contributors
  + mapped critical features
  + valid attachments
```

기사 fixture는 45~70개 의미 부품을 기대할 수 있지만 이를 모든 캐릭터의 전역 하드코드로 사용하지 않는다.

## 4. 캐릭터 비율과 pose layer

### 비율

`headUnits`, normalized landmark distances, thickness profile을 사용한다. 절대 좌표만 쓰면 scale 변경 때 모든 part가 깨진다.

초기 landmark:

- crown, chin
- shoulder-left/right
- sternum, pelvis
- elbow-left/right, wrist-left/right
- knee-left/right, ankle-left/right
- shield-center, sword-grip, sword-tip

### Pose

joint group이 실제 mesh parent가 되도록 한다. 현재처럼 limb을 동일한 축에 세운 뒤 장비만 offset하는 방식을 피한다.

```text
root
└─ pelvis
   ├─ spine -> chest -> neck -> head
   ├─ shoulder-l -> elbow-l -> wrist-l -> hand-l -> shield
   ├─ shoulder-r -> elbow-r -> wrist-r -> hand-r -> sword
   ├─ hip-l -> knee-l -> ankle-l -> foot-l
   └─ hip-r -> knee-r -> ankle-r -> foot-r
```

source pose와 neutral turnaround pose를 별도 profile로 둔다. geometry 자체를 source pose에 bake하지 않는다.

## 5. Geometry vocabulary

### M3 필수

| kind/builder | 용도 |
| --- | --- |
| `box`, `sphere`, `ellipsoid`, `capsule`, `cylinder`, `cone`, `torus` | 기본 mass와 관절 |
| `rounded-box` | torso shell, boots, prop body |
| `shape-extrude` | sword, shield, emblem, armor profile |
| `lathe` | helmet dome, pommel, ringed forms |
| `tube` | trim, strap, cable, rim |
| `beveled-plate` | armor plate, pauldron, shield frame |
| `curve-blade` | 굴곡진 fantasy blade |
| `feather` | 겹친 plume silhouette |
| `cloth-patch` | scarf, cape, tunic flap |
| `instance-set` | rivet, stud, 반복 장식 |

`boolean-composite`는 초기 필수 범위에서 제외한다. visor slit과 opening은 layered geometry 또는 alpha/part separation으로 먼저 해결하고, 실제 CSG가 필요한 fixture가 생기면 추가한다.

### Builder 계약

```ts
type GeometryBuilder = (
  spec: GeometrySpec,
  context: BuildContext,
) => THREE.BufferGeometry;
```

- registry에 없는 kind는 `UnsupportedGeometryError`다.
- 모든 builder는 bounds와 triangle estimate를 반환한다.
- profile point 수, extrusion depth, bevel segment에 상한을 둔다.
- geometry key는 deterministic하고 registry cache에 사용할 수 있어야 한다.
- handedness/mirroring은 negative scale 남용보다 geometry/transform helper로 명시한다.

## 6. 기사 vertical slice

첫 품질 개선은 전체 캐릭터를 한 번에 polish하지 않는다. 다음 순서로 gate를 통과한다.

### Slice 1: camera, handedness, mass

- source 3/4 camera profile
- 화면 기준 검/방패 좌우 배치
- 4~4.5 head-unit chibi profile
- 넓은 torso, 짧고 굵은 limb, 넓은 stance

### Slice 2: identity geometry

- helmet dome, visor, eye slit, cheek/chin guard 분리
- asymmetric layered pauldrons
- convex shield body, rim, sun emblem
- broad curve blade, guard, grip, pommel
- feather cluster와 crest root

### Slice 3: torso와 lower body

- breastplate/tunic/tabard를 하나의 rectangle로 만들지 않는다.
- scarf, cross-body strap, brooch, belt, skirt flap, cape를 계층화한다.
- thigh/knee/greave/sabaton에 taper와 plate overlap을 준다.

### Slice 4: meso/micro detail

- trim, rivet, seam, cloth fold
- surface map은 마지막에 적용한다.

## 7. Attachment와 관계 검증

`FormHandles`는 metadata만 존재해서는 안 된다. part attachment는 다음을 가진다.

```json
{
  "parentSocket": "hand-r-grip",
  "childSocket": "sword-grip",
  "contact": "grip",
  "maxGap": 0.015,
  "maxPenetration": 0.01,
  "required": true
}
```

검사 단계:

1. 참조 무결성
2. local/world transform 계산
3. socket gap
4. collider 또는 bounds 기반 gross penetration
5. critical view에서 screen-space occlusion/visibility

초기에는 exact mesh collision 대신 bounding volume과 contact point로 시작한다. 충분히 설명 가능하고 deterministic하다.

## 8. Material readability

surface detail은 geometry gate 통과 후 적용한다.

### 역할

- `steel-worn`
- `brass-trim`
- `blue-cloth`
- `teal-tunic`
- `brown-leather`
- `blue-gem`
- `dark-glove`

### 규칙

- metalness가 높은 재질은 canonical environment 또는 reflection fallback을 요구한다.
- AO intensity는 profile과 texel density에 따라 제한한다. high detail이 더 검게 보인다는 이유로 preview에서 몰래 low로 낮추지 않는다.
- preview quality와 review quality가 다르면 UI와 report에 명시한다.
- neutral/albedo/roughness-metalness debug pass로 문제 원인을 분리한다.
- black crush, clipped highlight, material role contrast를 readability metric으로 기록한다.

## 9. 구현 순서

1. BP-101: v2 schema와 v1 migration
2. BP-110: strict common structural validation
3. BP-120: modeling profile rule table
4. BP-130: stylized-character proportion/pose/landmark 계약
5. GEO-101: geometry registry와 unknown-kind error
6. GEO-110: rounded-box, shape-extrude, lathe, tube
7. GEO-120: plate, shield, blade, feather, cloth builders
8. ATT-101: socket/contact schema와 static validation
9. ATT-110: world-space gap/penetration 검사
10. CHAR-101: 기사 Slice 1~3 Blueprint/factory
11. MAT-101: neutral environment와 readability policy
12. CHAR-120: 기사 meso/micro detail

## 10. 테스트

### Validator unit

- duplicate ID, cycle, NaN, Infinity, 잘못된 vector length를 거부한다.
- unknown geometry를 거부한다.
- character에서 proportion 또는 landmarks가 하나라도 없으면 strict 실패다.
- ledger `mapsTo`가 실제 feature/override/part에 연결되지 않으면 실패다.
- held equipment의 socket이 없으면 실패다.

### Geometry unit

- 동일 spec은 동일 geometry key와 bounds를 만든다.
- invalid profile, self-intersection, 과도한 segment 수를 명확히 실패한다.
- shape-extrude depth 인자 누락 같은 호출 오류를 TypeScript에서 잡는다.

### Integration

- v1 sample을 v2로 migration한 후 기본 cast가 유지된다.
- v0 shallow knight는 strict v2에서 실패한다.
- target knight는 required role coverage와 attachment 검사를 통과한다.
- generic prop fixture는 character 전용 gate의 영향을 받지 않는다.

## 완료 기준

- 기사 몸통이 단일 box로 남지 않는다.
- helmet, shield, sword가 profile geometry로 identity를 보존한다.
- pose와 handedness가 source-aligned render에서 맞는다.
- 주요 equipment contact가 자동 검사된다.
- unknown geometry fallback이 완전히 제거된다.
- micro maps를 끈 상태에서도 캐릭터가 읽힌다.
