"""Tests for image/spec sufficiency gate."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.sense.sufficiency import assess_sufficiency
from engine.shared.pngio import Image, write_png


def _write_png(path: Path, w: int, h: int, rgb=(40, 40, 40), box=None) -> None:
    img = Image(w, h, bytearray(w * h * 4))
    for y in range(h):
        for x in range(w):
            img.set_pixel(x, y, (*rgb, 255))
    if box:
        x0, y0, x1, y1, col = box
        for y in range(y0, y1):
            for x in range(x0, x1):
                img.set_pixel(x, y, (*col, 255))
    write_png(path, img)


class SufficiencyTests(unittest.TestCase):
    def test_missing_file_reject(self) -> None:
        r = assess_sufficiency("/no/such/image.png")
        self.assertEqual(r["verdict"], "reject")
        self.assertFalse(r["sufficient"])
        self.assertEqual(r["agentAction"], "abort")
        self.assertTrue(any(i["code"] == "FILE_MISSING" for i in r["issues"]))
        self.assertIn("부족", r["userMessage"])

    def test_tiny_resolution_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "tiny.png"
            _write_png(p, 64, 64, rgb=(120, 120, 120))
            r = assess_sufficiency(p)
            self.assertEqual(r["verdict"], "reject")
            self.assertTrue(any(i["code"] == "RES_TOO_LOW" for i in r["issues"]))

    def test_character_single_view_ask(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "ok.png"
            # decent size, mid gray
            _write_png(p, 512, 640, rgb=(100, 100, 100), box=(150, 80, 360, 560, (180, 40, 40)))
            r = assess_sufficiency(
                p,
                domain="character",
                intent="game",
                view_count=1,
                has_side=False,
            )
            self.assertIn(r["verdict"], ("conditional", "reject", "pass"))
            self.assertTrue(
                any(i["code"] in ("CHAR_SINGLE_VIEW", "CHAR_NO_SIDE") for i in r["issues"])
            )
            # without sense, may still be conditional/ask
            self.assertIn(r["agentAction"], ("ask", "continue", "abort"))

    def test_ledger_all_todo_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "ok.png"
            _write_png(p, 400, 400, rgb=(90, 90, 90))
            ledger = Path(td) / "ledger.json"
            ledger.write_text(
                '{"entries":[{"id":"a","status":"todo"},{"id":"b","status":"todo"}],"targetMin":6}',
                encoding="utf-8",
            )
            r = assess_sufficiency(p, ledger_path=ledger, domain="object")
            self.assertTrue(any(i["code"] == "LEDGER_ALL_TODO" for i in r["issues"]))
            self.assertEqual(r["agentAction"], "abort")

    def test_user_message_nonempty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.png"
            _write_png(p, 300, 300)
            r = assess_sufficiency(p)
            self.assertTrue(len(r["userMessage"]) > 20)
            self.assertIn("nextSteps", r)


if __name__ == "__main__":
    unittest.main()
