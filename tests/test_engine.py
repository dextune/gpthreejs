"""Smoke tests for gpthreejs engine (stdlib only)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.blueprint.draft import draft_blueprint, draft_brief, draft_ledger
from engine.blueprint.validate import validate_blueprint
from engine.cast.emit_factory import emit_factory
from engine.cast.layers import check, status, sync
from engine.critique.metrics import ssim_approx
from engine.sense.pack import build_sense_pack
from engine.shared.jsonutil import load_json
from engine.shared.pngio import Image, read_png, write_png


def _solid_png(path: Path, w: int = 64, h: int = 64, rgb=(200, 40, 40)) -> None:
    img = Image(w, h, bytearray(w * h * 4))
    # red square on gray background
    for y in range(h):
        for x in range(w):
            if 16 <= x < 48 and 16 <= y < 48:
                img.set_pixel(x, y, (*rgb, 255))
            else:
                img.set_pixel(x, y, (220, 220, 220, 255))
    write_png(path, img)


class gpthreejsTests(unittest.TestCase):
    def test_png_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "t.png"
            _solid_png(p)
            im = read_png(p)
            self.assertEqual(im.width, 64)
            self.assertEqual(im.pixel(32, 32)[0], 200)

    def test_sense_and_blueprint_cast(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            img = td_path / "ref.png"
            _solid_png(img)
            sense_dir = td_path / "sense"
            pack = build_sense_pack(img, sense_dir, mode="sharp")
            self.assertIn("maps", pack)
            self.assertTrue((sense_dir / "matte.png").exists())

            brief_path = td_path / "brief.json"
            draft_brief(
                "TestBox",
                image=str(img),
                sense_path=sense_dir / "sense_pack.json",
                complexity="simple",
                domain="object",
                quality_mode="draft",
                out=brief_path,
            )
            ledger_path = td_path / "ledger.json"
            led = draft_ledger(str(img), sense_dir, ledger_path)
            # fill todos for non-strict
            for e in led["entries"]:
                e["status"] = "filled"
                e["mapsTo"] = {"type": "feature", "ref": "placeholder"}
            ledger_path.write_text(json.dumps(led), encoding="utf-8")

            bp_path = td_path / "bp.json"
            bp = draft_blueprint(
                "TestBox",
                brief_path=brief_path,
                ledger_path=ledger_path,
                sense_path=sense_dir / "sense_pack.json",
                out=bp_path,
            )
            # non-strict validate
            res = validate_blueprint(bp_path, strict=False)
            self.assertTrue(res.ok, res.errors)

            st = status(bp_path)
            self.assertIn("mass", st["open"] + st["done"] + st["locked"])
            self.assertTrue(check(bp_path, "mass")["ok"])

            out_ts = td_path / "createTestBoxForm.ts"
            emit_factory(bp, out_ts)
            text = out_ts.read_text(encoding="utf-8")
            self.assertIn("createTestBoxForm", text)
            self.assertIn("formHandles", text)
            self.assertIn("three", text.lower())

    def test_ssim_identical(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "a.png"
            _solid_png(p)
            im = read_png(p)
            self.assertGreater(ssim_approx(im, im), 0.99)

    def test_layer_sync_after_accept(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            img = td_path / "ref.png"
            _solid_png(img)
            sense_dir = td_path / "sense"
            build_sense_pack(img, sense_dir, mode="draft")
            brief_path = td_path / "brief.json"
            draft_brief(
                "X",
                image=str(img),
                sense_path=sense_dir / "sense_pack.json",
                out=brief_path,
            )
            bp_path = td_path / "bp.json"
            draft_blueprint(
                "X",
                brief_path=brief_path,
                ledger_path=None,
                sense_path=sense_dir / "sense_pack.json",
                out=bp_path,
            )
            bp = load_json(bp_path)
            bp["journal"] = [
                {
                    "layer": "mass",
                    "decision": "accept",
                    "policyTrace": {
                        "policyIssued": True,
                        "issuer": "review-policy",
                        "decision": "accept",
                    },
                }
            ]
            bp_path.write_text(json.dumps(bp), encoding="utf-8")
            st = sync(bp_path, in_place=True)
            self.assertIn("mass", st["done"])
            self.assertTrue(st["open"])


if __name__ == "__main__":
    unittest.main()
