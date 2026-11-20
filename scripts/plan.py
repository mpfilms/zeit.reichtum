#!/usr/bin/env python3
"""14-Tage-Content-Plan (Blaupause aus data/brand-dna.md / CLAUDE.md).

  plan.py generate [--force]      Gerüst erzeugen (Hook-Ideen bleiben erhalten, --force setzt sie zurück)
  plan.py slot T05-R1             Zeile als JSON ausgeben (auch: "5 reel1", "t3-k")
  plan.py set-hook T05-R1 "Idee"  Hook-Idee eintragen
  plan.py set-thema T04-S "Thema" Thema für einen Slot setzen ("" löscht es)
  plan.py themen [--neu]          Wunschthemen aus data/themen-wuensche.md auf freie Slots verteilen
                                  (--neu: alle Themen zurücksetzen und neu verteilen)
  plan.py show                    Tabelle ausgeben
  plan.py kalender [--anker 2026-11-09] [--von 2026-11-11] [--bis 2026-11-30] [--md DATEI]
                                  Plan auf echte Daten legen (Anker = Montag von Plan-Tag 1, wird gemerkt)

Regeln (Wochenrhythmus, gilt für Woche 1 = Tag 1-7 und Woche 2 = Tag 8-14):
- Start Montag, Tag 7 und 14 = Sonntag (Sunday Mode).
- Karussell-Tage = Tag 3 und 6 jeder Woche (Tag 3, 6, 10, 13): 1 Morgen-Reel (06:45) + 1 Karussell (12:30).
- Alle anderen Tage: Morgen-Reel (06:45) + Abend-Reel (20:00). → 12 Reels + 2 Karussells pro Woche.
- Jeden Tag 2 Story-Sequenzen (Pamina, 2026-11-19): Txx-SN = Nurture (08:30), Txx-SP = Verkauf/Pitch (20:30,
  am Sonntag im ruhigen Sunday Mode). Dienstag und Samstag zusätzlich Txx-SE = Community-Erfolg (18:30, echter Erfolg
  aus medien/erfolge/, jeder nur einmal; scripts/erfolg.py). Alte Slots Txx-S (eine Story pro Tag) bleiben lesbar.
- Pro Tag je 1 Pitch und 1 Nurture im Feed, Reihenfolge wechselnd (ungerade Tage: erster Post Pitch).
- Fokus rotiert A-D. Reels und Storys abwechselnd Leuchtturm/Spiegel (50/50, seit 20.11.2026; beide beginnen mit einer Szene). Karussells abwechselnd Leuchtturm/Spiegel.
- Reel-Typ: Morgen-Reel (R1) = A „Ein Satz" (nur Hook, max. ca. 10 Wörter),
  Abend-Reel (R2) = B „Schichten" (Überschrift + Textbox 20-35 Wörter + Schlusszeile; Caption kurz, ohne Wiederholung).
- Slide-Design wechselt nur von Tag zu Tag: ungerade Tage „glas“ (sehr transparente Karte),
  gerade Tage „ohne“ (Text direkt auf dem Foto).
"""
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "data" / "content-plan.md"
WISHES = ROOT / "data" / "themen-wuensche.md"
WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
FOCUS = {
    "A": "Erschöpfung am Morgen / Funktionieren-Müssen",
    "B": "Mental Load / Gedanken am Abend",
    "C": "Fehlender Selbstwert",
    "D": "Der Ausbruch / Die Erkenntnis",
    "S": "Sunday Mode: Loslassen, Quality Time, durchatmen",
}
HEAD = "| Slot | Tag & Uhrzeit | Format & Typ | Fokus | Stil | Thema | Hook-Idee |"
SEP = "|---|---|---|---|---|---|---|"
COLS = ["slot", "tag", "fmt", "fokus", "stil", "thema", "hook"]
NO_THEME = "–"
OPEN = "(offen)"
KALENDER = ROOT / "data" / "kalender.json"
WD = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


CAROUSEL_DAYS = {3, 6, 10, 13}
STORY_TIME = "17:30"          # alte Einzel-Story (Txx-S), nur noch für bestehende Posts
STORY_NURTURE_TIME = "08:30"
STORY_PITCH_TIME = "20:30"
STORY_ERFOLG_TIME = "18:30"
ERFOLG_WEEKDAYS = {1, 5}      # Dienstag, Samstag (0 = Montag)
STORY_RE = re.compile(r"-S[NPE]?$")


def slide_design(day):
    """Slide-Look pro Tag (nie gemischt innerhalb eines Tages)."""
    return "glas" if day % 2 else "ohne"


def build_rows():
    rows = []
    reel_n = carousel_n = 0

    def row(slot, day, time, fmt, pitch, code, stil):
        short = WEEKDAYS[(day - 1) % 7][:2]
        focus = "Sunday Mode" if code == "S" else "–" if code == "-" else f"{code}) {FOCUS[code]}"
        ausr = pitch if isinstance(pitch, str) else ("Pitch" if pitch else "Nurture")
        rows.append({"slot": slot, "tag": f"Tag {day} · {short} · {time}",
                     "fmt": f"{fmt} · {ausr}",
                     "fokus": focus, "stil": stil, "thema": NO_THEME, "hook": OPEN})

    for day in range(1, 15):
        sunday = (day - 1) % 7 == 6
        first_pitch = day % 2 == 1
        # Reel 1 (Morgen)
        row(f"T{day:02d}-R1", day, "06:45", "Reel 1", first_pitch,
            "S" if sunday else "ABCD"[reel_n % 4], "Spiegel" if reel_n % 2 == 1 else "Leuchtturm")
        reel_n += 1
        if day in CAROUSEL_DAYS:
            row(f"T{day:02d}-K", day, "12:30", "Karussell", not first_pitch,
                "ABCD"[(carousel_n + 1) % 4], "Leuchtturm" if carousel_n % 2 == 0 else "Spiegel")
            carousel_n += 1
        else:
            row(f"T{day:02d}-R2", day, "20:00", "Reel 2", not first_pitch,
                "S" if sunday else "ABCD"[reel_n % 4], "Spiegel" if reel_n % 2 == 1 else "Leuchtturm")
            reel_n += 1
        row(f"T{day:02d}-SN", day, STORY_NURTURE_TIME, "Story-Sequenz", False,
            "S" if sunday else "ABCD"[(day + 2) % 4], "Spiegel" if day % 2 == 0 else "Leuchtturm")
        row(f"T{day:02d}-SP", day, STORY_PITCH_TIME, "Story-Sequenz", True,
            "S" if sunday else "ABCD"[(day + 3) % 4], "Spiegel" if day % 2 == 1 else "Leuchtturm")
        if (day - 1) % 7 in ERFOLG_WEEKDAYS:
            row(f"T{day:02d}-SE", day, STORY_ERFOLG_TIME, "Story-Erfolg", "Erfolg", "-", "Community")
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
        if len(cells) == 6:  # alter Plan ohne Thema-Spalte
            cells.insert(5, NO_THEME)
        if len(cells) == 7:
            rows.append(dict(zip(COLS, cells)))
    return rows


def write_plan(rows):
    lines = [
        "# 14-Tage-Content-Plan @zeit.reichtum",
        "",
        "Start Montag · Tag 7 und 14 = Sonntag (Sunday Mode) · Erzeugt mit `python3 scripts/plan.py generate`.",
        "Pro Woche: 12 Reels + 2 Karussells (Tag 3 und 6) + täglich 2 Story-Sequenzen (SN Nurture 08:30, SP Verkauf 20:30) + Di/Sa Community-Erfolg (SE 18:30).",
        "Reel-Typ: Morgen-Reel (R1) = A „Ein Satz“, Abend-Reel (R2) = B „Schichten“ (Überschrift + Textbox + Schlusszeile).",
        "Slide-Design: ungerade Tage „glas“ (sehr transparente Karte), gerade Tage „ohne“ (Text direkt aufs Foto).",
        "Themen aus `data/themen-wuensche.md` verteilt `python3 scripts/plan.py themen`.",
        "Einzelne Posts anfordern, z. B. „Reel 1 von Tag 5“ (Slot `T05-R1`), „Nurture-Story von Tag 2“ (`T02-SN`), „Verkaufs-Story von Tag 2“ (`T02-SP`), „Erfolgs-Story von Tag 2“ (`T02-SE`).",
        "",
        HEAD,
        SEP,
    ]
    for r in rows:
        lines.append("| " + " | ".join(r[c] for c in COLS) + " |")
    PLAN.write_text("\n".join(lines) + "\n", encoding="utf-8")


def norm_slot(s):
    s = s.strip().lower().replace("_", "-")
    m = re.match(r"^t?0*(\d{1,2})[-\s]*(?:r(?:eel)?\s*([12])|(k)(?:arussell)?|s(?:tory)?\s*-?\s*([npe])?)$", s)
    if not m:
        sys.exit(f"Unbekannter Slot: {s!r} (erwartet z. B. T05-R1, T03-K, T02-SN, T02-SP, T02-SE)")
    day = int(m.group(1))
    if m.group(2):
        return f"T{day:02d}-R{m.group(2)}"
    if m.group(3):
        return f"T{day:02d}-K"
    return f"T{day:02d}-S" + (m.group(4) or "").upper()


def cmd_generate(force):
    old = {} if force else {r["slot"]: r for r in parse_plan()}
    rows = build_rows()
    for r in rows:
        src = old.get(r["slot"])
        if not src and r["slot"].endswith(("-SN", "-SP")):  # alte Einzel-Story Txx-S → passende neue Story
            o = old.get(r["slot"][:-1])
            if o and o["fmt"].endswith("Pitch") == r["slot"].endswith("-SP"):
                src = o
        if src:
            r["hook"] = src["hook"]
            r["thema"] = src["thema"]
    write_plan(rows)
    print(f"Plan geschrieben: {PLAN.relative_to(ROOT)} ({len(rows)} Slots)")


def reel_typ(slot):
    """Reel-Typ: Morgen-Reel (R1) = A „Ein Satz", Abend-Reel (R2) = B „Schichten". Sonst None."""
    if slot.endswith("-R1"):
        return "A"
    if slot.endswith("-R2"):
        return "B"
    return None


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
        "format": ("Karussell" if fmt.startswith("Karussell") else "Story-Erfolg" if fmt.startswith("Story-Erfolg")
                   else "Story-Sequenz" if fmt.startswith("Story") else "Reel"),
        "highlight": highlight_for(slot, None if r["thema"] == NO_THEME else r["thema"]),
        "woche": 1 if day <= 7 else 2,
        "slide_design": slide_design(day),
        "reel_nummer": int(fmt.split()[1]) if fmt.startswith("Reel") else None,
        "reel_typ": reel_typ(slot),
        "ausrichtung": ausr,
        "fokus": r["fokus"],
        "stil": r["stil"],
        "sunday_mode": sunday,
        "thema": None if r["thema"] == NO_THEME else r["thema"],
        "thema_hinweise": wish_hints(r["thema"]),
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


def clean_cell(s):
    return s.replace("|", "/").replace("\n", " ").strip()


def read_wishes():
    """Tabelle aus data/themen-wuensche.md → [dict(thema, format, anzahl, tage, hinweise)]."""
    if not WISHES.exists():
        return []
    out = []
    for line in WISHES.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or line.startswith("|---") or line.startswith("| Thema |"):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) < 5 or not c[0]:
            continue
        try:
            n = int(c[2])
        except ValueError:
            n = 1
        tage = [x.strip()[:2].capitalize() for x in re.split(r"[,/ ]+", c[3]) if x.strip()]
        out.append({"thema": clean_cell(c[0]), "format": c[1].strip().lower(), "anzahl": n,
                    "tage": tage, "hinweise": c[4]})
    return out


def wish_hints(thema):
    for w in read_wishes():
        if thema and w["thema"] == thema:
            return w["hinweise"]
    return None


def is_story(slot):
    return bool(STORY_RE.search(slot))


def slot_kind(slot):
    return "karussell" if slot.endswith("-K") else "story" if is_story(slot) else "reel"


# Highlights (Pamina, 2026-11-19): jede Story bekommt ein Ziel-Highlight; Pamina fügt sie in der App hinzu
HIGHLIGHTS = ["START", "Erfolg", "Über mich", "Ehrlich", "Fragen"]


def highlight_for(slot, thema=None):
    if slot.endswith("-SE"):
        return "Erfolg"
    if slot.endswith("-SP"):
        return "START"
    if slot.endswith(("-SN", "-S")) and thema:
        for h in HIGHLIGHTS:  # Thema „Highlight Über mich: …“ aus den Wunschthemen
            if thema.lower().startswith(f"highlight {h.lower()}"):
                return h
        if thema.lower().startswith("q&a"):
            return "Fragen"
        if thema.lower().startswith("community-einblick"):
            return "Erfolg"
    return "–" if is_story(slot) else None


def cmd_themen(reset):
    rows = parse_plan()
    if not rows:
        sys.exit("Noch kein Plan – erst `python3 scripts/plan.py generate`.")
    wishes = read_wishes()
    if not wishes:
        sys.exit(f"Keine Wunschthemen in {WISHES.relative_to(ROOT)}")
    if reset:
        for r in rows:
            r["thema"] = NO_THEME
    report = []
    for w in wishes:
        fmt = w["format"].split("-")[0]
        cands = [r for r in rows if r["thema"] == NO_THEME and (fmt.startswith("bel") or slot_kind(r["slot"]) == fmt)
                 and not r["fokus"].startswith("Sunday")
                 and not r["slot"].endswith(("-SE", "-SP"))]  # Story-Themen in die Nurture-Story; SP verkauft, SE zeigt Erfolge
        if w["tage"]:
            cands = [r for r in cands if WEEKDAYS[(int(r["slot"][1:3]) - 1) % 7][:2] in w["tage"]]
            pick = cands[:w["anzahl"]]
        else:  # gleichmässig über die 14 Tage verteilen
            k = len(cands)
            pick = [cands[round(i * k / w["anzahl"])] for i in range(w["anzahl"])] if k >= w["anzahl"] else cands
        for r in pick:
            r["thema"] = w["thema"]
        report.append(f"{w['thema'][:60]}: {', '.join(r['slot'] for r in pick) or 'kein freier passender Slot'}"
                      + ("" if len(pick) == w["anzahl"] else f" ({len(pick)}/{w['anzahl']})"))
    write_plan(rows)
    print("\n".join(report))


def cmd_set_thema(arg, text):
    slot = norm_slot(arg)
    rows = parse_plan()
    hit = [r for r in rows if r["slot"] == slot]
    if not hit:
        sys.exit(f"Slot {slot} nicht im Plan.")
    hit[0]["thema"] = clean_cell(text) or NO_THEME
    write_plan(rows)
    print(f"{slot}: Thema gesetzt")


def load_kalender():
    return json.loads(KALENDER.read_text(encoding="utf-8")) if KALENDER.exists() else {}


def plan_tag(datum, anker):
    """Datum → Plan-Tag 1-14 (Anker = Montag von Tag 1; danach läuft der 14-Tage-Zyklus weiter)."""
    return (datum - anker).days % 14 + 1


def cmd_kalender(args):
    import argparse
    ap = argparse.ArgumentParser(prog="plan.py kalender")
    ap.add_argument("--anker")
    ap.add_argument("--von")
    ap.add_argument("--bis")
    ap.add_argument("--md")
    a = ap.parse_args(args)
    kal = load_kalender()
    if a.anker:
        anker = datetime.date.fromisoformat(a.anker)
        if anker.weekday() != 0:
            sys.exit("Der Anker muss ein Montag sein (Plan-Tag 1 = Montag).")
        kal["anker"] = anker.isoformat()
    if not kal.get("anker"):
        sys.exit("Noch kein Anker: plan.py kalender --anker <Montag von Plan-Tag 1>")
    if a.von:
        kal["von"] = a.von
    if a.bis:
        kal["bis"] = a.bis
    KALENDER.write_text(json.dumps(kal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    anker = datetime.date.fromisoformat(kal["anker"])
    von = datetime.date.fromisoformat(kal.get("von") or kal["anker"])
    bis = datetime.date.fromisoformat(kal.get("bis") or (von + datetime.timedelta(days=13)).isoformat())
    rows = parse_plan()
    if not rows:
        sys.exit("Kein Plan: python3 scripts/plan.py generate")
    by_day = {}
    for r in rows:
        by_day.setdefault(int(r["slot"][1:3]), []).append(r)
    lines = [f"# Kalender @zeit.reichtum · {von.strftime('%d.%m.')}–{bis.strftime('%d.%m.%Y')}", "",
             f"Plan-Tag 1 = Montag {anker.strftime('%d.%m.%Y')}; der 14-Tage-Plan läuft danach im Kreis weiter.",
             "Fotos: Wochen-Pool der Kalenderwoche (Skill woche-vorbereiten). Videos: Monats-Pool (Skill videos-monat).",
             "Reel-Typ: A = „Ein Satz“ (morgens), B = „Schichten“ (abends).", "",
             "| Datum | Zeit | Slot | Format & Typ | Reel-Typ | Fokus | Stil | Thema | Medien | Hook-Idee |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    weeks = {}
    d = von
    while d <= bis:
        tag = plan_tag(d, anker)
        y, kw, _ = d.isocalendar()
        weeks.setdefault(f"{y}-KW{kw:02d}", set()).add(1 if tag <= 7 else 2)
        for r0 in sorted(by_day.get(tag, []), key=lambda r: r["tag"].split("·")[-1]):
            zeit = r0["tag"].split("·")[-1].strip()
            r = r0
            # Tausch: kalender.json {"tausch": {"2026-11-19 T04-R2": "T02-R2"}} – an diesem Datum und dieser Uhrzeit läuft der andere Slot
            neu = (kal.get("tausch") or {}).get(f"{d.isoformat()} {r0['slot']}")
            if neu:
                r = next((x for x in rows if x["slot"] == neu), r0)
            typ = reel_typ(r["slot"]) or "–"
            fokus = r["fokus"].split(")")[0] if ")" in r["fokus"] else "–" if r["fokus"] == "–" else "Sonntag"
            if r["slot"].endswith(("-R1", "-R2")):
                med = f"Video {d.year}-{d.month:02d} + Titelbild KW{kw:02d}"
            elif r["slot"].endswith("-K"):
                med = f"2 Fotos KW{kw:02d}"
            elif r["slot"].endswith("-SE"):
                med = "Erfolg aus medien/erfolge/"
            else:
                med = f"Foto KW{kw:02d}"
            lines.append(f"| {WD[d.weekday()]} {d.strftime('%d.%m.')} | {zeit} | {r['slot']} | {r['fmt']} | {typ} | "
                         f"{fokus} | {r['stil']} | {r['thema']} | {med} | {r['hook']} |")
        d += datetime.timedelta(days=1)
    lines += ["", "## Medien-Wochen", ""]
    for k, pws in weeks.items():
        lines.append(f"- {k}: Plan-Woche {', '.join(map(str, sorted(pws)))} → "
                     + " / ".join(f"`python3 scripts/media.py init {k} --plan-woche {pw}`" for pw in sorted(pws)))
    text = "\n".join(lines) + "\n"
    if a.md:
        Path(a.md).write_text(text, encoding="utf-8")
        print(f"Geschrieben: {a.md}")
    else:
        print(text)


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
    elif cmd == "set-thema" and len(argv) == 4:
        cmd_set_thema(argv[2], argv[3])
    elif cmd == "themen":
        cmd_themen("--neu" in argv)
    elif cmd == "kalender":
        cmd_kalender(argv[2:])
    elif cmd == "show":
        print(PLAN.read_text(encoding="utf-8") if PLAN.exists() else "Noch kein Plan.")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
