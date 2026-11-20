#!/usr/bin/env python3
"""Macht aus den Story-Slides kurze Videos mit durchlaufender Musik.

    python3 scripts/render_story.py T03-S                 # je Slide ein Video, Musik automatisch
    python3 scripts/render_story.py T03-S --sekunden 8    # Länge pro Slide (Standard 7 s)
    python3 scripts/render_story.py T03-S --musik M06     # bestimmtes Stück

Instagram und Facebook nehmen Ton in Storys nur bei Videos. Deshalb wird jede Slide (output/<slot>/slides/slide-N.png)
ein Video story-N.mp4 (1080x1920). Die Musik ist EIN zusammenhängender Abschnitt eines Stücks, der in so viele
aufeinanderfolgende Stücke geteilt wird, wie es Slides gibt: Story 1 bekommt den Anfang, Story 2 die Fortsetzung usw.
So klingt es beim Durchtippen wie ein Stück. Einblenden nur am Anfang von Story 1, Ausblenden nur am Ende der letzten.
Lautstärke wie bei Reels (musik.MUSIK_ZIEL_DB). Verwendung wird in medien/musikliste.jsonl eingetragen.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import musik  # noqa: E402

ROOT = musik.ROOT
W, H = 1080, 1920


def slides_of(slot):
    d = ROOT / "output" / slot / "slides"
    num = lambda p: int(re.search(r"(\d+)", p.stem).group(1))
    s = sorted(d.glob("slide-*.png"), key=num)
    if not s:
        sys.exit(f"Keine Slides in output/{slot}/slides/ (erst render_images.py ausführen)")
    return s


def choose_music(slot, total, datum, wanted):
    """Gibt (Datensatz, Startsekunde) zurück: ein zusammenhängender Abschnitt von `total` Sekunden."""
    recs = musik.read_list()
    if wanted and wanted != "auto":
        rec = next((r for r in recs if r["id"] == wanted), None)
        if not rec:
            sys.exit(f"Unbekanntes Musikstück: {wanted}")
        return rec, 0.0 if rec["dauer"] >= total else sys.exit(f"{wanted} ist mit {rec['dauer']:.0f} s zu kurz für {total:.0f} s")
    p = musik.pick(slot, datum)
    if p:
        rec = next(r for r in recs if r["id"] == p["id"])
        start = min(p["start"], max(0.0, rec["dauer"] - total))
        if rec["dauer"] >= total:
            return rec, start
    # Ausweichen: Stück mit genug Länge, nicht an Nachbartagen verwendet (pick() hat sie schon aussortiert → hier nur Länge)
    import datetime
    day = datetime.date.fromisoformat(datum) if datum else datetime.date.today()
    for r in sorted(recs, key=lambda r: len(r.get("verwendet", []))):
        if r["dauer"] < total or not (ROOT / r["datei"]).exists():
            continue
        if any(abs((day - datetime.date.fromisoformat(u["datum"])).days) <= musik.NACHBAR_TAGE for u in r.get("verwendet", [])):
            continue
        return r, 0.0
    sys.exit("Kein Musikstück mit genug Länge frei (medien/musik/).")


def cmd(slide, out, music, start, D, gain_db, first, last):
    fades = []
    if first:
        fades.append("afade=t=in:st=0:d=0.6")
    if last:
        fades.append(f"afade=t=out:st={D - 1.2:.2f}:d=1.2")
    af = ",".join([f"aformat=sample_rates=44100:channel_layouts=stereo,volume={gain_db:.1f}dB"] + fades + ["alimiter=limit=0.89"])
    return ["ffmpeg", "-y", "-v", "error",
            "-loop", "1", "-framerate", "30", "-t", f"{D}", "-i", str(slide),
            "-ss", f"{start:.3f}", "-t", f"{D}", "-i", str(music),
            "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,format=yuv420p",
            "-af", af, "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-profile:v", "high", "-r", "30",
            "-c:a", "aac", "-b:a", "160k", "-t", f"{D}", "-movflags", "+faststart", str(out)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slot")
    ap.add_argument("--sekunden", type=float, default=7.0, help="Länge pro Slide (Standard 7)")
    ap.add_argument("--musik", default="auto", help="auto | M## (Standard auto)")
    ap.add_argument("--musik-lautstaerke", type=float, default=1.0, help="Faktor auf die Ziel-Lautstärke (1.0 = wie Reels)")
    ap.add_argument("--datum", help="YYYY-MM-DD (Standard heute)")
    a = ap.parse_args()
    slides = slides_of(a.slot)
    D = a.sekunden
    total = D * len(slides)
    rec, start = choose_music(a.slot, total, a.datum, a.musik)
    gain = musik.MUSIK_ZIEL_DB - rec.get("laut_db", -18.0) + (0 if a.musik_lautstaerke == 1.0 else
                                                             20 * __import__("math").log10(a.musik_lautstaerke))
    outdir = ROOT / "output" / a.slot
    for old in outdir.glob("story-*.mp4"):
        old.unlink()
    for i, s in enumerate(slides):
        out = outdir / f"story-{i + 1}.mp4"
        r = subprocess.run(cmd(s, out, ROOT / rec["datei"], start + i * D, D, gain, i == 0, i == len(slides) - 1),
                           capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"ffmpeg-Fehler bei {s.name}: {r.stderr.strip()[-500:]}")
        print(f"  {out.relative_to(ROOT)} ({D:.0f} s, Musik {rec['id']} {start + i * D:.0f}-{start + (i + 1) * D:.0f} s)")
    musik.use(a.slot, rec["id"], start, a.datum)
    print(f"Fertig: {len(slides)} Story-Videos, durchlaufende Musik {rec['id']} ab {start:.0f} s ({total:.0f} s).")


if __name__ == "__main__":
    main()
