# Intake · Reference Prep · 파이프라인 고도화 갭 문서

## 문서 상태

| Field | Value |
| --- | --- |
| 상태 | `implemented-p0` |
| 기준일 | 2026-07-21 |
| 적용 대상 | gpthreejs v0.2+ (quality-upgrade M0–M6 이후, production-delivery 병행) |
| 언어 | 한국어 (관련 planning 묶음과 동일) |
| 선행 문서 | [quality-upgrade-execution/readme.md](./quality-upgrade-execution/readme.md), [02-reference-sense-and-sufficiency-plan.md](./quality-upgrade-execution/02-reference-sense-and-sufficiency-plan.md), [production-character-delivery-plan.md](./production-character-delivery-plan.md) |
| 트리거 | 텍스트 전용·저해상 단일 스프라이트 요청이 sufficiency `reject`/`abort`로 끝난 뒤, “유리한 조건의 참조를 먼저 생성·요청하는 프로세스가 없다”는 제품 피드백 |

## 1. 목적

이 문서는 **이미 구현된 품질 게이트와 납품 골격 위에**, 아직 제품 루프에 묶이지 않았거나 의도적으로 비어 있는 고도화 항목을 정리한다.

핵심 공백은 다음과 같다.

> **Sufficiency는 “부족하다”고 잘 거절한다. 그러나 “부족할 때 무엇을 어떤 스펙으로 만들어 채울지”를 엔진·스킬·에이전트가 기본 경로로 수행하지 않는다.**

사용자는 다음을 기대할 수 있다.

- 이미지를 안 줬을 때 → 캐스팅에 유리한 **콘셉트/턴어라운드 생성 스펙**을 먼저 제시·생성
- 이미지가 부족할 때 → 단순 “더 달라”가 아니라 **투명 배경, 해상도, 정면/측면/후면, 포즈** 등 **렌더·matte·multi-view에 유리한 조건**을 명시한 생성/촬영 브리프
- 생성 결과 → `ReferenceSet`에 **증거 등급을 속이지 않고** 넣어 다시 sufficiency → cast

이 문서는 그 경로와, 같은 계열의 인접 갭을 작업 단위로 고정한다.

## 2. 제품 원칙 (변경하지 않음)

다음 원칙은 유지한다. Reference Prep은 **우회가 아니라 입력 보강**이다.

| 원칙 | Reference Prep에서의 의미 |
| --- | --- |
| Evidence before aesthetics | 생성된 뷰는 예쁘기 전에 **실루엣·비율·장비 가시성**을 만족해야 한다 |
| Honest failure | 생성 뷰를 `observed`로 위장하지 않는다 |
| Source ownership | 최종 산출물은 절차적 TypeScript; 생성 이미지는 **참조 레이어** |
| Fail-closed gates | Prep 없이 cast를 강제 열지 않는다; Prep 후에도 게이트를 통과해야 한다 |
| No silent 3D LLM body | 2D 생성/편집만 허용; 본체 mesh 생성기는 기본 경로가 아님 |

**금지:** “게이트가 귀찮으니 단일 저해상 스프라이트로도 accept” 같은 완화.

## 3. 관찰된 실패 (이 문서를 연 이유)

### 3.1 사용자 시나리오

1. 요청: 성검전설 3 기사를 **현대식으로 재해석**해 3D(절차형 Three.js)로 제작
2. 참조: 약 **228×302 단일 스프라이트** (또는 이미지 없이 텍스트만인 경우도 동일 계열)
3. 결과: sufficiency / delivery gate에서 **reject**
4. 에이전트 응답: 고해상 정면·측면·후면·턴어라운드를 달라고 안내 후 중단
5. 사용자 질문: 애초에 생성 요청 시 **투명 배경·정사각·유리한 촬영 조건**을 전제로 잡을 수 있지 않나? 그런 프로세스가 없나?

### 3.2 엔진이 한 일 (정상)

| 코드 / 동작 | 의미 |
| --- | --- |
| `RES_TOO_LOW` (short side &lt; 256px) | blocker → `reject` / `abort` |
| `CHAR_SINGLE_VIEW` / `CHAR_NO_SIDE` | major → 캐릭터 단일 뷰 위험 |
| `DELIVERY_VIEW_INSUFFICIENT` | 납품 경로 multi-view 부족 |
| `NullImageProvider` | 이미지 생성 불가 → 항상 `ask` |
| skill nextSteps | “측면 요청”, “고해상 요청” 문구 수준 |

### 3.3 엔진·스킬이 하지 않은 일 (갭)

| 기대 | 현재 |
| --- | --- |
| 텍스트 전용 진입 → RequestSpec + 생성 브리프 | 이미지가 Required input; 텍스트 전용 루프 없음 |
| reject/`ask` 시 **생성 프롬프트 템플릿** 자동 산출 | remedy 한 줄 수준 |
| 투명/단색 배경, 최소 해상도, front/side/back 스펙 | 문서·코드에 **표준 GenerationSpec 없음** |
| 호스트 Imagine / 외부 2D provider 호출 | provider port만 있고 기본 null; skill이 생성 루프를 강제하지 않음 |
| 생성 이미지를 `design-intent`로 ReferenceSet 편입 후 재검사 | 수동 가능, **기본 루틴 아님** |
| “현대식 재해석”을 **의도 변환 단계**로 분리 | 원본 스프라이트 fidelity 경로와 혼동 |

## 4. 목표 아키텍처: Intake → Reference Prep → Cast

현재 기본 루프:

```text
image → probe/sense → sufficiency
  → abort  (blocker)  → stop
  → ask    (major)    → “이미지 달라”
  → continue          → brief → ledger → cast …
```

목표 루프:

```text
user intent (± images ± qualityMode ± domain)
        │
        v
  RequestSpec
  (subject, intent, modelingProfile, targetViews,
   redesignPolicy, qualityMode, mustHave)
        │
        v
  IntakeRoute
  ├─ has usable observed refs? ──yes──> ReferenceNormalize
  │                                      │
  │                                      v
  │                               SufficiencySet
  │                                 │
  │                    pass ────────┼──> Ledger → Blueprint → Cast
  │                    generate_more ┤
  │                    ask / abort   ┘
  │
  └─ no / insufficient ──> ReferencePrep
                            │
                            ├─ GenerationBrief (machine + human)
                            │    bg, resolution, aspect, views, pose,
                            │    identity locks, evidenceClass targets
                            ├─ agentAction:
                            │    generate | edit | request-user-capture | abort
                            ├─ optional ImageProvider / host Imagine
                            └─ outputs → ReferenceSet entries
                                 evidenceClass:
                                   design-intent | design-hypothesis
                                   (never silent observed)
                            │
                            v
                     re-enter SufficiencySet
```

### 4.1 진입 모드 (명시)

| mode | 사용자 입력 | Prep 역할 | cast 전 최소 조건 |
| --- | --- | --- | --- |
| `photo-lock` | 실사/아트 참조 충분 | normalize + matte only | observed multi-view 또는 object single-view 정책 |
| `redesign-from-ref` | 저품질/단일 원작 참조 + “현대식” 등 | 원작을 **identity seed**로, 새 콘셉트 뷰 생성 | 생성 턴어라운드 + 원작 링크(provenance) |
| `concept-first` | 텍스트만 | 전량 생성 턴어라운드 | design-intent front+side(+back), 해상도 게이트 |
| `hybrid-body` | 사용자 GLB + 참조 | 기존 hybrid 정책 유지 | 명시적 동의 + labeled bodySource |

`redesign-from-ref` / `concept-first` 에서는 **원작 likeness 보장을 클레임하지 않는다.**  
Fidelity Pact에 `redesign: true`, `likenessFloor: stylized` 등을 기록한다.

## 5. 고도화 영역 목록

아래 ID 접두사:

| 접두사 | 영역 |
| --- | --- |
| `RP` | Reference Prep / GenerationBrief |
| `IN` | Intake / RequestSpec / 라우팅 |
| `PV` | Image provider 실연결 |
| `SK` | Skill / agent 루프 / playbook |
| `UX` | 사용자 메시지·CLI·App |
| `EV` | 증거 등급·provenance·waiver |
| `QA` | 테스트·golden·벤치 |

우선순위: **P0** = 제품 약속 공백, **P1** = 납품 품질, **P2** = 편의·확장.

---

### 5.1 P0 — Reference Prep (사용자 피드백 핵심)

#### RP-001 · GenerationBrief 계약

**목표:** sufficiency/`ask`/`generate_more` 시 기계가 읽을 수 있는 생성 브리프를 출력한다.

최소 필드:

```json
{
  "schemaVersion": 1,
  "subject": "modern reinterpretation of SNES-era fantasy knight",
  "route": "redesign-from-ref",
  "evidenceClassDefault": "design-intent",
  "views": [
    {"id": "front", "camera": "orthographic-front", "required": true},
    {"id": "side", "camera": "orthographic-left", "required": true},
    {"id": "back", "camera": "orthographic-back", "required": false}
  ],
  "frame": {
    "minShortSidePx": 512,
    "recommendedShortSidePx": 1024,
    "aspect": "1:1",
    "subjectFill": [0.15, 0.80],
    "background": "transparent-or-solid-neutral",
    "backgroundHex": "#808080",
    "alphaPreferred": true
  },
  "pose": {
    "preset": "A-pose",
    "facing": "camera-relative",
    "noHeavyOcclusion": true
  },
  "identityLocks": [
    "helmet silhouette family",
    "shield presence and handedness",
    "primary weapon class"
  ],
  "style": {
    "direction": "modern hard-surface fantasy",
    "not": ["photoreal human skin pores", "illegible micro deco"]
  },
  "hostPrompt": "... single string for Imagine / external gen ...",
  "perViewPrompts": {},
  "remediesFromIssues": ["RES_TOO_LOW", "CHAR_NO_SIDE"]
}
```

**DoD:**

- schema + parser + fixture
- issue 코드 집합 → GenerationBrief 필드 매핑 테이블
- CLI: `python -m engine reference-prep … --out work/generation-brief.json`

#### RP-002 · 캐스팅 유리 조건 표준 (Capture / Gen defaults)

엔진·playbook에 **권장 기본값**을 고정한다. 정사각은 필수가 아니라 기본 권장이다.

| 항목 | 기본값 | 근거 |
| --- | --- | --- |
| 짧은 변 | ≥ 512px (절대 하한 256) | `RES_*` 정책과 정렬 |
| 배경 | 투명 PNG 또는 중성 단색 | matte 안정 |
| 종횡비 | 1:1 권장, 자유 허용 | 크롭·생성 편의; short-side가 진실 |
| 뷰 (character) | front + side 필수, back 권장 | `CHAR_*`, delivery DG-01 |
| 포즈 | A-pose / T-pose | 비율·부착 |
| 조명 | 부드러운 스튜디오, 강한 rim 과다 금지 | edge map·실루엣 |
| 한 파일 한 뷰 | 시트 분할은 후순위 | sense/ledger 단순화 |
| 포맷 | PNG | alpha + sense 호환 |

**DoD:** `playbook/reference_prep.md` + engine 상수 모듈 공유 (magic number 중복 금지).

#### RP-003 · reject/ask → Prep 분기

현재: `agentAction=abort|ask` 후 human prose만.

목표:

| sufficiency action | Prep 기본 동작 |
| --- | --- |
| `abort` + 해상도/파일 blocker | GenerationBrief 또는 “재촬영 체크리스트” 출력 후 stop |
| `ask` + `CHAR_*` / thin views | `generate_more` 후보 + brief 출력; 사용자 승인 시 생성 |
| `continue` + minor only | Prep 스킵, journal에 minor 기록 |

**DoD:** `sufficiency_messages.next_steps` / set-report에 `generationBriefPath` 또는 inline brief 링크; golden: knight-single-view가 brief 산출.

#### RP-004 · 텍스트 전용 / concept-first 진입

이미지가 없어도:

1. `RequestSpec` 작성 가능
2. `IntakeRoute=concept-first`
3. GenerationBrief 필수 뷰 생성 계획
4. 사용자 승인 또는 provider/host gen
5. ReferenceSet 구성 후 기존 파이프

**DoD:** CLI `python -m engine intake "modern knight" --domain character --route concept-first`; 이미지 없이 brief 생성 테스트.

#### RP-005 · redesign-from-ref 정책

저해상 원작 + “현대식” 요청 시:

- 원작 entry: `observed` (identity seed, 저신뢰 matte 허용 표시)
- 신규 턴어라운드: `design-intent` (재해석 기준 뷰)
- Pact: 원작 픽셀 매칭 의무 없음; **mustHave 아이덴티티**만 강제
- metrics: 생성 의도 뷰 대비 정렬 (원작 스프라이트 IoU를 hero metric으로 쓰지 않음)

**DoD:** policy 문서 + validator + 테스트 1건 이상.

---

### 5.2 P0 — Agent / Skill 루프

#### SK-001 · SKILL.md Operating loop에 Reference Prep 삽입

`1b) Sufficiency` 다음에:

```text
1c) Reference Prep (when abort/ask/generate_more or no image)
    - emit GenerationBrief
    - if host can generate images: produce views under brief
    - register ReferenceSet with correct evidenceClass
    - re-run sufficiency-set
    - only then cast
```

**DoD:** skill root `SKILL.md` + `~/.grok/skills/gpthreejs` 동기 정책에 반영(배포 경로 문서화).

#### SK-002 · abort 응답 템플릿 강화

에이전트가 사용자에게 말할 때 최소 포함:

1. 왜 막혔는지 (코드)
2. **지금 바로 생성/촬영할 스펙** (RP-002 표)
3. 선택지: (A) 호스트가 생성 (B) 사용자가 업로드 (C) stylized limited-info 명시 waiver (기본 비권장)

**DoD:** `playbook/reference_prep.md` “Agent speech” 절; 한글 `userMessage` 확장.

#### SK-003 · “이미지 없음”을 실패가 아닌 라우트로

Required inputs를 다음으로 개정:

1. **의도 문장 또는 이미지** (둘 중 하나)
2. intended use
3. qualityMode (optional)

이미지 없음 → concept-first, 이미지 부족 → prep, 충분 → cast.

---

### 5.3 P1 — Provider · provenance · honesty

#### PV-001 · REF-150 실어댑터 (host-agnostic)

현재: `NullImageProvider` only.

목표:

- `ImageProvider` 구현 1개 이상 **또는** “host-agent-generates, engine consumes paths” 어댑터
- budget: max gens/edits/wall time (기존 `ProviderBudget` 재사용)
- 실패 시 항상 `ask`, 부분 성공 시 incomplete ReferenceSet + `generate_more`

벤더 락인 금지: 어댑터는 파일 경로를 ReferenceSet에 넣는 수준으로 유지.

#### PV-002 · plan_missing_views → 실제 산출물

`plan_missing_views`가 `planned`만 내지 말고:

- brief per missing view
- 완료 시 entry draft (`path`, `declaredView`, `evidenceClass`, `origin=generated`)

#### EV-001 · evidenceClass 강제 (회귀 방지)

이미 계획된 규칙 재확인:

| origin | 허용 evidenceClass |
| --- | --- |
| user upload | `observed` |
| 2D gen from brief | `design-intent` or `design-hypothesis` |
| symmetry pad | `inferred` only, never sole side evidence for delivery |

생성 뷰를 `observed`로 올리면 **validator reject** (기존 테스트 유지·확장).

#### EV-002 · waiver 계약 (제한 경로)

사용자가 “정보 부족해도 스타일라이즈드로 진행”을 **명시**할 때만:

- `qualityMode` 상한 (`draft`/`solid`)
- delivery-export 기본 차단
- journal에 `waiver: limited-information-stylization`
- likeness / hero intent와 동시 불가

---

### 5.4 P1 — CLI · 메시지 · App

#### UX-001 · `reference-prep` / `intake` CLI

```bash
python -m engine intake "Subject" --domain character --intent game \
  --route concept-first --out work/request-spec.json

python -m engine reference-prep work/request-spec.json \
  --issues work/sufficiency.json \
  --seed-image optional.png \
  --out work/generation-brief.json

python -m engine reference-register work/generation-brief.json \
  --images work/gen/front.png work/gen/side.png \
  --out work/reference-set.json
```

#### UX-002 · sufficiency `userMessage` / `nextSteps` 한국어 품질

- 코드별 remedy에 **체크리스트** 포함
- `nextSteps`에 “GenerationBrief 작성”, “Imagine으로 front/side 생성” 등 **실행 가능한 단계**

#### UX-003 · ChatGPT App / UI (APP-120 연계)

deferred App 작업과 연결:

- generate-more UI
- brief 프리뷰
- 업로드 슬롯 front/side/back

본 문서의 품질 본체는 엔진+스킬; App은 소비 계층.

---

### 5.5 P1 — 인접 파이프라인 갭 (Prep 이후도 여전히 약함)

Reference Prep만으로 납품 품질이 완성되지 않는다. 아래는 **Prep과 직렬로 고도화할 인접 갭**이다. 상세 실행은 production-delivery / quality tasklist와 중복될 수 있으며, 여기서는 **누락 인식**을 고정한다.

| ID | 갭 | 현재 | 목표 한 줄 |
| --- | --- | --- | --- |
| `QA-GEO-01` | 형상 정밀도 | primitive + 일부 builder | 캐릭 identity 파트 일반화, fixture 밖 주제 |
| `QA-MAT-01` | matte 일반화 | heuristic + normalize | 복잡 배경·프레임 풀 피사체 자동 신뢰도 |
| `QA-LED-01` | ledger 밀도 | targetMin 충족 가능 | evidence-dense, redesign 시 identityLocks 매핑 |
| `QA-MET-01` | metrics 정렬 대상 | 종종 원본 단일 뷰 | redesign 시 design-intent 뷰를 기준으로 |
| `QA-REV-01` | accept theater 방지 | ReviewPolicy 존재 | delivery-export와 동일 hard gate |
| `QA-POR-01` | portable 번들 | 개선됨 | Prep 산출물 경로가 번들에 오염되지 않게 |
| `QA-DOC-01` | playbook 분산 | sufficiency / suitability 분리 | reference_prep 단일 진입 문서 |

---

### 5.6 P2 — 선택 확장

| ID | 내용 |
| --- | --- |
| `RP-010` | 턴어라운드 시트 1장 → 뷰 분할 도구 |
| `RP-011` | 비디오/스프라이트 시트에서 대표 프레임 추출 |
| `PV-010` | image edit: 배경 제거·업스케일 전용 경로 (전신 re-gen 대체) |
| `SK-010` | game-character-consistency 스킬과 prompt 공유 계약 |
| `UX-010` | 브라우저 데모에 “prep checklist” 패널 |

## 6. 구현 순서 (권장)

```text
Phase A  계약·문서 (막힌 루프를 말로 고정)
  RP-002 playbook defaults
  RP-001 GenerationBrief schema
  SK-001/002/003 skill loop
  EV-001 회귀 테스트 보강

Phase B  엔진 분기
  RP-003 sufficiency → brief
  RP-004 concept-first intake
  RP-005 redesign-from-ref
  UX-001/002 CLI + messages

Phase C  생성 연결
  PV-001/002 provider 또는 host-path adapter
  golden: text-only knight modern → brief → (fixture images) → sufficiency pass path

Phase D  납품 정렬
  QA-MET-01 redesign metrics base
  EV-002 waiver
  production-delivery DG와 brief 필드 정합
  UX-003 App (deferred 가능)
```

Phase A는 코드 없이도 에이전트 행동을 크게 개선한다.  
Phase B 없이는 재현 가능한 제품 계약이 아니다.  
Phase C 없이는 “프로세스가 있다”고 말하기 어렵다.

## 7. 테스트 · Golden

### 7.1 신규/확장 fixture

| fixture | 시나리오 | 기대 |
| --- | --- | --- |
| `knight-single-view` (기존) | reject 유지 | + GenerationBrief 필수 필드 존재 |
| `knight-text-only` | 이미지 없음 | intake → brief → views planned; cast 전 abort/ask without register |
| `knight-redesign-prep` | 저해상 seed + modern brief + 생성 front/side fixtures | sufficiency conditional/pass; evidenceClass ≠ 전부 observed |
| `knight-gen-as-observed` (negative) | 생성 뷰를 observed로 위장 | validate fail |

### 7.2 단위

- issue codes → brief.views / frame.minShortSidePx 매핑
- short side 228 → RES_TOO_LOW + brief 권장 1024
- character domain + viewCount 1 → side required=true
- Null provider → plan status ask, brief still emitted

### 7.3 통합 (호스트 gen 없이)

생성 PNG는 **체크인 fixture**로 두고, provider는 null이어도  
`reference-register` → `sufficiency-set` → (optional) cast dry-run 가능해야 한다.

## 8. 성공 기준

이 문서 범위가 “완료”이려면 다음이 모두 참이어야 한다.

1. **텍스트만**으로 modern character 요청 시, 에이전트/CLI가 cast를 시도하기 전에 **GenerationBrief**를 낸다.
2. **단일 저해상 스프라이트** reject 시, 사용자 메시지에 **투명/단색·해상도·front/side(/back)·포즈** 체크리스트가 포함된다.
3. Prep으로 만든 뷰는 ReferenceSet에 **올바른 evidenceClass**로만 들어간다.
4. Prep 없이도 통과 가능한 multi-view 고해상 입력 경로는 **회귀 없이** 유지된다.
5. delivery-export는 기존과 같이 **증거 부족 시 실패**한다 (Prep waiver 없는 한).
6. “프로세스가 없다”는 피드백에 대해, playbook + skill + CLI로 **재현 가능한 답**을 제시할 수 있다.

## 9. Non-goals

- 생성 이미지 품질을 자동 미학 점수로 accept
- 2D gen 한 장으로 360° likeness 주장
- 3D foundation model을 본체 생성기로 도입
- 특정 이미지 벤더 SDK를 엔진 코어 의존으로 고정
- sufficiency 해상도/뷰 hard gate 삭제
- 원작 저해상 스프라이트에 대한 픽셀 단위 재구성 약속

## 10. 기존 문서·코드 매핑

| 자산 | 관계 |
| --- | --- |
| [02-reference-sense-and-sufficiency-plan.md](./quality-upgrade-execution/02-reference-sense-and-sufficiency-plan.md) | ReferenceSet, `generate_more`, REF-150 port — **Prep의 상위 계획** |
| tasklist REF-150 | port **done**; 실어댑터·brief는 본 문서 PV/RP |
| [production-character-delivery-plan.md](./production-character-delivery-plan.md) | 납품 게이트; Prep은 입력 단계 보강 |
| `engine/reference/provider.py` | Null provider; plan_missing_views |
| `engine/sense/sufficiency_*.py` | 거절은 강함, Prep 연동 약함 |
| `playbook/sufficiency.md` / `suitability.md` | 검사 문서; **prep 문서 신설 필요** |
| `SKILL.md` Required inputs / loop | 이미지 전제; Prep 단계 없음 |
| golden `knight-single-view` | reject 고정 — brief 확장 대상 |

## 11. 작업 체크리스트 (추적용)

| Done | ID | 작업 | 우선 | 의존 |
| --- | --- | --- | --- | --- |
| [x] | RP-001 | GenerationBrief schema/parser/CLI | P0 | — |
| [x] | RP-002 | capture/gen defaults playbook + constants | P0 | — |
| [x] | RP-003 | sufficiency → Prep 분기 + brief emit | P0 | RP-001, RP-002 |
| [x] | RP-004 | concept-first / 텍스트 전용 intake | P0 | RP-001 |
| [x] | RP-005 | redesign-from-ref policy + pact fields | P0 | RP-004, EV-001 |
| [x] | SK-001 | SKILL.md loop 1c Reference Prep | P0 | RP-002 |
| [x] | SK-002 | abort/ask 사용자 응답 템플릿 | P0 | RP-002 |
| [x] | SK-003 | Required inputs 개정 (intent OR image) | P0 | RP-004 |
| [x] | EV-001 | evidenceClass 위장 회귀 테스트 확장 | P0 | REF-102 |
| [ ] | EV-002 | limited-info waiver 계약 | P1 | RP-005 |
| [ ] | PV-001 | host/path 또는 실 provider adapter | P1 | REF-150 |
| [ ] | PV-002 | plan_missing_views → entry drafts | P1 | RP-001, PV-001 |
| [x] | UX-001 | intake / reference-prep / register CLI | P1 | RP-001 |
| [x] | UX-002 | userMessage/nextSteps 실행형 체크리스트 | P1 | RP-003 |
| [ ] | UX-003 | App generate-more UI (APP-120) | P2 | UX-001 |
| [ ] | QA-MET-01 | redesign metrics base = design-intent | P1 | RP-005 |
| [x] | QA-DOC-01 | `playbook/reference_prep.md` 작성 | P0 | RP-002 |
| [ ] | RP-010+ | 시트 분할·업스케일 등 | P2 | Phase C |

## 12. 요약 (한 페이지)

```text
문제
  게이트는 거절에 강하고, “거절 후 올바른 참조를 만드는” 루프는 약하다.
  사용자는 투명 배경·해상도·정사각·3뷰 같은 유리 조건을
  생성 전에 고정하기를 기대한다.

방향
  IntakeRoute + GenerationBrief + ReferencePrep 단계를
  sufficiency와 cast 사이에 정식 삽입한다.
  생성 뷰는 design-intent/hypothesis로만 등록한다.

하지 않을 것
  게이트 완화, 3D LLM 본체, observed 위장, 벤더 코어 락인.

완료의 정의
  텍스트만 / 깨진 스프라이트 요청이 “reject 한 줄”이 아니라
  “이 스펙으로 그려서(또는 찍어서) 다시 넣으면 진행”으로 끝난다.
```

---

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-07-21 | 초안: 사용자 Reference Prep 피드백 + 인접 파이프라인 갭 문서화 |
| 2026-07-21 | P0 구현: GenerationBrief·intake/prep/register CLI·playbook·skill·EV-001 테스트 |
