#!/usr/bin/env python3
"""Community-Erfolg als Story (Di + Sa, Slot Txx-SE) und Link-Slide für die Verkaufs-Story.

    python3 scripts/erfolg.py status                   # wie viele Erfolge noch unbenutzt sind
    python3 scripts/erfolg.py T02-SE [--datum JJJJ-MM-TT] [--datei NAME]
                                                       # nächsten Erfolg aus medien/erfolge/neu/ als Story bauen
    python3 scripts/erfolg.py link-slide T05-SP        # letzte Slide als output/T05-SP/link-slide.jpg (zum Posten mit Link-Sticker)

Material: Screenshots (jpg/png/webp/heic) oder kurze Texte (.txt) in medien/erfolge/neu/. Pamina legt nur Erfolge ab,
die sie mit Erlaubnis teilen darf, und schwärzt Namen und Profilbilder vorher (das Skript kann das nicht erkennen).
Regeln (Pamina, 2026-11-19): jeder Erfolg wird nur EINMAL geteilt (Prüfsumme in medien/erfolgsliste.jsonl,
benutzte Dateien wandern nach medien/erfolge/verwendet/). Auf jeder Erfolgs-Story steht
„Geteilt mit Erlaubnis · Einzelfall, kein Ergebnisversprechen“. Die Story bekommt Musik wie alle Storys
(render_story.py, 10 s) und eine Mini-Post-Datei output/<slot>.md, damit die Warteschlange sie einplanen kann.
"""
import argparse
import datetime
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NEU = ROOT / "medien" / "erfolge" / "neu"
BENUTZT = ROOT / "medien" / "erfolge" / "verwendet"
LISTE = ROOT / "medien" / "erfolgsliste.jsonl"
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".heic")
W, H = 1080, 1920
TITEL = "Aus der Community"
FUSS = "Geteilt mit Erlaubnis · Einzelfall, kein Ergebnisversprechen"
SEKUNDEN = 10.0


class Fehler(Exception):
    pass


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read_list():
    if not LISTE.exists():
        return []
    return [json.loads(l) for l in LISTE.read_text(encoding="utf-8").splitlines() if l.strip()]


def kandidaten():
    used = {r["sha256"] for r in read_list()}
    files = sorted(p for p in NEU.glob("*") if p.is_file() and p.suffix.lower() in IMG_EXT + (".txt",)) if NEU.exists() else []
    frei, doppelt = [], []
    for p in files:
        (doppelt if sha(p) in used else frei).append(p)
    return frei, doppelt


def cmd_status():
    frei, doppelt = kandidaten()
    n = len(read_list())
    print(f"{len(frei)} Erfolg(e) unbenutzt in medien/erfolge/neu/, {n} schon geteilt.")
    for p in doppelt:
        print(f"  ACHTUNG: {p.name} wurde schon geteilt (gleiche Datei) – wird nie erneut verwendet")
    tage = len([1 for _ in range(2)])  # Di + Sa
    if frei:
        print(f"Reicht für ca. {len(frei) // tage} Wochen (2 pro Woche).")


# ---------- Bild ----------
def open_image(p):
    from PIL import Image, ImageOps
    if p.suffix.lower() == ".heic":
        tmp = ROOT / "output" / "_vorschau" / (p.stem + ".png")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["sips", "-s", "format", "png", str(p), "--out", str(tmp)], capture_output=True)
        if r.returncode != 0:
            raise Fehler(f"{p.name}: HEIC konnte nicht gelesen werden (als JPG/PNG ablegen)")
        p = tmp
    return ImageOps.exif_transpose(Image.open(p)).convert("RGB")  # Metadaten fallen beim Neuzeichnen weg


def background(slot):
    """Hintergrund: Foto der Nurture-Story dieses Tags (weich, abgedunkelt), sonst warmes Beige."""
    from PIL import Image, ImageEnhance, ImageFilter
    try:
        import media
        res = media.pick(f"{slot[:3]}-SN")
        f = next((x for x in res.get("fotos", []) if x.get("datei")), None)
        if f:
            img = Image.open(ROOT / f["datei"]).convert("RGB")
            s = max(W / img.width, H / img.height)
            img = img.resize((round(img.width * s), round(img.height * s)))
            l, t = (img.width - W) // 2, (img.height - H) // 2
            img = img.crop((l, t, l + W, t + H)).filter(ImageFilter.GaussianBlur(14))
            return ImageEnhance.Brightness(img).enhance(0.55)
    except SystemExit:
        pass
    except Exception:
        pass
    return Image.new("RGB", (W, H), (92, 76, 62))


def wrap(draw, text, font, max_w):
    lines = []
    for para in text.splitlines():
        words, cur = para.split(), ""
        for w in words:
            t = (cur + " " + w).strip()
            if draw.textlength(t, font=font) <= max_w:
                cur = t
            else:
                if cur:
                    lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def render(src, out_png, slot):
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    import render_images as ri
    fonts = ri.Fonts(ImageFont)
    img = background(slot)
    d = ImageDraw.Draw(img)
    f_title = fonts.get("bold", 64)
    f_foot = fonts.get("accent", 34)
    tw = d.textlength(TITEL, font=f_title)
    d.text(((W - tw) / 2, 190), TITEL, font=f_title, fill=(255, 255, 255))
    d.line([(W / 2 - 60, 290), (W / 2 + 60, 290)], fill=(255, 255, 255), width=2)
    box_top, box_bot, max_w = 350, 1580, 900
    if src.suffix.lower() == ".txt":
        text = src.read_text(encoding="utf-8").strip()
        if not text:
            raise Fehler(f"{src.name} ist leer")
        size = 54
        while size > 30:
            f = fonts.get("text", size)
            lines = wrap(d, f"„{text}“", f, max_w - 120)
            lh = int(size * 1.35)
            if lh * len(lines) <= box_bot - box_top - 120:
                break
            size -= 2
        card_h = lh * len(lines) + 120
        y0 = box_top + (box_bot - box_top - card_h) // 2
        card = Image.new("RGBA", (max_w, card_h), (250, 245, 237, 236))
        img.paste(card, ((W - max_w) // 2, y0), card)
        y = y0 + 60
        for ln in lines:
            lw = d.textlength(ln, font=f)
            d.text(((W - lw) / 2, y), ln, font=f, fill=(62, 50, 40))
            y += lh
    else:
        shot = open_image(src)
        s = min(max_w / shot.width, (box_bot - box_top) / shot.height)
        shot = shot.resize((round(shot.width * s), round(shot.height * s)), Image.LANCZOS)
        x0, y0 = (W - shot.width) // 2, box_top + (box_bot - box_top - shot.height) // 2
        shadow = Image.new("RGBA", (shot.width + 40, shot.height + 40), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle([20, 20, shot.width + 20, shot.height + 20], 28, fill=(0, 0, 0, 110))
        shadow = shadow.filter(ImageFilter.GaussianBlur(14))
        img.paste(shadow, (x0 - 20, y0 - 10), shadow)
        mask = Image.new("L", shot.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, shot.width, shot.height], 24, fill=255)
        img.paste(shot, (x0, y0), mask)
    for i, ln in enumerate(wrap(d, FUSS, f_foot, W - 160)):
        lw = d.textlength(ln, font=f_foot)
        d.text(((W - lw) / 2, 1660 + i * 48), ln, font=f_foot, fill=(255, 255, 255))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png)


def write_md(slot, src_name, datum):
    md = ROOT / "output" / f"{slot}.md"
    md.write_text(f"""# Post {slot} · Story-Erfolg · Community · Erfolg

## Agent 1 · Strategist
- **Slot:** {slot}
- **Format:** Story-Erfolg
- **Ausrichtung:** Erfolg (Social Proof, kein Keyword)
- **Highlight:** Erfolg
- **Quelle:** medien/erfolge/verwendet/{src_name} (geteilt mit Erlaubnis, nur einmal verwendet, {datum})

## Agent 7 · Copywriter
- **Variante:** story
**Caption:**

Werbung 🤍
""", encoding="utf-8")
    return md


def cmd_build(slot, datum, datei):
    slot = plan.norm_slot(slot)
    if not slot.endswith("-SE"):
        raise Fehler(f"{slot} ist kein Erfolgs-Slot (Txx-SE, Di und Sa)")
    datum = datum or datetime.date.today().isoformat()
    if any(r["slot"] == slot and r["datum"] == datum for r in read_list()):
        raise Fehler(f"{slot} hat für {datum} schon einen Erfolg (output/{slot}/ ansehen)")
    frei, _ = kandidaten()
    if datei:
        frei = [p for p in frei if p.name == datei]
        if not frei:
            raise Fehler(f"{datei} nicht in medien/erfolge/neu/ oder schon einmal geteilt")
    if not frei:
        raise Fehler("Kein unbenutzter Erfolg in medien/erfolge/neu/ – Pamina bitten, neue (anonymisierte) Erfolge abzulegen")
    src = frei[0]
    h = sha(src)
    outdir = ROOT / "output" / slot
    for old in list((outdir / "slides").glob("slide-*.png")) if (outdir / "slides").exists() else []:
        old.unlink()
    render(src, outdir / "slides" / "slide-1.png", slot)
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "render_story.py"), slot, "--sekunden", str(SEKUNDEN),
                        "--datum", datum], capture_output=True, text=True)
    if r.returncode != 0:
        raise Fehler(f"render_story.py: {(r.stderr or r.stdout).strip()[-400:]}")
    BENUTZT.mkdir(parents=True, exist_ok=True)
    ziel = BENUTZT / src.name
    if ziel.exists():
        ziel = BENUTZT / f"{src.stem}-{h[:8]}{src.suffix}"
    shutil.move(str(src), str(ziel))
    with LISTE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"sha256": h, "datei": str(ziel.relative_to(ROOT)), "slot": slot, "datum": datum},
                            ensure_ascii=False) + "\n")
    md = write_md(slot, ziel.name, datum)
    print(f"{slot}: Erfolg {src.name} → output/{slot}/story-1.mp4 ({SEKUNDEN:.0f} s, mit Musik), {md.relative_to(ROOT)}")
    print("Bitte ansehen: output/" + slot + "/slides/slide-1.png (Namen/Profilbilder geschwärzt? keine fremden Daten?)")


def cmd_link_slide(slot):
    slot = plan.norm_slot(slot)
    d = ROOT / "output" / slot / "slides"
    num = lambda p: int(re.search(r"(\d+)", p.stem).group(1))
    slides = sorted(d.glob("slide-*.png"), key=num) if d.exists() else []
    if not slides:
        raise Fehler(f"Keine Slides in output/{slot}/slides/")
    from PIL import Image
    out = ROOT / "output" / slot / "link-slide.jpg"
    Image.open(slides[-1]).convert("RGB").save(out, quality=92)
    print(f"{out.relative_to(ROOT)} – zum Posten mit Link-Sticker (Button-Text frei wählbar)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", help="status | link-slide | <Slot Txx-SE>")
    ap.add_argument("slot", nargs="?")
    ap.add_argument("--datum")
    ap.add_argument("--datei")
    a = ap.parse_args()
    if a.cmd == "status":
        cmd_status()
    elif a.cmd == "link-slide":
        if not a.slot:
            sys.exit("Slot fehlt: erfolg.py link-slide T05-SP")
        cmd_link_slide(a.slot)
    else:
        cmd_build(a.cmd, a.datum, a.datei)


if __name__ == "__main__":
    try:
        main()
    except Fehler as e:
        print(f"FEHLER: {e}", file=sys.stderr)
        sys.exit(1)
