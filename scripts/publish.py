#!/usr/bin/env python3
"""Veröffentlicht einen fertigen Post (Karussell oder Einzelbild) auf Instagram, optional auch Facebook.

    python3 scripts/publish.py T10-K              # Vorschau, kein Netz, es passiert nichts
    python3 scripts/publish.py T10-K --test       # lädt hoch, legt Instagram-Container an, VERÖFFENTLICHT NICHT
    python3 scripts/publish.py T10-K --test --fb  # dasselbe, prüft zusätzlich das Posten auf die Facebook-Seite
    python3 scripts/publish.py T10-K --publish    # veröffentlicht auf Instagram (nach Rückfrage "ja")
    python3 scripts/publish.py T10-K --publish --fb   # zusätzlich auf die Facebook-Seite

Story-Sequenzen (Slot endet auf -S, z. B. T03-S): jede Slide wird eine eigene Story (Instagram media_type=STORIES,
Facebook photo_stories), ohne Caption, im 9:16-Format, in der Reihenfolge der Slides.

Nimmt output/<slot>/slides/slide-*.png (sonst output/<slot>/bild-*.jpg) und die Caption aus
output/<slot>.md (Abschnitt Agent 7). Bilder werden zu JPEG, bei Supabase Storage öffentlich
abgelegt, von Meta abgeholt und danach wieder gelöscht.
Nötig in .env: SUPABASE_URL, SUPABASE_SECRET_KEY, SUPABASE_BUCKET, IG_USER_ID, FB_PAGE_ID, META_SYSTEM_TOKEN.
Gibt nie einen Schlüssel oder Token aus. Nur Pillow und die Standardbibliothek.
"""
import argparse
import io
import json
import re
import subprocess
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRAPH = "https://graph.facebook.com/v25.0"
MAX_BYTES = 8 * 1024 * 1024


class Fehler(Exception):
    pass


def load_env():
    env = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s*(?:export\s+)?([A-Z_][A-Z0-9_]*)=(.*)$", line)
            if m:
                env[m.group(1)] = m.group(2).strip().strip("\"'")
    # In GitHub Actions kommen die Werte als Umgebungsvariablen (Secrets), nicht aus .env
    import os
    for k in ("SUPABASE_URL", "SUPABASE_SECRET_KEY", "SUPABASE_BUCKET", "IG_USER_ID", "FB_PAGE_ID", "META_SYSTEM_TOKEN"):
        if os.environ.get(k) and not env.get(k):
            env[k] = os.environ[k].strip()
    return env


ENV = load_env()
SECRETS = [v for k, v in ENV.items() if v and re.search(r"TOKEN|SECRET|KEY", k)]


def redact(t):
    t = str(t)
    for s in SECRETS:
        t = t.replace(s, "<geheim>")
    return t


def http(method, url, data=None, headers=None, timeout=90):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)
    except Exception as e:
        raise Fehler(redact(f"Keine Verbindung ({type(e).__name__}: {e})"))


def graph(method, path, token, **params):
    params["access_token"] = token
    if method == "GET":
        status, body, _ = http("GET", f"{GRAPH}/{path}?" + urllib.parse.urlencode(params))
    else:
        status, body, _ = http(method, f"{GRAPH}/{path}", data=urllib.parse.urlencode(params).encode(),
                               headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        d = json.loads(body.decode("utf-8"))
    except Exception:
        raise Fehler(f"Meta antwortet mit HTTP {status}, kein JSON")
    if "error" in d:
        e = d["error"]
        raise Fehler(redact(f"Meta: {e.get('error_user_title') or e.get('message')} "
                            f"(Code {e.get('code')}/{e.get('error_subcode')}) {e.get('error_user_msg', '')}").strip())
    return d


# ---------- Eingaben ----------
def read_caption(slot):
    md = ROOT / "output" / f"{slot}.md"
    if not md.exists():
        raise Fehler(f"{md.relative_to(ROOT)} fehlt")
    m = re.search(r"(?ms)^## Agent 7[^\n]*\n.*?\*\*Caption:\*\*\s*\n(.*?)(?=^## Agent |^---\s*$|\Z)", md.read_text(encoding="utf-8"))
    if not m:
        raise Fehler("Caption (Agent 7, '**Caption:**') nicht gefunden")
    cap = re.sub(r"<!--.*?-->", "", m.group(1), flags=re.S).strip()
    if not cap.startswith("Werbung 🤍 |"):
        raise Fehler("Caption beginnt nicht mit der Pflicht-Kopfzeile 'Werbung 🤍 | …'")
    if len(cap) > 2200:
        raise Fehler(f"Caption hat {len(cap)} Zeichen (Instagram-Maximum 2200)")
    return cap


def find_images(slot, files):
    if files:
        return [Path(f) for f in files]
    d = ROOT / "output" / slot
    num = lambda p: int(re.search(r"(\d+)", p.stem).group(1))
    imgs = sorted((d / "slides").glob("slide-*.png"), key=num) or sorted(d.glob("bild-*.jpg"), key=num)
    if not imgs:
        raise Fehler(f"Keine Bilder in output/{slot}/slides/ (slide-*.png) oder output/{slot}/bild-*.jpg")
    return imgs


def to_jpeg(path, outdir, check_aspect=True):
    try:
        from PIL import Image
    except ImportError:
        raise Fehler("Pillow fehlt: pip install -r requirements.txt")
    im = Image.open(path).convert("RGB")
    w, h = im.size
    if check_aspect and not 0.8 - 1e-9 <= w / h <= 1.91 + 1e-9:
        raise Fehler(f"{path.name}: Seitenverhältnis {w}x{h} ausserhalb 4:5 bis 1.91:1")
    out = outdir / (path.stem + ".jpg")
    for q in (92, 88, 82, 75):
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=q, optimize=True)
        if buf.tell() <= MAX_BYTES:
            out.write_bytes(buf.getvalue())
            return out, (w, h), buf.tell()
    raise Fehler(f"{path.name}: auch bei Qualität 75 über 8 MiB")


# ---------- Supabase Storage ----------
class Storage:
    def __init__(self):
        for k in ("SUPABASE_URL", "SUPABASE_SECRET_KEY", "SUPABASE_BUCKET"):
            if not ENV.get(k):
                raise Fehler(f"{k} fehlt in .env")
        self.url = ENV["SUPABASE_URL"].rstrip("/")
        self.key, self.bucket = ENV["SUPABASE_SECRET_KEY"], ENV["SUPABASE_BUCKET"]
        self.hdr_sets = [{"apikey": self.key}, {"apikey": self.key, "Authorization": f"Bearer {self.key}"}]
        self.hdr = self.hdr_sets[0]
        self.paths = []

    def upload(self, file, slot):
        ext = file.suffix.lower() or ".jpg"
        ctype = {".mp4": "video/mp4", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}.get(ext, "application/octet-stream")
        path = f"{slot}/{uuid.uuid4().hex}{ext}"
        data = file.read_bytes()
        for i, h in enumerate(self.hdr_sets):
            st, body, _ = http("POST", f"{self.url}/storage/v1/object/{self.bucket}/{path}", data=data,
                               headers={**h, "Content-Type": ctype, "x-upsert": "false"})
            if st in (200, 201):
                self.hdr = h
                self.paths.append(path)
                return f"{self.url}/storage/v1/object/public/{self.bucket}/{path}"
            if i == len(self.hdr_sets) - 1:
                hint = " (Bucket 'posts' vorhanden? Key korrekt?)" if st in (400, 401, 403, 404) else ""
                raise Fehler(redact(f"Upload fehlgeschlagen: HTTP {st} {body[:200].decode('utf-8', 'replace')}{hint}"))

    def verify(self, url):
        video = url.endswith(".mp4")
        st, body, hd = http("GET", url, headers={"Range": "bytes=0-4095"} if video else None)
        ct = {k.lower(): v for k, v in hd.items()}.get("content-type", "")
        if st not in (200, 206):
            raise Fehler(f"Öffentliche URL nicht abrufbar (HTTP {st}). Ist der Bucket 'Public'?")
        if video:
            if not ct.startswith("video/mp4") or body[4:8] != b"ftyp":
                raise Fehler(f"Öffentliche URL liefert kein MP4 (Content-Type {ct!r})")
        elif not ct.startswith("image/jpeg") or body[:3] != b"\xff\xd8\xff":
            raise Fehler(f"Öffentliche URL liefert kein JPEG (Content-Type {ct!r})")

    def cleanup(self):
        if not self.paths:
            return
        st, body, _ = http("DELETE", f"{self.url}/storage/v1/object/{self.bucket}",
                           data=json.dumps({"prefixes": self.paths}).encode(),
                           headers={**self.hdr, "Content-Type": "application/json"})
        print("  Hochgeladene Dateien gelöscht." if st in (200, 204) else f"  Hinweis: Löschen im Storage nicht bestätigt (HTTP {st}), bitte im Bucket prüfen.")


# ---------- Instagram / Facebook ----------
def wait_ready(cid, token, what, tries=40):
    for _ in range(tries):
        d = graph("GET", cid, token, fields="status_code,status")
        s = d.get("status_code")
        if s == "FINISHED":
            return
        if s in ("ERROR", "EXPIRED"):
            raise Fehler(f"Instagram-Container ({what}) {s}: {d.get('status', '')}")
        time.sleep(3)
    raise Fehler(f"Instagram-Container ({what}) nach {tries * 3 // 60} Minuten nicht fertig")


def instagram_reel(ig_id, token, video_url, cover_url, caption, publish):
    params = dict(media_type="REELS", video_url=video_url, caption=caption, share_to_feed="true")
    if cover_url:
        params["cover_url"] = cover_url
    cid = graph("POST", f"{ig_id}/media", token, **params)["id"]
    print("  Reel-Container angelegt, Meta verarbeitet das Video …")
    wait_ready(cid, token, "Reel", tries=100)
    if not publish:
        return {"container": cid, "veroeffentlicht": False}
    media_id = graph("POST", f"{ig_id}/media_publish", token, creation_id=cid)["id"]
    perm = graph("GET", media_id, token, fields="permalink").get("permalink")
    return {"container": cid, "media_id": media_id, "link": perm, "veroeffentlicht": True}


def instagram(ig_id, token, urls, caption, publish):
    if len(urls) == 1:
        cid = graph("POST", f"{ig_id}/media", token, image_url=urls[0], caption=caption)["id"]
    else:
        if not 2 <= len(urls) <= 10:
            raise Fehler("Ein Karussell braucht 2 bis 10 Bilder")
        kids = []
        for i, u in enumerate(urls, 1):
            kids.append(graph("POST", f"{ig_id}/media", token, image_url=u, is_carousel_item="true")["id"])
            print(f"  Bild {i}/{len(urls)}: Container angelegt")
        for i, k in enumerate(kids, 1):
            wait_ready(k, token, f"Bild {i}")
        cid = graph("POST", f"{ig_id}/media", token, media_type="CAROUSEL", children=",".join(kids), caption=caption)["id"]
    wait_ready(cid, token, "Beitrag")
    if not publish:
        return {"container": cid, "veroeffentlicht": False}
    media_id = graph("POST", f"{ig_id}/media_publish", token, creation_id=cid)["id"]
    perm = graph("GET", media_id, token, fields="permalink").get("permalink")
    return {"container": cid, "media_id": media_id, "link": perm, "veroeffentlicht": True}


def facebook_video(page_id, token, video_url, caption, publish=True):
    ptoken = graph("GET", page_id, token, fields="access_token").get("access_token")
    if not ptoken:
        raise Fehler("Kein Seiten-Token (System-User braucht Zugriff mit Inhalten erstellen auf die Seite)")
    r = graph("POST", f"{page_id}/videos", ptoken, file_url=video_url, description=caption,
              published="true" if publish else "false")
    return {"video_id": r.get("id"), "veroeffentlicht": publish}


def facebook(page_id, token, urls, caption, publish=True):
    ptoken = graph("GET", page_id, token, fields="access_token").get("access_token")
    if not ptoken:
        raise Fehler("Kein Seiten-Token (System-User braucht Zugriff mit Inhalten erstellen auf die Seite)")
    if not publish:
        # Test: Fotos unveröffentlicht hochladen (published=false). Sie erscheinen nirgends, beweisen aber das Recht zum Posten.
        ids = [graph("POST", f"{page_id}/photos", ptoken, url=u, published="false")["id"] for u in urls]
        return {"foto_ids": ids, "veroeffentlicht": False}
    if len(urls) == 1:
        r = graph("POST", f"{page_id}/photos", ptoken, url=urls[0], message=caption, published="true")
        return {"post_id": r.get("post_id") or r.get("id")}
    ids = [graph("POST", f"{page_id}/photos", ptoken, url=u, published="false")["id"] for u in urls]
    params = {"message": caption}
    for i, pid in enumerate(ids):
        params[f"attached_media[{i}]"] = json.dumps({"media_fbid": pid})
    return {"post_id": graph("POST", f"{page_id}/feed", ptoken, **params)["id"]}


def instagram_stories(ig_id, token, urls, publish):
    """Jede URL wird eine eigene Story. Test: Container anlegen und warten, nicht veröffentlichen."""
    res = []
    for i, u in enumerate(urls, 1):
        cid = graph("POST", f"{ig_id}/media", token, media_type="STORIES", image_url=u)["id"]
        wait_ready(cid, token, f"Story {i}")
        if not publish:
            res.append({"container": cid})
            print(f"  Story {i}/{len(urls)}: Container akzeptiert")
            continue
        media_id = graph("POST", f"{ig_id}/media_publish", token, creation_id=cid)["id"]
        res.append({"container": cid, "media_id": media_id})
        print(f"  Story {i}/{len(urls)}: veröffentlicht")
    return {"stories": res, "veroeffentlicht": publish}


def instagram_story_videos(ig_id, token, urls, publish):
    """Jede Video-URL wird eine eigene Story (mit Ton). Test: Container anlegen und warten, nicht veröffentlichen."""
    res = []
    for i, u in enumerate(urls, 1):
        cid = graph("POST", f"{ig_id}/media", token, media_type="STORIES", video_url=u)["id"]
        wait_ready(cid, token, f"Story-Video {i}", tries=100)
        if not publish:
            res.append({"container": cid})
            print(f"  Story {i}/{len(urls)}: Container akzeptiert")
            continue
        media_id = graph("POST", f"{ig_id}/media_publish", token, creation_id=cid)["id"]
        res.append({"container": cid, "media_id": media_id})
        print(f"  Story {i}/{len(urls)}: veröffentlicht")
    return {"stories": res, "veroeffentlicht": publish}


def facebook_story_videos(page_id, token, urls, publish=True):
    """Facebook-Video-Storys in drei Schritten: start → Datei per URL laden (rupload) → finish.
    Test: start und Upload, aber kein finish (die Story erscheint nicht)."""
    ptoken = graph("GET", page_id, token, fields="access_token").get("access_token")
    if not ptoken:
        raise Fehler("Kein Seiten-Token (System-User braucht Zugriff mit Inhalten erstellen auf die Seite)")
    res = []
    for i, u in enumerate(urls, 1):
        s = graph("POST", f"{page_id}/video_stories", ptoken, upload_phase="start")
        vid, up = s.get("video_id"), s.get("upload_url") or ""
        if not vid or not up.startswith("https://rupload.facebook.com/"):
            raise Fehler("Facebook hat keine gültige Upload-Adresse für die Video-Story geliefert")
        st, body, _ = http("POST", up, headers={"Authorization": f"OAuth {ptoken}", "file_url": u})
        try:
            d = json.loads(body.decode("utf-8"))
        except Exception:
            d = {}
        if st >= 300 or d.get("error"):
            raise Fehler(redact(f"Facebook-Upload der Story {i} fehlgeschlagen: HTTP {st} {str(d)[:200]}"))
        for _ in range(40):  # warten, bis Facebook das Video verarbeitet hat
            status = graph("GET", vid, ptoken, fields="status").get("status", {})
            vs = status.get("video_status")
            if vs == "ready":
                break
            if vs == "error":
                raise Fehler(f"Facebook konnte Story-Video {i} nicht verarbeiten")
            time.sleep(3)
        else:
            raise Fehler(f"Facebook-Story-Video {i} nach 2 Minuten nicht fertig")
        if not publish:
            res.append({"video_id": vid})
            print(f"  Facebook-Story {i}/{len(urls)}: Video akzeptiert (nicht veröffentlicht)")
            continue
        r = graph("POST", f"{page_id}/video_stories", ptoken, upload_phase="finish", video_id=vid)
        res.append({"video_id": vid, "story_id": r.get("post_id") or r.get("id")})
        print(f"  Facebook-Story {i}/{len(urls)}: veröffentlicht")
    return {"stories": res, "veroeffentlicht": publish}


def facebook_stories(page_id, token, urls, publish=True):
    """Facebook-Foto-Storys: Foto unveröffentlicht hochladen, dann als Story veröffentlichen."""
    ptoken = graph("GET", page_id, token, fields="access_token").get("access_token")
    if not ptoken:
        raise Fehler("Kein Seiten-Token (System-User braucht Zugriff mit Inhalten erstellen auf die Seite)")
    res = []
    for i, u in enumerate(urls, 1):
        pid = graph("POST", f"{page_id}/photos", ptoken, url=u, published="false")["id"]
        if not publish:
            res.append({"foto_id": pid})
            continue
        r = graph("POST", f"{page_id}/photo_stories", ptoken, photo_id=pid)
        res.append({"foto_id": pid, "story_id": r.get("post_id") or r.get("id")})
        print(f"  Story {i}/{len(urls)}: veröffentlicht")
    return {"stories": res, "veroeffentlicht": publish}


MAX_VIDEO = 45 * 1024 * 1024   # Supabase Free erlaubt 50 MB pro Datei


def check_reel(path):
    """Prüft reel.mp4 mit ffprobe: Länge 3-90 s, Hochformat, Grösse, Ton. Gibt (Sekunden, Breite, Höhe, Ton) zurück."""
    if not path.exists():
        raise Fehler(f"{path.relative_to(ROOT)} fehlt (erst render_reel.py ausführen)")
    if path.stat().st_size > MAX_VIDEO:
        raise Fehler(f"{path.name} ist {path.stat().st_size // 1048576} MB (Supabase Free: höchstens 45 MB)")
    if not shutil.which("ffprobe"):
        raise Fehler("ffprobe fehlt (brew install ffmpeg)")
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
                        "-of", "json", str(path)], capture_output=True, text=True)
    d = json.loads(r.stdout or "{}")
    v = next((x for x in d.get("streams", []) if x.get("codec_type") == "video"), None)
    if not v:
        raise Fehler(f"{path.name}: kein Videostrom")
    secs, w, h = float(d["format"]["duration"]), v["width"], v["height"]
    if not 3 <= secs <= 90:
        raise Fehler(f"{path.name}: {secs:.1f} s (Reels: 3 bis 90 s)")
    if abs(w / h - 9 / 16) > 0.02:
        raise Fehler(f"{path.name}: {w}x{h} ist kein 9:16-Hochformat")
    return secs, w, h, any(x.get("codec_type") == "audio" for x in d["streams"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slot", help="z. B. T10-K oder T03-R1")
    ap.add_argument("--test", action="store_true", help="hochladen und Container anlegen, nicht veröffentlichen")
    ap.add_argument("--publish", action="store_true", help="wirklich veröffentlichen (fragt vorher nach)")
    ap.add_argument("--fb", action="store_true", help="zusätzlich auf die Facebook-Seite (mit --test nur Zugriffstest)")
    ap.add_argument("--yes", action="store_true", help="Rückfrage vor dem Veröffentlichen überspringen")
    ap.add_argument("--bilder", action="store_true", help="Story als Bilder ohne Ton, auch wenn story-*.mp4 existieren")
    ap.add_argument("--files", nargs="+", help="Bilddateien statt output/<slot>/slides/")
    a = ap.parse_args()
    if a.test and a.publish:
        sys.exit("Entweder --test oder --publish.")

    caption = read_caption(a.slot)
    tmp = Path(tempfile.mkdtemp(prefix="zr-publish-"))
    reel = bool(re.search(r"-R\d$", a.slot)) and not a.files
    story = a.slot.endswith("-S")
    sv = sorted((ROOT / "output" / a.slot).glob("story-*.mp4"),
                key=lambda p: int(re.search(r"(\d+)", p.stem).group(1))) if story and not a.files and not a.bilder else []
    jpgs, video, cover = [], None, None
    if sv:
        for v in sv:
            secs, w, h, ton = check_reel(v)
            if secs > 60:
                raise Fehler(f"{v.name}: {secs:.0f} s (Storys höchstens 60 s)")
            print(f"Story-Video {v.name}: {w}x{h}, {secs:.1f} s, {'mit' if ton else 'OHNE'} Ton")
    elif reel:
        video = ROOT / "output" / a.slot / "reel.mp4"
        secs, w, h, ton = check_reel(video)
        print(f"Reel {a.slot}: {w}x{h}, {secs:.1f} s, {video.stat().st_size / 1048576:.1f} MB, {'mit' if ton else 'OHNE'} Ton")
        c = ROOT / "output" / a.slot / "cover.jpg"
        if c.exists():
            cover, size, nbytes = to_jpeg(c, tmp, check_aspect=False)
            print(f"  Titelbild cover.jpg → JPEG {size[0]}x{size[1]}, {nbytes // 1024} KB")
        else:
            print("  Hinweis: kein cover.jpg, Instagram nimmt ein Bild aus dem Video")
    else:
        images = find_images(a.slot, a.files)
        print(f"Post {a.slot}: {len(images)} Bild(er)")
        for p in images:
            j, size, nbytes = to_jpeg(p, tmp, check_aspect=not story)
            if story and abs(size[0] / size[1] - 9 / 16) > 0.02:
                raise Fehler(f"{p.name}: {size[0]}x{size[1]} ist kein 9:16-Hochformat (Stories)")
            jpgs.append(j)
            print(f"  {p.name} → JPEG {size[0]}x{size[1]}, {nbytes // 1024} KB")
    print(f"Caption ({len(caption)} Zeichen): {caption[:90].replace(chr(10), ' ')}…")
    if not (a.test or a.publish):
        print("\nVorschau OK. Nichts wurde hochgeladen. Weiter mit --test (ohne Veröffentlichung) oder --publish.")
        return

    need = ["IG_USER_ID", "META_SYSTEM_TOKEN"] + (["FB_PAGE_ID"] if a.fb else [])
    miss = [k for k in need if not ENV.get(k)]
    if miss:
        raise Fehler(f".env: {', '.join(miss)} fehlt")
    if a.publish and not a.yes:
        ziel = "Instagram @zeit.reichtum" + (" UND Facebook-Seite" if a.fb else "")
        if input(f"\nJetzt wirklich auf {ziel} veröffentlichen? Tippe 'ja': ").strip().lower() != "ja":
            print("Abgebrochen, nichts veröffentlicht.")
            return

    token, log = ENV["META_SYSTEM_TOKEN"], {"slot": a.slot, "modus": "publish" if a.publish else "test"}
    st = Storage()
    try:
        print("\n1) Upload zu Supabase")
        urls, vurl, curl = [], None, None
        if sv:
            for v in sv:
                u = st.upload(v, a.slot)
                st.verify(u)
                urls.append(u)
            print(f"  {len(urls)} Story-Video(s) hochgeladen, öffentlich abrufbar (geprüft)")
        elif reel:
            vurl = st.upload(video, a.slot)
            st.verify(vurl)
            if cover:
                curl = st.upload(cover, a.slot)
                st.verify(curl)
            print("  Video" + (" und Titelbild" if cover else "") + " hochgeladen, öffentlich abrufbar (geprüft)")
        else:
            for j in jpgs:
                u = st.upload(j, a.slot)
                st.verify(u)
                urls.append(u)
            print(f"  {len(urls)} Datei(en) hochgeladen, öffentlich abrufbar (JPEG geprüft)")
        print("2) Instagram" + (" (veröffentlichen)" if a.publish else " (nur Test, wird nicht veröffentlicht)"))
        if reel:
            log["instagram"] = instagram_reel(ENV["IG_USER_ID"], token, vurl, curl, caption, a.publish)
        elif sv:
            log["instagram"] = instagram_story_videos(ENV["IG_USER_ID"], token, urls, a.publish)
        elif story:
            log["instagram"] = instagram_stories(ENV["IG_USER_ID"], token, urls, a.publish)
        else:
            log["instagram"] = instagram(ENV["IG_USER_ID"], token, urls, caption, a.publish)
        print("  " + (f"Veröffentlicht: {log['instagram'].get('link')}" if a.publish
                      else "Meta hat Medien und Container akzeptiert. Test bestanden."))
        if a.fb:
            print("3) Facebook-Seite" + (" (veröffentlichen)" if a.publish else " (nur Test, unveröffentlicht)"))
            if reel:
                log["facebook"] = facebook_video(ENV["FB_PAGE_ID"], token, vurl, caption, a.publish)
                print("  " + (f"Veröffentlicht: Video-ID {log['facebook']['video_id']}" if a.publish
                              else "Facebook hat das Video akzeptiert (unveröffentlicht). Test bestanden."))
            elif sv:
                log["facebook"] = facebook_story_videos(ENV["FB_PAGE_ID"], token, urls, a.publish)
                print("  " + ("Facebook-Storys veröffentlicht." if a.publish
                              else "Facebook hat die Story-Videos akzeptiert (nicht veröffentlicht). Test bestanden."))
            elif story:
                log["facebook"] = facebook_stories(ENV["FB_PAGE_ID"], token, urls, a.publish)
                print("  " + ("Facebook-Storys veröffentlicht." if a.publish
                              else "Facebook hat die Bilder akzeptiert (unveröffentlicht). Test bestanden."))
            else:
                log["facebook"] = facebook(ENV["FB_PAGE_ID"], token, urls, caption, a.publish)
                print("  " + (f"Veröffentlicht: Post-ID {log['facebook']['post_id']}" if a.publish
                              else "Facebook hat die Bilder akzeptiert (unveröffentlicht). Test bestanden."))
    finally:
        st.cleanup()
        (ROOT / "output" / a.slot).mkdir(parents=True, exist_ok=True)
        (ROOT / "output" / a.slot / "publish-log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Fehler as e:
        print(f"\nFEHLER: {redact(e)}", file=sys.stderr)
        sys.exit(1)
