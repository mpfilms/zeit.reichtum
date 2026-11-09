#!/usr/bin/env python3
"""Wochen-Medien-Pool für @zeit.reichtum: Fotos und Videos einmal pro Woche erzeugen, mehrfach nutzen.

  media.py init [2026-KW47] --plan-woche 1   Ordner anlegen und Zuteilung festlegen (Standard: nächste KW)
  media.py plan 2026-KW47                     Zuteilung zeigen: Foto-IDs pro Tag, Video-Dateien pro Reel
  media.py status [2026-KW47]                 was fehlt noch (Fotos, Videos von Pamina)
  media.py scan                               eigene Fotos in medien/eigene/ ohne Eintrag auflisten
  media.py add-eigen DATEI --ort garten --licht abendlicht [--farbe salbei] [--stimmung ruhig]
                                              eigenes Foto aufnehmen: sprechender Name, Metadaten (GPS!) entfernt
  media.py pick SLOT [--kw 2026-KW47]         passende Medien für einen Post (JSON)
  media.py use SLOT ID [ID …] [--force]       Verwendung eintragen (Feed-Regel wird geprüft)
  media.py path ID                            Dateipfad zu einer ID

Ablage (nicht im öffentlichen Repo, siehe .gitignore):
  medien/<KW>/fotos/<KW>-F01_<ort>-<licht>-<farbe>.jpg   Gemini-Fotos der Woche (9:16)
  medien/<KW>/videos/T01-R1.mp4                          Reel-Videos, von Pamina manuell erzeugt
  medien/<KW>/woche.json                                 Zuteilung der Woche
  medien/eigene/eigen-001_<ort>-<licht>.jpg              Paminas eigene Fotos
  medien/bildliste.jsonl                                 alle Fotos mit Beschreibung und Verwendung

Regeln: Pro Woche 9 Fotos (1 pro Tag, an Karussell-Tagen 2) und 12 Reel-Videos.
Im Feed (Karussell) wird ein Foto höchstens einmal in 42 Tagen genutzt; in Stories beliebig oft.
"""
import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEDIA = ROOT / "medien"
OWN = MEDIA / "eigene"
LIST = MEDIA / "bildliste.jsonl"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan  # noqa: E402

FEED_PAUSE_DAYS = 42
VIDEO_EXT = (".mp4", ".mov", ".m4v")
PHOTO_EXT = (".jpg", ".jpeg", ".png", ".webp", ".heic")


# ---------- Hilfen ----------
def slug(s):
    s = s.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:40]


def norm_kw(s=None):
    """'KW47' | '2026-KW47' | None (= nächste Kalenderwoche) → '2026-KW47'."""
    if not s:
        d = datetime.date.today()
        d += datetime.timedelta(days=7 - d.weekday())  # nächster Montag
        y, w, _ = d.isocalendar()
        return f"{y}-KW{w:02d}"
    m = re.match(r"^(?:(\d{4})-)?kw\s*0*(\d{1,2})$", s.strip().lower())
    if not m:
        sys.exit(f"Unbekannte Kalenderwoche: {s!r} (erwartet z. B. 2026-KW47)")
    y = int(m.group(1) or datetime.date.today().year)
    return f"{y}-KW{int(m.group(2)):02d}"


def read_list():
    if not LIST.exists():
        return []
    out = []
    for line in LIST.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def write_list(recs):
    LIST.parent.mkdir(parents=True, exist_ok=True)
    LIST.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs), encoding="utf-8")


def upsert(rec):
    recs = [r for r in read_list() if r["id"] != rec["id"]]
    old = {r["id"]: r for r in read_list()}.get(rec["id"])
    if old:
        rec.setdefault("verwendet", old.get("verwendet", []))
    rec.setdefault("verwendet", [])
    recs.append(rec)
    write_list(recs)


def week_file(kw):
    return MEDIA / kw / "woche.json"


def load_week(kw):
    f = week_file(kw)
    if not f.exists():
        sys.exit(f"Woche {kw} ist nicht angelegt: python3 scripts/media.py init {kw} --plan-woche 1")
    return json.loads(f.read_text(encoding="utf-8"))


def allocation(kw, plan_woche):
    """Feste Zuteilung: Fotos pro Tag (Karussell-Tage 2), ein Video pro Reel-Slot."""
    days = range(1, 8) if plan_woche == 1 else range(8, 15)
    fotos, videos, n = [], [], 0
    for day in days:
        k = day in plan.CAROUSEL_DAYS
        for _ in range(2 if k else 1):
            n += 1
            zweck = [f"T{day:02d}-K", f"T{day:02d}-S"] if k else [f"T{day:02d}-S"]
            fotos.append({"id": f"{kw}-F{n:02d}", "tag": day, "zweck": zweck})
        for r in ("R1",) if k else ("R1", "R2"):
            slot = f"T{day:02d}-{r}"
            videos.append({"id": f"{kw}-{slot}", "tag": day, "slot": slot, "datei": f"videos/{slot}.mp4"})
    return {"kw": kw, "plan_woche": plan_woche, "tage": list(days), "fotos": fotos, "videos": videos,
            "slide_design": {str(d): plan.slide_design(d) for d in days}}


def find_video(kw, slot):
    for ext in VIDEO_EXT:
        p = MEDIA / kw / "videos" / f"{slot}{ext}"
        if p.exists():
            return p
    return None


def photo_path(rec):
    p = ROOT / rec["datei"] if rec.get("datei") else None
    return p if p and p.exists() else None


def strip_metadata(src, dst):
    """Kopie ohne EXIF/GPS (Wohnort!). HEIC wird über sips (macOS) zu JPEG."""
    try:
        from PIL import Image, ImageOps
    except ImportError:
        sys.exit("Für eigene Fotos fehlt Pillow: python3 -m pip install -r requirements.txt")
    src = Path(src)
    tmp = None
    if src.suffix.lower() == ".heic":
        if not shutil.which("sips"):
            sys.exit("HEIC kann hier nicht gelesen werden – bitte als JPEG exportieren")
        tmp = Path(tempfile.mkdtemp()) / "x.jpg"
        subprocess.run(["sips", "-s", "format", "jpeg", str(src), "--out", str(tmp)], check=True,
                       capture_output=True)
        src = tmp
    img = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    clean = Image.new("RGB", img.size)
    clean.paste(img)  # neue Bilddaten ohne Metadaten
    clean.save(dst, "JPEG", quality=94)
    if tmp:
        shutil.rmtree(tmp.parent, ignore_errors=True)


def recent_feed_use(rec, days=FEED_PAUSE_DAYS):
    today = datetime.date.today()
    for u in rec.get("verwendet", []):
        if u.get("feed") and (today - datetime.date.fromisoformat(u["datum"])).days < days:
            return u
    return None


# ---------- Befehle ----------
def cmd_init(kw, plan_woche):
    kw = norm_kw(kw)
    for sub in ("fotos", "videos"):
        (MEDIA / kw / sub).mkdir(parents=True, exist_ok=True)
    OWN.mkdir(parents=True, exist_ok=True)
    f = week_file(kw)
    if f.exists():
        print(f"{kw} existiert schon – Zuteilung bleibt unverändert")
    else:
        f.write_text(json.dumps(allocation(kw, plan_woche), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Woche angelegt: {f.relative_to(ROOT)}")
    cmd_plan(kw)


def cmd_plan(kw):
    w = load_week(norm_kw(kw))
    rows = {r["slot"]: r for r in plan.parse_plan()}
    print(f"\n{w['kw']} · Plan-Woche {w['plan_woche']} (Tag {w['tage'][0]}-{w['tage'][-1]})\n")
    print("Fotos (Gemini, 9:16):")
    for p in w["fotos"]:
        info = " + ".join(f"{s} ({rows.get(s, {}).get('fmt', '?')})" for s in p["zweck"])
        print(f"  {p['id']} · Tag {p['tag']} · {info}")
    print("\nVideos (von Pamina in Luma/Runway erzeugt):")
    for v in w["videos"]:
        r = rows.get(v["slot"], {})
        print(f"  {v['slot']} · {r.get('fmt', '?')} · {r.get('fokus', '?')} → medien/{w['kw']}/{v['datei']}")


def cmd_status(kw):
    kws = [norm_kw(kw)] if kw else sorted(p.parent.name for p in MEDIA.glob("*/woche.json"))
    if not kws:
        print("Noch keine Woche angelegt (media.py init).")
    recs = {r["id"]: r for r in read_list()}
    for k in kws:
        w = load_week(k)
        fm = [p["id"] for p in w["fotos"] if not (recs.get(p["id"]) and photo_path(recs[p["id"]]))]
        vm = [v["slot"] for v in w["videos"] if not find_video(k, v["slot"])]
        print(f"{k}: Fotos {len(w['fotos']) - len(fm)}/{len(w['fotos'])}, Videos {len(w['videos']) - len(vm)}/{len(w['videos'])}")
        if fm:
            print(f"  fehlende Fotos: {', '.join(fm)}")
        if vm:
            print(f"  fehlende Videos (medien/{k}/videos/<SLOT>.mp4): {', '.join(vm)}")
    new = unregistered_own()
    if new:
        print(f"Eigene Fotos ohne Eintrag: {len(new)} (media.py scan)")


def unregistered_own():
    known = {Path(r["datei"]).name for r in read_list() if r.get("quelle") == "eigen"}
    return sorted(p for p in OWN.glob("*") if p.suffix.lower() in PHOTO_EXT and p.name not in known) if OWN.exists() else []


def cmd_scan():
    new = unregistered_own()
    if not new:
        print("Keine neuen eigenen Fotos in medien/eigene/.")
    for p in new:
        print(p.relative_to(ROOT))


def cmd_add_eigen(datei, ort, licht, farbe, stimmung):
    src = Path(datei)
    if not src.exists():
        sys.exit(f"Datei nicht gefunden: {src}")
    OWN.mkdir(parents=True, exist_ok=True)
    nums = [int(m.group(1)) for r in read_list() if (m := re.match(r"eigen-(\d+)", r["id"]))]
    rid = f"eigen-{(max(nums) + 1) if nums else 1:03d}"
    name = "-".join(x for x in (slug(ort), slug(licht), slug(farbe or "")) if x)
    dst = OWN / f"{rid}_{name}.jpg"
    strip_metadata(src, dst)
    if src.resolve() != dst.resolve() and src.resolve().parent == OWN.resolve():
        src.unlink()  # Original mit Metadaten nicht liegen lassen
    upsert({"id": rid, "datei": str(dst.relative_to(ROOT)), "quelle": "eigen", "kw": None, "tag": None,
            "ort": ort, "licht": licht, "stoff": farbe, "motiv": stimmung, "zweck": ["Story"]})
    print(f"{rid}: {dst.relative_to(ROOT)} (Metadaten entfernt)")


def register_photo(rid, datei, meta):
    """Von render_images.py --week aufgerufen."""
    rec = {"id": rid, "datei": str(Path(datei).resolve().relative_to(ROOT)), "quelle": "gemini"}
    rec.update(meta)
    upsert(rec)


def kw_for_slot(slot, kw):
    if kw:
        return norm_kw(kw)
    day = int(slot[1:3])
    pw = 1 if day <= 7 else 2
    cands = sorted(p.parent.name for p in MEDIA.glob("*/woche.json")
                   if json.loads(p.read_text(encoding="utf-8")).get("plan_woche") == pw)
    if not cands:
        return None
    return cands[-1]


def pick(slot, kw=None):
    slot = plan.norm_slot(slot)
    day = int(slot[1:3])
    kw = kw_for_slot(slot, kw)
    out = {"slot": slot, "kw": kw, "slide_design": plan.slide_design(day), "fotos": [], "video": None,
           "eigene_vorschlag": [], "hinweise": []}
    if not kw:
        out["hinweise"].append("Keine Wochen-Medien für diese Plan-Woche (Skill woche-vorbereiten)")
        return out
    w = load_week(kw)
    recs = {r["id"]: r for r in read_list()}
    if slot.endswith(("-R1", "-R2")):
        v = next((v for v in w["videos"] if v["slot"] == slot), None)
        if v:
            p = find_video(kw, slot)
            out["video"] = {"id": v["id"], "datei": str(p.relative_to(ROOT)) if p else None}
            if not p:
                out["hinweise"].append(f"Video fehlt noch: medien/{kw}/{v['datei']}")
        return out
    for f in w["fotos"]:
        if slot in f["zweck"]:
            r = recs.get(f["id"])
            path = photo_path(r) if r else None
            out["fotos"].append({"id": f["id"], "datei": str(path.relative_to(ROOT)) if path else None,
                                 "ort": (r or {}).get("ort")})
            if not path:
                out["hinweise"].append(f"Foto {f['id']} ist noch nicht erzeugt")
            elif slot.endswith("-K") and (u := recent_feed_use(r)) and u["slot"] != slot:
                out["hinweise"].append(f"{f['id']} war schon im Feed ({u['slot']}, {u['datum']})")
    if slot.endswith("-S"):
        cutoff = datetime.date.today() - datetime.timedelta(days=14)
        for r in read_list():
            if r.get("quelle") == "eigen" and photo_path(r) and not any(
                    datetime.date.fromisoformat(u["datum"]) >= cutoff for u in r.get("verwendet", [])):
                out["eigene_vorschlag"].append({"id": r["id"], "datei": r["datei"], "ort": r.get("ort")})
    return out


def cmd_use(slot, ids, force):
    slot = plan.norm_slot(slot)
    feed = slot.endswith("-K")
    recs = read_list()
    by = {r["id"]: r for r in recs}
    for i in ids:
        if i not in by:
            sys.exit(f"Unbekannte ID: {i}")
        u = recent_feed_use(by[i])
        if feed and u and u["slot"] != slot and not force:
            sys.exit(f"{i} war am {u['datum']} schon im Feed ({u['slot']}) – Pause {FEED_PAUSE_DAYS} Tage (--force)")
    today = datetime.date.today().isoformat()
    for i in ids:
        r = by[i]
        r["verwendet"] = [u for u in r.get("verwendet", []) if u["slot"] != slot]
        r["verwendet"].append({"slot": slot, "feed": feed, "datum": today})
    write_list(recs)
    print(f"{slot}: Verwendung eingetragen für {', '.join(ids)}")


def cmd_path(rid):
    r = {x["id"]: x for x in read_list()}.get(rid)
    if not r or not photo_path(r):
        sys.exit(f"Keine Datei zu {rid}")
    print(photo_path(r))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("kw", nargs="?"); p.add_argument("--plan-woche", type=int, choices=(1, 2), required=True)
    p = sub.add_parser("plan"); p.add_argument("kw")
    p = sub.add_parser("status"); p.add_argument("kw", nargs="?")
    sub.add_parser("scan")
    p = sub.add_parser("add-eigen"); p.add_argument("datei"); p.add_argument("--ort", required=True)
    p.add_argument("--licht", required=True); p.add_argument("--farbe"); p.add_argument("--stimmung")
    p = sub.add_parser("pick"); p.add_argument("slot", nargs="+"); p.add_argument("--kw")
    p = sub.add_parser("use"); p.add_argument("slot"); p.add_argument("ids", nargs="+"); p.add_argument("--force", action="store_true")
    p = sub.add_parser("path"); p.add_argument("id")
    a = ap.parse_args()
    if a.cmd == "init":
        cmd_init(a.kw, a.plan_woche)
    elif a.cmd == "plan":
        cmd_plan(a.kw)
    elif a.cmd == "status":
        cmd_status(a.kw)
    elif a.cmd == "scan":
        cmd_scan()
    elif a.cmd == "add-eigen":
        cmd_add_eigen(a.datei, a.ort, a.licht, a.farbe, a.stimmung)
    elif a.cmd == "pick":
        print(json.dumps(pick(" ".join(a.slot), a.kw), ensure_ascii=False, indent=2))
    elif a.cmd == "use":
        cmd_use(a.slot, a.ids, a.force)
    elif a.cmd == "path":
        cmd_path(a.id)


if __name__ == "__main__":
    main()
