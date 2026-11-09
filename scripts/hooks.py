#!/usr/bin/env python3
"""Hook-Bank für @zeit.reichtum (data/hook-bank.md) – deterministischer Teil des Skills hook-generator.

  hooks.py check "Hook" [--stil spiegel|leuchtturm]   Hook prüfen (Blacklist, Namen, ss, Länge, Dubletten)
  hooks.py add --stil spiegel --fokus B --trigger Paradoxon "Hook"
  hooks.py add --stil leuchtturm --fokus S --trigger "Epiktet, Enchiridion 1" "Hook"
                                                     in die Bank aufnehmen (nur ohne FAIL)
  hooks.py list [--fokus B] [--stil spiegel] [--frei] Bank anzeigen
  hooks.py open                                      offene Plan-Slots + passende freie Hooks
  hooks.py use H007 T05-R1                           Hook in den Plan übernehmen, in der Bank als verplant markieren

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
HEAD = "| ID | Stil | Fokus | Trigger / Quelle | Hook | Status |"
SEP = "|---|---|---|---|---|---|"
FREI = "frei"
MAX_WORDS = 22      # On-Screen in 1-2 Sekunden lesbar
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
        if len(c) == 6:
            rows.append(dict(zip(["id", "stil", "fokus", "trigger", "hook", "status"], c)))
    return rows


def write_bank(rows):
    out = [
        "# Hook-Bank @zeit.reichtum",
        "",
        "Vorrat geprüfter Hooks. Erzeugt mit dem Skill `hook-generator`, gepflegt mit `python3 scripts/hooks.py`.",
        "Fokus: A Erschöpfung am Morgen · B Mental Load am Abend · C Fehlender Selbstwert · D Ausbruch/Erkenntnis · S Sunday Mode.",
        "Leuchttürme nur mit belegter Quelle (siehe `data/quotes.md`). Status: frei · verplant Txx-xx · benutzt.",
        "",
        HEAD,
        SEP,
    ]
    for r in rows:
        out.append("| " + " | ".join(r[k] for k in ["id", "stil", "fokus", "trigger", "hook", "status"]) + " |")
    BANK.write_text("\n".join(out) + "\n", encoding="utf-8")


def fokus_of(plan_cell):
    m = re.match(r"^([A-D])\)", plan_cell)
    return m.group(1) if m else "S"


def check(hook, stil=None, skip_id=None):
    """Gibt (fails, warns) zurück."""
    fails, warns = [], []
    text = hook.strip().strip("„“\"")
    low = text.lower()
    if not text:
        return ["Hook ist leer"], []
    for w in lines_of(ROOT / "data" / "blacklist.txt"):
        if w.lower() in low:
            fails.append(f"Blacklist-Wort '{w}'")
    for n in lines_of(ROOT / "data" / "forbidden-names.txt"):
        if n.lower() in low:
            fails.append("Verbotener Name (Ersteller/Kurs)")
    if re.search(r"\bworkshop\b", low):
        fails.append("'Workshop' → 'kostenloses Info-Video'")
    if "ß" in text:
        fails.append("„ß“ gefunden – Schweizer Schreibweise „ss“")
    if "magic words" in low:
        fails.append("Interner Begriff 'Magic Words'")
    sents = [s for s in re.split(r"(?<=[.!?…])\s+", text) if re.search(r"\w", s)]
    if len(sents) > 2:
        fails.append(f"{len(sents)} Sätze – maximal 2")
    words = len(text.split())
    if words > MAX_WORDS:
        warns.append(f"{words} Wörter – über {MAX_WORDS} ist On-Screen schwer in 2 Sekunden lesbar")
    if re.search(r"\d+\s*(€|euro|eur|franken|chf|%|mitglieder|kundinnen)", low):
        fails.append("Zahl mit Geld/Prozent/Mitgliedern – nur belegbar und von Pamina bestätigt")
    if re.search(r"\b(garantiert|sofort reich|passives einkommen über nacht|ohne arbeit)\b", low):
        fails.append("Ergebnisversprechen")
    if text.count("!") > 1 or re.search(r"[A-ZÄÖÜ]{5,}", text):
        warns.append("Marktschreierisch (mehrere ! oder GROSSBUCHSTABEN) – passt nicht zur ruhigen Boss-Mama")
    if stil == "spiegel" and re.search(r"(seneca|marc aurel|epiktet|sagte|sprach)", low):
        warns.append("Spiegel-Hooks enthalten keine bekannten Zitate")
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
    fails, warns = check(a.hook, a.stil)
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
                 "hook": cell(a.hook.strip().strip("„“\"")), "status": FREI})
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
        print(f"{r['id']} | {r['stil']:<10} | {r['fokus']} | {r['trigger']:<28} | {r['status']:<14} | {r['hook']}")
    return 0


def cmd_open(a):
    bank = [r for r in read_bank() if r["status"] == FREI]
    rows = [r for r in plan.parse_plan() if r["hook"] == plan.OPEN]
    if not rows:
        print("Alle Plan-Slots haben eine Hook-Idee.")
    for r in rows:
        f = fokus_of(r["fokus"])
        match = [b["id"] for b in bank if b["fokus"] == f and b["stil"] == r["stil"]]
        print(f"{r['slot']} | {r['fmt']:<22} | {f} | {r['stil']:<10} | frei in Bank: {', '.join(match) or '–'}")
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
    plan.cmd_set_hook(slot, h["hook"])
    h["status"] = f"verplant {slot}"
    write_bank(rows)
    print(f"{h['id']} → {slot}")
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description="Hook-Bank @zeit.reichtum")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("hook")
    c.add_argument("--stil", choices=STILE)
    c = sub.add_parser("add")
    c.add_argument("hook")
    c.add_argument("--stil", choices=STILE, required=True)
    c.add_argument("--fokus", choices=FOKUS, required=True)
    c.add_argument("--trigger", required=True)
    c = sub.add_parser("list")
    c.add_argument("--fokus", choices=FOKUS)
    c.add_argument("--stil", choices=STILE)
    c.add_argument("--frei", action="store_true")
    sub.add_parser("open")
    c = sub.add_parser("use")
    c.add_argument("id")
    c.add_argument("slot")
    a = ap.parse_args(argv)
    return {"check": cmd_check, "add": cmd_add, "list": cmd_list, "open": cmd_open, "use": cmd_use}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
