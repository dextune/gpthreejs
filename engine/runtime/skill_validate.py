"""SKILL folder validation (DX-410)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def validate_skill_folder(skill_dir: str | Path) -> dict[str, Any]:
    root = Path(skill_dir)
    errors: list[str] = []
    warnings: list[str] = []
    if not root.exists():
        return {"ok": False, "errors": [f"skill folder missing: {root}"], "warnings": []}

    skill_md = root / "SKILL.md"
    if not skill_md.exists():
        errors.append("SKILL.md missing")
    else:
        text = skill_md.read_text(encoding="utf-8")
        lines = text.splitlines()
        if not text.startswith("---"):
            errors.append("SKILL.md missing YAML frontmatter")
        else:
            # frontmatter closed?
            if text.count("---") < 2:
                errors.append("SKILL.md frontmatter not closed")
        if len(lines) > 500:
            errors.append(f"SKILL.md has {len(lines)} lines; limit is 500")
        if "gpthreejs" not in text.lower() and "workflow" not in text.lower():
            warnings.append("SKILL.md may lack core workflow keywords")

    # playbooks optional but if present should not fully duplicate SKILL
    playbooks = list(root.glob("**/playbook*.md")) + list(root.glob("**/*playbook*.md"))
    for playbook in playbooks:
        ptext = playbook.read_text(encoding="utf-8")
        if skill_md.exists():
            skill_text = skill_md.read_text(encoding="utf-8")
            # crude duplication: >60% of playbook lines appear in skill
            plines = [ln.strip() for ln in ptext.splitlines() if ln.strip()]
            if plines:
                overlap = sum(1 for ln in plines if ln in skill_text) / len(plines)
                if overlap > 0.6 and len(plines) > 20:
                    warnings.append(f"{playbook.name}: high duplication with SKILL.md")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "skillPath": str(skill_md if skill_md.exists() else root),
        "lineCount": len(skill_md.read_text(encoding="utf-8").splitlines()) if skill_md.exists() else 0,
    }


def quick_validate(skill_dir: str | Path) -> int:
    report = validate_skill_folder(skill_dir)
    if report["ok"]:
        print(f"skill validation success: {report['skillPath']} ({report['lineCount']} lines)")
        return 0
    for err in report["errors"]:
        print(f"error: {err}")
    return 2
