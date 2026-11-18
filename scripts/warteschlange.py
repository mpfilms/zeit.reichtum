#!/usr/bin/env python3
"""Warteschlange für die automatische Veröffentlichung auf Instagram und Facebook.

    python3 scripts/warteschlange.py add T04-R1 --at "2026-11-19 06:45"   # Dateien hochladen und für die Zeit einplanen (Zürcher Zeit)
    python3 scripts/warteschlange.py add-tag 2026-11-19                   # alle fertigen Posts dieses Kalendertags, Zeiten aus dem Plan
    python3 scripts/warteschlange.py status                               # was ist geplant, was ist raus
    python3 scripts/warteschlange.py cancel T04-R1                        # Eintrag stornieren (Dateien werden gelöscht)
    python3 scripts/warteschlange.py run                                  # fällige Einträge veröffentlichen (das macht GitHub alle 10 Minuten)

`add` lädt Bilder/Videos in den öffentlichen Supabase-Bucket (queue/<slot>/…) und legt eine Zeile in der Tabelle
publish_queue an (sql/publish_queue.sql). `run` läuft in GitHub Actions (.github/workflows/publish.yml): holt fällige
Zeilen, markiert sie atomar als „running“ (kein Doppelpost), veröffentlicht mit den Funktionen aus publish.py,
löscht danach die Dateien. Fehler vor dem Posten werden bis zu 3 Mal wiederholt; schon veröffentlichte Ziele
(Instagram/Facebook) werden bei einer Wiederholung übersprungen. Eingeplante Zeit älter als 3 Stunden = „verpasst“.
Gibt nie einen Schlüssel oder Token aus.
"""
import argparse
import datetime
import json
import re
import sys
import tempfile
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish  # noqa: E402
from publish import ENV, Fehler, http, redact, ROOT  # noqa: E402

try:
    from zoneinfo import ZoneInfo
    ZH = ZoneInfo("Europe/Zurich")
except Exception:  # pragma: no cover
    ZH = None

TABLE = "publish_queue"
MAX_VERSUCHE = 3
VERPASST_STUNDEN = 3


# ---------- Supabase REST ----------
class Rest:
    def __init__(self):
        for k in ("SUPABASE_URL", "SUPABASE_SECRET_KEY"):
            if not ENV.get(k):
                raise Fehler(f"{k} fehlt (.env oder GitHub-Secret)")
        self.base = ENV["SUPABASE_URL"].rstrip("/") + "/rest/v1/"
        key = ENV["SUPABASE_SECRET_KEY"]
        self.hdr_sets = [{"apikey": key}, {"apikey": key, "Authorization": f"Bearer {key}"}]
        self.hdr = self.hdr_sets[0]

    def call(self, method, path, body=None, params=None, prefer=None):
        url = self.base + path + ("?" + urllib.parse.urlencode(params) if params else "")
        data = json.dumps(body).encode() if body is not None else None
        last = None
        for i, h in enumerate(self.hdr_sets if self.hdr is self.hdr_sets[0] else [self.hdr]):
            hd = {**h, "Content-Type": "application/json"}
            if prefer:
                hd["Prefer"] = prefer
            st, resp, _ = http(method, url, data=data, headers=hd)
            if st in (200, 201, 204):
                self.hdr = h
                return json.loads(resp.decode("utf-8")) if resp else None
            last = (st, resp[:300].decode("utf-8", "replace"))
        hint = " (Tabelle publish_queue angelegt? sql/publish_queue.sql im SQL Editor ausführen)" if last[0] in (404, 400) else ""
        raise Fehler(redact(f"Supabase-Tabelle: HTTP {last[0]} {last[1]}{hint}"))


# ---------- Zeit ----------
def zurich_to_utc(text):
    """'2026-11-19 06:45' (Zürcher Zeit) → ISO-UTC."""
    d = datetime.datetime.strptime(text.strip(), "%Y-%m-%d %H:%M")
    if ZH is None:
        raise Fehler("zoneinfo fehlt (Python 3.9+ nötig)")
    return d.replace(tzinfo=ZH).astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_to_zurich(iso):
    d = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return d.astimezone(ZH).strftime("%a %d.%m. %H:%M") if ZH else iso


# ---------- Plan: Slots eines Tages ----------
def slots_of_day(datum):
    """[(slot, 'HH:MM')] für ein Datum nach plan.py/kalender.json (inkl. Tausch)."""
    import plan
    kal = plan.load_kalender()
    if not kal.get("anker"):
        raise Fehler("Kein Anker in data/kalender.json")
    anker = datetime.date.fromisoformat(kal["anker"])
    tag = plan.plan_tag(datum, anker)
    rows = plan.parse_plan()
    out = []
    for r0 in sorted((r for r in rows if int(r["slot"][1:3]) == tag), key=lambda r: r["tag"].split("·")[-1]):
        zeit = r0["tag"].split("·")[-1].strip()
        neu = (kal.get("tausch") or {}).get(f"{datum.isoformat()} {r0['slot']}")
        slot = next((x["slot"] for x in rows if x["slot"] == neu), r0["slot"]) if neu else r0["slot"]
        out.append((slot, zeit))
    return out


# ---------- Vorbereiten und hochladen ----------
def prepare(slot, tmp):
    """Prüft die fertigen Dateien. Gibt (kind, [Pfade], Titelbild-Pfad) zurück."""
    d = ROOT / "output" / slot
    if re.search(r"-R\d$", slot):
        v = d / "reel.mp4"
        publish.check_reel(v)
        c = d / "cover.jpg"
        cover = publish.to_jpeg(c, tmp, check_aspect=False)[0] if c.exists() else None
        return "reel", [v], cover
    if slot.endswith("-S"):
        sv = sorted(d.glob("story-*.mp4"), key=lambda p: int(re.search(r"(\d+)", p.stem).group(1)))
        if sv:
            for v in sv:
                secs = publish.check_reel(v)[0]
                if secs > 60:
                    raise Fehler(f"{v.name}: {secs:.0f} s (Storys höchstens 60 s)")
            return "story-videos", sv, None
        imgs = publish.find_images(slot, None)
        jp = []
        for p in imgs:
            j, size, _ = publish.to_jpeg(p, tmp, check_aspect=False)
            if abs(size[0] / size[1] - 9 / 16) > 0.02:
                raise Fehler(f"{p.name}: {size[0]}x{size[1]} ist kein 9:16-Hochformat (Stories)")
            jp.append(j)
        return "story-bilder", jp, None
    imgs = publish.find_images(slot, None)
    return "karussell", [publish.to_jpeg(p, tmp)[0] for p in imgs], None


def cmd_add(slot, at, targets, force=False):
    rest = Rest()
    off = rest.call("GET", TABLE, params={"slot": f"eq.{slot}", "status": "in.(pending,running,done)", "select": "id,status,publish_at"})
    if off and not force:
        raise Fehler(f"{slot} ist schon in der Warteschlange ({off[0]['status']}, {utc_to_zurich(off[0]['publish_at'])}). "
                     f"Mit `cancel {slot}` stornieren oder --force.")
    caption = publish.read_caption(slot)
    tmp = Path(tempfile.mkdtemp(prefix="zr-queue-"))
    kind, files, cover = prepare(slot, tmp)
    when = zurich_to_utc(at)
    if datetime.datetime.fromisoformat(when.replace("Z", "+00:00")) < datetime.datetime.now(datetime.timezone.utc):
        print(f"  Hinweis: {at} liegt in der Vergangenheit, der Post geht beim nächsten Lauf (innerhalb von ca. 10 Minuten) raus.")
    st = publish.Storage()
    urls, curl = [], None
    try:
        for f in files:
            u = st.upload(f, f"queue/{slot}")
            st.verify(u)
            urls.append(u)
        if cover:
            curl = st.upload(cover, f"queue/{slot}")
            st.verify(curl)
        row = {"slot": slot, "kind": kind, "publish_at": when, "caption": caption, "urls": urls, "cover_url": curl,
               "targets": targets, "paths": st.paths}
        rest.call("POST", TABLE, row, prefer="return=minimal")
    except Exception:
        st.cleanup()
        raise
    print(f"  {slot}: {kind}, {len(urls)} Datei(en) hochgeladen, geplant für {utc_to_zurich(when)} (Zürcher Zeit)")


def cmd_add_tag(datum, targets, force):
    d = datetime.date.fromisoformat(datum)
    fertig, fehlt = 0, []
    for slot, zeit in slots_of_day(d):
        try:
            if not (ROOT / "output" / f"{slot}.md").exists():
                raise Fehler("Post-Datei fehlt")
            cmd_add(slot, f"{d.isoformat()} {zeit}", targets, force)
            fertig += 1
        except Fehler as e:
            fehlt.append(f"{slot} ({zeit}): {redact(e)}")
    print(f"\n{fertig} Post(s) für {d.strftime('%d.%m.%Y')} eingeplant.")
    for f in fehlt:
        print(f"  NICHT eingeplant: {f}")
    return 1 if fehlt else 0


def cmd_status():
    rows = Rest().call("GET", TABLE, params={"select": "id,slot,kind,publish_at,status,attempts,error,result",
                                             "order": "publish_at.desc", "limit": "30"})
    if not rows:
        print("Warteschlange ist leer.")
    for r in reversed(rows):
        extra = f"  FEHLER: {r['error'][:120]}" if r.get("error") else ""
        print(f"#{r['id']:<4} {utc_to_zurich(r['publish_at'])}  {r['slot']:<8} {r['kind']:<13} {r['status']:<9}{extra}")


def cmd_cancel(slot):
    rest = Rest()
    rows = rest.call("GET", TABLE, params={"slot": f"eq.{slot}", "status": "in.(pending,error)", "select": "id,paths"})
    if not rows:
        raise Fehler(f"Kein offener Eintrag für {slot}")
    st = publish.Storage()
    for r in rows:
        rest.call("PATCH", TABLE, {"status": "cancelled", "updated_at": now_iso()}, params={"id": f"eq.{r['id']}"}, prefer="return=minimal")
        st.paths = r.get("paths") or []
        st.cleanup()
    print(f"{slot} storniert, Dateien gelöscht.")


# ---------- Veröffentlichen ----------
def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def publish_row(row, token, res):
    """Veröffentlicht eine Zeile. `res` (dict je Ziel) wird direkt gefüllt, damit bei einem Fehler im zweiten Ziel
    das erste nicht verloren geht; schon erledigte Ziele werden übersprungen."""
    kind, urls, cap = row["kind"], row["urls"], row["caption"]
    ig, fb = ENV["IG_USER_ID"], ENV.get("FB_PAGE_ID")
    if "ig" in row["targets"] and "instagram" not in res:
        if kind == "reel":
            res["instagram"] = publish.instagram_reel(ig, token, urls[0], row.get("cover_url"), cap, True)
        elif kind == "story-videos":
            res["instagram"] = publish.instagram_story_videos(ig, token, urls, True)
        elif kind == "story-bilder":
            res["instagram"] = publish.instagram_stories(ig, token, urls, True)
        else:
            res["instagram"] = publish.instagram(ig, token, urls, cap, True)
    if "fb" in row["targets"] and "facebook" not in res:
        if not fb:
            raise Fehler("FB_PAGE_ID fehlt")
        if kind == "reel":
            res["facebook"] = publish.facebook_video(fb, token, urls[0], cap, True)
        elif kind == "story-videos":
            res["facebook"] = publish.facebook_story_videos(fb, token, urls, True)
        elif kind == "story-bilder":
            res["facebook"] = publish.facebook_stories(fb, token, urls, True)
        else:
            res["facebook"] = publish.facebook(fb, token, urls, cap, True)
    return res


def cmd_run(now=None):
    rest = Rest()
    now = now or now_iso()
    due = rest.call("GET", TABLE, params={"status": "eq.pending", "publish_at": f"lte.{now}", "select": "*",
                                          "order": "publish_at.asc"}) or []
    print(f"{len(due)} fällige(r) Eintrag/Einträge.")
    problems = 0
    # Hängengebliebene Einträge (Lauf abgebrochen): nie blind wiederholen, es ist unklar, ob schon gepostet wurde
    grenze = (datetime.datetime.fromisoformat(now.replace("Z", "+00:00")) - datetime.timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for h in rest.call("GET", TABLE, params={"status": "eq.running", "updated_at": f"lt.{grenze}", "select": "id,slot"}) or []:
        rest.call("PATCH", TABLE, {"status": "error", "error": "Lauf abgebrochen, unklar ob veröffentlicht: bitte in Instagram/Facebook prüfen",
                                   "updated_at": now}, params={"id": f"eq.{h['id']}"}, prefer="return=minimal")
        print(f"  {h['slot']}: Lauf hing, bitte prüfen, ob der Post schon draussen ist")
        problems += 1
    for row in due:
        late = (datetime.datetime.fromisoformat(now.replace("Z", "+00:00")) -
                datetime.datetime.fromisoformat(row["publish_at"].replace("Z", "+00:00")))
        if late > datetime.timedelta(hours=VERPASST_STUNDEN):
            rest.call("PATCH", TABLE, {"status": "error", "error": f"verpasst: {late} zu spät, nicht veröffentlicht",
                                       "updated_at": now}, params={"id": f"eq.{row['id']}"}, prefer="return=minimal")
            print(f"  {row['slot']}: VERPASST (eingeplant {utc_to_zurich(row['publish_at'])}), nicht veröffentlicht")
            problems += 1
            continue
        claim = rest.call("PATCH", TABLE, {"status": "running", "attempts": row["attempts"] + 1, "updated_at": now},
                          params={"id": f"eq.{row['id']}", "status": "eq.pending"}, prefer="return=representation")
        if not claim:
            print(f"  {row['slot']}: schon von einem anderen Lauf übernommen")
            continue
        row = claim[0]
        print(f"  {row['slot']} ({row['kind']}): veröffentliche …")
        res = dict(row.get("result") or {})
        try:
            publish_row(row, ENV["META_SYSTEM_TOKEN"], res)
            rest.call("PATCH", TABLE, {"status": "done", "result": res, "error": None, "updated_at": now_iso()},
                      params={"id": f"eq.{row['id']}"}, prefer="return=minimal")
            st = publish.Storage()
            st.paths = row.get("paths") or []
            st.cleanup()
            print(f"  {row['slot']}: veröffentlicht")
        except Exception as e:
            msg = redact(e)[:500]
            # Zwischenstand speichern, damit schon veröffentlichte Ziele nicht doppelt gepostet werden
            partial = res
            final = row["attempts"] >= MAX_VERSUCHE
            rest.call("PATCH", TABLE, {"status": "error" if final else "pending", "error": msg, "result": partial,
                                       "updated_at": now_iso()}, params={"id": f"eq.{row['id']}"}, prefer="return=minimal")
            print(f"  {row['slot']}: FEHLER (Versuch {row['attempts']}/{MAX_VERSUCHE}): {msg}")
            problems += 1
    return 1 if problems else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add"); p.add_argument("slot"); p.add_argument("--at", required=True, help='"JJJJ-MM-TT HH:MM" Zürcher Zeit')
    p.add_argument("--nur", choices=["ig", "fb"], help="nur ein Ziel"); p.add_argument("--force", action="store_true")
    p = sub.add_parser("add-tag"); p.add_argument("datum"); p.add_argument("--nur", choices=["ig", "fb"]); p.add_argument("--force", action="store_true")
    sub.add_parser("status")
    p = sub.add_parser("cancel"); p.add_argument("slot")
    p = sub.add_parser("run"); p.add_argument("--jetzt", help="ISO-UTC statt der aktuellen Zeit (Test)")
    a = ap.parse_args()
    tg = lambda: [a.nur] if getattr(a, "nur", None) else ["ig", "fb"]
    if a.cmd == "add":
        cmd_add(a.slot, a.at, tg(), a.force)
    elif a.cmd == "add-tag":
        sys.exit(cmd_add_tag(a.datum, tg(), a.force))
    elif a.cmd == "status":
        cmd_status()
    elif a.cmd == "cancel":
        cmd_cancel(a.slot)
    elif a.cmd == "run":
        sys.exit(cmd_run(a.jetzt))


if __name__ == "__main__":
    try:
        main()
    except Fehler as e:
        print(f"\nFEHLER: {redact(e)}", file=sys.stderr)
        sys.exit(1)
