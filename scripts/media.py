#!/usr/bin/env python3
"""Wochen-Medien-Pool für @zeit.reichtum: Fotos und Videos einmal pro Woche erzeugen, mehrfach nutzen.

  media.py init [2026-KW47] --plan-woche 1   Ordner anlegen und Zuteilung festlegen (Standard: nächste KW)
  media.py plan 2026-KW47                     Zuteilung zeigen: Foto-IDs pro Tag, Video-Dateien pro Reel
  media.py status [2026-KW47]                 was fehlt noch (Fotos, Videos von Pamina)
  media.py scan                               eigene Fotos in medien/eigene/ ohne Eintrag auflisten
  media.py add-eigen DATEI --ort garten --licht abendlicht [--farbe salbei] [--stimmung ruhig]
                                              eigenes Foto aufnehmen: sprechender Name, Metadaten (GPS!) entfernt
                                              [--fuer 2026-KW47-F04]  erfüllt einen Foto-Wunsch
  media.py wunsch 2026-KW47 2026-KW47-F04 "Laptop am Küchentisch abends, ohne Gesichter" [--bis "Tag 3"]
                                              Foto-Wunsch an Pamina: dieses Foto lieber echt statt Gemini
  media.py pick SLOT [--kw 2026-KW47]         passende Medien für einen Post (JSON)
  media.py use SLOT ID [ID …] [--force]       Verwendung eintragen (Feed-Regel wird geprüft)
  media.py path ID                            Dateipfad zu einer ID

Monats-Video-Pool (18 Videos pro Monat, jedes bis zu 3× verwendet: original, gespiegelt, gespiegelt + Ausschnitt):
  media.py monat-init [2026-12]               Ordner medien/videos/<Monat>/ und 18 Video-IDs anlegen
  media.py monat-status [2026-12]             welche Videos fehlen noch, wie oft wurde welches verwendet
  media.py add-video DATEI --ort balkon --stimmung ruhig [--fokus B]
                                              eigenes Video aufnehmen: 9:16, Metadaten (GPS!) entfernt
  media.py video-pick SLOT [--datum 2026-12-03]   passendes Video + Variante für ein Reel (JSON)
  media.py video-use SLOT ID VARIANTE [--datum …] Verwendung eintragen (macht render_reel.py automatisch)

Ablage (nicht im öffentlichen Repo, siehe .gitignore):
  medien/<KW>/fotos/<KW>-F01_<ort>-<licht>-<farbe>.jpg   Gemini-Fotos der Woche (9:16)
  medien/<KW>/videos/T01-R1.mp4                          (alt) Reel-Videos pro Woche
  medien/videos/2026-12/2026-12-V01.mp4                  Monats-Videos, von Pamina in einer App erzeugt
  medien/eigene-videos/eigen-v001_<ort>.mp4              Paminas eigene Videos
  medien/videoliste.jsonl                                alle Videos mit Verwendung
  medien/<KW>/woche.json                                 Zuteilung der Woche
  medien/eigene/eigen-001_<ort>-<licht>.jpg              Paminas eigene Fotos
  medien/bildliste.jsonl                                 alle Fotos mit Beschreibung und Verwendung

Foto-Wünsche: Für einzelne Foto-IDs kann ein eigenes Foto von Pamina gewünscht werden. Solange der Wunsch
offen ist, erzeugt render_images.py --week dafür kein Gemini-Bild (spart Kosten); kommt kein Foto, wird es
später gezielt nachgeholt (render_images.py … --week --only <ID>).

Regeln: Pro Woche 9 Fotos (1 pro Tag, an Karussell-Tagen 2). Videos kommen aus dem Monats-Pool:
18 pro Monat, jedes höchstens 3× und frühestens nach 10 Tagen wieder.
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
VLIST = MEDIA / "videoliste.jsonl"
VPOOL = MEDIA / "videos"
OWN_V = MEDIA / "eigene-videos"
MONTH_FOKUS = ["A"] * 4 + ["B"] * 4 + ["C"] * 3 + ["D"] * 3 + ["S"] * 4   # 18 Videos
VARIANTS = ["original", "spiegel", "ausschnitt"]
VIDEO_PAUSE_DAYS = 10
sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan  # noqa: E402

FEED_PAUSE_DAYS = 42
SIMILAR_DAYS = 1   # ähnliche Videos (gleiche Gruppe) brauchen mindestens 2 Tage Abstand
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
    """Feste Zuteilung: Fotos pro Tag (Karussell-Tage 2). Videos kommen aus dem Monats-Pool."""
    days = range(1, 8) if plan_woche == 1 else range(8, 15)
    fotos, videos, n = [], [], 0
    for day in days:
        # 2 Stories pro Tag (Pamina, 2026-11-19): eigenes Foto für Nurture- und Verkaufs-Story,
        # an Karussell-Tagen zusätzlich 2 Karussell-Fotos (Story-Foto ≠ Karussell-Foto am selben Tag)
        zwecke = [[f"T{day:02d}-SN"], [f"T{day:02d}-SP"]]
        if day in plan.CAROUSEL_DAYS:
            zwecke += [[f"T{day:02d}-K"], [f"T{day:02d}-K"]]
        for zweck in zwecke:
            n += 1
            fotos.append({"id": f"{kw}-F{n:02d}", "tag": day, "zweck": zweck})
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
        wish = f"  ← Foto-Wunsch an Pamina: {p['wunsch']['text']}" if p.get("wunsch") else ""
        print(f"  {p['id']} · Tag {p['tag']} · {info}{wish}")
    if w["videos"]:
        print("\nVideos (alte Wochen-Zuteilung):")
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
        fm = [p["id"] for p in w["fotos"] if not p.get("wunsch") and not p.get("eigen")
              and not (recs.get(p["id"]) and photo_path(recs[p["id"]]))]
        vm = [v["slot"] for v in w["videos"] if not find_video(k, v["slot"])]
        print(f"{k}: Fotos {len(w['fotos']) - len(fm)}/{len(w['fotos'])}, Videos {len(w['videos']) - len(vm)}/{len(w['videos'])}")
        if fm:
            print(f"  fehlende Fotos: {', '.join(fm)}")
        if vm:
            print(f"  fehlende Videos (medien/{k}/videos/<SLOT>.mp4): {', '.join(vm)}")
        for f in open_wishes(w):
            print(f"  Foto-Wunsch an dich: {f['id']} für {', '.join(f['zweck'])} – {f['wunsch']['text']} "
                  f"(bis {f['wunsch']['bis']}; in medien/eigene/ legen)")
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
    newv = unregistered_own_videos()
    if newv:
        print("Neue eigene Videos (media.py add-video …):")
    for p in newv:
        print(p.relative_to(ROOT))


def save_week(w):
    week_file(w["kw"]).write_text(json.dumps(w, ensure_ascii=False, indent=2), encoding="utf-8")


def find_week_photo(fid):
    kw = fid.rsplit("-F", 1)[0]
    w = load_week(kw)
    f = next((f for f in w["fotos"] if f["id"] == fid), None)
    if not f:
        sys.exit(f"{fid} gehört nicht zur Zuteilung von {kw}")
    return w, f


def cmd_wunsch(kw, fid, text, bis):
    w, f = find_week_photo(fid)
    if norm_kw(kw) != w["kw"]:
        sys.exit(f"{fid} gehört nicht zu {norm_kw(kw)}")
    f["wunsch"] = {"text": text.strip(), "bis": bis or f"Tag {f['tag']}"}
    save_week(w)
    print(f"Foto-Wunsch für {fid} ({', '.join(f['zweck'])}): {text.strip()} – bis {f['wunsch']['bis']}")


def open_wishes(w):
    return [f for f in w["fotos"] if f.get("wunsch") and not f.get("eigen")]


def cmd_add_eigen(datei, ort, licht, farbe, stimmung, fuer=None, figur=False):
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
            "ort": ort, "licht": licht, "stoff": farbe, "motiv": stimmung, "zweck": ["Story"], "figur": figur})
    print(f"{rid}: {dst.relative_to(ROOT)} (Metadaten entfernt{', mit der Frau' if figur else ''})")
    if fuer:
        w, f = find_week_photo(fuer)
        f["eigen"] = rid
        save_week(w)
        print(f"Foto-Wunsch {fuer} erfüllt: {', '.join(f['zweck'])} nutzt jetzt {rid}")


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
    # mehrere Wochen mit gleicher Plan-Woche: die aktuelle bzw. nächste Kalenderwoche nehmen
    y, w, _ = datetime.date.today().isocalendar()
    now = f"{y}-KW{w:02d}"
    later = [c for c in cands if c >= now]
    return later[0] if later else cands[-1]


def pick(slot, kw=None):
    slot = plan.norm_slot(slot)
    day = int(slot[1:3])
    kw = kw_for_slot(slot, kw)
    out = {"slot": slot, "kw": kw, "slide_design": plan.slide_design(day), "fotos": [], "video": None,
           "eigene_vorschlag": [], "hinweise": []}
    if slot.endswith(("-R1", "-R2")):
        old = load_week(kw)["videos"] if kw else []
        if not any(v["slot"] == slot for v in old):
            out["video"] = video_pick(slot)
            if not out["video"]:
                out["hinweise"].append("Kein freies Video im Monats-Pool (media.py monat-status) – Skill videos-monat")
            return out
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
    zweck_of = lambda f: f["zweck"]
    if plan.is_story(slot) and slot[-1] in "NP" and not any(slot in f["zweck"] for f in w["fotos"]):
        zweck_of = lambda f: legacy_story_zweck(w, f, slot, day)
    for f in w["fotos"]:
        if slot in zweck_of(f) and f.get("eigen") and recs.get(f["eigen"]) and photo_path(recs[f["eigen"]]):
            r = recs[f["eigen"]]
            out["fotos"].append({"id": r["id"], "datei": r["datei"], "ort": r.get("ort"), "ersetzt": f["id"]})
            continue
        if slot in zweck_of(f):
            if f.get("wunsch") and not (recs.get(f["id"]) and photo_path(recs[f["id"]])):
                out["hinweise"].append(
                    f"Foto-Wunsch {f['id']} offen ({f['wunsch']['text']}): Pamina fragen; ohne Foto Gemini-Ersatz mit "
                    f"render_images.py output/woche-{kw}.md --week --only {f['id']}")
            r = recs.get(f["id"])
            path = photo_path(r) if r else None
            out["fotos"].append({"id": f["id"], "datei": str(path.relative_to(ROOT)) if path else None,
                                 "ort": (r or {}).get("ort")})
            if not path:
                out["hinweise"].append(f"Foto {f['id']} ist noch nicht erzeugt")
            elif slot.endswith("-K") and (u := recent_feed_use(r)) and u["slot"] != slot:
                out["hinweise"].append(f"{f['id']} war schon im Feed ({u['slot']}, {u['datum']})")
    if plan.is_story(slot):
        cutoff = datetime.date.today() - datetime.timedelta(days=14)
        for r in read_list():
            if r.get("quelle") == "eigen" and photo_path(r) and not any(
                    datetime.date.fromisoformat(u["datum"]) >= cutoff for u in r.get("verwendet", [])):
                out["eigene_vorschlag"].append({"id": r["id"], "datei": r["datei"], "ort": r.get("ort")})
    return out


def legacy_story_zweck(w, f, slot, day):
    """Ältere Wochen (1 Story-Foto pro Tag, Zweck Txx-S): Nurture-Story nimmt das Story-Foto des Tags (wenn es
    kein Karussell-Foto ist), die Verkaufs-Story ein Foto eines anderen Tags (nie ein Karussell-Foto dieses Tags)."""
    legacy, kar = f"T{day:02d}-S", f"T{day:02d}-K"
    if slot.endswith("-SN"):
        first = next((x for x in w["fotos"] if legacy in x["zweck"] and kar not in x["zweck"]), None)
        if first:
            return [slot] if first is f else []
        offset = 2
    else:
        offset = 3
    own = [x for x in w["fotos"] if x["tag"] != day and kar not in x["zweck"]]
    if not own:
        return []
    best = min(own, key=lambda x: (abs(((x["tag"] - day) % 7) - offset), x["tag"], x["id"]))
    return [slot] if best is f else []


def cmd_use(slot, ids, force):
    slot = plan.norm_slot(slot)
    feed = slot.endswith(("-K", "-R1", "-R2"))  # Karussell und Reel-Titelbild stehen im Profilraster
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


# ---------- Monats-Video-Pool ----------
def norm_month(s=None):
    """'2026-12' | '12' | None (= nächster Monat) → '2026-12'."""
    today = datetime.date.today()
    if not s:
        y, m = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
        return f"{y}-{m:02d}"
    mm = re.match(r"^(?:(\d{4})-)?0?(\d{1,2})$", s.strip())
    if not mm or not 1 <= int(mm.group(2)) <= 12:
        sys.exit(f"Unbekannter Monat: {s!r} (erwartet z. B. 2026-12)")
    return f"{int(mm.group(1) or today.year)}-{int(mm.group(2)):02d}"


def read_vlist():
    if not VLIST.exists():
        return []
    return [json.loads(l) for l in VLIST.read_text(encoding="utf-8").splitlines() if l.strip()]


def write_vlist(recs):
    VLIST.parent.mkdir(parents=True, exist_ok=True)
    VLIST.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs), encoding="utf-8")


def month_file(m):
    return VPOOL / m / "monat.json"


def find_month_video(m, vid):
    for ext in VIDEO_EXT:
        p = VPOOL / m / f"{vid}{ext}"
        if p.exists():
            return p
    return None


def sync_videos():
    """Videos aus den Monats-Ordnern, die Pamina abgelegt hat, in die Videoliste aufnehmen."""
    recs = read_vlist()
    by = {r["id"]: r for r in recs}
    changed = False
    for mf in sorted(VPOOL.glob("*/monat.json")):
        mon = json.loads(mf.read_text(encoding="utf-8"))
        for v in mon["videos"]:
            if v["id"] in by and by[v["id"]].get("gruppe") != v.get("gruppe"):
                by[v["id"]]["gruppe"] = v.get("gruppe")  # Ähnlichkeits-Gruppe aus monat.json
                changed = True
            p = find_month_video(mon["monat"], v["id"])
            if p and (v["id"] not in by or by[v["id"]].get("datei") != str(p.relative_to(ROOT))):
                rec = by.get(v["id"]) or {"id": v["id"], "verwendet": []}
                rec.update({"datei": str(p.relative_to(ROOT)), "quelle": "app", "monat": mon["monat"],
                            "fokus": v["fokus"], "gruppe": v.get("gruppe"),
                            "prompts": f"output/videos-{mon['monat']}.md"})
                if v["id"] not in by:
                    recs.append(rec)
                    by[v["id"]] = rec
                changed = True
    if changed:
        write_vlist(recs)
    return recs


def cmd_monat_init(m):
    m = norm_month(m)
    (VPOOL / m).mkdir(parents=True, exist_ok=True)
    OWN_V.mkdir(parents=True, exist_ok=True)
    f = month_file(m)
    if f.exists():
        print(f"{m} existiert schon – Zuteilung bleibt unverändert")
    else:
        vids = [{"id": f"{m}-V{i + 1:02d}", "fokus": fk} for i, fk in enumerate(MONTH_FOKUS)]
        f.write_text(json.dumps({"monat": m, "videos": vids}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Monat angelegt: {f.relative_to(ROOT)}")
    mon = json.loads(f.read_text(encoding="utf-8"))
    print(f"\n{m}: {len(mon['videos'])} Videos (jedes bis zu 3× verwendbar)")
    for v in mon["videos"]:
        print(f"  {v['id']} · Fokus {v['fokus']} → medien/videos/{m}/{v['id']}.mp4")


def uses(rec):
    return rec.get("verwendet", [])


def cmd_monat_status(m):
    recs = {r["id"]: r for r in sync_videos()}
    months = [norm_month(m)] if m else sorted(p.parent.name for p in VPOOL.glob("*/monat.json"))
    if not months:
        print("Noch kein Monat angelegt (media.py monat-init).")
    for mo in months:
        if not month_file(mo).exists():
            print(f"{mo}: nicht angelegt (media.py monat-init {mo})")
            continue
        mon = json.loads(month_file(mo).read_text(encoding="utf-8"))
        miss = [v["id"] for v in mon["videos"] if not find_month_video(mo, v["id"])]
        frei = sum(3 - min(3, len(uses(recs.get(v["id"], {})))) for v in mon["videos"] if v["id"] not in miss)
        print(f"{mo}: Videos {len(mon['videos']) - len(miss)}/{len(mon['videos'])} vorhanden, "
              f"noch {frei} Verwendungen frei")
        if miss:
            print(f"  fehlend (als medien/videos/{mo}/<ID>.mp4 ablegen): {', '.join(miss)}")
    own = [r for r in recs.values() if r.get("quelle") == "eigen"]
    if own:
        print(f"Eigene Videos: {len(own)}, noch {sum(3 - min(3, len(uses(r))) for r in own)} Verwendungen frei")
    newv = unregistered_own_videos()
    if newv:
        print(f"Neue eigene Videos ohne Eintrag: {len(newv)} (media.py scan)")


def unregistered_own_videos():
    known = {Path(r["datei"]).name for r in read_vlist() if r.get("quelle") == "eigen"}
    return sorted(p for p in OWN_V.glob("*") if p.suffix.lower() in VIDEO_EXT and p.name not in known) \
        if OWN_V.exists() else []


def cmd_add_video(datei, ort, stimmung, fokus):
    src = Path(datei)
    if not src.exists():
        sys.exit(f"Datei nicht gefunden: {src}")
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg fehlt (brew install ffmpeg)")
    OWN_V.mkdir(parents=True, exist_ok=True)
    recs = read_vlist()
    nums = [int(mm.group(1)) for r in recs if (mm := re.match(r"eigen-v(\d+)", r["id"]))]
    vid = f"eigen-v{(max(nums) + 1) if nums else 1:03d}"
    dst = OWN_V / f"{vid}_{slug(ort)}.mp4"
    # 9:16 zuschneiden, Metadaten (GPS, Gerät, Datum) entfernen, Ton behalten
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-map", "0:v:0", "-map", "0:a:0?",
           "-map_metadata", "-1", "-map_chapters", "-1",
           "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30",
           "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(dst)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"ffmpeg-Fehler: {r.stderr.strip()[-400:]}")
    if src.resolve().parent == OWN_V.resolve():
        src.unlink()  # Original mit Metadaten nicht liegen lassen
    recs.append({"id": vid, "datei": str(dst.relative_to(ROOT)), "quelle": "eigen", "monat": None,
                 "fokus": fokus or "-", "ort": ort, "stimmung": stimmung, "verwendet": []})
    write_vlist(recs)
    print(f"{vid}: {dst.relative_to(ROOT)} (9:16, Metadaten entfernt)")


def slot_fokus(slot):
    row = {r["slot"]: r for r in plan.parse_plan()}.get(slot)
    if not row:
        return None
    m = re.match(r"^([A-D])\)", row["fokus"])
    return m.group(1) if m else "S"


def video_pick(slot, datum=None):
    """Video für ein Reel: Fokus passend, höchstens 3 Verwendungen, mindestens 10 Tage Pause."""
    slot = plan.norm_slot(slot)
    day = datetime.date.fromisoformat(datum) if datum else datetime.date.today()
    recs = [r for r in sync_videos() if (ROOT / r["datei"]).exists()]
    for r in recs:  # schon zugeteilt (z. B. neu rendern) → gleiche Variante
        for u in uses(r):
            if u["slot"] == slot:
                return {"id": r["id"], "datei": r["datei"], "variante": u["variante"], "quelle": r["quelle"],
                        "fokus": r.get("fokus"), "prompts": r.get("prompts"), "schon_verwendet": True}
    fk = slot_fokus(slot)
    # Ähnliche Szenen (gleiche "gruppe") nie am selben oder am Nachbartag: sonst wirken zwei Reels hintereinander gleich
    nah = {r["gruppe"] for r in recs if r.get("gruppe") for u in uses(r)
           if u["slot"] != slot and abs((day - datetime.date.fromisoformat(u["datum"])).days) <= SIMILAR_DAYS}
    cands = []
    for r in recs:
        if r.get("gesperrt"):  # z. B. Bildfehler im Video: nie mehr verwenden
            continue
        if r.get("gruppe") and r["gruppe"] in nah:
            continue
        us = [u for u in uses(r)]
        if len(us) >= len(VARIANTS):
            continue
        last = max((datetime.date.fromisoformat(u["datum"]) for u in us), default=None)
        if last and abs((day - last).days) < VIDEO_PAUSE_DAYS:
            continue
        match = 0 if r.get("fokus") == fk else (1 if r.get("fokus") in ("-", None) else 2)
        if fk == "S" and match == 2:
            match = 3  # Sunday Mode möglichst nur mit ruhigen Sonntags-Videos
        cands.append((match, len(us), last or datetime.date.min, r["id"], r))
    if not cands:
        return None
    cands.sort(key=lambda c: c[:4])
    r = cands[0][4]
    return {"id": r["id"], "datei": r["datei"], "variante": VARIANTS[len(uses(r))], "quelle": r["quelle"],
            "fokus": r.get("fokus"), "prompts": r.get("prompts"), "schon_verwendet": False}


def video_use(slot, vid, variante, datum=None):
    slot = plan.norm_slot(slot)
    if variante not in VARIANTS:
        sys.exit(f"Variante muss {', '.join(VARIANTS)} sein")
    recs = read_vlist()
    r = next((x for x in recs if x["id"] == vid), None)
    if not r:
        sys.exit(f"Unbekanntes Video: {vid}")
    r["verwendet"] = [u for u in uses(r) if u["slot"] != slot]
    r["verwendet"].append({"slot": slot, "datum": datum or datetime.date.today().isoformat(), "variante": variante})
    write_vlist(recs)
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("kw", nargs="?"); p.add_argument("--plan-woche", type=int, choices=(1, 2), required=True)
    p = sub.add_parser("plan"); p.add_argument("kw")
    p = sub.add_parser("status"); p.add_argument("kw", nargs="?")
    sub.add_parser("scan")
    p = sub.add_parser("add-eigen"); p.add_argument("datei"); p.add_argument("--ort", required=True)
    p.add_argument("--licht", required=True); p.add_argument("--farbe"); p.add_argument("--stimmung")
    p.add_argument("--fuer", help="Foto-ID der Woche, deren Wunsch damit erfüllt ist")
    p.add_argument("--figur", action="store_true", help="Foto zeigt die wiederkehrende Frau (von hinten)")
    p = sub.add_parser("wunsch"); p.add_argument("kw"); p.add_argument("id"); p.add_argument("text"); p.add_argument("--bis")
    p = sub.add_parser("pick"); p.add_argument("slot", nargs="+"); p.add_argument("--kw")
    p = sub.add_parser("use"); p.add_argument("slot"); p.add_argument("ids", nargs="+"); p.add_argument("--force", action="store_true")
    p = sub.add_parser("path"); p.add_argument("id")
    p = sub.add_parser("monat-init"); p.add_argument("monat", nargs="?")
    p = sub.add_parser("monat-status"); p.add_argument("monat", nargs="?")
    p = sub.add_parser("add-video"); p.add_argument("datei"); p.add_argument("--ort", required=True)
    p.add_argument("--stimmung", default="ruhig"); p.add_argument("--fokus", choices=["A", "B", "C", "D", "S"])
    p = sub.add_parser("video-pick"); p.add_argument("slot"); p.add_argument("--datum")
    p = sub.add_parser("video-use"); p.add_argument("slot"); p.add_argument("id"); p.add_argument("variante")
    p.add_argument("--datum")
    a = ap.parse_args()
    if a.cmd == "monat-init":
        return cmd_monat_init(a.monat)
    if a.cmd == "monat-status":
        return cmd_monat_status(a.monat)
    if a.cmd == "add-video":
        return cmd_add_video(a.datei, a.ort, a.stimmung, a.fokus)
    if a.cmd == "video-pick":
        print(json.dumps(video_pick(a.slot, a.datum), ensure_ascii=False, indent=2))
        return
    if a.cmd == "video-use":
        video_use(a.slot, a.id, a.variante, a.datum)
        print(f"{plan.norm_slot(a.slot)}: {a.id} ({a.variante}) eingetragen")
        return
    if a.cmd == "init":
        cmd_init(a.kw, a.plan_woche)
    elif a.cmd == "plan":
        cmd_plan(a.kw)
    elif a.cmd == "status":
        cmd_status(a.kw)
    elif a.cmd == "scan":
        cmd_scan()
    elif a.cmd == "add-eigen":
        cmd_add_eigen(a.datei, a.ort, a.licht, a.farbe, a.stimmung, a.fuer, a.figur)
    elif a.cmd == "wunsch":
        cmd_wunsch(a.kw, a.id, a.text, a.bis)
    elif a.cmd == "pick":
        print(json.dumps(pick(" ".join(a.slot), a.kw), ensure_ascii=False, indent=2))
    elif a.cmd == "use":
        cmd_use(a.slot, a.ids, a.force)
    elif a.cmd == "path":
        cmd_path(a.id)


if __name__ == "__main__":
    main()
