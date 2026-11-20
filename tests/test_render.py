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
**Zitat:** Seneca, *Briefe* 1 (sinngemäss)

**Slide 1 (Hook):**
„Erster Satz. Zweiter Satz.“
**Quelle:** Seneca, *Briefe* 1 (sinngemäss)

**Slide 2:**
*Zeile A.*
*Zeile B.*

**Slide 3 (Lösung):**
*Letzte Zeile.*
"""


NEW_23 = """**Slide 1 · Hook:**
# Titel

**Slide 2 · Kontext:**
# Überschrift
> Akzent.
Der **Minijob**. Die _unsichtbare_ ==Liste== bleibt.
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
        url, body, calls = ri.build_request("gemini-2.5-flash-image", "p", "4:5", 2)
        self.assertTrue(url.endswith(":generateContent"))
        self.assertEqual(calls, 2)
        self.assertEqual(body["generationConfig"]["imageConfig"]["aspectRatio"], "4:5")

    def test_extract_images_both_formats(self):
        b = base64.b64encode(b"PNG").decode()
        imgs, notes = ri.extract_images({"predictions": [{"bytesBase64Encoded": b},
                                                          {"raiFilteredReason": "x"}]})
        self.assertEqual((imgs, notes), ([b"PNG"], ["x"]))
        imgs, _ = ri.extract_images({"candidates": [{"content": {"parts": [{"inlineData": {"data": b}}]},
                                                     "finishReason": "STOP"}]})
        self.assertEqual(imgs, [b"PNG"])

    def test_parse_slides_old_format(self):
        s = ri.parse_slides({"2&3": qa_check.strip_comments(CAROUSEL_23)})
        self.assertEqual([x["nr"] for x in s], [1, 2, 3])
        self.assertEqual(s[0]["blocks"][0][0], "h")  # alter Hook wird zur Überschrift
        self.assertIn(("src", "Seneca, Briefe 1 (sinngemäss)"), s[0]["blocks"])
        self.assertEqual(s[1]["blocks"], [("p", "Zeile A."), ("p", "Zeile B.")])

    def test_parse_slides_new_format_and_runs(self):
        s = ri.parse_slides({"2&3": NEW_23})
        self.assertEqual([b[0] for b in s[1]["blocks"]], ["h", "k", "p"])
        self.assertEqual(s[1]["label"], "Kontext")
        r = ri.runs(s[1]["blocks"][2][1])
        self.assertIn(("Minijob", "b", "."), r)            # Satzzeichen klebt am fetten Wort
        self.assertIn(("Liste", "m", ""), r)
        self.assertIn(("unsichtbare", "a", ""), r)

    def test_variants_differ_and_keep_formula(self):
        _, clean = ri.load_post(FIX / "nurture_ok.md")
        prompt, _ = ri.image_prompt(clean)
        vs = ri.variant_prompts(prompt, 3)
        self.assertEqual(len(set(vs)), 3)
        for v in vs:
            self.assertTrue(v.endswith(qa_check.IMG_FORMULA))

    def test_dry_run_cli(self):
        p = subprocess.run(CMD + [str(FIX / "nurture_ok.md"), "--dry-run", "--count", "2"],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.count("POST "), 2)
        self.assertIn('"aspectRatio": "9:16"', p.stdout)  # Fixture ist ein Reel
        self.assertIn('"imageSize": "2K"', p.stdout)

    def test_refuses_without_qa(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "x.md"
            bad = (FIX / "nurture_ok.md").read_text(encoding="utf-8").replace("**Caption:**", "**Caption:**\nKarma", 1)
            f.write_text(bad, encoding="utf-8")
            p = subprocess.run(CMD + [str(f)], capture_output=True, text=True)  # Blacklist → QA-FAIL
            self.assertEqual(p.returncode, 1)
            self.assertIn("QA nicht bestanden", p.stderr)

    @unittest.skipUnless(__import__("importlib").util.find_spec("PIL"), "Pillow nicht installiert")
    def test_bridge_sentence_on_new_line(self):
        sl = {"nr": 2, "blocks": [("p", "Wäsche, Einkauf. Bezahlt wurde nur eines: Stunde gegen Lohn. Bis ich mich fragte:")]}
        out = ri.split_bridge(sl, 8)["blocks"]
        self.assertEqual([a for a, _ in out], ["pb", "p"])
        self.assertEqual(out[1][1], "Bis ich mich fragte:")

    def test_bridge_not_on_last_slide_and_keeps_abbreviations(self):
        last = {"nr": 8, "blocks": [("p", "Ein Satz. Was würdest du weiterempfehlen?")]}
        self.assertEqual(ri.split_bridge(last, 8)["blocks"], last["blocks"])
        abk = {"nr": 3, "blocks": [("p", "Etwa z. B. Amazon oder LEGO und Lidl, mehr nicht und dann:")]}
        self.assertEqual(ri.split_bridge(abk, 8)["blocks"], abk["blocks"])

    def test_glass_window_blur_is_minimal(self):
        self.assertLessEqual(ri.GLAS_BLUR, 5)  # früher 18: das Foto hinter dem Text soll erkennbar bleiben

    def test_slides_overlay(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            base = Path(d) / "b.png"
            Image.new("RGB", (768, 1408), (110, 95, 80)).save(base)
            slides = ri.parse_slides({"2&3": qa_check.strip_comments(CAROUSEL_23)})
            written, _ = ri.render_slides([base], slides, Path(d) / "s")
            self.assertEqual(len(written), 3)
            self.assertEqual(Image.open(written[0]).size, (1080, 1350))


if __name__ == "__main__":
    unittest.main()
