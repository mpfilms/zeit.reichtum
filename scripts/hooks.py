#!/usr/bin/env python3
"""Hook-Bank für @zeit.reichtum (data/hook-bank.md) – deterministischer Teil des Skills hook-generator.

  hooks.py check "Hook" [--stil spiegel|leuchtturm] [--box "Textbox (Typ B)"]
                                                     Hook prüfen (Blacklist, Namen, ss, Länge, Dubletten)
  hooks.py add --stil spiegel --fokus B --trigger Paradoxon --einstieg Kontrast --typ A "Hook"
  hooks.py add --stil leuchtturm --fokus S --trigger "Epiktet, Enchiridion 1" --einstieg Zitat --typ A "Hook"
                                                     in die Bank aufnehmen (nur ohne FAIL)
  hooks.py list [--fokus B] [--stil spiegel] [--frei] Bank anzeigen
  hooks.py open                                      offene Plan-Slots + passende freie Hooks
  hooks.py use H007 T05-R1                           Hook in den Plan übernehmen, als verplant markieren
  hooks.py messen H007 --hold 62 --speichern 14 --teilen 5 --start 3
                                                     Insights eintragen (3-Sek.-Rate in %, Anzahl Speichern/Teilen/START)
  hooks.py auswertung                                Durchschnitt je Einstieg, Trigger und Reel-Typ

Exit-Code 1, wenn check/add ein FAIL findet.
"""
import argparse
import difflib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANK = ROOT / "data" / "hook-bank.md"
sys.path.insert(0, str(ROOT / "scripts"))
import plan  # noqa: E402

STILE = {"spiegel": "Spiegel", "leuchtturm": "Leuchtturm"}
FOKUS = ["A", "B", "C", "D", "S"]
TRIGGER = ["Paradoxon", "Validierung", "Umdeutung"]
EINSTIEGE = [
    "Zitat",                       # Leuchtturm
    "Geständnis", "Szene", "Niemand-sagt-dir", "Direkte-Ansprache", "Paradox-Paar", "Stille-Frage",
    "Kontrast", "Alltags-Zahl", "Offene-Schleife", "Quick-Win", "Challenge", "Aber-nicht-so", "Echter-Kommentar",
    "Uhrzeit-Szene", "Dialog", "POV", "Erkennungszeichen", "Zitat-im-Moment",   # seit 20.11.2026 (Szene zuerst)
]
TYPEN = ["A", "B"]
COLS = ["id", "stil", "fokus", "trigger", "einstieg", "typ", "hook", "status", "hold", "speichern", "teilen", "start"]
HEAD = "| ID | Stil | Fokus | Trigger / Quelle | Einstieg | Typ | Hook | Status | 3-Sek. % | Speichern | Teilen | START |"
SEP = "|" + "---|" * len(COLS)
FREI = "frei"
LEER = "–"
HOOK_WARN = 10      # Wörter: in einem Atemzug erfassbar
HOOK_FAIL = 16      # Wörter: Spiegel-Hook zu lang für die erste Einblendung
BOX_MIN, BOX_MAX = 20, 35   # Wörter in der Textbox (Typ B)
SIMILAR = 0.82      # ab dieser Ähnlichkeit gilt ein Hook als Dublette


def lines_of(path):
    if not path.exists():
        return []
    return [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]


def norm(s):
    return re.sub(r"\W+", " ", s.lower()).strip()


def cell(s):
    return s.replace("|", "/").replace("\n", " ").strip()


def read_bank():
    rows = []
    for line in lines_of(BANK):
        if not line.startswith("| H"):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) == 6:  # altes Format ohne Einstieg/Typ/Messwerte
            c = c[:4] + [LEER, LEER] + c[4:] + [LEER] * 4
        if len(c) == len(COLS):
            rows.append(dict(zip(COLS, c)))
    return rows


def write_bank(rows):
    out = [
        "# Hook-Bank @zeit.reichtum",
        "",
        "Vorrat geprüfter Hooks. Erzeugt mit dem Skill `hook-generator`, gepflegt mit `python3 scripts/hooks.py`.",
        "Fokus: A Erschöpfung am Morgen · B Mental Load am Abend · C Fehlender Selbstwert · D Ausbruch/Erkenntnis · S Sunday Mode.",
        "Typ: A = Ein-Satz-Reel (nur Hook) · B = Schichten-Reel (Überschrift + Textbox + Schlusszeile).",
        "Leuchttürme nur mit belegter Quelle (siehe `data/quotes.md`). Status: frei · verplant Txx-xx · benutzt.",
        "Messwerte aus den Instagram-Insights nach ca. 48 h: `hooks.py messen H001 --hold 62 --speichern 14 --teilen 5 --start 3`.",
        "",
        HEAD,
        SEP,
    ]
    for r in rows:
        out.append("| " + " | ".join(r[k] for k in COLS) + " |")
    BANK.write_text("\n".join(out) + "\n", encoding="utf-8")


def fokus_of(plan_cell):
    m = re.match(r"^([A-D])\)", plan_cell)
    return m.group(1) if m else "S"


def content_rules(text, label, fails, warns):
    """Regeln, die für Hook und Textbox gleichermassen gelten."""
    low = text.lower()
    for w in lines_of(ROOT / "data" / "blacklist.txt"):
        if w.lower() in low:
            fails.append(f"{label}: Blacklist-Wort '{w}'")
    for n in lines_of(ROOT / "data" / "forbidden-names.txt"):
        if n.lower() in low:
            fails.append(f"{label}: Verbotener Name (Ersteller/Kurs)")
    if re.search(r"\bworkshop\b", low):
        fails.append(f"{label}: 'Workshop' → 'kostenloses Info-Video'")
    if re.search(r"stoi(sch|ker|zismus)", low):
        fails.append(f"{label}: 'stoisch/Stoiker' → Alltagssprache ('gelassen', 'alte Weisheit')")
    if "ß" in text:
        fails.append(f"{label}: „ß“ gefunden – Schweizer Schreibweise „ss“")
    if "magic words" in low:
        fails.append(f"{label}: Interner Begriff 'Magic Words'")
    if re.search(r"\d[\d'.,]*\s*(€|euro|eur|franken|chf|fr\.|%|mitglieder|kundinnen|follower)", low) or \
            re.search(r"(€|chf|fr\.)\s*\d", low):
        fails.append(f"{label}: Zahl mit Geld/Prozent/Mitgliedern – nur belegbar und von Pamina bestätigt")
    if re.search(r"\b(garantiert|sofort reich|über nacht|ohne arbeit|million|nebenbei reich)\b", low):
        fails.append(f"{label}: Ergebnisversprechen")
    if re.search(r"\b(nur noch|letzte chance|bevor es zu spät|noch genügend platz|nur heute)\b", low):
        fails.append(f"{label}: künstliche Verknappung")
    if text.count("!") > 1 or re.search(r"\b[A-ZÄÖÜ]{4,}\b", text.replace("START", "")):
        warns.append(f"{label}: Marktschreierisch (mehrere ! oder GROSSBUCHSTABEN) – passt nicht zur ruhigen Boss-Mama")


def check(hook, stil=None, box=None, skip_id=None):
    """Gibt (fails, warns) zurück."""
    fails, warns = [], []
    text = hook.strip().strip("„“\"")
    if not text:
        return ["Hook ist leer"], []
    content_rules(text, "Hook", fails, warns)
    low = text.lower()
    sents = [s for s in re.split(r"(?<=[.!?…])\s+", text) if re.search(r"\w", s)]
    if len(sents) > 2:
        fails.append(f"Hook: {len(sents)} Sätze – maximal 2")
    words = len(text.split())
    if words > HOOK_FAIL and stil != "leuchtturm":
        fails.append(f"Hook: {words} Wörter – über {HOOK_FAIL} passt nicht in die erste Einblendung")
    elif words > HOOK_WARN:
        hint = "Brücke in Einblendung 2 verschieben" if stil == "leuchtturm" else "kürzen"
        warns.append(f"Hook: {words} Wörter – ideal sind höchstens {HOOK_WARN} ({hint})")
    if stil == "spiegel" and re.search(r"(seneca|marc aurel|epiktet|sagte|sprach)", low):
        warns.append("Spiegel-Hooks enthalten keine bekannten Zitate")
    if box is not None:
        b = box.strip()
        content_rules(b, "Textbox", fails, warns)
        bw = len(b.split())
        if not BOX_MIN <= bw <= BOX_MAX:
            warns.append(f"Textbox: {bw} Wörter – für Typ B ideal {BOX_MIN}-{BOX_MAX}")
    # Dubletten gegen Bank und Plan
    pool = [(r["id"], r["hook"]) for r in read_bank() if r["id"] != skip_id]
    pool += [(r["slot"], r["hook"]) for r in plan.parse_plan() if r["hook"] != plan.OPEN]
    for ref, other in pool:
        ratio = difflib.SequenceMatcher(None, norm(text), norm(other)).ratio()
        if ratio >= SIMILAR:
            fails.append(f"Fast identisch mit {ref} ({ratio:.0%}): {other[:60]}")
        elif ratio >= 0.6:
            warns.append(f"Ähnlich wie {ref} ({ratio:.0%}) – Wiederholung vermeiden")
    return fails, warns


def report(hook, fails, warns):
    status = "FAIL" if fails else ("WARN" if warns else "OK")
    print(f"[{status}] {hook}")
    for f in fails:
        print(f"   FAIL  {f}")
    for w in warns:
        print(f"   WARN  {w}")
    return status


def cmd_check(a):
    fails, warns = check(a.hook, a.stil, a.box)
    return 1 if report(a.hook, fails, warns) == "FAIL" else 0


def cmd_add(a):
    fails, warns = check(a.hook, a.stil)
    if report(a.hook, fails, warns) == "FAIL":
        print("Nicht aufgenommen.")
        return 1
    if a.stil == "spiegel" and a.trigger not in TRIGGER:
        sys.exit(f"Spiegel braucht --trigger {'|'.join(TRIGGER)}")
    if a.stil == "leuchtturm" and len(a.trigger) < 5:
        sys.exit("Leuchtturm braucht --trigger mit Quelle, z. B. \"Seneca, Epistulae morales 1,1\"")
    rows = read_bank()
    nr = max([int(r["id"][1:]) for r in rows] + [0]) + 1
    hid = f"H{nr:03d}"
    rows.append({"id": hid, "stil": STILE[a.stil], "fokus": a.fokus, "trigger": cell(a.trigger),
                 "einstieg": a.einstieg, "typ": a.typ, "hook": cell(a.hook.strip().strip("„“\"")),
                 "status": FREI, "hold": LEER, "speichern": LEER, "teilen": LEER, "start": LEER})
    write_bank(rows)
    print(f"{hid} aufgenommen.")
    return 0


def cmd_list(a):
    rows = read_bank()
    if a.fokus:
        rows = [r for r in rows if r["fokus"] == a.fokus]
    if a.stil:
        rows = [r for r in rows if r["stil"] == STILE[a.stil]]
    if a.frei:
        rows = [r for r in rows if r["status"] == FREI]
    if not rows:
        print("Keine Hooks gefunden.")
    for r in rows:
        print(f"{r['id']} | {r['stil']:<10} | {r['fokus']} | {r['trigger']:<28} | {r['einstieg']:<17} | "
              f"{r['typ']} | {r['status']:<14} | {r['hook']}")
    return 0


def cmd_open(a):
    bank = [r for r in read_bank() if r["status"] == FREI]
    rows = [r for r in plan.parse_plan() if r["hook"] == plan.OPEN]
    if not rows:
        print("Alle Plan-Slots haben eine Hook-Idee.")
    for r in rows:
        f = fokus_of(r["fokus"])
        typ = plan.reel_typ(r["slot"]) or "–"
        match = [b["id"] for b in bank if b["fokus"] == f and b["stil"] == r["stil"] and b["typ"] in (typ, LEER)]
        print(f"{r['slot']} | {r['fmt']:<22} | {f} | {r['stil']:<10} | Typ {typ} | frei in Bank: {', '.join(match) or '–'}")
    print(f"\n{len(rows)} offene Slots, {len(bank)} freie Hooks in der Bank.")
    return 0


def cmd_use(a):
    rows = read_bank()
    hit = [r for r in rows if r["id"] == a.id.upper()]
    if not hit:
        sys.exit(f"{a.id} nicht in der Bank.")
    slot = plan.norm_slot(a.slot)
    prow = [r for r in plan.parse_plan() if r["slot"] == slot]
    if not prow:
        sys.exit(f"Slot {slot} nicht im Plan.")
    h, p = hit[0], prow[0]
    if h["status"] != FREI:
        print(f"Hinweis: {h['id']} ist bereits '{h['status']}'.")
    if h["stil"] != p["stil"] or h["fokus"] != fokus_of(p["fokus"]):
        print(f"Hinweis: Hook ist {h['stil']}/{h['fokus']}, Slot verlangt {p['stil']}/{fokus_of(p['fokus'])}.")
    typ = plan.reel_typ(slot)
    if typ and h["typ"] not in (typ, LEER):
        print(f"Hinweis: Hook ist für Reel-Typ {h['typ']} gedacht, Slot ist Typ {typ}.")
    plan.cmd_set_hook(slot, h["hook"])
    h["status"] = f"verplant {slot}"
    write_bank(rows)
    print(f"{h['id']} → {slot}")
    return 0


def cmd_messen(a):
    rows = read_bank()
    hit = [r for r in rows if r["id"] == a.id.upper()]
    if not hit:
        sys.exit(f"{a.id} nicht in der Bank.")
    h = hit[0]
    for k in ("hold", "speichern", "teilen", "start"):
        v = getattr(a, k)
        if v is not None:
            h[k] = f"{v:g}"
    if h["status"].startswith("verplant") or h["status"] == FREI:
        h["status"] = "benutzt"
    write_bank(rows)
    print(f"{h['id']}: 3-Sek. {h['hold']} % · Speichern {h['speichern']} · Teilen {h['teilen']} · START {h['start']}")
    return 0


def num(v):
    try:
        return float(v)
    except ValueError:
        return None


def cmd_auswertung(a):
    rows = [r for r in read_bank() if any(num(r[k]) is not None for k in ("hold", "speichern", "teilen", "start"))]
    if not rows:
        print("Noch keine Messwerte. Nach ca. 48 h mit `hooks.py messen …` eintragen.")
        return 0
    print(f"{len(rows)} gemessene Hooks. Aussagekräftig erst ab ca. 3 Posts pro Gruppe.\n")
    for key, title in (("einstieg", "Einstieg"), ("trigger", "Trigger"), ("typ", "Reel-Typ"), ("stil", "Stil")):
        groups = {}
        for r in rows:
            g = r[key] if key != "trigger" or r["stil"] == "Spiegel" else "Zitat"
            groups.setdefault(g, []).append(r)
        print(f"## {title}")
        print(f"{'':<18} {'n':>3} {'3-Sek. %':>9} {'Speichern':>10} {'Teilen':>7} {'START':>6}")
        stats = []
        for g, rs in groups.items():
            avg = []
            for k in ("hold", "speichern", "teilen", "start"):
                vals = [num(r[k]) for r in rs if num(r[k]) is not None]
                avg.append(sum(vals) / len(vals) if vals else None)
            stats.append((g, len(rs), avg))
        stats.sort(key=lambda s: -(s[2][0] or 0))
        for g, n, avg in stats:
            cells = " ".join(f"{(f'{v:.1f}' if v is not None else '–'):>{w}}" for v, w in zip(avg, (9, 10, 7, 6)))
            print(f"{g:<18} {n:>3} {cells}")
        print()
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description="Hook-Bank @zeit.reichtum")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("hook")
    c.add_argument("--stil", choices=STILE)
    c.add_argument("--box", help="Textbox eines Typ-B-Reels mitprüfen")
    c = sub.add_parser("add")
    c.add_argument("hook")
    c.add_argument("--stil", choices=STILE, required=True)
    c.add_argument("--fokus", choices=FOKUS, required=True)
    c.add_argument("--trigger", required=True)
    c.add_argument("--einstieg", choices=EINSTIEGE, required=True)
    c.add_argument("--typ", choices=TYPEN, required=True)
    c = sub.add_parser("list")
    c.add_argument("--fokus", choices=FOKUS)
    c.add_argument("--stil", choices=STILE)
    c.add_argument("--frei", action="store_true")
    sub.add_parser("open")
    c = sub.add_parser("use")
    c.add_argument("id")
    c.add_argument("slot")
    c = sub.add_parser("messen")
    c.add_argument("id")
    c.add_argument("--hold", type=float, help="Zuschauerinnen nach 3 Sekunden in %%")
    c.add_argument("--speichern", type=float)
    c.add_argument("--teilen", type=float)
    c.add_argument("--start", type=float, help="Kommentare mit START")
    sub.add_parser("auswertung")
    a = ap.parse_args(argv)
    return {"check": cmd_check, "add": cmd_add, "list": cmd_list, "open": cmd_open, "use": cmd_use,
            "messen": cmd_messen, "auswertung": cmd_auswertung}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
