"""Tests für scripts/musik.py und die Musik-Mischung in render_reel.py (mit synthetischen Tönen, ohne echte Musik)."""
import datetime
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import musik  # noqa: E402
import render_reel as rr  # noqa: E402

HAVE_FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")


def tone(path, secs, freq=330):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={secs}",
                    str(path)], check=True)


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg fehlt")
class Musik(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self._old = (musik.ROOT, musik.DIR, musik.LIST)
        musik.ROOT, musik.DIR, musik.LIST = t, t / "medien" / "musik", t / "medien" / "musikliste.jsonl"
        musik.DIR.mkdir(parents=True)
        for i, secs in enumerate((35, 35, 25)):
            tone(musik.DIR / f"Stueck {i}.mp3", secs, 300 + i * 50)
        musik.scan()

    def tearDown(self):
        musik.ROOT, musik.DIR, musik.LIST = self._old
        self.tmp.cleanup()

    def test_scan_names_and_segments(self):
        recs = musik.read_list()
        self.assertEqual([r["id"] for r in recs], ["M01", "M02", "M03"])
        self.assertEqual([len(musik.segments(r)) for r in recs], [3, 3, 2])
        self.assertTrue(recs[0]["datei"].startswith("medien/musik/M01_"))

    def test_same_track_not_on_neighbour_days(self):
        d = datetime.date(2026, 11, 18)
        a = musik.pick("T03-R1", d.isoformat())
        musik.use("T03-R1", a["id"], a["start"], d.isoformat())
        b = musik.pick("T04-R1", (d + datetime.timedelta(days=1)).isoformat())
        self.assertNotEqual(a["id"], b["id"])

    def test_segment_pause_30_days(self):
        d = datetime.date(2026, 11, 18)
        used = set()
        for i in range(8):  # genau 8 Abschnitte vorhanden (3+3+2)
            day = (d + datetime.timedelta(days=i * 2)).isoformat()
            p = musik.pick(f"T{i:02d}-R1", day)
            self.assertIsNotNone(p, i)
            self.assertNotIn((p["id"], p["start"]), used)
            used.add((p["id"], p["start"]))
            musik.use(f"T{i:02d}-R1", p["id"], p["start"], day)
        # alle Abschnitte benutzt und jünger als 30 Tage → nichts frei; nach 30 Tagen wieder alles frei
        self.assertIsNone(musik.pick("T20-R1", (d + datetime.timedelta(days=17)).isoformat()))
        self.assertIsNotNone(musik.pick("T21-R1", (d + datetime.timedelta(days=60)).isoformat()))

    def test_same_slot_gets_same_segment(self):
        d = "2026-11-18"
        a = musik.pick("T03-R1", d)
        musik.use("T03-R1", a["id"], a["start"], d)
        again = musik.pick("T03-R1", d)
        self.assertEqual((a["id"], a["start"]), (again["id"], again["start"]))


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg fehlt")
class Mix(unittest.TestCase):
    def test_music_is_mixed_into_reel_audio(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            vid, mus, out = t / "v.mp4", t / "m.mp3", t / "out.mp4"
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:s=720x1280:d=3",
                            "-f", "lavfi", "-i", "sine=frequency=500:duration=3", "-shortest", str(vid)], check=True)
            tone(mus, 12)
            cmd = rr.ffmpeg_cmd(vid, [], "original", 3.0, out, True, (mus, 1.0, -12.0), 1.0)
            r = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
                                "stream=codec_name,channels", "-of", "csv=p=0", str(out)], capture_output=True, text=True)
            self.assertIn("aac", p.stdout)
            # ohne Musik bleibt es beim Originalton
            cmd2 = rr.ffmpeg_cmd(vid, [], "original", 3.0, t / "o2.mp4", True)
            self.assertEqual(subprocess.run(cmd2, capture_output=True, text=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg fehlt")
class ReelCheck(unittest.TestCase):
    def test_check_reel_accepts_vertical_and_rejects_landscape(self):
        import publish
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            ok, bad = t / "ok.mp4", t / "bad.mp4"
            for f, size in ((ok, "720x1280"), (bad, "1280x720")):
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=gray:s={size}:d=4",
                                "-f", "lavfi", "-i", "sine=duration=4", "-shortest", str(f)], check=True)
            orig_root = publish.ROOT
            publish.ROOT = t
            try:
                secs, w, h, ton = publish.check_reel(ok)
                self.assertTrue(ton and (w, h) == (720, 1280))
                with self.assertRaises(publish.Fehler):
                    publish.check_reel(bad)
            finally:
                publish.ROOT = orig_root
