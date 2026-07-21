"""Regression checks for the M0 knight quality baseline fixture."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.blueprint.validate import validate_blueprint

FIXTURE_ROOT = ROOT / "tests" / "golden" / "knight"
EXPECTED_V2_FAILURE_CODES = {
    "CHARACTER_PARTS_TOO_SHALLOW",
    "CHARACTER_MISSING_PROPORTION_MEASUREMENTS",
    "CHARACTER_MISSING_LANDMARKS",
    "CHARACTER_MISSING_SOCKET_CONTACTS",
    "CHARACTER_IDENTITY_GEOMETRY_NOT_SEPARATED",
    "CHARACTER_LAYERED_DETAIL_NOT_SEPARATED",
}
KNOWN_TASK_IDS = {
    "REF-110",
    "REF-111",
    "REF-120",
    "REF-130",
    "REF-131",
    "BP-111",
    "CHAR-101",
    "GEO-101",
    "GEO-102",
    "DX-101",
    "DX-110",
    "DX-201",
    "DX-210",
    "DX-220",
    "DX-301",
    "MAT-101",
    "MAT-110",
    "PERF-110",
    "PERF-120",
    "ATT-101",
    "ATT-110",
    "FIT-101",
    "FIT-110",
    "REV-110",
    "REV-120",
    "M0-010",
    "M0-011",
    "CI-101",
}
KNOWN_EVIDENCE_IDS = {
    "test:matte-confidence-report",
    "artifact:normalization-transform-manifest",
    "test:reference-set-view-coverage",
    "test:ledger-target-min-category-coverage",
    "fixture:v0-shallow-blueprint",
    "report:gate-a-b-failure",
    "test:strict-v2-character-depth-rejection",
    "test:unknown-geometry-hard-error",
    "preflight:typescript-typecheck",
    "test:browser-pageerror-smoke",
    "scan:no-repository-relative-import",
    "test:portable-bundle-consumer",
    "report:neutral-material-readability",
    "report:bundle-runtime-profile",
    "test:socket-contact-gap",
    "artifact:portable-ts-bundle",
    "test:wheel-install-smoke",
    "test:utf8-roundtrip",
    "test:production-run-excludes-proxy-fit",
    "test:render-loop-objective",
    "test:missing-evidence-fail-closed",
    "report:machine-backend-metadata",
    "report:repeated-baseline",
    "preflight:demo-dependency",
    "ci:clean-checkout",
}
ALLOWED_SOURCE_CLASSES = {
    "repo-local-sample",
    "tracked-generated-demo-source",
}
ALLOWED_EVIDENCE_CLASSES = {
    "repo-local-sample",
    "tracked-current-output",
}
EXPECTED_BASELINE_FINGERPRINT_FILES = [
    "tests/golden/knight/blueprints/v0-shallow.json",
    "tests/golden/knight/expected-contracts/v2-character-depth-failures.json",
    "tests/golden/knight/manifest.json",
    "tests/golden/knight/reports/obs-traceability.json",
    "tests/test_knight_m0_baseline.py",
]
EXPECTED_MISSING_EVIDENCE = {
    "canonical beauty render",
    "alpha render",
    "browser console/pageerror log",
}
EXPECTED_FINGERPRINT_ALGORITHM = (
    "sha256(sorted '<relative-path>  <file-sha256>' lines joined with '\\n' "
    "and one terminal '\\n')"
)
EXPECTED_FINGERPRINT_SCOPE_NOTE = (
    "Covers the tracked M0 baseline fixture and its validation test. "
    "This is an artifact-set checksum, not a full reconstruction of the dirty "
    "source state that produced the command baseline."
)
EXPECTED_GATE_FAILURE_CODES = {
    "gate-a-reference-and-comparison": {
        "SOURCE_ALIGNED_CAMERA_NOT_LOCKED",
        "LEFT_RIGHT_EQUIPMENT_MAPPING_UNVERIFIED",
    },
    "gate-b-mass-and-pose": {
        "CHARACTER_PARTS_TOO_SHALLOW",
        "MISSING_PROPORTION_MEASUREMENTS",
        "MISSING_LANDMARKS",
    },
    "gate-c-identity-geometry": {
        "IDENTITY_GEOMETRY_NOT_SEPARATED",
        "PART_ID_EVIDENCE_MISSING",
    },
    "gate-d-attachment": {
        "SOCKET_CONTACTS_MISSING",
        "ATTACHMENT_CHAIN_UNVERIFIED",
    },
    "gate-e-material-readability": {
        "MATERIAL_ROLE_COVERAGE_INCOMPLETE",
        "NEUTRAL_READABILITY_METRICS_MISSING",
    },
}
EXPECTED_GATE_OBSERVATIONS = {
    "gate-a-reference-and-comparison": {"OBS-04", "OBS-11"},
    "gate-b-mass-and-pose": {"OBS-04", "OBS-05"},
    "gate-c-identity-geometry": {"OBS-03", "OBS-05", "OBS-06"},
    "gate-d-attachment": {"OBS-11"},
    "gate-e-material-readability": {"OBS-09"},
}
EXPECTED_GATE_ORDER = [
    "gate-a-reference-and-comparison",
    "gate-b-mass-and-pose",
    "gate-c-identity-geometry",
    "gate-d-attachment",
    "gate-e-material-readability",
]
EXPECTED_CAPTURE_HARNESS_KEYS = {
    "schema",
    "artifactScope",
    "usage",
    "rendererVersion",
    "profileId",
    "viewport",
    "determinism",
}
EXPECTED_CAPTURE_DETERMINISM_KEYS = {
    "method",
    "command",
    "latestObservedResult",
    "freshnessPolicy",
}
FORBIDDEN_CAPTURE_EVIDENCE_KEYS = {
    "passes",
    "pass",
    "pixels",
    "pixelStats",
    "pixelHash",
    "readback",
    "readbackStats",
    "sameEnvironmentReadbackHash",
    "readbackHash",
    "stats",
    "foregroundPixels",
    "nonBackgroundPixels",
    "opaquePixels",
    "transparentPixels",
}
FORBIDDEN_V0_PIXEL_EVIDENCE_KEY_PATTERNS = (
    "pixels",
    "pixelstats",
    "beautyhash",
    "alphahash",
    "pixelhash",
    "readback",
    "readbackstats",
    "readbackhash",
    "sameenvironmentreadbackhash",
    "foregroundpixels",
    "nonbackgroundpixels",
    "opaquepixels",
    "transparentpixels",
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_state_fingerprint(paths: list[str]) -> str:
    lines = []
    for rel_path in sorted(paths):
        lines.append(f"{rel_path}  {_sha256(ROOT / rel_path)}")
    return hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()


def _git_tracks(path: str) -> bool:
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", path],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _contains_forbidden_key(value: object, forbidden: set[str]) -> bool:
    if isinstance(value, dict):
        return any(key in forbidden or _contains_forbidden_key(child, forbidden) for key, child in value.items())
    if isinstance(value, list):
        return any(_contains_forbidden_key(child, forbidden) for child in value)
    return False


def _find_forbidden_pixel_evidence(value: object, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            normalized = "".join(character for character in key.lower() if character.isalnum())
            if normalized in {"sha256", "hashkind"}:
                pass
            elif any(pattern in normalized for pattern in FORBIDDEN_V0_PIXEL_EVIDENCE_KEY_PATTERNS):
                found.append(child_path)
            found.extend(_find_forbidden_pixel_evidence(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_forbidden_pixel_evidence(child, f"{path}[{index}]"))
    return found


def _walk_parts(parts: list[dict]) -> list[dict]:
    found: list[dict] = []
    for part in parts:
        found.append(part)
        found.extend(_walk_parts(part.get("children") or []))
    return found


def _target_v2_character_depth_failures(blueprint: dict) -> set[str]:
    failures: set[str] = set()
    if blueprint.get("domain") not in {"character", "hybrid"}:
        return failures

    parts = _walk_parts(blueprint.get("parts") or [])
    roles = {part.get("role") for part in parts}
    if not {"head", "torso", "arm", "leg"}.issubset(roles):
        failures.add("CHARACTER_PARTS_TOO_SHALLOW")

    measurements = blueprint.get("proportionProfile", {}).get("measurements")
    if not measurements:
        failures.add("CHARACTER_MISSING_PROPORTION_MEASUREMENTS")

    landmarks = blueprint.get("landmarks")
    if not landmarks:
        failures.add("CHARACTER_MISSING_LANDMARKS")

    contacts = [part.get("attachment", {}).get("contact") for part in parts]
    if not any(contacts):
        failures.add("CHARACTER_MISSING_SOCKET_CONTACTS")

    identity_roles = {"helmet", "plume", "shield", "sword"}
    if not identity_roles.intersection(roles):
        failures.add("CHARACTER_IDENTITY_GEOMETRY_NOT_SEPARATED")

    layered_roles = {"scarf", "strap", "brooch", "belt", "cape", "tabard"}
    if len(layered_roles.intersection(roles)) < 2:
        failures.add("CHARACTER_LAYERED_DETAIL_NOT_SEPARATED")

    return failures


class KnightM0BaselineTests(unittest.TestCase):
    def test_manifest_inventory_paths_and_hashes_exist(self) -> None:
        manifest = _load_json(FIXTURE_ROOT / "manifest.json")
        self.assertEqual(
            manifest["sourcePolicy"]["licenseStatus"],
            "repo-local-sample-provenance-not-yet-audited",
        )
        self.assertEqual(
            manifest["sourcePolicy"]["provenanceStatus"],
            "known-repository-paths-with-sha256",
        )
        for group in ("references", "trackedArtifacts"):
            for item in manifest[group]:
                path = ROOT / item["path"]
                self.assertTrue(path.exists(), item["path"])
                self.assertEqual(_sha256(path), item["sha256"], item["path"])
                self.assertTrue(_git_tracks(item["path"]), item["path"])
                self.assertIn(item.get("sourceClass"), ALLOWED_SOURCE_CLASSES, item["id"])
                self.assertIn(item.get("evidenceClass"), ALLOWED_EVIDENCE_CLASSES, item["id"])

    def test_v0_shallow_blueprint_fails_character_depth_contract(self) -> None:
        blueprint = FIXTURE_ROOT / "blueprints" / "v0-shallow.json"
        result = validate_blueprint(blueprint, strict=True)
        self.assertFalse(result.ok, result.to_dict())
        blueprint_data = _load_json(blueprint)

        expected = _load_json(
            FIXTURE_ROOT / "expected-contracts" / "v2-character-depth-failures.json"
        )
        self.assertEqual(expected["currentContract"]["expected"], "fail")
        self.assertEqual(expected["targetV2Contract"]["expected"], "fail")
        self.assertEqual(
            set(expected["targetV2Contract"]["requiredFailureCodes"]),
            EXPECTED_V2_FAILURE_CODES,
        )
        self.assertEqual(
            {
                code
                for code in EXPECTED_V2_FAILURE_CODES
                if any(code in error for error in result.errors)
            },
            EXPECTED_V2_FAILURE_CODES,
        )
        self.assertEqual(
            _target_v2_character_depth_failures(blueprint_data),
            EXPECTED_V2_FAILURE_CODES,
        )

    def test_obs_01_to_17_are_mapped_to_tasks_and_evidence(self) -> None:
        trace = _load_json(FIXTURE_ROOT / "reports" / "obs-traceability.json")
        observations = trace["observations"]
        self.assertEqual(
            {item["id"] for item in observations},
            {f"OBS-{i:02d}" for i in range(1, 18)},
        )
        for item in observations:
            self.assertTrue(item["tasks"], item["id"])
            self.assertTrue(set(item["tasks"]).issubset(KNOWN_TASK_IDS), item["id"])
            self.assertTrue(item["evidenceIds"], item["id"])
            self.assertTrue(set(item["evidenceIds"]).issubset(KNOWN_EVIDENCE_IDS), item["id"])

    def test_m0_baseline_report_records_commands_commit_and_duration(self) -> None:
        report = _load_json(FIXTURE_ROOT / "baselines" / "m0-baseline-report.json")
        self.assertEqual(report["status"], "baseline-captured")
        self.assertEqual(report["repository"]["commit"], "5d658c6d1d309648f3727800a969483416641410")
        self.assertEqual(report["repository"]["shortCommit"], "5d658c6")
        self.assertEqual(report["repository"]["worktreeState"], "dirty-with-m0-baseline-changes")
        fingerprint = report["repository"]["artifactSetFingerprint"]
        self.assertEqual(fingerprint["algorithm"], EXPECTED_FINGERPRINT_ALGORITHM)
        self.assertEqual(fingerprint["scopeNote"], EXPECTED_FINGERPRINT_SCOPE_NOTE)
        self.assertEqual(fingerprint["files"], EXPECTED_BASELINE_FINGERPRINT_FILES)
        self.assertEqual(
            _source_state_fingerprint(fingerprint["files"]),
            fingerprint["value"],
        )
        self.assertEqual(set(report["missingEvidence"]), EXPECTED_MISSING_EVIDENCE)

        python_tests = report["commands"]["pythonTests"]
        self.assertEqual(python_tests["command"], "python3 -m unittest discover -s tests -v")
        self.assertEqual(python_tests["exitCode"], 0)
        self.assertEqual(python_tests["result"], "pass")
        self.assertEqual(python_tests["testCount"], 23)
        self.assertGreater(python_tests["durationSeconds"], 0)

        demo_build = report["commands"]["demoBuild"]
        self.assertEqual(demo_build["command"], "npm --prefix demo run build")
        self.assertEqual(demo_build["exitCode"], 0)
        self.assertEqual(demo_build["result"], "pass-with-warning")
        self.assertGreater(demo_build["durationSeconds"], 0)
        warning_codes = {warning["code"] for warning in demo_build["warnings"]}
        self.assertEqual(warning_codes, {"VITE_CHUNK_SIZE_GT_500KB"})

    def test_v0_gate_a_to_e_failure_report_is_locked(self) -> None:
        report_path = FIXTURE_ROOT / "reports" / "v0-gate-a-e-failure-report.json"
        report = _load_json(report_path)
        self.assertEqual(report["status"], "fail-closed-baseline")
        self.assertEqual(report["reviewPolicy"]["recommendation"], "reject")
        self.assertFalse(report["reviewPolicy"]["acceptAllowed"])

        blueprint = report["inputs"]["blueprint"]
        reference_manifest = report["inputs"]["referenceManifest"]
        expected_v2 = report["inputs"]["expectedV2Failures"]
        self.assertEqual(reference_manifest["path"], "tests/golden/knight/manifest.json")
        self.assertEqual(_sha256(ROOT / reference_manifest["path"]), reference_manifest["sha256"])
        self.assertEqual(
            expected_v2["path"],
            "tests/golden/knight/expected-contracts/v2-character-depth-failures.json",
        )
        self.assertEqual(_sha256(ROOT / expected_v2["path"]), expected_v2["sha256"])

        self.assertEqual(blueprint["path"], "tests/golden/knight/blueprints/v0-shallow.json")
        self.assertEqual(_sha256(ROOT / blueprint["path"]), blueprint["sha256"])
        self.assertEqual(blueprint["currentV1StrictValidation"], "fail")
        self.assertEqual(blueprint["targetV2Contract"], "fail")

        harness = report["inputs"]["captureHarness"]
        self.assertEqual(harness["command"], "npm --prefix demo run capture:smoke")
        self.assertEqual(harness["profilePath"], "demo/src/capture/m0-profile.json")
        self.assertEqual(harness["harnessPath"], "demo/tests/capture-smoke.mjs")
        self.assertEqual(_sha256(ROOT / harness["profilePath"]), harness["profileSha256"])
        self.assertEqual(_sha256(ROOT / harness["harnessPath"]), harness["harnessSha256"])

        capture = report["captureHarnessEvidence"]
        profile = _load_json(ROOT / harness["profilePath"])
        self.assertEqual(set(capture), EXPECTED_CAPTURE_HARNESS_KEYS)
        self.assertEqual(profile["id"], "knight-source-34-m0")
        self.assertEqual(capture["profileId"], profile["id"])
        self.assertEqual(capture["artifactScope"], "current-demo-factory-not-v0-shallow-blueprint")
        self.assertIn("not used as proof", capture["usage"])
        self.assertEqual(profile["viewport"], {"width": 640, "height": 640, "deviceScaleFactor": 1})
        self.assertEqual(capture["viewport"], profile["viewport"])
        self.assertEqual(set(capture["determinism"]), EXPECTED_CAPTURE_DETERMINISM_KEYS)
        self.assertEqual(capture["determinism"]["command"], "npm --prefix demo run capture:smoke")
        self.assertEqual(capture["determinism"]["latestObservedResult"], "pass")
        self.assertFalse(_contains_forbidden_key(capture, FORBIDDEN_CAPTURE_EVIDENCE_KEYS))
        self.assertEqual(_find_forbidden_pixel_evidence(report), [])

        gates = report["metricReport"]["gates"]
        self.assertEqual(
            report["metricReport"]["evidenceBasis"],
            "static v0-shallow Blueprint and tracked fixture manifest; no rendered v0-shallow Blueprint pixels exist yet",
        )
        self.assertEqual(report["metricReport"]["overallDecision"], "reject")
        self.assertEqual([gate["id"] for gate in gates], EXPECTED_GATE_ORDER)
        self.assertEqual(len(gates), 5)
        self.assertEqual(len({gate["id"] for gate in gates}), 5)
        self.assertEqual([gate["label"] for gate in gates], ["Gate A", "Gate B", "Gate C", "Gate D", "Gate E"])
        self.assertEqual(report["reviewPolicy"]["gateOrder"], ["Gate A", "Gate B", "Gate C", "Gate D", "Gate E"])
        self.assertTrue(all(gate["status"] == "fail" for gate in gates))
        self.assertEqual(
            {gate["id"]: set(gate["failureCodes"]) for gate in gates},
            EXPECTED_GATE_FAILURE_CODES,
        )
        for gate in gates:
            self.assertEqual(len(gate["failureCodes"]), len(set(gate["failureCodes"])))
            self.assertEqual(len(gate["observations"]), len(set(gate["observations"])))
        self.assertEqual(
            {gate["id"]: set(gate["observations"]) for gate in gates},
            EXPECTED_GATE_OBSERVATIONS,
        )
        for gate in gates:
            self.assertTrue(gate["observations"], gate["id"])
            self.assertTrue(gate["evidence"], gate["id"])


if __name__ == "__main__":
    unittest.main()
