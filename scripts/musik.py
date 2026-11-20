#!/usr/bin/env python3
"""Musik-Pool für Reels (z. B. Soundstripe-Downloads). Jedes Stück wird in 10-Sekunden-Abschnitte geteilt;
jeder Abschnitt darf nach MUSIK_PAUSE_TAGE Tagen wieder verwendet werden, dasselbe Stück nie an Nachbartagen.

  musik.py scan                          neue Dateien in medien/musik/ aufnehmen (benennt sie M01_titel.mp3 usw.)
  musik.py add DATEI [--stimmung TEXT]   einzelne Datei aufnehmen
  musik.py status                        Stücke, Abschnitte, Reichweite in Monaten
  musik.py pick SLOT [--datum D] [--stimmung TEXT]
  musik.py use SLOT ID START [--datum D]

Dateien liegen nur lokal (medien/ ist git-ignoriert). Lizenz: Nachweis (Proof of License) im Soundstripe-Konto.
"""
import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "medien" / "musik"
LIST = ROOT / "medien" / "musikliste.jsonl"
EXT = (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg")
SEG = 10.0                 # Länge eines Abschnitts in Sekunden (Reels sind 9-10 s lang)
MUSIK_ZIEL_DB = -19.0     # Ziel-Lautstärke der Musik im Reel (RMS in dBFS); jedes Stück wird darauf angeglichen
MUSIK_PAUSE_TAGE = 30      # derselbe Abschnitt frühestens nach 30 Tagen wieder
NACHBAR_TAGE = 1           # dasselbe Stück nicht am selben oder an Nachbartagen
REELS_PRO_MONAT = 52       # Plan: 12 Reels pro Woche


def read_list():
    if not LIST.exists():
        return []
    return [json.loads(l) for l in LIST.read_text(encoding="utf-8").splitlines() if l.strip()]


def write_list(recs):
    LIST.parent.mkdir(parents=True, exist_ok=True)
    LIST.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs), encoding="utf-8")


def slug(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")).strip("-")
    return s[:40] or "stueck"


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    try:
        return round(float(r.stdout.strip()), 2)
    except ValueError:
        sys.exit(f"Dauer nicht lesbar (ffprobe): {path}")


def loudness(path):
    """Mittlere Lautstärke (RMS in dBFS) des ganzen Stücks, damit leise und laute Stücke gleich laut ins Reel kommen."""
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(path), "-af", "volumedetect", "-vn", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"mean_volume:\s*(-?[\d.]+) dB", r.stderr)
    return round(float(m.group(1)), 1) if m else -18.0


def segments(rec):
    """Anfangszeiten der vollständigen 10-Sekunden-Abschnitte eines Stücks."""
    d, out, t = rec["dauer"], [], 0.0
    while t + SEG <= d + 0.01:
        out.append(round(t, 2))
        t += SEG
    return out


def add(datei, stimmung=""):
    src = Path(datei)
    if not src.exists():
        sys.exit(f"Datei nicht gefunden: {src}")
    recs = read_list()
    known = {Path(r["datei"]).name for r in recs}
    if src.name in known:
        return None
    nums = [int(m.group(1)) for r in recs if (m := re.match(r"M(\d+)", r["id"]))]
    mid = f"M{(max(nums) + 1) if nums else 1:02d}"
    DIR.mkdir(parents=True, exist_ok=True)
    dst = DIR / f"{mid}_{slug(src.stem)}{src.suffix.lower()}"
    if src.resolve() != dst.resolve():
        shutil.move(str(src), dst)
    rec = {"id": mid, "datei": str(dst.relative_to(ROOT)), "titel": src.stem, "dauer": duration(dst),
           "laut_db": loudness(dst), "stimmung": stimmung, "verwendet": []}
    recs.append(rec)
    write_list(recs)
    return rec


def scan():
    recs = read_list()
    known = {Path(r["datei"]).name for r in recs}
    new = [p for p in sorted(DIR.glob("*")) if p.suffix.lower() in EXT and p.name not in known] if DIR.exists() else []
    for p in new:
        r = add(p)
        print(f"{r['id']}: {r['datei']} ({r['dauer']:.0f} s, {len(segments(r))} Abschnitte)")
    if not new:
        print("Keine neuen Dateien in medien/musik/")


def status():
    recs = read_list()
    if not recs:
        print("Noch keine Musik. MP3 in medien/musik/ legen, dann: python3 scripts/musik.py scan")
        return
    tot = sum(len(segments(r)) for r in recs)
    for r in recs:
        print(f"{r['id']} · {r['dauer']:.0f} s · {len(segments(r))} Abschnitte · {len(r.get('verwendet', []))}× verwendet · {r['titel']}")
    monate = tot * (30 / MUSIK_PAUSE_TAGE) / REELS_PRO_MONAT
    print(f"\n{len(recs)} Stücke, {tot} Abschnitte. Bei {REELS_PRO_MONAT} Reels pro Monat und {MUSIK_PAUSE_TAGE} Tagen Pause "
          f"reicht das für ein Reel ohne Wiederholung eines Abschnitts: {'ja, dauerhaft' if tot >= REELS_PRO_MONAT * MUSIK_PAUSE_TAGE / 30 else 'nein, zu wenig'} "
          f"(Bedarf {round(REELS_PRO_MONAT * MUSIK_PAUSE_TAGE / 30)} Abschnitte, vorhanden {tot}).")


def pick(slot, datum=None, stimmung=None):
    day = datetime.date.fromisoformat(datum) if datum else datetime.date.today()
    recs = read_list()
    for r in recs:  # schon zugeteilt → gleicher Abschnitt (z. B. neu rendern)
        for u in r.get("verwendet", []):
            if u["slot"] == slot:
                return {"id": r["id"], "datei": r["datei"], "start": u["start"], "laenge": SEG, "schon_verwendet": True,
                        "laut_db": r.get("laut_db", -18.0)}
    nah = {r["id"] for r in recs for u in r.get("verwendet", [])
           if abs((day - datetime.date.fromisoformat(u["datum"])).days) <= NACHBAR_TAGE}
    cands = []
    for r in recs:
        if r["id"] in nah or not (ROOT / r["datei"]).exists():
            continue
        if stimmung and stimmung.lower() not in r.get("stimmung", "").lower():
            continue
        for s in segments(r):
            us = [u for u in r.get("verwendet", []) if abs(u["start"] - s) < SEG]
            last = max((datetime.date.fromisoformat(u["datum"]) for u in us), default=None)
            if last and abs((day - last).days) < MUSIK_PAUSE_TAGE:
                continue
            cands.append((len(r.get("verwendet", [])), last or datetime.date.min, len(us), s, r))
    if not cands:
        return None
    cands.sort(key=lambda c: c[:4])
    n, last, k, s, r = cands[0]
    return {"id": r["id"], "datei": r["datei"], "start": s, "laenge": SEG, "schon_verwendet": False,
            "laut_db": r.get("laut_db", -18.0)}


def use(slot, mid, start, datum=None):
    recs = read_list()
    r = next((x for x in recs if x["id"] == mid), None)
    if not r:
        sys.exit(f"Unbekanntes Stück: {mid}")
    for x in recs:
        x["verwendet"] = [u for u in x.get("verwendet", []) if u["slot"] != slot]
    r["verwendet"].append({"slot": slot, "datum": datum or datetime.date.today().isoformat(), "start": float(start)})
    write_list(recs)
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("scan")
    sub.add_parser("status")
    p = sub.add_parser("add"); p.add_argument("datei"); p.add_argument("--stimmung", default="")
    p = sub.add_parser("pick"); p.add_argument("slot"); p.add_argument("--datum"); p.add_argument("--stimmung")
    p = sub.add_parser("use"); p.add_argument("slot"); p.add_argument("id"); p.add_argument("start", type=float)
    p.add_argument("--datum")
    a = ap.parse_args()
    if not shutil.which("ffprobe"):
        sys.exit("ffprobe fehlt (brew install ffmpeg)")
    if a.cmd == "scan":
        scan()
    elif a.cmd == "status":
        status()
    elif a.cmd == "add":
        r = add(a.datei, a.stimmung)
        print(f"{r['id']}: {r['datei']}" if r else "schon bekannt")
    elif a.cmd == "pick":
        print(json.dumps(pick(a.slot, a.datum, a.stimmung), ensure_ascii=False, indent=2))
    else:
        use(a.slot, a.id, a.start, a.datum)
        print(f"{a.slot}: {a.id} ab {a.start:.0f} s eingetragen")


if __name__ == "__main__":
    main()
