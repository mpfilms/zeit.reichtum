"""Tests für scripts/qa_check.py, plan.py und roll.py (nur Standardbibliothek)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures"
QA_CMD = [sys.executable, str(ROOT / "scripts" / "qa_check.py")]
PITCH = (FIX / "pitch_ok.md").read_text(encoding="utf-8")
NURTURE = (FIX / "nurture_ok.md").read_text(encoding="utf-8")


class QA(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.hist = self.dir / "history.jsonl"
        self.names = self.dir / "names.txt"
        self.names.write_text("# leer\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_qa(self, text, *extra, name="post.md"):
        f = self.dir / name
        f.write_text(text, encoding="utf-8")
        p = subprocess.run(
            QA_CMD + [str(f), "--history", str(self.hist), "--names", str(self.names), *extra],
            capture_output=True, text=True)
        return p.returncode, p.stdout

    def assertFails(self, text, needle, *extra):
        code, out = self.run_qa(text, *extra)
        self.assertEqual(code, 1, out)
        self.assertIn(needle, out)

    # --- gültige Posts ---
    def test_pitch_ok(self):
        code, out = self.run_qa(PITCH, "--final")
        self.assertEqual(code, 0, out)

    def test_nurture_ok(self):
        code, out = self.run_qa(NURTURE, "--final")
        self.assertEqual(code, 0, out)

    # --- Blacklist & Namen ---
    def test_blacklist(self):
        for w in ["magisch", "Karma", "Hexenwerk", "magie"]:
            self.assertFails(PITCH.replace("Wir verlieren nur viel davon.", f"Das ist {w}."), "Blacklist-Wort")

    def test_forbidden_name(self):
        self.names.write_text("Max Mustermann\nSuperkurs 3000\n", encoding="utf-8")
        self.assertFails(PITCH.replace("digitalen Fahrplan", "Superkurs 3000"), "Verbotener Name")

    # --- Kopfzeile / Hashtags ---
    def test_header(self):
        self.assertFails(PITCH.replace("Werbung 🤍\n", "Werbung\n"), "Kennzeichnung")
        self.assertFails(PITCH.replace("\nFolge mir, wenn du dir als Mama etwas Eigenes aufbauen möchtest.\n", "\n"), "Folge-Satz")

    def test_hashtag_block(self):
        self.assertFails(PITCH.replace("System. 🕊️\n", "System. 🕊️\n\n#mama #geld #zeit\n"), "Hashtag-Block")

    def test_three_hashtags(self):
        self.assertFails(PITCH.replace("Pflichten,", "#Pflichten #Alltag,"), "Hashtags (max. 2)")

    # --- Hook ---
    def test_hook_three_sentences(self):
        self.assertFails(PITCH.replace("Wir verlieren nur viel davon.", "Wir verlieren viel. Davon sehr viel."), "Hook hat 3 Sätze")

    def test_reel_last_einblendung_points_to_caption(self):
        self.assertFails(PITCH.replace("steht in der Caption.", "steht anderswo."), "Caption")

    def test_missing_sinngemaess(self):
        self.assertFails(PITCH.replace("sinngemäss", "frei"), "sinngemäss")

    # --- Pitch / Nurture ---
    def test_pitch_two_keywords(self):
        self.assertFails(PITCH.replace("zu meinem automatisierten System.", "zu meinem System. Oder „INFO\"."), "genau ein Keyword")

    def test_pitch_without_manychat(self):
        head, _, _ = PITCH.partition("## Agent 11")
        self.assertFails(head, "Agent 11 fehlt")

    def test_nurture_with_manychat(self):
        self.assertFails(NURTURE + "\n## Agent 11 · Manychat-Flow (Absender: PAMINA)\nNachricht 1 Nachricht 2 {{Vorname}} text text text\n", "Nurture")

    def test_nurture_with_keyword(self):
        self.assertFails(NURTURE.replace("ganz ohne schlechtes Gewissen?", "ganz ohne schlechtes Gewissen? Kommentiere „START\"."), "Nurture")

    def test_nurture_without_question(self):
        self.assertFails(NURTURE.replace("Gewissen?", "Gewissen."), "Community-Frage")

    def test_variant_a_needs_four_sentences(self):
        self.assertFails(PITCH.replace("Ich nutze einen", "Ich sage dir etwas. Ich nutze einen"), "gefunden: 5 Sätze")

    # --- Formeln ---
    def test_image_formula_changed(self):
        self.assertFails(PITCH.replace("Slightly underexposed by 10-15%", "Slightly underexposed by 15%"), "Bild-Formel")

    def test_text_after_params(self):
        self.assertFails(PITCH.replace("--v 6.1\n```", "--v 6.1 dark moody\n```"), "Parameter")

    def test_formula_after_params(self):
        formula_start = PITCH.index("Slightly underexposed")
        formula_end = PITCH.index("--ar 9:16")
        formula = PITCH[formula_start:formula_end]
        moved = PITCH[:formula_start] + PITCH[formula_end:].replace("--v 6.1", "--v 6.1 " + formula.strip(), 1)
        self.assertFails(moved, "Parameter")

    def test_video_formula_missing(self):
        self.assertFails(PITCH.replace("Static camera, seamless loop.", "Static camera."), "Video-Formel")

    def test_people_in_image_prompt(self):
        self.assertFails(PITCH.replace("no people", "a woman holding the cup"), "Menschen")

    def test_moving_camera(self):
        self.assertFails(PITCH.replace("Very slow, subtle", "Camera pan across the table, very slow, subtle"), "Kamera")

    # --- Variablen & Historie ---
    def test_variables_missing(self):
        self.assertFails(PITCH.replace("3. **Stoff-Farbe:** Salbeigrün (Leinen)\n", ""), "Variablen fehlen")

    def test_history_repetition(self):
        self.hist.write_text(json.dumps({"slug": "alt", "licht": "weiches, goldenes Licht kurz nach Sonnenaufgang"}) + "\n", encoding="utf-8")
        self.assertFails(PITCH, "wiederholt einen früheren Post")

    def test_log_and_idempotence(self):
        code, out = self.run_qa(PITCH, "--log", "--slug", "T05-R1")
        self.assertEqual(code, 0, out)
        self.assertEqual(len(self.hist.read_text(encoding="utf-8").splitlines()), 1)
        code, out = self.run_qa(PITCH, "--log", "--slug", "T05-R1")  # derselbe Slot darf erneut laufen
        self.assertEqual(code, 0, out)
        self.assertEqual(len(self.hist.read_text(encoding="utf-8").splitlines()), 1)
        code, out = self.run_qa(PITCH, "--slug", "T99-R1")  # anderer Post mit gleichen Variablen darf nicht durch
        self.assertEqual(code, 1, out)
        code, out = self.run_qa(NURTURE, "--log", "--slug", "T05-R2")
        self.assertEqual(code, 0, out)
        self.assertEqual(len(self.hist.read_text(encoding="utf-8").splitlines()), 2)

    def test_no_log_on_failure(self):
        code, _ = self.run_qa(PITCH.replace("Werbung 🤍\n", "Werbung\n"), "--log")
        self.assertEqual(code, 1)
        self.assertFalse(self.hist.exists())

    # --- CapCut & Manychat ---
    def test_capcut_font_missing(self):
        self.assertFails(PITCH.replace("Playfair Display Bold", "Arial"), "Playfair Display Bold")

    def test_affiliate_hint_missing(self):
        self.assertFails(PITCH.replace("Das ist ein Affiliate-Link, ich erhalte ggf. eine Provision. Für dich bleibt es kostenlos.", "Viel Spass."), "Affiliate")

    def test_final_requires_agent10(self):
        text = PITCH.split("## Agent 10")[0] + "## Agent 11" + PITCH.split("## Agent 11")[1]
        self.assertFails(text, "Agent 10", "--final")

    def test_order(self):
        a, b = PITCH.split("## Agent 4 · Audio & Mood")
        b4, rest = b.split("## Agent 5 · Art Director")
        swapped = a + "## Agent 5 · Art Director" + rest.split("## Agent 6")[0] + "## Agent 4 · Audio & Mood" + b4 + "## Agent 6" + rest.split("## Agent 6", 1)[1]
        self.assertFails(swapped, "Reihenfolge")

    # --- WARN, kein FAIL ---
    def test_no_stoic_jargon(self):
        self.assertFails(PITCH.replace("Deine Pamina 🤍", "Deine Pamina 🤍 Ganz stoisch.", 1), "stoisch")

    # --- Sprach-Lint ---
    def test_language_possessive_without_noun(self):
        self.assertFails(PITCH.replace("Deine Pamina 🤍", "Und wohin ist deine heute gegangen? Deine Pamina 🤍", 1), "Besitzwort ohne Nomen")

    def test_language_double_word(self):
        self.assertFails(PITCH.replace("Deine Pamina 🤍", "Das ist ist schön. Deine Pamina 🤍", 1), "Doppeltes Wort")

    def test_language_missing_space(self):
        self.assertFails(PITCH.replace("Deine Pamina 🤍", "Es war schön.Danach kam es. Deine Pamina 🤍", 1), "Leerzeichen nach Satzzeichen")

    def test_swiss_spelling(self):
        self.assertFails(PITCH.replace("Deine Pamina 🤍", "Deine Pamina 🤍 Grüße", 1), "ß")

    def test_numbers_warn_only(self):
        code, out = self.run_qa(PITCH.replace("nur mit dem Handy.", "nur mit dem Handy und 2 Stunden pro Tag."))
        self.assertEqual(code, 0, out)
        self.assertIn("Zeitangabe", out)


class Scripts(unittest.TestCase):
    def test_plan_slot_consistent_with_blueprint(self):
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "plan.py"), "slot", "T05-R1"],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        d = json.loads(out.stdout)
        self.assertEqual((d["wochentag"], d["uhrzeit"], d["format"]), ("Freitag", "06:45", "Reel"))

    def test_plan_blueprint_rules(self):
        rows = [l for l in (ROOT / "data" / "content-plan.md").read_text(encoding="utf-8").splitlines() if l.startswith("| T")]
        reels = [r for r in rows if "-R" in r.split("|")[1]]
        self.assertEqual(len(reels), 24)  # 12 Reels pro Woche
        self.assertEqual(len([r for r in rows if "-K " in r.split("|")[1] + " "]), 4)  # Tag 3, 6, 10, 13
        slot = lambda r: r.split("|")[1].strip()
        self.assertEqual(len([r for r in rows if slot(r).endswith("-SN") and "Nurture" in r]), 14)  # täglich Nurture-Story
        self.assertEqual(len([r for r in rows if slot(r).endswith("-SP") and "Pitch" in r]), 14)  # täglich Verkaufs-Story
        se = [slot(r) for r in rows if slot(r).endswith("-SE")]
        self.assertEqual(se, ["T02-SE", "T06-SE", "T09-SE", "T13-SE"])  # Community-Erfolg Di + Sa
        self.assertTrue(all("08:30" in r for r in rows if slot(r).endswith("-SN")))
        self.assertTrue(all("20:30" in r for r in rows if slot(r).endswith("-SP")))
        feed = [r for r in rows if "-S" not in slot(r)]
        for d in range(1, 15):  # pro Tag genau 1 Pitch und 1 Nurture im Feed
            day = [r for r in feed if f"| T{d:02d}-" in r]
            self.assertEqual(sorted(r.split("|")[3].split("· ")[1].strip() for r in day), ["Nurture", "Pitch"])
        for d in (7, 14):
            self.assertTrue(all("Sunday Mode" in r for r in rows if f"| T{d:02d}-" in r and "-SE" not in r))
        self.assertEqual(sum("Spiegel" in r.split("|")[5] for r in reels), 12)  # 50/50 seit 20.11.2026

    def test_story_slots(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import plan
        self.assertEqual(plan.norm_slot("t5 sn"), "T05-SN")
        self.assertEqual(plan.norm_slot("T02-SE"), "T02-SE")
        self.assertEqual(plan.norm_slot("T03-S"), "T03-S")
        self.assertEqual(plan.slot_kind("T05-SP"), "story")
        self.assertEqual(plan.highlight_for("T05-SP"), "START")
        self.assertEqual(plan.highlight_for("T06-SE"), "Erfolg")
        self.assertEqual(plan.highlight_for("T11-SN", "Highlight Über mich: wer …"), "Über mich")

    def test_roll(self):
        for cmd, ok in (("pitch-nurture", {"Pitch", "Nurture"}), ("caption-variant", {"a", "b"})):
            seen = set()
            for _ in range(40):
                seen.add(subprocess.run([sys.executable, str(ROOT / "scripts" / "roll.py"), cmd], capture_output=True, text=True).stdout.strip())
            self.assertEqual(seen, ok)

    def test_validate_repo(self):
        p = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate_repo.py")], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()


class TestAufhaengung(unittest.TestCase):
    """Lernregel 20.11.2026: Was hängt, braucht eine sichtbare Aufhängung (KW48-F13)."""
    def _warns(self, text):
        class R:
            def __init__(self): self.w = []
            def warn(self, g, m): self.w.append(m)
        sys.path.insert(0, str(ROOT / "scripts"))
        import qa_check
        r = R()
        qa_check.check_hanging(r, None, text)
        return r.w

    def test_schaukel_ohne_geruest_warnt(self):
        self.assertTrue(self._warns("An empty wooden swing hangs still on its chains."))

    def test_schaukel_mit_querbalken_ok(self):
        self.assertFalse(self._warns("The swing hangs from two chains attached to the visible crossbeam."))
