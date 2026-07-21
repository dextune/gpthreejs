# Runtime, Tooling, Portability 고도화 계획

## 목표

생성 코드는 저장소 내부 경로에 기대지 않고 다른 Three.js 프로젝트로 옮겨도 build와 runtime smoke를 통과해야 한다. Vite build 성공만으로 완료 처리하지 않고 TypeScript 계약, 브라우저 console, 자원 해제까지 검증한다.

## 현재 상태

재사용 가능한 것:

- [`engine/commands/registry.py`](../../../engine/commands/registry.py)의 분리된 CLI registry
- [`engine/cast/emit_factory.py`](../../../engine/cast/emit_factory.py)의 geometry/material registry 생성
- [`engine/cast/surface/presets.json`](../../../engine/cast/surface/presets.json)의 단일 surface preset
- [`demo/src/app/resources.ts`](../../../demo/src/app/resources.ts)의 기본 geometry/material disposal
- [`demo/src/detail/surfaceKit.ts`](../../../demo/src/detail/surfaceKit.ts)의 deterministic surface cache

남은 문제:

- generated/demo code가 저장소 상대 JSON import에 결합되어 있다.
- `createKnightForm(blueprint, options)`는 blueprint의 seed와 quality mode 외 구조를 사용하지 않는다.
- Vite/esbuild build는 TypeScript typecheck를 대신하지 않는다.
- 브라우저 런타임 오류와 console error를 자동으로 잡지 않는다.
- texture, render target, surface library의 ownership과 disposal이 통합되지 않았다.
- Python install metadata가 없어 실행 위치와 패키지 데이터 경로가 취약하다.
- 생성 산출물의 UTF-8 검증과 replacement-character gate가 없다.

## 1. Factory 계약

Blueprint를 source of truth로 유지하기 위해 factory를 다음 형태로 정리한다.

```ts
export interface FormRuntime {
  group: THREE.Group;
  nodes: Record<string, THREE.Object3D>;
  handles: FormHandles;
  dispose(): void;
}

export function createSubjectForm(
  blueprint: ValidatedFormBlueprint,
  options?: CreateFormOptions,
): FormRuntime;
```

하위 호환이 필요하면 `createSubjectGroup()` wrapper가 `runtime.group`을 반환하게 한다. 새 production path는 `dispose()`가 있는 runtime을 사용한다.

### Blueprint 사용 보장

contract test는 다음 Blueprint patch가 render/runtime에 실제 반영되는지 확인한다.

- part transform
- geometry parameter
- material baseColor/roughness/metalness
- pose joint
- attachment socket
- quality/detail level

인자만 받고 무시하는 API는 금지한다.

## 2. Portable output bundle

기존 단일 `--out file.ts`는 simple/legacy path로 유지한다. advanced output은 directory bundle을 생성한다.

```text
generated/subject-form/
├─ create-subject-form.ts
├─ blueprint.ts
├─ contracts.ts
├─ geometry-builders.ts
├─ surface-presets.ts
├─ resources.ts
└─ manifest.json
```

규칙:

- Three.js 외에는 저장소 바깥 상대 import가 없다.
- JSON preset은 generated TypeScript constant로 변환하거나 bundle 내부에 복사한다.
- manifest는 emitter version, source hashes, required Three.js range를 기록한다.
- 파일 이름과 import는 kebab-case/canonical path를 사용한다.
- 동일 Blueprint와 emitter version은 byte-stable output을 목표로 한다.

## 3. Geometry 호출의 타입 안전성

실행 중 helper 인자 위치가 밀려 `parent.add is not a function`이 발생했다. JavaScript의 인자 수 허용과 Vite transpile만으로는 막을 수 없다.

대책:

- 위치 인자 대신 named object parameter를 사용한다.
- `parent`, `geometry`, `material`, `name`, `transform`을 구조체로 분리한다.
- `strict: true`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`를 단계적으로 적용한다.
- geometry kind별 discriminated union을 사용한다.
- runtime에서 외부 JSON을 받을 때 schema validation을 다시 수행한다.

예시:

```ts
addMesh({
  parent: torso,
  geometry: { kind: "shape-extrude", points, depth: 0.08 },
  material: materials.steel,
  name: "breastplate",
  transform: { position: [0, 0.1, 0.12] },
});
```

## 4. Demo와 CI 검증 명령

[`demo/package.json`](../../../demo/package.json)에 다음 script를 추가한다.

```json
{
  "scripts": {
    "typecheck": "tsc --noEmit",
    "build": "vite build",
    "test:runtime": "playwright test",
    "check": "npm run typecheck && npm run build && npm run test:runtime"
  }
}
```

`tsconfig.json`과 최소 Playwright config를 추가한다. runtime smoke는 다음을 확인한다.

- page load 완료
- console error와 pageerror 0개
- `formHandles`와 required node 존재
- WebGL context 생성
- 한 장의 deterministic smoke screenshot
- teardown 후 renderer memory가 계속 증가하지 않음

브라우저가 WebGL을 제공하지 않는 CI에서는 명확한 skip reason을 남기고 별도 software-rendered job을 둔다. silent skip은 허용하지 않는다.

## 5. Python 패키징과 실행 위치

`python -m engine`은 저장소 root에서는 작동하지만 설치·복사 환경 계약이 없다.

계획:

- `pyproject.toml` 추가
- console script `gpthreejs = engine.cli:main`
- `engine.cast.surface/presets.json` package data 포함
- Python 3.10+와 optional CPU extras 명시
- source checkout, editable install, wheel install 세 경로의 smoke test
- subprocess test는 working directory를 바꿔도 명령이 동작하는지 확인

기존 `python -m engine`은 계속 지원한다.

## 6. Resource ownership

현재 `RuntimeResources.disposeObject()`는 mesh geometry/material을 해제하지만 material이 가진 texture, SurfaceLibrary cache, render target 중복 ownership을 완전히 처리하지 않는다.

대책:

- 생성한 geometry/material/texture/render target을 identity set으로 추적한다.
- shared resource는 한 번만 dispose한다.
- `FormRuntime.dispose()`가 form 소유 자원을 해제한다.
- harness가 scene/camera/controls/renderer/render targets를 해제한다.
- material traversal 시 map, normalMap, roughnessMap, aoMap 등 texture channel을 처리한다.
- iteration E2E에서 `renderer.info.memory`를 기록한다.

## 7. UTF-8와 산출물 정합성

생성 파일은 UTF-8 without BOM으로 고정한다.

검사:

- `U+FFFD` replacement character
- 의도하지 않은 `???` 또는 mojibake pattern
- JSON/TS/Markdown decode round-trip
- Windows/Unix line ending 차이가 content hash를 흔들지 않도록 canonical hashing에서 newline normalization
- CLI `userMessage` locale은 template 파일과 snapshot test로 관리

생성 주석은 품질에 영향을 주지 않으므로 문제가 반복되면 ASCII/English comments로 제한할 수 있다. 사용자 메시지 locale은 보존한다.

## 8. Surface preset과 preview 품질

현재 단일 JSON source는 유지한다. 문제는 공유 source가 아니라 소비 경로다.

- Python은 package resources로 읽는다.
- TypeScript runtime은 build 시 생성된 local module을 읽는다.
- generated bundle은 해당 module을 포함한다.
- detail level과 review profile 차이를 manifest에 기록한다.
- demo에서 임의로 low detail로 낮춰 품질 문제를 숨기지 않는다.

## 9. Bundle size

500 kB Vite warning은 현재 품질 고도화의 P0 blocker가 아니다. 다음 조건에서만 release gate로 승격한다.

- ChatGPT widget 초기 로드 예산을 넘음
- capture worker startup을 지연시킴
- Three.js examples import가 불필요하게 전체 번들에 포함됨

그 전에는 warning을 기록하고, runtime/capture가 분리된 후 chunk split을 적용한다.

## 10. SKILL.md와 playbook

`skill-creator` 기준을 반영해 core workflow는 [`SKILL.md`](../../../SKILL.md)에 간결하게 유지하고 상세 규칙은 playbook으로 분리한다.

계획:

- frontmatter를 `name`, `description`만 남기는 형식으로 정리한다.
- `agents/openai.yaml`을 추가하거나 현재 metadata 정책과 맞게 생성한다.
- character profile, readability, canonical review 상세는 새 playbook으로 이동한다.
- `SKILL.md`는 어떤 입력에서 어떤 playbook을 읽을지 명시한다.
- 수정 후 `quick_validate.py`를 실행한다.
- 기사와 비기사 fixture로 독립 forward test를 한다.

## 11. 구현 순서

1. DX-101: tsconfig와 strict typecheck
2. DX-110: runtime browser smoke
3. DX-120: named geometry helper arguments
4. DX-201: local preset module과 portable bundle
5. DX-210: temporary consumer project build test
6. DX-220: pyproject/wheel/package-data test
7. DX-301: UTF-8/replacement-character gate
8. RES-101: FormRuntime과 통합 disposal
9. DX-401: SKILL/playbook progressive disclosure와 validation
10. PERF-201: 실제 예산이 정해진 뒤 chunk split

## 12. 테스트

### TypeScript

- helper 인자 누락/순서 오류가 compile-time failure다.
- unknown geometry union member는 compile-time 또는 schema error다.
- Blueprint patch가 runtime node/material에 반영된다.
- dispose를 두 번 호출해도 예외가 없다.

### Portability

- 임시 디렉터리에 fresh Vite consumer를 만든다.
- generated bundle과 Three.js dependency만 복사한다.
- typecheck, build, browser smoke를 실행한다.
- 저장소 경로 문자열이 generated output에 없음을 검사한다.

### Python

- repo root 밖에서 wheel 설치 후 `gpthreejs --help` 실행
- package data에서 preset JSON 로드
- `python -m engine` 기존 smoke 유지

### Failure modes

| 실패 | 테스트 | 처리 | 사용자 가시성 |
| --- | --- | --- | --- |
| preset 누락 | package-data fixture | startup/cast 실패 | missing resource path |
| helper signature drift | type fixture | CI typecheck 실패 | compiler diagnostic |
| browser runtime exception | Playwright pageerror | smoke 실패 | console artifact/screenshot |
| texture leak | repeated create/dispose | release gate 실패 | memory counters |
| encoding corruption | generated fixture scan | emission 실패 | offending file/offset |

## 완료 기준

- `npm run check`가 typecheck, build, runtime smoke를 모두 실행한다.
- generated bundle이 임시 독립 프로젝트에서 동작한다.
- `parent.add is not a function` 계열 오류가 type/runtime test로 재현되고 차단된다.
- Python wheel과 package data가 working directory에 무관하게 동작한다.
- 모든 생성 산출물이 UTF-8 gate를 통과한다.
- form 생성/폐기 반복에서 resource count가 지속 증가하지 않는다.
