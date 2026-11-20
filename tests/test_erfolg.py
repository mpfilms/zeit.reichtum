"""Erfolgs-Stories: jeder Erfolg nur einmal (Pamina, 2026-11-19)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import erfolg  # noqa: E402


class Erfolg(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.old = (erfolg.NEU, erfolg.LISTE)
        erfolg.NEU, erfolg.LISTE = d / "neu", d / "liste.jsonl"
        erfolg.NEU.mkdir()

    def tearDown(self):
        erfolg.NEU, erfolg.LISTE = self.old
        self.tmp.cleanup()

    def test_schon_geteilt_wird_nie_wieder_genommen(self):
        a = erfolg.NEU / "a.txt"
        a.write_text("Erster Abend nur für mich.", encoding="utf-8")
        b = erfolg.NEU / "b.txt"
        b.write_text("Anderer Erfolg.", encoding="utf-8")
        erfolg.LISTE.write_text(json.dumps({"sha256": erfolg.sha(a), "datei": "x", "slot": "T02-SE",
                                            "datum": "2026-11-17"}) + "\n", encoding="utf-8")
        frei, doppelt = erfolg.kandidaten()
        self.assertEqual([p.name for p in frei], ["b.txt"])
        self.assertEqual([p.name for p in doppelt], ["a.txt"])

    def test_nur_se_slots(self):
        with self.assertRaises(erfolg.Fehler):
            erfolg.cmd_build("T02-SP", "2026-11-17", None)


if __name__ == "__main__":
    unittest.main()
