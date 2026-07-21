# gpthreejs 프로덕션 캐릭터 납품 준 품질 고도화 계획

## 문서 상태

| Field | Value |
| --- | --- |
| 상태 | `planned` |
| 기준일 | 2026-07-21 |
| 적용 대상 | gpthreejs v0.2+ (quality-upgrade-execution M0–M6 이후) |
| 언어 | 한국어 (실행 계획 묶음과 동일) |
| 선행 문서 | [quality-upgrade-execution/readme.md](./quality-upgrade-execution/readme.md), [tasklist.md](./quality-upgrade-execution/tasklist.md), [intake-and-reference-prep-upgrade.md](./intake-and-reference-prep-upgrade.md) |
| 핵심 전제 | **3D LLM 메시 생성 없이** 절차적 TypeScript + 증거 게이트로 납품 준 품질에 도달 |
| 입력 보강 | 참조 부족·텍스트 전용 요청의 **Reference Prep / GenerationBrief** 는 [intake-and-reference-prep-upgrade.md](./intake-and-reference-prep-upgrade.md) 가 담당 (납품 게이트 완화 아님) |

## 1. 목적

이 문서는 이미 구축된 품질 고도화 골격(계약, fail-closed review, ReferenceSet, character slice, `run`, portable emit)을 **“내부 실험 툴”에서 “프로덕션 캐릭터 납품에 준하는 도구”**로 올리는 실행 계획이다.

목표는 “디테일이 많은 코드”나 “그럴듯한 한 장 렌더”가 아니다. 다음 결과를 목표로 한다.

> **다뷰 참조 증거를 보존한 채**, 형상·포즈·부착·재질이 **참조와 정렬되어 읽히고**, 산출물은 **편집 가능한 절차적 Three.js TypeScript**이며, 기준 미달 결과는 **deterministic policy 없이는 납품(accept/export)되지 않는다.**

### 1.1 “납품 준(production-delivery-grade)” 정의

이 계획에서 **납품 준**은 다음을 동시에 만족하는 상태를 말한다.

1. **Identity readability**  
   지정된 뷰(최소 front + side + source-aligned)에서 helmet/shield/sword(또는 prop identity parts), handedness, silhouette이 사람 검토 없이 **metric + 체크리스트**로 통과한다.
2. **Evidence-backed accept**  
   accept/export는 RenderSet PNG, MetricReport, ReviewPolicy policyTrace, journal 해시 연쇄 없이 불가능하다.
3. **Editable ownership**  
   최종 산출물은 불투명 glTF-only가 아니라 **Blueprint 개정 + factory TypeScript**이며, 파트/재질/포즈를 코드로 수정 가능하다.
4. **Portable delivery bundle**  
   저장소 밖 임시 Vite 프로젝트에서 typecheck/build/runtime smoke가 통과하는 번들을 내보낸다.
5. **Honest failure**  
   단일 뷰·낮은 matte 신뢰도·장비 접촉 실패·참조 대비 silhouette 미달 시 `ask`/`abort`/`replan`으로 멈추고, 가짜 accept를 하지 않는다.
6. **Scope honesty**  
   스타일라이즈드/게임/하드서피스 캐릭터·장비 prop에 한정한다. 포토리얼 인체·단일 스냅샷 전신 재구성은 비목표로 명시한다.

### 1.2 이 문서가 다루지 않는 것 (Non-goals)

- 3D foundation model / image-to-3D mesh LLM을 **본체 생성기**로 사용
- Boolean/CSG를 초기 필수로 도입 (필요 시 후속 단계)
- micro texture / film-grade shading을 geometry gate보다 앞세우기
- ChatGPT App UI 전체 (M7)를 납품 품질의 전제 조건으로 삼기 — App은 **소비 계층**, 품질 본체는 엔진
- 특정 상용 이미지 생성 벤더 락인 (port만 허용)
- “벤치마크 수치만 올리면 납품” — 사람 가독 체크리스트와 병행

## 2. 전략 원칙 (3D LLM 없이 가는 이유)

### 2.1 제품 약속과의 정합

gpthreejs의 핵심 약속은 다음과 같다.

- Evidence before aesthetics  
- Source ownership before asset opacity  
- Honest failure before shallow success  
- Runtime budgets before decorative complexity  

3D LLM 직접 메시 생성은 대개:

| 특성 | 납품 파이프에 미치는 영향 |
| --- | --- |
| 불투명 메시 출력 | diff·리뷰·부분 수정이 어려움 |
| 비결정성 | CI/게이트 재현 실패 |
| “그럴듯한” 실패 | 관대한 accept 유혹 |
| 근거 부재 | Feature Ledger / critical feature 역추적 불가 |

따라서 **본체 생성 경로에 3D LLM을 두지 않는다.**  
선택적으로 쓸 수 있는 것은 오직:

- **2D** image generate/edit provider (뷰 보강, REF-150 확장)  
- 사람이 공급한 turnaround  
- (후순위) 외부 메시를 **명시적 bodySource=external** 로 감싸는 경로 — 기본 경로 아님

### 2.2 품질 실패의 실제 순서 (재확인)

선행 quality-upgrade 계획과 동일하게, 납품 실패도 보통 다음 순서로 발생한다.

```text
불완전 입력 (단일 뷰 / 나쁜 matte)
  → 빈약하거나 스캐폴드 수준 Ledger
  → 의미 부품·비율·포즈 부족 Blueprint
  → 근사 geometry emit (형태 미달)
  → 잘못된 부착 / handedness
  → 참조 비정렬 beauty만 확인
  → 느슨한 accept
```

고도화 순서도 이 역순이 아니라 **입력·계약·형상·참조 정렬 게이트**를 지킨다. surface polish는 항상 마지막이다.

### 2.3 현재 기준선 (quality-upgrade 이후, 2026-07-21)

이미 존재하는 자산 (요지):

| 영역 | 상태 | 납품 관점 평가 |
| --- | --- | --- |
| Blueprint v2 / strict validate | 있음 | 계약 기반 OK |
| ReferenceSet / set CLI / matte confidence | 있음 | 다뷰·실참조 정렬 강화 필요 |
| production ledger (no TODO) | 있음 | 스캐폴드 → evidence-dense ledger 필요 |
| character vertical slice | 있음 | fixture 고정 품질 → 일반화 필요 |
| CPU multi-pass PNG + metrics | 있음 | **참조 사진 정렬** 및 WebGL 정합 필요 |
| ReviewPolicy + journal wiring | 있음 | 납품 export 게이트로 격상 필요 |
| emit FormRuntime.dispose + named geom helpers | 있음 | Extrude/Lathe 정밀도와 파트 수 확대 필요 |
| portable bundle / wheel / CI | 있음 | 납품 번들 체크리스트 자동화 필요 |
| ChatGPT App (M7) | deferred | 품질 본체와 분리 |

**결론:** “파이프라인을 돌릴 수 있는 툴”은 됨. “납품 준 캐릭터 품질”은 **참조 정렬·형상 fidelity·export 게이트·벤치 세트**가 빠져 있다.

## 3. 목표 아키텍처

### 3.1 납품 데이터 흐름

```text
Client brief + images
        │
        v
  RequestSpec (intent, modelingProfile, qualityMode, mustHave)
        │
        v
  ReferencePlanner
    ├─ observed views (required)
    ├─ optional 2D provider → design-hypothesis views (never observed)
    └─ normalize + matte confidence
        │
        v
  ReferenceSet (hashes, provenance, coverage)
        │
        v
  SenseSet + SufficiencySet  ──fail──> ask | abort
        │ pass/conditional(with waiver)
        v
  LedgerSet (evidence-dense, category coverage)
        │
        v
  Blueprint draft (profile rules) → strict validate
        │
        v
  Cast (precise geometry emit) → FormRuntime factory + portable bundle
        │
        v
  Canonical RenderSet
    ├─ software (CI/deterministic) AND/OR
    └─ WebGL capture (delivery beauty, same camera profiles)
        │
        v
  Metrics vs reference mattes/landmarks/part visibility
        │
        v
  ReviewPolicy (hard metrics; reviewer advisory only)
        │
        ├─ accept  → Delivery Export (bundle + report + journal)
        ├─ replan  → Iteration (issue→JSON patch, budget, rollback)
        └─ abort   → structured failure report
```

### 3.2 두 개의 진실 원천 금지

납품 경로에서는 다음을 **하나의 체인**으로 묶는다.

| 금지 | 이유 |
| --- | --- |
| 데모 수작업 knight 메시와 emit factory가 서로 다른 형상 진실 | 게이트가 데모를 통과해도 납품 코드가 다를 수 있음 |
| CPU metrics only accept + 사람이 다른 뷰로 육안 납품 | 재현 불가 |
| journal 없는 export | 감사 추적 단절 |

**규칙:** Delivery Export는 `run` (또는 동등 오케스트레이션) 산출 artifact 집합만 패키징한다.

### 3.3 품질 모드와 모델링 프로필 (유지·강화)

| 축 | 역할 |
| --- | --- |
| `qualityMode` | 계산 예산, map 해상도, iteration 한도 |
| `modelingProfile` | 필수 파트/비율/ledger category (`stylized-character` 등) |

납품 프로필 예:

- `stylized-character` + `sharp` 또는 `razor`  
- `hard-surface-hero` (무기/방패 단독 납품)

## 4. 납품 성공 기준 (Exit Criteria)

### 4.1 자동 게이트 (Hard)

아래를 **전부** 통과해야 `delivery-export`가 성공한다.

| ID | 게이트 | 최소 기준 (초안, 캘리브레이션 후 고정) |
| --- | --- | --- |
| DG-01 | 뷰 커버리지 | stylized-character: front + side + source-aligned 필수; back 권장, sharp+에서 side 없으면 fail |
| DG-02 | Matte confidence | 주 뷰 confidence ≥ 임계 또는 normalize 후 회복; 아니면 ask |
| DG-03 | Ledger | production mode, TODO 0, targetMin, character categories 전부 |
| DG-04 | Blueprint strict | v2 strict + profile rules + attachment sockets |
| DG-05 | Contact | 필수 장비 attachment gap/penetration 통과 |
| DG-06 | Silhouette | 각 필수 뷰에서 ref-matte 대비 IoU / boundary F ≥ 캘리브 임계 |
| DG-07 | Framing | bbox center/occupancy 대역 내 |
| DG-08 | Part identity | part-ID pass에서 mustHave / critical parts 가시 |
| DG-09 | Handedness | shield/sword (또는 mustHave 장비) 좌우 일치 |
| DG-10 | Material readability | black crush / AO overdrive fail 없음 |
| DG-11 | Policy | accept only with policyTrace.policyIssued |
| DG-12 | Freshness | Blueprint/factory/render/metric 해시 연쇄 유효 |
| DG-13 | Portable | temp consumer typecheck + build (+ runtime smoke) |
| DG-14 | Budget | stage wall/CPU/render count 한도 내 종료 |

### 4.2 사람/에이전트 체크리스트 (Soft, 필수 기록)

자동 통과 후에도 납품 패키지에 서명 체크리스트를 남긴다.

- [ ] source-aligned 뷰에서 실루엣이 참조와 “같은 캐릭터”로 읽힘  
- [ ] side 뷰에서 두께/헬멧 깊이가 납작하지 않음  
- [ ] 장비 접촉이 떠 있거나 과도 침투하지 않음  
- [ ] 금속이 검게 뭉개지지 않음  
- [ ] factory.ts가 의도 파트 트리를 반영 (임의 박스 더미 아님)  
- [ ] 알려진 불확실성 (히든 백페이스 등)이 report에 명시  

### 4.3 벤치마크 세트

납품 준 선언 전에 최소 fixture 세트:

| Fixture | 유형 | 목적 |
| --- | --- | --- |
| knight-turnaround | stylized-character | 주 벤치 (front/side/back/source-34) |
| knight-single-view | negative | 반드시 ask/abort |
| hard-surface-shield | hard-surface-hero | prop identity |
| generic-crate | generic-prop | 회귀·과적합 방지 |
| mutated-side | negative | cross-view consistency reject |

각 fixture는:

- ReferenceSet + RequestSpec  
- 기대 verdict (pass/fail codes)  
- 허용 metric 대역  
- 마지막 성공 delivery bundle 해시 (선택)

## 5. 갭 분석 → 작업 패키지

선행 quality-upgrade 대비 **납품 준**에 모자란 점과 대응 패키지.

| 갭 | 현재 | 목표 패키지 |
| --- | --- | --- |
| 참조 정렬 약함 | self/parent alpha 중심 | **PD-REF** reference mattes/landmarks as metric targets |
| 다뷰 강제 약함 | 조건부 이슈 | **PD-REF** hard gate for character sharp+ |
| Ledger 스캐폴드 | category 채움 | **PD-LED** sense/zone/palette driven dense entries |
| Geometry fidelity | helpers 있으나 파트 밀도·정밀 한계 | **PD-GEO** vocabulary depth + part authoring rules |
| Attachment 정밀 | translation MVP | **PD-ATT** full transform chain + contact fixtures |
| Dual truth (demo vs emit) | 수작업 demo 기사 | **PD-CAST** emit-first path; demo consumes factory |
| Canonical beauty | CPU software 주 | **PD-RND** profile-locked WebGL capture parity |
| Comparison | overlay PNG 기초 | **PD-REV** full sheet + gate annotations |
| Iteration | stage/issue patch MVP | **PD-ITER** issue taxonomy → patch library + budgets |
| Export | portable partial | **PD-DLV** delivery-export command + SBOM-like manifest |
| Bench | knight 중심 | **PD-BENCH** multi-fixture release gate |
| Ops | CI 기본 | **PD-OPS** delivery matrix job |

## 6. 마일스톤 계획

버전 태그는 논리 마일스톤이다. 기존 M0–M7과 충돌을 피하기 위해 **PD-0 … PD-7** 을 사용한다.

```text
PD-0  납품 정의·벤치 fixture 고정
  → PD-1  참조· sufficiency 납품 게이트
  → PD-2  Ledger·Blueprint 깊이
  → PD-3  Geometry·Attachment·emit-first
  → PD-4  Canonical WebGL + 참조 정렬 metrics
  → PD-5  Iteration·rollback·예산
  → PD-6  Delivery export·portability·CI
  → PD-7  (선택) App/MCP 소비 계층
```

---

### PD-0 — 납품 정의와 벤치 고정

**Exit:** “납품 준” 체크리스트와 fixture 계약이 repo에 고정되고, 현재 파이프라인으로 baseline 점수가 기록된다.

| ID | 작업 | Depends | Definition of done |
| --- | --- | --- | --- |
| PD-0-001 | 본 문서 기준 성공 기준을 `docs/planning/production-character-delivery-plan.md`에 동결 | - | 이 파일; 리뷰 체크리스트 포함 |
| PD-0-002 | knight turnaround ReferenceSet 완성 (front/side/back/source-34) | PD-0-001 | `tests/golden/knight/` 다뷰 경로·hash·license |
| PD-0-003 | negative fixtures (single-view, mutated-side) | PD-0-002 | 기대 fail codes 테스트 |
| PD-0-004 | baseline delivery report 생성 스크립트 | PD-0-002 | `run` 결과 JSON + metric snapshot 저장 |
| PD-0-005 | metric 임계 초안 테이블 | PD-0-004 | 캘리브레이션 전 provisional thresholds 문서화 |

**Verification**

```bash
python -m engine run tests/golden/knight/project.json --max-iterations 0
python -m unittest tests.test_knight_m0_baseline tests.test_forward_and_gaps -v
```

---

### PD-1 — 참조·Sufficiency 납품 게이트

**Exit:** stylized-character sharp+ 는 side 없이 통과 불가. matte 실패 시 normalize 또는 ask. 생성 뷰는 observed로 승격 불가.

| ID | 작업 | Depends | Definition of done |
| --- | --- | --- | --- |
| PD-1-001 | RequestSpec delivery profile 필드 (`deliveryGrade`, `requiredViews`) | PD-0-001 | schema + parser tests |
| PD-1-002 | character sharp+ side/back policy를 sufficiency-set hard error로 격상 | PD-1-001 | 단일 뷰 fixture fail-closed |
| PD-1-003 | matte confidence → auto-normalize → remeasure → ask 상태머신 | PD-1-002 | frame-filling 자동 pad 후 confidence 회복 테스트 |
| PD-1-004 | 참조 뷰별 matte/alpha artifact를 ReferenceSet에 연결 | PD-1-003 | 경로+hash; metrics 입력으로 사용 |
| PD-1-005 | cross-view consistency를 픽셀/팔레트 신호로 강화 | PD-1-004 | mutated-side 반드시 reject |
| PD-1-006 | 2D provider port 예산 소진 시 ask 메시지 표준화 | PD-1-001 | null provider 계약 유지, 메시지 고정 |

**Verification**

```bash
python -m engine sufficiency-set tests/golden/knight/reference-set.json \
  --request tests/golden/knight/request-spec.json --strict
python -m unittest tests.test_reference_set tests.test_sufficiency -v
```

---

### PD-2 — Ledger·Blueprint 깊이

**Exit:** production ledger가 sense 근거 밀도 있는 entry를 만들고, Blueprint가 납품 파트 트리 최소 밀도를 만족한다.

| ID | 작업 | Depends | Definition of done |
| --- | --- | --- | --- |
| PD-2-001 | ledger entry 생성기: zone + palette + edge density → description/confidence | PD-1-004 | TODO 0, evidenceRefs 비어 있지 않음 |
| PD-2-002 | mapsTo 자동 초안 (part/feature id 제안) + strict 전 resolve 게이트 | PD-2-001 | unresolved mapsTo 시 cast 차단 옵션 |
| PD-2-003 | modelingProfile rule table을 `validate --strict` 기본 경로에 연결 | PD-2-002 | character rules fail codes |
| PD-2-004 | proportion/pose/landmark 필수 세트 납품 프로필 | PD-2-003 | landmark projection tests |
| PD-2-005 | criticalFeatures ↔ partIds ↔ targetViews 완전 연결 강제 | PD-2-004 | v2-target 및 신규 draft 모두 통과/실패 명확 |
| PD-2-006 | shallow semantic depth 점수 (role coverage × hierarchy × attachments) | PD-2-005 | 박스 세분화 우회 차단 |

**Verification**

```bash
python -m engine validate tests/golden/knight/blueprints/v2-target.json --strict
python -m engine ledger-set tests/golden/knight/reference-set.json --sense <sense-out> \
  --request tests/golden/knight/request-spec.json --out /tmp/ledger.json
```

---

### PD-3 — Geometry·Attachment·emit-first

**Exit:** 납품 factory가 데모 수작업 메시 없이도 identity geometry를 재현하고, 장비 접촉이 world-space로 검사된다.

| ID | 작업 | Depends | Definition of done |
| --- | --- | --- | --- |
| PD-3-001 | geometry builders ↔ emit helpers 1:1 계약 테스트 | PD-2-006 | kind별 snapshot/bounds |
| PD-3-002 | shape-extrude/lathe/tube/beveled-plate 파라미터 검증 강화 | PD-3-001 | invalid input JSON path errors |
| PD-3-003 | attachment: 회전 포함 transform 누적 world pose | PD-3-002 | sword/shield gap fixtures |
| PD-3-004 | contact 실패 시 구체 코드 (`ATTACHMENT_GAP`, …)를 Review issue로 승격 | PD-3-003 | run metrics 연결 |
| PD-3-005 | **emit-first demo path**: demo가 생성된 factory 또는 shared authoring 모듈 소비 | PD-3-003 | 수작업 createKnightForm과 이중 진실 제거 로드맵 실행 |
| PD-3-006 | part 네이밍·layer 규칙 (mass/secondary/trim) | PD-3-005 | part-ID pass 안정 색 매핑 |
| PD-3-007 | FormRuntime dispose E2E (browser): create→render→dispose 반복 | PD-3-005 | RES-110 WebGL 또는 headless 가능 범위 |

**Verification**

```bash
python -m engine cast tests/golden/knight/blueprints/v2-target.json --out /tmp/f.ts --out-dir /tmp/bundle
npm --prefix demo run typecheck
# emit-first 이후: demo가 bundle/factory를 로드하는 경로 smoke
```

---

### PD-4 — Canonical Render와 참조 정렬 Metrics

**Exit:** 필수 뷰×pass가 재현 가능하고, silhouette/framing/part metrics가 **참조 matte/landmark**에 대해 계산된다.

| ID | 작업 | Depends | Definition of done |
| --- | --- | --- | --- |
| PD-4-001 | camera profile 단일 소스 (Blueprint renderProfiles = capture profiles) | PD-3-006 | hash equality tests |
| PD-4-002 | WebGL capture harness를 multi-view multi-pass로 확장 | PD-4-001 | RND-101 확장; beauty/alpha/partId 최소 |
| PD-4-003 | software render와 WebGL alpha IoU 상관/허용 오차 문서화 | PD-4-002 | CI는 software, 납품은 WebGL+software dual |
| PD-4-004 | metrics: reference matte 대비 silhouette IoU/F/contour | PD-1-004, PD-4-002 | 사진 정렬 테스트 |
| PD-4-005 | landmark 화면 오차 metric | PD-2-004, PD-4-004 | per-view report |
| PD-4-006 | part visibility vs mustHave weights | PD-4-005 | coverage score |
| PD-4-007 | comparison sheet: ref | beauty | alpha-diff | part labels | PD-4-006 | PNG 세트 + manifest |
| PD-4-008 | metric 임계 캘리브레이션 (knight fixture) | PD-4-004 | provisional → calibrated 테이블 |

**Verification**

```bash
python -m engine run tests/golden/knight/project.json --max-iterations 0
npm --prefix demo run capture:smoke
# 확장 후: multi-view capture command
```

**이중 렌더러 정책**

| 환경 | 렌더러 | 용도 |
| --- | --- | --- |
| CI | software multi-pass | 결정적 회귀 |
| 개발자 GPU | WebGL capture | 납품 beauty / 사람 리뷰 |
| accept | 둘 다 가능하되 **동일 camera hash** | 불일치 시 fail or warn-by-policy |

---

### PD-5 — Iteration과 예산

**Exit:** 실패 metric이 허용 패치 표면으로만 수정되고, critical regression 시 rollback, 예산 초과 시 정상 종료한다.

| ID | 작업 | Depends | Definition of done |
| --- | --- | --- | --- |
| PD-5-001 | issue taxonomy 확장 (framing/silhouette/part/attach/material/handedness) | PD-4-006 | map_issue_to_scope 완전 |
| PD-5-002 | patch library per issue (JSON Patch only) | PD-5-001 | validator 통과 케이스 표 |
| PD-5-003 | coarse-to-fine: camera → mass → part → attachment | PD-5-002 | fit stages |
| PD-5-004 | critical feature regression table (helmet vs shield 등) | PD-5-003 | rollback fixture |
| PD-5-005 | budgets: iteration/render/wall/reviewer | PD-5-004 | stopReason 결정적 |
| PD-5-006 | render cache hit로 부분 재렌더 | PD-5-005 | cache stats in report |
| PD-5-007 | production path에서 experimental matte proxy 호출 금지 유지 | - | 정적/단위 가드 |

**Verification**

```bash
python -m engine run tests/golden/knight/project.json --max-iterations 5
```

기대: metric 개선 또는 `stopReason` + best revision.

---

### PD-6 — Delivery Export·Portability·Release

**Exit:** 한 명령으로 납품 번들+리포트가 나오고, 클린 환경에서 재검증된다.

| ID | 작업 | Depends | Definition of done |
| --- | --- | --- | --- |
| PD-6-001 | `delivery-export` CLI | PD-4-008, PD-5-005 | 번들 디렉터리 + manifest |
| PD-6-002 | export 전 DG-01…14 체크리스트 실행 | PD-6-001 | 실패 시 non-zero |
| PD-6-003 | 번들 내용: factory, FormRuntime, surface presets, blueprint snapshot, reports, renders | PD-6-001 | no repo-relative imports |
| PD-6-004 | temp Vite consumer typecheck/build/runtime | PD-6-003 | DX-211 강화 |
| PD-6-005 | UTF-8 / mojibake gate on all text artifacts | PD-6-003 | DX-301 강화 |
| PD-6-006 | release CI job: python + demo + wheel + delivery fixture | PD-6-004 | fail-closed |
| PD-6-007 | 성능 리포트: stage wall/CPU/RSS/render counts | PD-6-006 | PERF JSON |
| PD-6-008 | 버전 정책: deliveryGrade 성공 시에만 `delivery` 태그 허용 (프로세스) | PD-6-002 | 문서화 |

**번들 레이아웃 (목표)**

```text
delivery/<subject>-<revision>/
  manifest.json          # hashes, versions, gate results
  blueprint.json
  factory.ts
  surfacePresets.ts
  reports/
    sufficiency.json
    metric-report.json
    review-report.json
    comparison-sheet.json
    journal-excerpt.json
    delivery-checklist.json
  renders/
    <view>/<pass>.png
  sbom-ish/
    toolchain.json       # python/node/three versions
```

**Verification**

```bash
python -m build && pip install dist/*.whl   # venv
gpthreejs delivery-export tests/golden/knight/project.json --out /tmp/delivery
# temp consumer check
```

---

### PD-7 — (선택) 소비 계층 App/MCP

**Exit:** 품질 본체를 바꾸지 않고 동일 `run`/`delivery-export`를 호출한다.

| ID | 작업 | Depends | Definition of done |
| --- | --- | --- | --- |
| PD-7-001 | MCP tool: run_project / export_delivery | PD-6-002 | schema + idempotency |
| PD-7-002 | job state resume/cancel | PD-7-001 | E2E |
| PD-7-003 | UI: reference gaps, comparison, timeline | PD-7-002 | 기존 M7 APP-* |

App은 **품질을 만들지 않는다.** 게이트를 우회하는 UI 경로 금지.

## 7. 상세 설계 노트

### 7.1 참조 정렬 Metrics

**입력**

- ReferenceSet 뷰 `i`의 matte/alpha (또는 sense matte)  
- RenderSet 동일 뷰 alpha / partId / beauty  

**계산**

| Metric | 정의 |
| --- | --- |
| silhouette_iou | ref_matte ∩ render_alpha / ∪ |
| boundary_f | edge pixel F1 (tolerant band 허용 픽셀) |
| contour_distance | 정규화 mean nearest-edge distance |
| framing | bbox center error + occupancy band |
| landmark_err | projected landmark vs annotated 2D (있으면) |
| part_coverage | Σ w_k * visible(k) / Σ w_k |
| handedness | 장비 무게중심 x 부호 vs RequestSpec/ledger |

**금지:** 참조 없이 self-IoU=1.0 으로 accept.

### 7.2 Issue → Patch 표면 (허용 목록 유지)

허용 JSON Patch prefix (기존 ITER 계약 확장 가능):

- `/proportionProfile/`  
- `/poseProfile/joints/`  
- `/parts/*/transform/`  
- `/materials/*/channels/`  
- `/environment/`  
- `/renderProfiles/*/camera/`  

금지: 임의 코드 삽입, geometry kind 무단 변경(별도 high-risk patch class로만).

### 7.3 3D LLM 사용 정책 (명시)

| 사용 | 허용? |
| --- | --- |
| 본체 mesh 생성 후 납품 | **금지** |
| 히든 면 가설 이미지를 2D로 생성 | 허용 (evidenceClass=design-hypothesis) |
| 리뷰 코멘트 초안 LLM | 허용 (advisory only; accept 불가) |
| 파라미터 제안 LLM | 허용 시 **JSON Patch 검증 필수** |

### 7.4 성능 예산 (초안)

| Stage | 개발자 머신 목표 (sharp, 128–512px) |
| --- | --- |
| sense-set (3 views) | < 30s wall (rembg off 기준 별도) |
| draft+validate | < 5s |
| software render 6 views × 8 passes @128 | < 20s |
| WebGL capture 6 views × 3 passes @512 | < 60s |
| iteration 5 steps | < 5 min |

초과 시 qualityMode 하향 또는 해상도 coarse-to-fine.

## 8. 테스트 전략

### 8.1 계층

| 계층 | 내용 |
| --- | --- |
| Unit | schema, patch allowlist, metric pure functions |
| Contract | Blueprint/RenderSet/Metric/Review hash freshness |
| Fixture | knight/prop/negative golden |
| Integration | `run` / `delivery-export` E2E |
| Portability | temp Vite consumer |
| Manual sign-off | soft checklist 기록 |

### 8.2 회귀 금지 목록

- silent box fallback 재도입  
- accept without policyTrace  
- production ledger TODO  
- observed로 생성된 뷰 승격  
- fit_root_mass production 호출  
- export without DG checklist  

### 8.3 릴리스 게이트 명령 (목표)

```bash
python -m unittest discover -s tests -v
python -m engine validate tests/golden/knight/blueprints/v2-target.json --strict
python -m engine run tests/golden/knight/project.json --max-iterations 3
python -m engine delivery-export tests/golden/knight/project.json --out work/delivery
npm --prefix demo run check
# venv wheel
python -m build && pip install dist/*.whl && gpthreejs --help
```

## 9. 실행 순서와 병렬화

```text
PD-0 ─────────────────────────────┐
PD-1 (ref gates) ─────────────────┼─→ PD-2 (ledger/bp)
PD-3 (geo/attach/emit-first) ─────┤
         └─ needs PD-2 rules      │
PD-4 (render/metrics) ←───────────┤ needs PD-1 mattes + PD-3 parts
PD-5 (iterate) ←────────────────── PD-4
PD-6 (export/CI) ←──────────────── PD-5
PD-7 optional ←─────────────────── PD-6
```

병렬 가능:

- PD-1와 PD-3-001/002 (builders)  
- PD-4 software metrics 강화와 PD-4 WebGL harness (인터페이스 합의 후)  
- PD-6 번들 레이아웃 초안과 PD-5 iteration  

순차 필수:

- 참조 matte 없이 참조 정렬 metric 완료 선언 금지  
- emit-first 없이 “납품 factory = 데모 품질” 주장 금지  
- DG checklist 없이 delivery-export 성공 금지  

## 10. 리스크와 완화

| 리스크 | 영향 | 완화 |
| --- | --- | --- |
| 단일 뷰 고객 입력 | 구조적 불가 | hard ask; 2D provider로 뷰 보강만 |
| WebGL CI 불안정 | 가짜 실패/성공 | CI software, 납품 dual hash |
| metric 임계 과적합 (knight only) | 다른 캐릭터 실패 | multi-fixture + prop fixture |
| emit-first 이관 비용 | 데모 깨짐 | 단계적: factory 병행 → 교체 |
| 과한 자동화 patch | 형상 붕괴 | allowlist + critical rollback |
| 3D LLM 유혹 | 소유권 상실 | 정책 문서 + export 게이트 |
| 성능 예산 초과 | 실사용 불가 | coarse-to-fine + cache |

## 11. 의사결정 로그 (이 계획 채택 시)

| Decision | Reason |
| --- | --- |
| 3D LLM 비본체 | 코드 소유·결정성·fail-closed 유지 |
| 납품 범위 = stylized/hard-surface | 단일 뷰 포토리얼 인체는 정직히 제외 |
| Dual renderer (software + WebGL) | CI 결정성 + 납품 가독 |
| delivery-export 단일 입구 | 우회 accept 방지 |
| App은 PD-7 선택 | 품질 본체와 분리 |
| Texture last | 기존 quality-upgrade 원칙 유지 |

## 12. 완료 정의 (프로그램 레벨)

다음이 모두 참일 때 **“프로덕션 캐릭터 납품 준 툴”** 로 선언한다.

1. PD-0…PD-6 exit 충족  
2. knight-turnaround fixture가 DG-01…14 및 soft checklist 통과  
3. negative fixtures가 모두 기대대로 거부  
4. prop fixture 회귀 없음  
5. 클린 머신에서 wheel + delivery-export + temp consumer 통과  
6. 알려진 한계(히든 면, 유기 변형 등)가 delivery report에 자동 포함  
7. 문서·tasklist·Evidence가 실제 명령과 일치 (체크만 된 done 금지)

## 13. 즉시 다음 액션 (구현 착수 시)

1. PD-0-002: knight 다뷰 ReferenceSet 실자산 고정  
2. PD-0-004: baseline delivery report 스크립트  
3. PD-1-002: character side hard gate  
4. PD-4-004: reference matte 정렬 silhouette metric  
5. PD-6-001: `delivery-export` 스케치 (게이트 스텁 포함)

## 14. 관련 문서

- [quality-upgrade-execution/readme.md](./quality-upgrade-execution/readme.md) — 선행 품질 골격  
- [quality-upgrade-execution/tasklist.md](./quality-upgrade-execution/tasklist.md) — M0–M7 추적  
- [quality-upgrade-execution/01-observed-failures-and-success-criteria.md](./quality-upgrade-execution/01-observed-failures-and-success-criteria.md)  
- [AGENTS.md](../../AGENTS.md) — 제품 약속·가치  

---

## 부록 A — 납품 거부 사유 코드 (초안)

| Code | 의미 | agentAction |
| --- | --- | --- |
| DELIVERY_VIEW_INSUFFICIENT | 필수 뷰 부족 | ask |
| DELIVERY_MATTE_LOW_CONFIDENCE | matte 신뢰 불가 | ask/normalize |
| DELIVERY_LEDGER_SPARSE | ledger 밀도/카테고리 부족 | ask/replan |
| DELIVERY_SEMANTIC_SHALLOW | Blueprint 의미 깊이 부족 | replan |
| DELIVERY_CONTACT_FAIL | 장비 접촉 실패 | replan |
| DELIVERY_SILHOUETTE_FAIL | 참조 대비 실루엣 미달 | replan |
| DELIVERY_IDENTITY_FAIL | critical part 비가시 | replan |
| DELIVERY_HANDEDNESS_FAIL | 좌우 불일치 | replan |
| DELIVERY_MATERIAL_UNREADABLE | 판독 불가 재질 | replan |
| DELIVERY_POLICY_DENY | policy non-accept | replan/abort |
| DELIVERY_STALE_ARTIFACT | 해시 연쇄 깨짐 | replan |
| DELIVERY_PORTABILITY_FAIL | consumer build 실패 | abort |
| DELIVERY_BUDGET_EXCEEDED | 예산 초과 | abort |

## 부록 B — 용어

| 용어 | 정의 |
| --- | --- |
| 납품 준 | 본 문서 §1.1 |
| Delivery Export | DG 통과 산출물 패키징 명령 |
| Canonical Render | camera-hash 고정 multi-view multi-pass |
| Emit-first | Blueprint→factory가 시각 진실의 주 경로 |
| Advisory reviewer | accept 권한 없는 추천만 하는 리뷰어 |
| Observed view | 사용자 제공 실측 이미지 evidenceClass |

## 부록 C — 변경 이력

| 날짜 | 변경 |
| --- | --- |
| 2026-07-21 | 초안 작성. quality-upgrade M0–M6 이후 납품 준 고도화 범위 정의. 3D LLM 비본체 정책 명시. |
