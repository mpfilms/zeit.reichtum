"""Licht- und Feuer-Regel für Bild-/Video-Prompts (Lernregel 2026-11-19, T04-R1 / 2026-11-V05)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import qa_check  # noqa: E402


def levels(prompt, strict=True):
    R = qa_check.Report()
    g = R.group("t")
    qa_check.check_fire(R, g, prompt, "", strict)
    return [i[0] for i in g["items"]]


class Feuer(unittest.TestCase):
    def test_ohne_feuer_ok(self):
        self.assertEqual(levels("A quiet kitchen in soft morning light, a floor lamp on the right."), [])

    def test_firelight_ohne_quelle_fail(self):
        p = "A cozy sofa corner at dusk, a faint warm firelight flickers softly across the wall."
        self.assertIn("FAIL", levels(p))

    def test_kerze_mit_schutzsatz_ok(self):
        p = ("A beeswax candle in a ceramic holder on the table. The flame stays only inside the candle, "
             "nothing else is burning, no smoke.")
        self.assertEqual(levels(p), [])

    def test_kerze_ohne_schutzsatz_fail(self):
        self.assertIn("FAIL", levels("A candle in a holder glows on the windowsill."))

    def test_kamin_nur_hinter_glas(self):
        p = "A stone fireplace with a calm fire, nothing else is burning."
        self.assertIn("FAIL", levels(p))
        p2 = ("A small fire burns calmly behind the glass door of a stone fireplace, nothing else is burning.")
        self.assertEqual(levels(p2), [])

    def test_pool_medium_nur_warnung(self):
        p = "A cozy sofa corner, a faint warm firelight flickers softly across the wall."
        lv = levels(p, strict=False)
        self.assertNotIn("FAIL", lv)
        self.assertIn("WARN", lv)


if __name__ == "__main__":
    unittest.main()
