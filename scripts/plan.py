#!/usr/bin/env python3
"""14-Tage-Content-Plan (Blaupause aus data/brand-dna.md / CLAUDE.md).

  plan.py generate [--force]      Gerüst erzeugen (Hook-Ideen bleiben erhalten, --force setzt sie zurück)
  plan.py slot T05-R1             Zeile als JSON ausgeben (auch: "5 reel1", "t3-k")
  plan.py set-hook T05-R1 "Idee"  Hook-Idee eintragen
  plan.py show                    Tabelle ausgeben

Regeln: Start Montag, Tag 7 und 14 = Sonntag (Sunday Mode). Pro Tag 1 Morgen-Reel (ca. 06:45)
und 1 Abend-Reel (ca. 20:00), jeden 3. Tag zusätzlich ein Karussell (ca. 12:30). Pro Tag je 1 Pitch-
und 1 Nurture-Reel, Reihenfolge wechselnd (ungerade Tage: Reel 1 Pitch). Fokus rotiert A-D.
Leuchtturm/Spiegel nach 75/25 (jedes 4. Reel ist ein Spiegel).
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


def build_rows():
    rows = []
    carousel_n = 0
    for day in range(1, 15):
        wd = (day - 1) % 7
        sunday = wd == 6
        short = WEEKDAYS[wd][:2]
        for r, time in ((1, "06:45"), (None, "12:30"), (2, "20:00")):
            if r is None:
                if day % 3 != 0 or sunday:
                    continue
                n = carousel_n
                carousel_n += 1
                slot = f"T{day:02d}-K"
                fmt = "Karussell"
                pitch = n % 2 == 1
                code = "S" if sunday else "ABCD"[n % 4]
                stil = "Leuchtturm" if n % 2 == 0 else "Spiegel"
            else:
                idx = (day - 1) * 2 + (r - 1)
                slot = f"T{day:02d}-R{r}"
                fmt = f"Reel {r}"
                pitch = (r == 1) == (day % 2 == 1)
                code = "S" if sunday else "ABCD"[idx % 4]
                stil = "Spiegel" if idx % 4 == 3 else "Leuchtturm"
            focus = "Sunday Mode" if code == "S" else f"{code}) {FOCUS[code]}"
            rows.append({
                "slot": slot,
                "tag": f"Tag {day} · {short} · {time}",
                "fmt": f"{fmt} · {'Pitch' if pitch else 'Nurture'}",
                "fokus": focus,
                "stil": stil,
                "hook": OPEN,
            })
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
        "Einzelne Posts anfordern, z. B. „Reel 1 von Tag 5“ (Slot `T05-R1`).",
        "",
        HEAD,
        SEP,
    ]
    for r in rows:
        lines.append(f"| {r['slot']} | {r['tag']} | {r['fmt']} | {r['fokus']} | {r['stil']} | {r['hook']} |")
    PLAN.write_text("\n".join(lines) + "\n", encoding="utf-8")


def norm_slot(s):
    s = s.strip().lower().replace("_", "-")
    m = re.match(r"^t?0*(\d{1,2})[-\s]*(?:r(?:eel)?\s*([12])|(k)(?:arussell)?)$", s)
    if not m:
        sys.exit(f"Unbekannter Slot: {s!r} (erwartet z. B. T05-R1, T03-K)")
    day = int(m.group(1))
    return f"T{day:02d}-R{m.group(2)}" if m.group(2) else f"T{day:02d}-K"


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
        "format": "Karussell" if fmt.startswith("Karussell") else "Reel",
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
