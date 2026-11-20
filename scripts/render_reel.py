#!/usr/bin/env python3
"""Fertiges Reel aus Video + Post: Text-Overlay, Loop auf Ziellänge, Titelbild. Keine API-Kosten.

  render_reel.py output/T05-R2.md [--video PFAD] [--variante original|spiegel|ausschnitt]
                 [--typ A|B] [--datum 2026-12-03] [--dry-run] [--ohne-cover] [--cover pool|video] [--force]

Ablauf
- Video: aus dem Monats-Pool (media.py video-pick: Fokus passend, höchstens 3×, 10 Tage Pause) oder --video.
  Variante „spiegel“ = links/rechts gespiegelt, „ausschnitt“ = gespiegelt + leicht hineingezoomt.
- Text: Einblendungen von Agent 3 im Look der Slides (Playfair Display / Montserrat, einfarbig ohne Schatten, keine Karte). Farbe automatisch: Creme, auf hellem Hintergrund Dunkelbraun, bei unruhigem Hintergrund Creme mit weichem Schleier.
  Typ A „Ein Satz“ (9 s): Einblendungen nacheinander, Hook ab Frame 1.
  Typ B „Schichten“ (10 s): Überschrift ab Frame 1, Textbox ab 1,0 s, Schlusszeile ab 6,0 s; alles bleibt stehen.
  Reels haben nie eine Glas-Karte (die gibt es nur bei Karussells und Stories).
- Ton: Originalton des Videos (z. B. Vögel, Regen) bleibt, mit kurzem Ein-/Ausblenden. Darunter liegt die Musik aus
  dem Musik-Pool (auf gleiche Lautstärke angeglichen) (medien/musik/, Soundstripe; scripts/musik.py wählt Stück und 10-s-Abschnitt, dieselben nie an
  Nachbartagen, denselben Abschnitt erst nach 30 Tagen). --musik aus = nur Originalton.
- Titelbild: Foto aus dem Wochen-Pool (Story-/Karussell-Fotos), Feed-Regel 42 Tage; sonst ein Videobild.

Ausgabe: output/<SLOT>/reel.mp4 (1080×1920, H.264, 30 fps) und output/<SLOT>/cover.jpg
Verwendung von Video und Titelbild wird eingetragen (videoliste.jsonl / bildliste.jsonl).
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
sys.path.insert(0, str(ROOT / "scripts"))
import media  # noqa: E402
import musik  # noqa: E402
import plan  # noqa: E402
import qa_check  # noqa: E402
import render_images as ri  # noqa: E402

W, H = 1080, 1920
CREAM = (245, 239, 230)      # Standard: warmes Off-White
DARK = (47, 38, 32)          # Dunkelbraun, wenn der Hintergrund hinter dem Text hell ist
MIN_CONTRAST = 3.0           # WCAG für grosse Schrift; darunter kommt ein weicher Lese-Schleier
LEN = {"A": 9.0, "B": 10.0}
FADE = 0.35
MUSIK_VOL = 1.0    # Faktor auf die Ziel-Lautstärke der Musik (musik.MUSIK_ZIEL_DB = -19 dBFS); mit --musik-lautstaerke änderbar
ORIG_VOL = 0.85


# ---------- Post lesen ----------
def read_post(path):
    _, clean = ri.load_post(path)
    s1 = clean.get("1", "")
    slot = (qa_check.field(s1, "Slot") or path.stem).strip()
    fmt = (qa_check.field(s1, "Format") or "").strip().lower()
    typ = (qa_check.field(s1, "Reel-Typ") or "").strip().upper()[:1]
    slides = ri.parse_slides(clean)
    return {"slot": slot, "format": fmt, "typ": typ if typ in LEN else None, "slides": slides, "clean": clean}


def plan_day(slot):
    m = re.match(r"^T(\d\d)-", slot)
    return int(m.group(1)) if m else None


# ---------- Text setzen ----------
def wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for w in text.split():
        t = f"{cur} {w}".strip()
        if cur and draw.textlength(t, font=font) > max_w:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def lay(draw, fonts, items, scale, max_w):
    """items: [(kind, rel_size, text, align)] → [(lines, font, line_h, gap, align)], Gesamthöhe."""
    out, total = [], 0
    for kind, rel, text, align in items:
        px = rel * W * scale
        f = fonts.get(kind, px)
        lines = []
        for part in text.split("\n"):
            lines += wrap(draw, part, f, max_w)
        lh = px * (1.16 if kind == "head" else 1.38)
        gap = px * 0.55
        out.append((lines, f, lh, gap, align))
        total += len(lines) * lh + gap
    if out:
        total -= out[-1][3]
    return out, total


def draw_laid(draw, laid, x0, max_w, y, color):
    for lines, f, lh, gap, align in laid:
        for ln in lines:
            lw = draw.textlength(ln, font=f)
            x = x0 if align == "left" else x0 + (max_w - lw) / 2
            draw.text((x, y), ln, font=f, fill=color)
            y += lh
        y += gap
    return y


def text_layer(PIL, fonts, items, top, bottom, max_w=W * 0.78, start_scale=1.0, card=False, center=True,
               shadow=0, color=CREAM, veil=None, part="all"):
    """Transparentes 1080×1920-Bild mit Text (und optional Karte) im Bereich top..bottom (Pixel).
    part: "all" | "veil" (nur Schleier/Karte) | "text" (nur Schrift) – so liegen bei Typ B alle Schleier
    unter allen Texten und ein später einblendender Schleier dunkelt keinen schon stehenden Text ab."""
    Image, ImageDraw, ImageFilter = PIL
    probe = ImageDraw.Draw(Image.new("RGBA", (W, H)))
    scale = start_scale
    while True:
        laid, total = lay(probe, fonts, items, scale, max_w)
        if total <= (bottom - top) or scale < 0.5:
            break
        scale *= 0.95
    y = top + ((bottom - top) - total) / 2 if center else top
    x0 = (W - max_w) / 2
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if card and part != "text":
        pad = W * 0.05
        c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(c).rounded_rectangle((x0 - pad, y - pad, x0 + max_w + pad, y + total + pad), 26,
                                            fill=(40, 30, 22, 92), outline=(245, 239, 230, 105), width=2)
        img = Image.alpha_composite(img, c)
    if veil and part != "text":  # nur wenn der Hintergrund unruhig ist: weicher, randloser Schleier hinter dem Textblock
        v = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        pad = W * 0.08
        ImageDraw.Draw(v).rounded_rectangle((x0 - pad, y - pad, x0 + max_w + pad, y + total + pad), int(pad),
                                            fill=veil)
        img = Image.alpha_composite(img, v.filter(ImageFilter.GaussianBlur(W * 0.05)))
    if part == "veil":
        return img, y, y + total
    if shadow:  # Standard: kein Schatten – die Videos sind schon abgedunkelt, Text bleibt einfarbig
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_laid(ImageDraw.Draw(sh), laid, x0, max_w, y + 2, (0, 0, 0, shadow))
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(6)))
    draw_laid(ImageDraw.Draw(img), laid, x0, max_w, y, color)
    return img, y, y + total


def block_items(slide, first, typ):
    """Blöcke einer Einblendung → Text-Items mit Schriftart und Grösse."""
    items = []
    quote = any(a == "src" for a, _ in slide["blocks"])  # Anführungszeichen nur bei echten Zitaten
    for art, text in slide["blocks"]:
        t = ri.strip_marks(text)
        if art == "h" and not quote:
            t = t.strip("„“”\"' ")
        if art == "h":
            items.append(("head", 0.078 if typ == "A" else 0.068, t, "center"))
        elif art == "src":
            items.append(("small", 0.030, t, "center"))
        elif first or (quote and typ == "A"):  # Typ A: Zitat als Wendung so gross wie der Hook
            items.append(("head", 0.070 if first else 0.062, t, "center"))
        else:
            items.append(("small" if typ == "A" else "text", 0.054 if typ == "A" else 0.043, t,
                          "center" if typ == "A" else "left"))
    return items


def build_layers(post, typ, design, tmp, PIL, fonts, color=CREAM, veil=None):
    """→ [(png, start, ende, fade_in, fade_out)]"""
    slides = post["slides"]
    if not slides:
        raise SystemExit("Keine Einblendungen in Agent 2 & 3 gefunden")
    T = LEN[typ]
    layers = []
    if typ == "A":
        n = len(slides)
        cuts = [0.0, 3.5] + [3.5 + (T - 3.5) * k / (n - 1) for k in range(1, n)] if n > 1 else [0.0, T]
        cuts = cuts[:n + 1]
        cuts[-1] = T
        for i, s in enumerate(slides):
            img, _, _ = text_layer(PIL, fonts, block_items(s, i == 0, "A"), H * 0.30, H * 0.64, color=color, veil=veil)
            p = tmp / f"layer-{i + 1}.png"
            img.save(p)
            layers.append((p, cuts[i], cuts[i + 1], i > 0, i < n - 1))
        return layers
    # Typ B: Überschrift oben, Textbox darunter, Schlusszeile unten – alles bleibt stehen.
    # Erst alle Schleier, dann alle Texte: sonst dunkelt der Schleier der Schlusszeile die Textbox ab.
    head = slides[0]
    box = slides[1] if len(slides) > 2 else None
    tail = slides[-1] if len(slides) >= 2 else None
    specs = []  # (name, items, top, bottom, max_w, start, fade_in)
    _, _, y1 = text_layer(PIL, fonts, block_items(head, True, "B"), H * 0.15, H * 0.36, center=False,
                          color=color, part="text")
    specs.append(("1", block_items(head, True, "B"), H * 0.15, H * 0.36, W * 0.78, 0.0, False))
    y = y1 + H * 0.045
    if box:
        _, _, y2 = text_layer(PIL, fonts, block_items(box, False, "B"), y, H * 0.68, max_w=W * 0.74,
                              center=False, color=color, part="text")  # Reels: nie Glas-Karte
        specs.append(("2", block_items(box, False, "B"), y, H * 0.68, W * 0.74, 1.0, True))
        y = y2 + H * 0.05
    if tail:
        items = [("small", 0.042, ri.strip_marks(t), "center") for _, t in tail["blocks"]]
        specs.append(("3", items, min(y, H * 0.70), H * 0.79, W * 0.78, 6.0, True))
    for part in (("veil", "text") if veil else ("text",)):
        for name, items, top, bottom, mw, start, fin in specs:
            img, _, _ = text_layer(PIL, fonts, items, top, bottom, max_w=mw, center=False, color=color,
                                   veil=veil, part=part)
            p = tmp / f"layer-{name}-{part}.png"
            img.save(p)
            layers.append((p, start, T, fin, False))
    return layers


# ---------- Lesbarkeit: Schriftfarbe nach Hintergrund ----------
def lum(rgb_or_v):
    """Relative Leuchtdichte (WCAG) aus RGB-Tupel oder Grauwert 0-255."""
    vals = rgb_or_v if isinstance(rgb_or_v, tuple) else (rgb_or_v,) * 3
    lin = [(c / 255 / 12.92) if c / 255 <= 0.04045 else ((c / 255 + 0.055) / 1.055) ** 2.4 for c in vals]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def percentile(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, int(q * (len(values) - 1)))] if values else 0


def pick_color(frames, boxes):
    """frames: PIL-Bilder (1080×1920), boxes: Textbereiche → (farbe, schleier, kontrast, bericht).
    Massgebend sind die hellsten Stellen (für helle Schrift) bzw. die dunkelsten (für dunkle Schrift)."""
    px = []
    for fr in frames:
        g = fr.convert("L")
        for b in boxes:
            small = g.crop(b).resize((60, max(1, int(60 * (b[3] - b[1]) / max(1, b[2] - b[0])))))
            px += list(small.get_flattened_data() if hasattr(small, "get_flattened_data") else small.getdata())
    if not px:
        return CREAM, None, 99.0, "kein Textbereich"
    # 99 %: auch kleine, sehr helle Stellen (Kerzenflamme, Lampe) hinter dem Text zählen
    v_bright, v_dark = percentile(px, 0.99), percentile(px, 0.05)
    c_cream = contrast(lum(CREAM), lum(v_bright))
    c_dark = contrast(lum(DARK), lum(v_dark))
    veil = None
    if c_cream >= MIN_CONTRAST:
        color, c = CREAM, c_cream                      # Normalfall: abgedunkeltes Video
    elif c_dark >= MIN_CONTRAST:
        color, c = DARK, c_dark                        # heller Hintergrund (Nebel, Fenster, Schnee)
    else:
        # unruhig (hell und dunkel gemischt): Creme bleibt, weicher dunkler Schleier – so stark wie nötig
        color = CREAM
        target = 128                                   # Grauwert, bei dem Creme ca. 3:1 erreicht
        a = min(0.8, max(0.3, (v_bright - target) / max(1, v_bright - 30)))
        veil = (30, 22, 16, int(255 * a))
        c = contrast(lum(CREAM), lum(int(v_bright * (1 - a) + 30 * a)))
    name = "Creme" if color == CREAM else "Dunkelbraun"
    return color, veil, c, f"{name} (Kontrast {c:.1f}:1{', mit weichem Lese-Schleier' if veil else ''})"


def layer_boxes(layers):
    from PIL import Image
    boxes = []
    for p, *_ in layers:
        bb = Image.open(p).getchannel("A").getbbox()
        if bb:
            pad = 20
            boxes.append((max(0, bb[0] - pad), max(0, bb[1] - pad), min(W, bb[2] + pad), min(H, bb[3] + pad)))
    return boxes


def sample_frames(video, variant, T, tmp):
    from PIL import Image
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                       capture_output=True, text=True)
    try:
        dur = float(r.stdout.strip())
    except ValueError:
        dur = T
    pre = ("hflip," if variant in ("spiegel", "ausschnitt") else "") + \
          ("crop=iw*0.86:ih*0.86:(iw-iw*0.86)/2:(ih-ih*0.86)*0.6," if variant == "ausschnitt" else "")
    frames = []
    for i, t in enumerate((0.3, T * 0.35, T * 0.65, T - 0.4)):
        out = tmp / f"probe-{i}.png"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t % max(dur, 0.5):.2f}", "-i", str(video),
                        "-frames:v", "1", "-vf",
                        f"{pre}scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}", str(out)],
                       capture_output=True)
        if out.exists():
            frames.append(Image.open(out).convert("RGB"))
    return frames


# ---------- Video ----------
def has_audio(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return bool(r.stdout.strip())


def ffmpeg_cmd(video, layers, variant, T, out, audio, music=None, mvol=MUSIK_VOL):
    """music = (Pfad, Startsekunde, Stück-Lautstärke in dB) oder None. Mit Musik: Originalton (falls vorhanden) + Musik, Musik auf Ziel-Lautstärke angeglichen."""
    cmd = ["ffmpeg", "-y", "-v", "error", "-stream_loop", "-1", "-i", str(video)]
    for p, *_ in layers:
        cmd += ["-loop", "1", "-framerate", "30", "-t", f"{T}", "-i", str(p)]
    mi = 1 + len(layers)
    if music:
        cmd += ["-ss", f"{music[1]:.2f}", "-t", f"{T}", "-i", str(music[0])]
    pre = ""
    if variant in ("spiegel", "ausschnitt"):
        pre += "hflip,"
    if variant == "ausschnitt":
        pre += "crop=iw*0.86:ih*0.86:(iw-iw*0.86)/2:(ih-ih*0.86)*0.6,"
    f = [f"[0:v]{pre}scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps=30[b0]"]
    prev = "b0"
    for k, (_, s, e, fin, fout) in enumerate(layers, start=1):
        chain = "format=rgba"
        if fin:
            chain += f",fade=t=in:st={s:.2f}:d={FADE}:alpha=1"
        if fout:
            chain += f",fade=t=out:st={e - FADE:.2f}:d={FADE}:alpha=1"
        f.append(f"[{k}:v]{chain}[l{k}]")
        f.append(f"[{prev}][l{k}]overlay=0:0:enable='between(t,{s:.2f},{e:.2f})'[b{k}]")
        prev = f"b{k}"
    f.append(f"[{prev}]format=yuv420p[vout]")
    fade_o = f"afade=t=in:st=0:d=0.2,afade=t=out:st={T - 0.5:.2f}:d=0.5"
    fade_m = f"afade=t=in:st=0:d=0.6,afade=t=out:st={T - 1.0:.2f}:d=1.0"
    if music:
        gain = f"volume={musik.MUSIK_ZIEL_DB - music[2]:.1f}dB,volume={mvol}"
        mus = f"[{mi}:a]aformat=sample_rates=44100:channel_layouts=stereo,{gain},{fade_m}"
    if music and audio:
        f.append(f"[0:a]atrim=0:{T},volume={ORIG_VOL},{fade_o}[ao]")
        f.append(mus + "[am]")
        f.append("[ao]aformat=sample_rates=44100:channel_layouts=stereo[ao2]")
        f.append("[ao2][am]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89[aout]")
        amap = ["-map", "[aout]"]
    elif music:
        f.append(mus + ",alimiter=limit=0.89[aout]")
        amap = ["-map", "[aout]"]
    else:
        amap = ["-map", "0:a:0", "-af", fade_o] if audio else []
    cmd += ["-filter_complex", ";".join(f), "-map", "[vout]"]
    if amap:
        cmd += amap + ["-c:a", "aac", "-b:a", "160k"]
    cmd += ["-t", f"{T}", "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
            "-profile:v", "high", "-movflags", "+faststart", str(out)]
    return cmd


# ---------- Titelbild ----------
def cover_photo(slot, day):
    """Foto aus dem Wochen-Pool, das in den letzten 42 Tagen nicht im Feed war (Titelbild steht im Raster)."""
    cands = []
    if day:
        res = media.pick(f"T{day:02d}-SN")
        cands += [f["id"] for f in res.get("fotos", []) if f.get("datei")]
    recs = {r["id"]: r for r in media.read_list()}
    rest = sorted((r for r in recs.values() if media.photo_path(r)), key=lambda r: r["id"], reverse=True)
    cands += [r["id"] for r in rest]
    for cid in cands:
        r = recs.get(cid)
        if not r or not media.photo_path(r):
            continue
        u = media.recent_feed_use(r)
        if u and u["slot"] != slot:
            continue
        return r
    return None


def render_cover(post, base_img, out, PIL, fonts):
    Image, ImageDraw, ImageFilter = PIL
    img = ri.cover(base_img.convert("RGB"), (W, H), Image, 0.6).convert("RGBA")
    items = [it for it in block_items(post["slides"][0], True, "A") if it[0] == "head"][:1]
    items = [("head", 0.084, t, al) for _, _, t, al in items]
    # Profilraster zeigt die Mitte (3:4) – Text bleibt dort
    layer, _, _ = text_layer(PIL, fonts, items, H * 0.36, H * 0.64, max_w=W * 0.76)
    bb = layer.getchannel("A").getbbox()
    color, veil, _, info = pick_color([img.convert("RGB")], [bb] if bb else [])
    if color != CREAM or veil:
        layer, _, _ = text_layer(PIL, fonts, items, H * 0.36, H * 0.64, max_w=W * 0.76, color=color, veil=veil)
    img = Image.alpha_composite(img, layer)
    print(f"Titelbild-Schrift: {info}")
    img.convert("RGB").save(out, "JPEG", quality=92)


def video_frame(video, t=1.0):
    tmp = Path(tempfile.mkdtemp()) / "frame.jpg"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t}", "-i", str(video), "-frames:v", "1", str(tmp)],
                   check=True)
    return tmp


# ---------- Ablauf ----------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("post")
    ap.add_argument("--video", help="Video-Datei statt Monats-Pool (wird nicht als Verwendung eingetragen)")
    ap.add_argument("--variante", choices=media.VARIANTS)
    ap.add_argument("--typ", choices=["A", "B"])
    ap.add_argument("--datum", help="Veröffentlichungsdatum (für die 10-Tage-Regel), Standard heute")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--ohne-cover", action="store_true")
    ap.add_argument("--cover", choices=["pool", "video"], default="pool",
                    help="Titelbild aus dem Foto-Pool (Standard) oder ein Bild aus dem Reel-Video")
    ap.add_argument("--force", action="store_true", help="auch ohne bestandene QA rendern")
    ap.add_argument("--musik", default="auto", help="auto (Standard, wenn Stücke in medien/musik/ liegen) | aus | Stück-ID, z. B. M03")
    ap.add_argument("--musik-lautstaerke", type=float, default=MUSIK_VOL, help="Faktor auf die Musik-Lautstärke (Standard 1,0; 0,7 = leiser)")
    a = ap.parse_args()

    path = Path(a.post)
    if not path.exists():
        sys.exit(f"Datei nicht gefunden: {path}")
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} fehlt (brew install ffmpeg)")
    post = read_post(path)
    if post["format"] and post["format"] != "reel":
        sys.exit(f"{path.name} ist kein Reel (Format: {post['format']})")
    if not a.force and not ri.qa_passed(path):
        sys.exit("QA (--final) nicht bestanden – erst prüfen: python3 scripts/qa_check.py " + str(path) + " --final")
    slot = post["slot"]
    typ = a.typ or post["typ"] or plan.reel_typ(slot) or "A"
    day = plan_day(slot)
    design = plan.slide_design(day) if day else "glas"

    pick = None
    if a.video:
        video, variant = Path(a.video), a.variante or "original"
        if not video.exists():
            sys.exit(f"Video nicht gefunden: {video}")
    else:
        pick = media.video_pick(slot, a.datum)
        if not pick:
            sys.exit("Kein freies Video im Monats-Pool – media.py monat-status zeigt, was fehlt (oder --video PFAD)")
        video, variant = ROOT / pick["datei"], a.variante or pick["variante"]

    T = LEN[typ]
    out_dir = ROOT / "output" / slot
    print(f"{slot}: Typ {typ} ({T:.0f} s), Design {design}, Video {video.name} ({variant})")
    if a.dry_run:
        return

    try:
        from PIL import Image, ImageDraw, ImageFilter, ImageFont
    except ImportError:
        sys.exit("Pillow fehlt: python3 -m pip install -r requirements.txt")
    PIL = (Image, ImageDraw, ImageFilter)
    fonts = ri.Fonts(ImageFont)
    for w in fonts.warnings:
        print("Hinweis:", w)
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    try:
        layers = build_layers(post, typ, design, tmp, PIL, fonts)
        # Lesbarkeit: Schriftfarbe nach den hellsten/dunkelsten Stellen hinter dem Text wählen
        color, veil, _, info = pick_color(sample_frames(video, variant, LEN[typ], tmp), layer_boxes(layers))
        if color != CREAM or veil:
            layers = build_layers(post, typ, design, tmp, PIL, fonts, color=color, veil=veil)
        print(f"Schrift: {info}")
        out = out_dir / "reel.mp4"
        mpick = None
        if a.musik != "aus":
            mpick = musik.pick(slot, a.datum)
            if a.musik not in ("auto", "aus"):
                rec = next((x for x in musik.read_list() if x["id"] == a.musik), None)
                if not rec:
                    sys.exit(f"Unbekanntes Musikstück: {a.musik}")
                mpick = {"id": rec["id"], "datei": rec["datei"], "start": musik.segments(rec)[0], "schon_verwendet": False,
                         "laut_db": rec.get("laut_db", -18.0)}
            if mpick is None and a.musik == "auto":
                print("Hinweis: keine Musik verfügbar (medien/musik/ leer oder alle Abschnitte in Pause) – nur Originalton")
        music = (ROOT / mpick["datei"], mpick["start"], mpick.get("laut_db", -18.0)) if mpick else None
        r = subprocess.run(ffmpeg_cmd(video, layers, variant, T, out, has_audio(video), music, a.musik_lautstaerke),
                           capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"ffmpeg-Fehler: {r.stderr.strip()[-600:]}")
        print(f"Reel: {out.relative_to(ROOT)}" + (f" mit Musik {mpick['id']} ab {mpick['start']:.0f} s" if mpick else ""))
        if mpick and not mpick.get("schon_verwendet"):
            musik.use(slot, mpick["id"], mpick["start"], a.datum)
        if pick and (not pick.get("schon_verwendet") or variant != pick["variante"]):
            media.video_use(slot, pick["id"], variant, a.datum)
            print(f"Video-Verwendung eingetragen: {pick['id']} ({variant})")

        if not a.ohne_cover:
            rec = cover_photo(slot, day) if a.cover == "pool" else None
            base = Image.open(media.photo_path(rec)) if rec else Image.open(video_frame(video))
            cpath = out_dir / "cover.jpg"
            render_cover(post, base, cpath, PIL, fonts)
            if rec:
                media.cmd_use(slot, [rec["id"]], False)
            print(f"Titelbild: {cpath.relative_to(ROOT)} ({'Foto ' + rec['id'] if rec else 'Bild aus dem Video'})")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
