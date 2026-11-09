#!/usr/bin/env python3
"""14-Tage-Content-Plan (Blaupause aus data/brand-dna.md / CLAUDE.md).

  plan.py generate [--force]      Gerüst erzeugen (Hook-Ideen bleiben erhalten, --force setzt sie zurück)
  plan.py slot T05-R1             Zeile als JSON ausgeben (auch: "5 reel1", "t3-k")
  plan.py set-hook T05-R1 "Idee"  Hook-Idee eintragen
  plan.py show                    Tabelle ausgeben

Regeln (Wochenrhythmus, gilt für Woche 1 = Tag 1-7 und Woche 2 = Tag 8-14):
- Start Montag, Tag 7 und 14 = Sonntag (Sunday Mode).
- Karussell-Tage = Tag 3 und 6 jeder Woche (Tag 3, 6, 10, 13): 1 Morgen-Reel (06:45) + 1 Karussell (12:30).
- Alle anderen Tage: Morgen-Reel (06:45) + Abend-Reel (20:00). → 12 Reels + 2 Karussells pro Woche.
- Jeden Tag 1 Story-Sequenz (17:30), Slot Txx-S.
- Pro Tag je 1 Pitch und 1 Nurture im Feed, Reihenfolge wechselnd (ungerade Tage: erster Post Pitch).
  Stories: gerade Tage Pitch, ungerade Nurture, Sonntag immer Nurture.
- Fokus rotiert A-D. Reels: jedes 4. Reel ist ein Spiegel (75/25). Karussells abwechselnd Leuchtturm/Spiegel.
- Slide-Design wechselt nur von Tag zu Tag: ungerade Tage „glas“ (sehr transparente Karte),
  gerade Tage „ohne“ (Text direkt auf dem Foto).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "data" / "content-plan.md"
WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
FOCUS = {
    "A": "Erschöpfung am Morgen / Funktionieren-Müssen",
    "B": "Mental Load / Gedanken am Abend",
    "C": "Fehlender Selbstwert",
    "D": "Der Ausbruch / Die Erkenntnis",
    "S": "Sunday Mode: Loslassen, Quality Time, durchatmen",
}
HEAD = "| Slot | Tag & Uhrzeit | Format & Typ | Fokus | Stil | Hook-Idee |"
SEP = "|---|---|---|---|---|---|"
OPEN = "(offen)"


CAROUSEL_DAYS = {3, 6, 10, 13}
STORY_TIME = "17:30"


def slide_design(day):
    """Slide-Look pro Tag (nie gemischt innerhalb eines Tages)."""
    return "glas" if day % 2 else "ohne"


def build_rows():
    rows = []
    reel_n = carousel_n = 0

    def row(slot, day, time, fmt, pitch, code, stil):
        short = WEEKDAYS[(day - 1) % 7][:2]
        focus = "Sunday Mode" if code == "S" else f"{code}) {FOCUS[code]}"
        rows.append({"slot": slot, "tag": f"Tag {day} · {short} · {time}",
                     "fmt": f"{fmt} · {'Pitch' if pitch else 'Nurture'}",
                     "fokus": focus, "stil": stil, "hook": OPEN})

    for day in range(1, 15):
        sunday = (day - 1) % 7 == 6
        first_pitch = day % 2 == 1
        # Reel 1 (Morgen)
        row(f"T{day:02d}-R1", day, "06:45", "Reel 1", first_pitch,
            "S" if sunday else "ABCD"[reel_n % 4], "Spiegel" if reel_n % 4 == 3 else "Leuchtturm")
        reel_n += 1
        if day in CAROUSEL_DAYS:
            row(f"T{day:02d}-K", day, "12:30", "Karussell", not first_pitch,
                "ABCD"[(carousel_n + 1) % 4], "Leuchtturm" if carousel_n % 2 == 0 else "Spiegel")
            carousel_n += 1
        else:
            row(f"T{day:02d}-R2", day, "20:00", "Reel 2", not first_pitch,
                "S" if sunday else "ABCD"[reel_n % 4], "Spiegel" if reel_n % 4 == 3 else "Leuchtturm")
            reel_n += 1
        row(f"T{day:02d}-S", day, STORY_TIME, "Story-Sequenz", day % 2 == 0 and not sunday,
            "S" if sunday else "ABCD"[(day + 2) % 4], "Spiegel" if day % 4 == 0 else "Leuchtturm")
    rows.sort(key=lambda r: (r["slot"][:3], r["tag"].rsplit("· ", 1)[1]))
    return rows


def parse_plan():
    if not PLAN.exists():
        return []
    rows = []
    for line in PLAN.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| T"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 6:
            rows.append(dict(zip(["slot", "tag", "fmt", "fokus", "stil", "hook"], cells)))
    return rows


def write_plan(rows):
    lines = [
        "# 14-Tage-Content-Plan @zeit.reichtum",
        "",
        "Start Montag · Tag 7 und 14 = Sonntag (Sunday Mode) · Erzeugt mit `python3 scripts/plan.py generate`.",
        "Pro Woche: 12 Reels + 2 Karussells (Tag 3 und 6) + täglich 1 Story-Sequenz.",
        "Slide-Design: ungerade Tage „glas“ (sehr transparente Karte), gerade Tage „ohne“ (Text direkt aufs Foto).",
        "Einzelne Posts anfordern, z. B. „Reel 1 von Tag 5“ (Slot `T05-R1`), „Story von Tag 2“ (`T02-S`).",
        "",
        HEAD,
        SEP,
    ]
    for r in rows:
        lines.append(f"| {r['slot']} | {r['tag']} | {r['fmt']} | {r['fokus']} | {r['stil']} | {r['hook']} |")
    PLAN.write_text("\n".join(lines) + "\n", encoding="utf-8")


def norm_slot(s):
    s = s.strip().lower().replace("_", "-")
    m = re.match(r"^t?0*(\d{1,2})[-\s]*(?:r(?:eel)?\s*([12])|(k)(?:arussell)?|(s)(?:tory)?)$", s)
    if not m:
        sys.exit(f"Unbekannter Slot: {s!r} (erwartet z. B. T05-R1, T03-K, T02-S)")
    day = int(m.group(1))
    if m.group(2):
        return f"T{day:02d}-R{m.group(2)}"
    return f"T{day:02d}-K" if m.group(3) else f"T{day:02d}-S"


def cmd_generate(force):
    old = {} if force else {r["slot"]: r["hook"] for r in parse_plan()}
    rows = build_rows()
    for r in rows:
        r["hook"] = old.get(r["slot"], OPEN)
    write_plan(rows)
    print(f"Plan geschrieben: {PLAN.relative_to(ROOT)} ({len(rows)} Slots)")


def cmd_slot(arg):
    slot = norm_slot(arg)
    rows = {r["slot"]: r for r in parse_plan()}
    if slot not in rows:
        sys.exit(f"Slot {slot} nicht im Plan. Erst `python3 scripts/plan.py generate` ausführen.")
    r = rows[slot]
    day = int(slot[1:3])
    m = re.search(r"· (\w\w) · (\d\d:\d\d)", r["tag"])
    fmt, _, ausr = r["fmt"].partition(" · ")
    sunday = r["fokus"].startswith("Sunday")
    print(json.dumps({
        "slot": slot,
        "tag": day,
        "wochentag": WEEKDAYS[(day - 1) % 7],
        "uhrzeit": m.group(2) if m else None,
        "format": "Karussell" if fmt.startswith("Karussell") else "Story-Sequenz" if fmt.startswith("Story") else "Reel",
        "woche": 1 if day <= 7 else 2,
        "slide_design": slide_design(day),
        "reel_nummer": int(fmt.split()[1]) if fmt.startswith("Reel") else None,
        "ausrichtung": ausr,
        "fokus": r["fokus"],
        "stil": r["stil"],
        "sunday_mode": sunday,
        "hook_idee": None if r["hook"] == OPEN else r["hook"],
    }, ensure_ascii=False, indent=2))


def cmd_set_hook(arg, text):
    slot = norm_slot(arg)
    rows = parse_plan()
    hit = [r for r in rows if r["slot"] == slot]
    if not hit:
        sys.exit(f"Slot {slot} nicht im Plan.")
    hit[0]["hook"] = text.replace("|", "/").replace("\n", " ").strip() or OPEN
    write_plan(rows)
    print(f"{slot}: Hook-Idee gesetzt")


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    cmd = argv[1]
    if cmd == "generate":
        cmd_generate("--force" in argv)
    elif cmd == "slot" and len(argv) >= 3:
        cmd_slot(" ".join(argv[2:]))
    elif cmd == "set-hook" and len(argv) == 4:
        cmd_set_hook(argv[2], argv[3])
    elif cmd == "show":
        print(PLAN.read_text(encoding="utf-8") if PLAN.exists() else "Noch kein Plan.")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
