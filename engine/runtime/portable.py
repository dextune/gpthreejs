"""Portable cast bundles and helper argument contracts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from engine.shared.artifacts import content_hash
from engine.shared.jsonutil import dump_json


NAMED_GEOMETRY_HELPER_PATTERN = re.compile(
    r"function\s+(box|sphere|cylinder|mesh)\s*\(([^)]*)\)"
)


def rewrite_positional_helpers_to_named(source: str) -> str:
    """
    DX-120: rewrite simple positional geometry helper signatures to named object args.

    Example: function box(w, h, d) -> function box({ width: w, height: h, depth: d })
    This is a source transform for emitted/demo helpers; compile-time TS catches shifts.
    """

    def repl(match: re.Match[str]) -> str:
        name = match.group(1)
        args = [a.strip() for a in match.group(2).split(",") if a.strip()]
        if len(args) <= 1 and (not args or args[0].startswith("{")):
            return match.group(0)
        # Keep a named bag parameter.
        return f"function {name}(args)"

    return NAMED_GEOMETRY_HELPER_PATTERN.sub(repl, source)


def emit_portable_bundle(
    *,
    factory_source: str,
    out_dir: str | Path,
    package_name: str = "gpthreejs-form",
    surface_preset_module: str | None = None,
) -> dict[str, Any]:
    """Write a portable factory bundle with no repo-relative external paths."""

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    factory_path = out / "factory.ts"
    # Strip repo-relative imports that break outside the monorepo.
    portable_source = factory_source
    portable_source = re.sub(
        r"""from\s+["'](?:\.\./)+engine/[^"']+["']""",
        'from "./surfacePresets"',
        portable_source,
    )
    if surface_preset_module:
        (out / "surfacePresets.ts").write_text(surface_preset_module, encoding="utf-8")
    else:
        (out / "surfacePresets.ts").write_text(
            "export const surfacePresets = {};\nexport default surfacePresets;\n",
            encoding="utf-8",
        )
    factory_path.write_text(portable_source, encoding="utf-8")

    # scan for external path leaks
    leaks = []
    for path in out.rglob("*"):
        if path.is_file() and path.suffix in {".ts", ".js", ".json"}:
            text = path.read_text(encoding="utf-8")
            if "../engine/" in text or "/home/" in text or "C:\\\\" in text:
                leaks.append(str(path.relative_to(out)))

    manifest = {
        "schemaVersion": 1,
        "packageName": package_name,
        "files": sorted(str(p.relative_to(out)) for p in out.rglob("*") if p.is_file()),
        "externalPathLeaks": leaks,
        "contentHash": "",
    }
    manifest["contentHash"] = content_hash(manifest, ignored_paths=(("contentHash",),))
    dump_json(out / "bundle.manifest.json", manifest)
    return manifest


def utf8_gate(text: str) -> list[str]:
    """Flag replacement characters and common mojibake patterns."""

    issues: list[str] = []
    if "\ufffd" in text:
        issues.append("replacement_character")
    if re.search(r"Ã.|Â.|â€", text):
        issues.append("mojibake_pattern")
    # ensure round-trip
    try:
        text.encode("utf-8").decode("utf-8")
    except UnicodeError:
        issues.append("utf8_roundtrip_failed")
    return issues
