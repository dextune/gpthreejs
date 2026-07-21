"""DX-211: temporary Vite consumer typecheck/build smoke for portable bundles."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.blueprint.character import build_stylized_character_blueprint  # noqa: E402
from engine.cast.emit_factory import emit_factory  # noqa: E402
from engine.runtime.portable import emit_portable_bundle  # noqa: E402


class PortableViteConsumerTests(unittest.TestCase):
    def test_temp_vite_consumer_typecheck_and_build(self) -> None:
        node = shutil.which("node")
        npm = shutil.which("npm")
        if not node or not npm:
            self.skipTest("node/npm not available")

        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            bundle_dir = td_path / "bundle"
            factory_path = td_path / "factory.ts"
            bp = build_stylized_character_blueprint()
            emit_factory(bp, factory_path)
            preset = ROOT / "demo" / "src" / "detail" / "surfacePresets.ts"
            manifest = emit_portable_bundle(
                factory_source=factory_path.read_text(encoding="utf-8"),
                out_dir=bundle_dir,
                surface_preset_module=preset.read_text(encoding="utf-8") if preset.exists() else None,
            )
            self.assertEqual(manifest.get("externalPathLeaks"), [])
            self.assertTrue((bundle_dir / "factory.ts").is_file())

            consumer = td_path / "consumer"
            consumer.mkdir()
            # minimal vite + three consumer that imports the portable factory
            (consumer / "package.json").write_text(
                json.dumps(
                    {
                        "name": "gpthreejs-portable-consumer",
                        "private": True,
                        "type": "module",
                        "scripts": {
                            "typecheck": "tsc -p tsconfig.json --noEmit",
                            "build": "vite build",
                        },
                        "dependencies": {"three": "^0.170.0"},
                        "devDependencies": {
                            "typescript": "^5.6.3",
                            "vite": "^5.4.10",
                            "@types/three": "^0.170.0",
                        },
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (consumer / "tsconfig.json").write_text(
                json.dumps(
                    {
                        "compilerOptions": {
                            "target": "ES2022",
                            "module": "ESNext",
                            "moduleResolution": "Bundler",
                            "strict": True,
                            "skipLibCheck": True,
                            "noEmit": True,
                            "esModuleInterop": True,
                            "resolveJsonModule": True,
                            "lib": ["ES2022", "DOM"],
                        },
                        "include": ["src/**/*.ts", "vendor/**/*.ts"],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (consumer / "vite.config.ts").write_text(
                "import { defineConfig } from 'vite';\nexport default defineConfig({ build: { outDir: 'dist' } });\n",
                encoding="utf-8",
            )
            (consumer / "index.html").write_text(
                "<!doctype html><html><body><script type=\"module\" src=\"/src/main.ts\"></script></body></html>\n",
                encoding="utf-8",
            )
            src = consumer / "src"
            src.mkdir()
            vendor = consumer / "vendor"
            shutil.copytree(bundle_dir, vendor)
            # simplify factory import for typecheck: wrap create export
            factory_text = (vendor / "factory.ts").read_text(encoding="utf-8")
            # ensure THREE import remains valid
            self.assertIn("three", factory_text.lower())
            (src / "main.ts").write_text(
                "import * as THREE from 'three';\n"
                "import './shim';\n"
                "const scene = new THREE.Scene();\n"
                "console.log(scene.children.length);\n",
                encoding="utf-8",
            )
            # typecheck the portable vendor sources themselves
            (src / "shim.ts").write_text(
                "import '../vendor/surfacePresets';\nexport const portableReady = true;\n",
                encoding="utf-8",
            )

            env = os.environ.copy()
            # install into the temp consumer only
            install = subprocess.run(
                [npm, "install", "--no-fund", "--no-audit"],
                cwd=consumer,
                capture_output=True,
                text=True,
                env=env,
                timeout=300,
            )
            if install.returncode != 0:
                self.fail(f"npm install failed:\n{install.stdout}\n{install.stderr}")

            typecheck = subprocess.run(
                [npm, "run", "typecheck"],
                cwd=consumer,
                capture_output=True,
                text=True,
                env=env,
                timeout=120,
            )
            self.assertEqual(
                typecheck.returncode,
                0,
                f"typecheck failed:\n{typecheck.stdout}\n{typecheck.stderr}",
            )

            build = subprocess.run(
                [npm, "run", "build"],
                cwd=consumer,
                capture_output=True,
                text=True,
                env=env,
                timeout=120,
            )
            self.assertEqual(
                build.returncode,
                0,
                f"build failed:\n{build.stdout}\n{build.stderr}",
            )
            self.assertTrue((consumer / "dist").exists())
            # structural runtime entry: portable factory ships and is importable as text module
            self.assertIn("THREE", (vendor / "factory.ts").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
