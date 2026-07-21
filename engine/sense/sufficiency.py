"""
Image & specification sufficiency gate.

Reports when a reference (and optional sense pack / brief / ledger / blueprint)
lacks enough information for a reliable gpthreejs cast — with codes, severity,
remedies, and a recommended agent action (continue | ask | abort).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.shared.jsonutil import dump_json, load_json
from engine.shared.pngio import read_png
from engine.sense.probe import probe_image


# ── thresholds (tunable) ──────────────────────────────────────────────
MIN_SHORT_SIDE = 256
MIN_SHORT_SIDE_SHARP = 512
MIN_MEGAPIXELS = 0.05
MIN_MEGAPIXELS_SHARP = 0.15
MIN_FOREGROUND_RATIO = 0.04
MAX_FOREGROUND_RATIO = 0.97
IDEAL_FOREGROUND = (0.12, 0.85)
VERY_DARK = 28
VERY_BRIGHT = 235
MIN_EDGE_DENSITY = 0.008
MAX_EDGE_DENSITY = 0.55
MIN_LEDGER_FILLED_FRAC = 0.5  # of targetMin


Severity = str  # blocker | major | minor | info


def _issue(
    code: str,
    severity: Severity,
    message: str,
    remedy: str,
    *,
    field: str | None = None,
    evidence: Any = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "code": code,
        "severity": severity,
        "message": message,
        "remedy": remedy,
    }
    if field:
        out["field"] = field
    if evidence is not None:
        out["evidence"] = evidence
    return out


def _load_optional(path: str | Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    try:
        data = load_json(p)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def assess_image_file(image_path: str | Path) -> tuple[list[dict], dict]:
    """Technical file / raster checks."""
    issues: list[dict] = []
    probe = probe_image(image_path)
    meta: dict[str, Any] = {"probe": probe}

    if probe.get("error") == "missing" or not probe.get("exists"):
        issues.append(
            _issue(
                "FILE_MISSING",
                "blocker",
                "이미지 파일이 없거나 경로를 읽을 수 없습니다.",
                "유효한 이미지 경로를 제공하세요.",
                field="image",
                evidence=probe.get("path"),
            )
        )
        return issues, meta

    if probe.get("error"):
        issues.append(
            _issue(
                "FILE_UNREADABLE",
                "blocker",
                f"이미지를 디코드하지 못했습니다: {probe.get('error')}",
                "손상되지 않은 PNG로 다시 저장하거나 변환하세요.",
                field="image",
            )
        )
        return issues, meta

    suffix = str(probe.get("suffix") or "").lower()
    if suffix and suffix not in (".png", ".jpg", ".jpeg", ".webp"):
        issues.append(
            _issue(
                "FORMAT_UNUSUAL",
                "major",
                f"엔진 Sense Pack은 PNG를 기준으로 합니다 (현재: {suffix}).",
                "PNG로 변환한 뒤 `engine sense`를 실행하세요.",
                field="format",
                evidence=suffix,
            )
        )
    elif suffix in (".jpg", ".jpeg", ".webp"):
        issues.append(
            _issue(
                "FORMAT_CONVERT",
                "minor",
                "JPEG/WebP는 메타 프로브만 가능하고 Sense 맵 생성 전 PNG 변환이 필요합니다.",
                "`convert` 또는 PIL로 PNG 저장 후 sense를 돌리세요.",
                field="format",
            )
        )

    w = probe.get("width")
    h = probe.get("height")
    if w and h:
        short = min(int(w), int(h))
        mp = float(probe.get("megapixels") or (w * h / 1e6))
        meta["shortSide"] = short
        meta["megapixels"] = mp
        if short < MIN_SHORT_SIDE:
            issues.append(
                _issue(
                    "RES_TOO_LOW",
                    "blocker",
                    f"해상도가 너무 낮습니다 (짧은 변 {short}px < {MIN_SHORT_SIDE}px).",
                    "최소 짧은 변 256px 이상, sharp 모드면 512px+ 권장 이미지를 주세요.",
                    field="resolution",
                    evidence={"width": w, "height": h},
                )
            )
        elif short < MIN_SHORT_SIDE_SHARP:
            issues.append(
                _issue(
                    "RES_MARGINAL",
                    "major",
                    f"해상도가 아슬아슬합니다 (짧은 변 {short}px). sharp/razor 품질에 부족할 수 있습니다.",
                    f"짧은 변 {MIN_SHORT_SIDE_SHARP}px 이상으로 재촬영/업스케일(선명 원본 권장)하세요.",
                    field="resolution",
                    evidence={"width": w, "height": h},
                )
            )
        if mp < MIN_MEGAPIXELS:
            issues.append(
                _issue(
                    "MP_TOO_LOW",
                    "blocker",
                    f"총 화소 수가 너무 적습니다 ({mp} MP).",
                    "더 큰 이미지를 제공하세요.",
                    field="resolution",
                )
            )
        elif mp < MIN_MEGAPIXELS_SHARP:
            issues.append(
                _issue(
                    "MP_MARGINAL",
                    "minor",
                    f"화소 수가 다소 적습니다 ({mp} MP).",
                    "디테일 재구성이 필요하면 더 큰 원본을 사용하세요.",
                    field="resolution",
                )
            )

        aspect = float(probe.get("aspect") or (w / max(1, h)))
        if aspect > 3.5 or aspect < 0.28:
            issues.append(
                _issue(
                    "ASPECT_EXTREME",
                    "major",
                    f"종횡비가 극단적입니다 (aspect={aspect:.2f}). 피사체가 잘리거나 작을 수 있습니다.",
                    "전신이 들어오도록 크롭하거나 정면에 가깝게 다시 구도하세요.",
                    field="composition",
                    evidence={"aspect": aspect},
                )
            )

    flags = list(probe.get("flags") or [])
    luma = probe.get("mean_luma_approx")
    if luma is not None:
        if luma < VERY_DARK or "very-dark" in flags:
            issues.append(
                _issue(
                    "EXPOSURE_DARK",
                    "major",
                    f"이미지가 매우 어둡습니다 (평균 휘도 ≈ {luma}).",
                    "노출을 올린 사진 또는 라이팅이 있는 참조를 제공하세요.",
                    field="exposure",
                    evidence={"meanLuma": luma},
                )
            )
        elif luma > VERY_BRIGHT or "very-bright" in flags:
            issues.append(
                _issue(
                    "EXPOSURE_BRIGHT",
                    "major",
                    f"이미지가 과노출에 가깝습니다 (평균 휘도 ≈ {luma}).",
                    "하이라이트가 날아가지 않은 참조를 제공하세요.",
                    field="exposure",
                    evidence={"meanLuma": luma},
                )
            )

    return issues, meta


def assess_sense_pack(sense: dict[str, Any] | None) -> tuple[list[dict], dict]:
    """Checks that need a Sense Pack (matte / edges)."""
    issues: list[dict] = []
    meta: dict[str, Any] = {}
    if not sense:
        issues.append(
            _issue(
                "SENSE_MISSING",
                "info",
                "Sense Pack이 없어 실루엣/엣지 기반  sufficiency를 건너뜁니다.",
                "`python3 -m engine sense <img> --out work/sense --mode sharp` 실행을 권장합니다.",
                field="sense",
            )
        )
        return issues, meta

    maps = sense.get("maps") or {}
    matte = maps.get("matte") or {}
    edges = maps.get("edges") or {}
    fg = matte.get("foreground_ratio")
    edge_d = edges.get("edge_density")
    bbox = matte.get("bbox")
    meta["foregroundRatio"] = fg
    meta["edgeDensity"] = edge_d
    meta["bbox"] = bbox

    if fg is not None:
        fg = float(fg)
        if fg < MIN_FOREGROUND_RATIO:
            issues.append(
                _issue(
                    "SUBJECT_TOO_SMALL",
                    "blocker",
                    f"전경 피사체가 프레임에서 너무 작습니다 (foreground≈{fg:.1%}).",
                    "피사체를 크게 크롭한 이미지를 주세요. 단색 배경이 유리합니다.",
                    field="composition",
                    evidence={"foregroundRatio": fg},
                )
            )
        elif fg < IDEAL_FOREGROUND[0]:
            issues.append(
                _issue(
                    "SUBJECT_SMALL",
                    "major",
                    f"전경 비율이 낮습니다 (foreground≈{fg:.1%}). 실루엣 잠금이 불안정할 수 있습니다.",
                    "피사체 중심 크롭 또는 배경 단순화를 권장합니다.",
                    field="composition",
                    evidence={"foregroundRatio": fg},
                )
            )
        elif fg > MAX_FOREGROUND_RATIO:
            issues.append(
                _issue(
                    "SUBJECT_FILLS_FRAME",
                    "major",
                    f"전경이 프레임 거의 전체입니다 (foreground≈{fg:.1%}). 실루엣/매트가 불안정할 수 있습니다.",
                    "피사체 주변에 여백이 있는 컷, 또는 깨끗한 알파/누끼를 제공하세요.",
                    field="composition",
                    evidence={"foregroundRatio": fg},
                )
            )

    if edge_d is not None:
        edge_d = float(edge_d)
        if edge_d < MIN_EDGE_DENSITY:
            issues.append(
                _issue(
                    "EDGE_TOO_FEW",
                    "major",
                    f"윤곽/디테일 엣지가 거의 없습니다 (edgeDensity≈{edge_d:.4f}). 형태 정보가 부족할 수 있습니다.",
                    "형태가 분명한 오브젝트 사진, 또는 더 높은 대비의 참조를 사용하세요. 텍스처 스와치만 있는 이미지는 부적합합니다.",
                    field="structure",
                    evidence={"edgeDensity": edge_d},
                )
            )
        elif edge_d > MAX_EDGE_DENSITY:
            issues.append(
                _issue(
                    "EDGE_TOO_BUSY",
                    "minor",
                    f"엣지가 매우 많습니다 (edgeDensity≈{edge_d:.4f}). 배경 잡음이거나 과한 패턴일 수 있습니다.",
                    "단색 배경으로 크롭하거나, 에이전트가 피사체 ROI만 쓰도록 지정하세요.",
                    field="composition",
                    evidence={"edgeDensity": edge_d},
                )
            )

    method = matte.get("method")
    if method == "corner-distance":
        issues.append(
            _issue(
                "MATTE_HEURISTIC",
                "info",
                "전경 매트가 휴리스틱(모서리 배경 추정)입니다. 복잡 배경에서는 부정확할 수 있습니다.",
                "단색 배경 촬영 또는 rembg 등 품질 높은 누끼를 사용하세요.",
                field="sense",
                evidence={"matteMethod": method},
            )
        )

    return issues, meta


def assess_intent_and_views(
    *,
    domain: str | None,
    intent: str | None,
    view_count: int,
    has_side: bool,
    has_back: bool,
) -> list[dict]:
    issues: list[dict] = []
    domain = (domain or "object").lower()
    intent = (intent or "realtime-prop").lower()

    if domain in ("character", "hybrid") and view_count < 2:
        issues.append(
            _issue(
                "CHAR_SINGLE_VIEW",
                "major",
                "캐릭터/하이브리드인데 참조가 사실상 단일 뷰입니다. 옆·뒷면 비율·부피가 불확실합니다.",
                "정면 + 측면(필수 권장) 턴어라운드를 추가하세요. 없으면 스타일화·대칭 추정으로만 진행하고 confidence를 낮춥니다.",
                field="views",
                evidence={"viewCount": view_count, "domain": domain},
            )
        )
    if domain in ("character", "hybrid") and not has_side:
        issues.append(
            _issue(
                "CHAR_NO_SIDE",
                "major",
                "캐릭터 측면 참조가 없습니다. 두께·헬멧·코 돌출 등이 규격 불충분입니다.",
                "`side` 또는 orthographic side 이미지를 추가하세요.",
                field="views",
            )
        )
    if intent in ("game", "playable", "animation", "rig") and view_count < 2:
        issues.append(
            _issue(
                "GAME_VIEWS_THIN",
                "minor",
                "게임/애니메이션 용도인데 멀티뷰가 부족합니다. 리그·실루엣 검증이 약해집니다.",
                "정면/측면 최소 2장, 가능하면 후면까지 제공하세요.",
                field="views",
            )
        )
    if intent in ("hero", "hero-render", "likeness", "maximum-likeness") and not (has_side and view_count >= 2):
        issues.append(
            _issue(
                "LIKENESS_VIEWS",
                "major",
                "높은 닮음/히어로 품질 요청 대비 뷰 정보가 부족합니다.",
                "정면·측면·(가능하면) 후면 및 디테일 크롭을 추가하세요. 한 장으로는 100% 닮음을 약속할 수 없습니다.",
                field="views",
            )
        )
    return issues


def assess_spec(
    *,
    brief: dict | None,
    ledger: dict | None,
    blueprint: dict | None,
    domain: str | None,
) -> list[dict]:
    """Specification completeness (when artifacts exist)."""
    issues: list[dict] = []
    domain = (domain or (brief or {}).get("domain") or (blueprint or {}).get("domain") or "object").lower()

    if brief is None and blueprint is None and ledger is None:
        return issues

    if brief is not None:
        if not brief.get("fidelityPact"):
            issues.append(
                _issue(
                    "BRIEF_NO_PACT",
                    "major",
                    "Intake Brief에 Fidelity Pact가 없습니다.",
                    "`engine brief`로 재생성하거나 fidelityPact 블록을 채우세요.",
                    field="brief",
                )
            )
        if not brief.get("complexity"):
            issues.append(
                _issue(
                    "BRIEF_NO_COMPLEXITY",
                    "minor",
                    "complexity가 비어 있습니다. Ledger 최소 개수 규격이 모호합니다.",
                    "simple|moderate|complex|ultra 중 하나를 지정하세요.",
                    field="brief",
                )
            )

    if ledger is not None:
        entries = ledger.get("entries") or []
        todos = [e for e in entries if e.get("status") == "todo"]
        filled = [e for e in entries if e.get("status") != "todo"]
        target = int(ledger.get("targetMin") or 0)
        unmapped = [e for e in filled if not e.get("mapsTo")]
        if todos and len(todos) == len(entries):
            issues.append(
                _issue(
                    "LEDGER_ALL_TODO",
                    "blocker",
                    "Feature Ledger가 전부 todo 상태입니다. 규격(디테일 인벤토리)이 비어 있습니다.",
                    "존별로 실제 디테일을 채우고 status=filled, mapsTo를 연결하세요.",
                    field="ledger",
                    evidence={"todo": len(todos)},
                )
            )
        elif target and len(filled) < max(1, int(target * MIN_LEDGER_FILLED_FRAC)):
            issues.append(
                _issue(
                    "LEDGER_SPARSE",
                    "major",
                    f"채워진 Ledger 항목이 목표 대비 부족합니다 (filled={len(filled)}, targetMin={target}).",
                    f"최소 약 {max(1, int(target * MIN_LEDGER_FILLED_FRAC))}개 이상 identity 디테일을 기입하세요.",
                    field="ledger",
                    evidence={"filled": len(filled), "targetMin": target},
                )
            )
        if unmapped:
            issues.append(
                _issue(
                    "LEDGER_UNMAPPED",
                    "major",
                    f"mapsTo가 없는 Ledger 항목이 {len(unmapped)}개 있습니다. 구현 규격으로 연결되지 않았습니다.",
                    "각 항목을 component feature 또는 material override id에 연결하세요.",
                    field="ledger",
                )
            )

    if blueprint is not None:
        parts = blueprint.get("parts") or []
        if not parts:
            issues.append(
                _issue(
                    "BP_NO_PARTS",
                    "blocker",
                    "Form Blueprint에 parts가 없습니다.",
                    "부품 트리를 작성한 뒤 validate하세요.",
                    field="blueprint",
                )
            )
        mats = blueprint.get("materials") or []
        if not mats:
            issues.append(
                _issue(
                    "BP_NO_MATERIALS",
                    "blocker",
                    "materials가 비어 있습니다.",
                    "최소 1개 이상의 PBR 머티리얼을 정의하세요.",
                    field="blueprint",
                )
            )
        if domain in ("character", "hybrid"):
            anatomy = blueprint.get("anatomy") or (blueprint.get("preSpec") or {})
            # also check nested
            if not blueprint.get("anatomy"):
                issues.append(
                    _issue(
                        "BP_NO_ANATOMY",
                        "major",
                        "character/hybrid 인데 anatomy(비율·랜드마크) 블록이 없습니다.",
                        "head-units, proportions, pose/landmarks를 채우세요. 없으면 측면 뷰를 요청하세요.",
                        field="blueprint",
                    )
                )
        complexity = str(blueprint.get("complexity") or "").lower()
        if complexity in ("complex", "ultra") and len(parts) < 2:
            issues.append(
                _issue(
                    "BP_SHALLOW_TREE",
                    "major",
                    "complexity가 높은데 부품 트리가 너무 얕습니다.",
                    "주요 서브파트를 분리해 parts 계층을 깊게 만드세요.",
                    field="blueprint",
                )
            )
        ss = blueprint.get("surfaceStack")
        if not ss and str(blueprint.get("qualityMode") or "") in ("sharp", "razor", "hybrid"):
            issues.append(
                _issue(
                    "BP_NO_SURFACE",
                    "minor",
                    "고품질 모드인데 surfaceStack이 없습니다.",
                    "`engine surface-annotate`를 실행하세요.",
                    field="blueprint",
                )
            )

    return issues


def _verdict_and_action(issues: list[dict]) -> tuple[str, str, bool]:
    """→ verdict, agentAction, sufficient."""
    sevs = {i["severity"] for i in issues}
    if "blocker" in sevs:
        return "reject", "abort", False
    majors = [i for i in issues if i["severity"] == "major"]
    if len(majors) >= 2:
        return "conditional", "ask", False
    if majors:
        return "conditional", "ask", False
    if issues:
        return "conditional", "continue", True  # only minor/info
    return "pass", "continue", True


def _user_message(
    verdict: str,
    issues: list[dict],
    *,
    domain: str,
    image: str,
) -> str:
    lines = [
        f"[gpthreejs sufficiency] verdict={verdict} · domain={domain}",
        f"image: {image}",
        "",
    ]
    if verdict == "pass":
        lines.append("제공된 이미지/규격으로 파이프라인을 진행할 수 있습니다.")
        return "\n".join(lines)

    lines.append("정보 또는 규격이 부족하거나 위험합니다. 아래를 확인하세요:")
    lines.append("")
    for i, iss in enumerate(issues, 1):
        if iss["severity"] == "info" and verdict != "reject":
            continue
        lines.append(f"{i}. [{iss['severity'].upper()}] {iss['code']}: {iss['message']}")
        lines.append(f"   → 조치: {iss['remedy']}")
    blockers = [i for i in issues if i["severity"] == "blocker"]
    majors = [i for i in issues if i["severity"] == "major"]
    lines.append("")
    if blockers:
        lines.append("권장 에이전트 행동: abort 또는 ask — blocker를 해소하기 전에는 cast를 시작하지 마세요.")
    elif majors:
        lines.append("권장 에이전트 행동: ask — 사용자에게 추가 이미지/규격을 요청한 뒤 조건부 진행하세요.")
    else:
        lines.append("권장 에이전트 행동: continue — minor 이슈는 기록하고 진행 가능합니다.")
    return "\n".join(lines)


def assess_sufficiency(
    image: str | Path,
    *,
    sense_path: str | Path | None = None,
    brief_path: str | Path | None = None,
    ledger_path: str | Path | None = None,
    blueprint_path: str | Path | None = None,
    domain: str | None = None,
    intent: str | None = None,
    view_count: int = 1,
    has_side: bool = False,
    has_back: bool = False,
    out: str | Path | None = None,
) -> dict[str, Any]:
    """
    Full sufficiency report.

    agentAction:
      - continue: proceed (maybe with notes)
      - ask: request more views / cleaner input / fill ledger
      - abort: not feasible with current inputs
    """
    issues, img_meta = assess_image_file(image)

    sense = _load_optional(sense_path)
    # also accept directory containing sense_pack.json
    if sense is None and sense_path:
        sp = Path(sense_path)
        if sp.is_dir() and (sp / "sense_pack.json").exists():
            sense = load_json(sp / "sense_pack.json")

    sense_issues, sense_meta = assess_sense_pack(sense)
    issues.extend(sense_issues)

    brief = _load_optional(brief_path)
    ledger = _load_optional(ledger_path)
    blueprint = _load_optional(blueprint_path)

    dom = domain or (brief or {}).get("domain") or (blueprint or {}).get("domain") or "object"
    intent_v = intent or (brief or {}).get("intent") or "realtime-prop"

    issues.extend(
        assess_intent_and_views(
            domain=str(dom),
            intent=str(intent_v),
            view_count=view_count,
            has_side=has_side,
            has_back=has_back,
        )
    )
    issues.extend(
        assess_spec(
            brief=brief,
            ledger=ledger,
            blueprint=blueprint,
            domain=str(dom),
        )
    )

    verdict, action, sufficient = _verdict_and_action(issues)
    # If only SENSE_MISSING info and image ok → still pass-ish
    non_info = [i for i in issues if i["severity"] != "info"]
    if not non_info and verdict == "conditional":
        verdict, action, sufficient = "pass", "continue", True

    score = 1.0
    for i in issues:
        score -= {"blocker": 0.45, "major": 0.18, "minor": 0.06, "info": 0.02}.get(i["severity"], 0.05)
    score = round(max(0.0, min(1.0, score)), 3)

    report: dict[str, Any] = {
        "version": 1,
        "verdict": verdict,  # pass | conditional | reject
        "sufficient": sufficient,
        "score": score,
        "agentAction": action,  # continue | ask | abort
        "domain": dom,
        "intent": intent_v,
        "image": str(Path(image).resolve()) if Path(image).exists() else str(image),
        "issues": issues,
        "summary": {
            "blockers": sum(1 for i in issues if i["severity"] == "blocker"),
            "majors": sum(1 for i in issues if i["severity"] == "major"),
            "minors": sum(1 for i in issues if i["severity"] == "minor"),
            "infos": sum(1 for i in issues if i["severity"] == "info"),
        },
        "evidence": {
            "image": img_meta,
            "sense": sense_meta,
            "viewCount": view_count,
            "hasSide": has_side,
            "hasBack": has_back,
            "artifacts": {
                "sense": bool(sense),
                "brief": brief is not None,
                "ledger": ledger is not None,
                "blueprint": blueprint is not None,
            },
        },
        "userMessage": _user_message(verdict, issues, domain=str(dom), image=str(image)),
        "nextSteps": _next_steps(action, issues),
    }

    if out:
        dump_json(out, report)
    return report


def _next_steps(action: str, issues: list[dict]) -> list[str]:
    steps: list[str] = []
    codes = {i["code"] for i in issues}
    if action == "abort":
        steps.append("Stop cast/codegen until blockers are resolved.")
    if action == "ask":
        steps.append("Call request-input / ask the user with userMessage remedies.")
    if "FORMAT_CONVERT" in codes or "FORMAT_UNUSUAL" in codes:
        steps.append("Convert reference to PNG.")
    if "SENSE_MISSING" in codes:
        steps.append("Run: python3 -m engine sense <image> --out work/sense --mode sharp")
    if "LEDGER_ALL_TODO" in codes or "LEDGER_SPARSE" in codes:
        steps.append("Fill Feature Ledger before --strict validate.")
    if "CHAR_SINGLE_VIEW" in codes or "CHAR_NO_SIDE" in codes:
        steps.append("Request side (and optionally back) turnaround images.")
    if "RES_TOO_LOW" in codes or "RES_MARGINAL" in codes:
        steps.append("Request higher-resolution source.")
    if action == "continue" and not steps:
        steps.append("Proceed to brief/ledger/blueprint or next open cast layer.")
    return steps
