"""Tests für scripts/render_images.py (ohne API-Aufruf; Overlay nur, wenn Pillow installiert ist)."""
import base64
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import qa_check  # noqa: E402
import render_images as ri  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
CMD = [sys.executable, str(ROOT / "scripts" / "render_images.py")]

CAROUSEL_23 = """
## Agent 2 & 3 · Hook & Script
**Zitat:** Seneca, *Briefe* 1 (sinngemäß)

**Slide 1 (Hook):**
„Erster Satz. Zweiter Satz.“
**Quelle:** Seneca, *Briefe* 1 (sinngemäß)

**Slide 2:**
*Zeile A.*
*Zeile B.*

**Slide 3 (Lösung):**
*Letzte Zeile.*
"""


class Render(unittest.TestCase):
    def test_prompt_keeps_formula_and_strips_params(self):
        _, clean = ri.load_post(FIX / "nurture_ok.md")
        prompt, aspect = ri.image_prompt(clean)
        self.assertEqual(aspect, "9:16")
        self.assertTrue(prompt.endswith(qa_check.IMG_FORMULA), prompt[-120:])
        self.assertNotIn("--", prompt)

    def test_imagen_request(self):
        url, body, calls = ri.build_request("imagen-4.0-generate-001", "p", "9:16", 3)
        self.assertTrue(url.endswith("imagen-4.0-generate-001:predict"))
        self.assertEqual(calls, 1)
        self.assertEqual(body["parameters"],
                         {"sampleCount": 3, "aspectRatio": "9:16", "personGeneration": "dont_allow"})

    def test_gemini_request_one_call_per_image(self):
        url, body, calls = ri.build_request("gemini-2.5-flash-image", "p", "3:4", 2)
        self.assertTrue(url.endswith(":generateContent"))
        self.assertEqual(calls, 2)
        self.assertEqual(body["generationConfig"]["imageConfig"]["aspectRatio"], "3:4")

    def test_extract_images_both_formats(self):
        b = base64.b64encode(b"PNG").decode()
        imgs, notes = ri.extract_images({"predictions": [{"bytesBase64Encoded": b},
                                                          {"raiFilteredReason": "x"}]})
        self.assertEqual((imgs, notes), ([b"PNG"], ["x"]))
        imgs, _ = ri.extract_images({"candidates": [{"content": {"parts": [{"inlineData": {"data": b}}]},
                                                     "finishReason": "STOP"}]})
        self.assertEqual(imgs, [b"PNG"])

    def test_parse_slides(self):
        _, clean = None, {"2&3": qa_check.strip_comments(CAROUSEL_23)}
        s = ri.parse_slides(clean)
        self.assertEqual([x["nr"] for x in s], [1, 2, 3])
        self.assertEqual(s[0]["source"], "Seneca, Briefe 1 (sinngemäß)")
        self.assertEqual(s[1]["lines"], ["Zeile A.", "Zeile B."])

    def test_dry_run_cli(self):
        p = subprocess.run(CMD + [str(FIX / "nurture_ok.md"), "--dry-run", "--model", "imagen-4-fast"],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("imagen-4.0-fast-generate-001:predict", p.stdout)
        body = json.loads(p.stdout.split("\n", 1)[1])
        self.assertEqual(body["parameters"]["personGeneration"], "dont_allow")

    def test_refuses_without_qa(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "x.md"
            bad = (FIX / "nurture_ok.md").read_text(encoding="utf-8").replace("**Caption:**", "**Caption:**\nKarma", 1)
            f.write_text(bad, encoding="utf-8")
            p = subprocess.run(CMD + [str(f)], capture_output=True, text=True)  # Blacklist → QA-FAIL
            self.assertEqual(p.returncode, 1)
            self.assertIn("QA nicht bestanden", p.stderr)

    @unittest.skipUnless(__import__("importlib").util.find_spec("PIL"), "Pillow nicht installiert")
    def test_slides_overlay(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            base = Path(d) / "b.png"
            Image.new("RGB", (768, 1408), (110, 95, 80)).save(base)
            slides = ri.parse_slides({"2&3": qa_check.strip_comments(CAROUSEL_23)})
            written, _ = ri.render_slides(base, slides, Path(d) / "s")
            self.assertEqual(len(written), 3)
            self.assertEqual(Image.open(written[0]).size, (1080, 1920))


if __name__ == "__main__":
    unittest.main()
