#!/usr/bin/env python3
"""Erzeugt die Bilder eines fertigen Posts direkt mit Google Imagen 4 / Gemini.

  render_images.py output/T03-K.md [--model imagen-4] [--count 2] [--aspect 9:16]
                   [--slides] [--base PFAD] [--no-images] [--dry-run] [--force]

Ablauf: nimmt den Midjourney-Prompt aus Agent 6 (wörtliche Abdunkelungs-Formel bleibt erhalten),
entfernt nur die Midjourney-Parameter (--ar/--style/--v) und übersetzt sie in API-Einstellungen.
Bilder landen in output/<slot>/bild-1.png … ; mit --slides werden zusätzlich die Slide-Texte aus
Agent 3 im Stil von Agent 9 auf das Bild gesetzt (output/<slot>/slides/slide-1.png …).

--model     gemini-pro (Standard) | gemini-flash | imagen-4 | imagen-4-ultra | imagen-4-fast | volle ID
--list-models  zeigt, welche Bildmodelle dein Schlüssel nutzen darf
--count     Anzahl Varianten (1-4)
--aspect    Seitenverhältnis (Standard: aus --ar des Prompts, also 9:16)
--slides    Text-Overlay für Karussell/Story (braucht Pillow und die Schriften in assets/fonts/)
--base      Basisbild für --slides (Standard: output/<slot>/bild-1.png)
--no-images keine API-Anfrage, nur --slides auf ein vorhandenes Bild
--dry-run   zeigt die Anfrage, ruft die API nicht auf (kein Schlüssel nötig)
--force     auch ohne bestandene QA (--final) rendern

API-Schlüssel: GEMINI_API_KEY (oder GOOGLE_API_KEY) als Umgebungsvariable oder in .env.
Exit-Code 1 bei Fehlern.
"""
import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import qa_check  # noqa: E402

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
MODELS = {
    "imagen-4": "imagen-4.0-generate-001",
    "imagen-4-ultra": "imagen-4.0-ultra-generate-001",
    "imagen-4-fast": "imagen-4.0-fast-generate-001",
    "gemini-pro": "gemini-3-pro-image",
    "gemini-flash": "gemini-3.1-flash-image",
    "gemini": "gemini-3-pro-image",
}
DEFAULT_MODEL = "gemini-pro"
ASPECTS = {"1:1", "3:4", "4:3", "9:16", "16:9"}
TEXT_COLOR = "#F5EFE6"  # Agent 9
FONT_FILES = {
    "hook": ["PlayfairDisplay-Bold.ttf", "PlayfairDisplay-VariableFont_wght.ttf"],
    "body": ["Montserrat-Italic.ttf", "Montserrat-Italic-VariableFont_wght.ttf"],
}
FONT_FALLBACK = {
    "hook": "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    "body": "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
}


# ---------- Post lesen ----------
def load_post(path):
    text = path.read_text(encoding="utf-8")
    secs, _ = qa_check.split_sections(text)
    return text, {k: qa_check.strip_comments(v) for k, v in secs.items()}


def image_prompt(clean):
    """Midjourney-Prompt aus Agent 6 → (API-Prompt, Seitenverhältnis)."""
    blocks = re.findall(r"```[^\n]*\n(.*?)```", clean.get("6", ""), re.S)
    mj = [b.strip() for b in blocks if "--ar" in b]
    if not mj:
        raise SystemExit("Agent 6: kein Midjourney-Prompt (Codeblock mit --ar) gefunden")
    p = mj[0]
    m = re.search(r"--ar\s+(\d+:\d+)", p)
    aspect = m.group(1) if m else "9:16"
    prompt = re.sub(r"\s--\w+(?:\s+[^\s-][^\s]*)?", "", " " + p).strip()
    if qa_check.IMG_FORMULA not in prompt:
        raise SystemExit("Die Bild-Formel ist im Prompt nicht mehr wörtlich enthalten – Abbruch")
    return prompt, aspect


def parse_slides(clean):
    """Slides/Einblendungen aus Agent 2 & 3 → [{'nr', 'lines', 'source'}]."""
    slides, cur = [], None
    for raw in clean.get("2&3", "").splitlines():
        line = raw.strip()
        h = re.match(r"^\*\*(?:Slide|Einblendung) (\d+)\b[^*]*\*\*\s*(.*)$", line)
        if h:
            cur = {"nr": int(h.group(1)), "lines": [], "source": None}
            slides.append(cur)
            if h.group(2).strip():
                cur["lines"].append(clean_line(h.group(2)))
            continue
        if cur is None:
            continue
        if not line:
            if cur["lines"]:
                cur = None
            continue
        if line.startswith("**Quelle:**"):
            cur["source"] = clean_line(line[len("**Quelle:**"):])
        elif line.startswith("**"):
            cur = None
        else:
            cur["lines"].append(clean_line(line))
    return [s for s in slides if s["lines"]]


def clean_line(s):
    s = s.strip()
    s = re.sub(r"\*\*?([^*]+)\*\*?", r"\1", s)
    return s.strip("*_ ").strip()


# ---------- API ----------
def api_key():
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        if os.environ.get(name):
            return os.environ[name].strip()
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            k, _, v = line.partition("=")
            if k.strip() in ("GEMINI_API_KEY", "GOOGLE_API_KEY") and v.strip():
                return v.strip().strip('"').strip("'")
    return None


def build_request(model, prompt, aspect, count):
    """→ (url, body, Anzahl Aufrufe). Imagen: ein Aufruf mit sampleCount; Gemini: ein Bild pro Aufruf."""
    if model.startswith("imagen"):
        body = {
            "instances": [{"prompt": prompt}],
            "parameters": {"sampleCount": count, "aspectRatio": aspect, "personGeneration": "dont_allow"},
        }
        return f"{API_BASE}/{model}:predict", body, 1
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": aspect}},
    }
    return f"{API_BASE}/{model}:generateContent", body, count


def post_json(url, body, key):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        try:
            detail = json.loads(detail)["error"]["message"]
        except (ValueError, KeyError, TypeError):
            pass
        hint = {
            404: "\nHinweis: Dieses Modell ist für deinen Schlüssel nicht verfügbar. "
                 "Verfügbare Modelle: python3 scripts/render_images.py --list-models",
            429: "\nHinweis: Kontingent erschöpft. Steht 'Free Tier' und 'limit: 0' in der Meldung, "
                 "musst du in Google AI Studio die Abrechnung (Billing) für das Projekt aktivieren.",
        }.get(e.code, "")
        raise SystemExit(f"API-Fehler {e.code}: {detail}{hint}")
    except urllib.error.URLError as e:
        raise SystemExit(f"Keine Verbindung zur API: {e.reason}")


def extract_images(resp):
    """Bilddaten (bytes) aus Imagen- oder Gemini-Antwort; dazu Hinweise bei Filterung."""
    imgs, notes = [], []
    for p in resp.get("predictions", []) or []:
        if p.get("bytesBase64Encoded"):
            imgs.append(base64.b64decode(p["bytesBase64Encoded"]))
        elif p.get("raiFilteredReason"):
            notes.append(p["raiFilteredReason"])
    for c in resp.get("candidates", []) or []:
        for part in (c.get("content") or {}).get("parts", []) or []:
            data = (part.get("inlineData") or part.get("inline_data") or {}).get("data")
            if data:
                imgs.append(base64.b64decode(data))
        if c.get("finishReason") not in (None, "STOP"):
            notes.append(f"finishReason={c.get('finishReason')}")
    fb = resp.get("promptFeedback", {}).get("blockReason")
    if fb:
        notes.append(f"blockReason={fb}")
    return imgs, notes


def list_models():
    key = api_key()
    if not key:
        raise SystemExit("Kein API-Schlüssel: GEMINI_API_KEY in .env eintragen (siehe .env.example)")
    tok, found = "", []
    while True:
        url = f"{API_BASE}?pageSize=1000" + (f"&pageToken={tok}" if tok else "")
        req = urllib.request.Request(url, headers={"x-goog-api-key": key})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise SystemExit(f"API-Fehler {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")
        found += [m for m in d.get("models", []) if re.search(r"imagen|image", m.get("name", ""))]
        tok = d.get("nextPageToken")
        if not tok:
            break
    if not found:
        print("Keine Bildmodelle für diesen Schlüssel freigeschaltet.")
    for m in found:
        print(m["name"].removeprefix("models/"))


# ---------- Text-Overlay ----------
def find_font(kind):
    dirs = [ROOT / "assets" / "fonts", Path.home() / "Library" / "Fonts", Path("/Library/Fonts"),
            Path("/usr/share/fonts/truetype")]
    for d in dirs:
        for name in FONT_FILES[kind]:
            if (d / name).exists():
                return d / name, False
    fb = Path(FONT_FALLBACK[kind])
    return (fb if fb.exists() else None), True


def wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textlength(test, font=font) <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_slides(base_path, slides, out_dir, size=(1080, 1920)):
    try:
        from PIL import Image, ImageDraw, ImageFilter, ImageFont
    except ImportError:
        raise SystemExit("Für --slides fehlt Pillow: python3 -m pip install -r requirements.txt")
    warnings = []
    fonts = {}
    for kind in ("hook", "body"):
        path, fallback = find_font(kind)
        if fallback:
            warnings.append(f"Schrift für {kind} nicht in assets/fonts/ gefunden – Ersatz: {path or 'Pillow-Standard'}")
        fonts[kind] = path

    def font(kind, px):
        p = fonts[kind]
        if p is None:
            return ImageFont.load_default(size=px)
        f = ImageFont.truetype(str(p), px)
        if "Variable" in p.name and kind == "hook":
            try:
                f.set_variation_by_name("Bold")
            except (OSError, ValueError):
                pass
        return f

    base = Image.open(base_path).convert("RGB")
    W, H = size
    scale = max(W / base.width, H / base.height)
    base = base.resize((round(base.width * scale), round(base.height * scale)), Image.LANCZOS)
    left, top = (base.width - W) // 2, (base.height - H) // 2
    base = base.crop((left, top, left + W, top + H))

    hook_px = round(W * 0.068)
    body_px = round(hook_px * 0.6)  # Agent 9: ca. 60 % der Hook-Größe
    max_w = W * 0.80
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for s in slides:
        is_hook = s["nr"] == 1
        f = font("hook" if is_hook else "body", hook_px if is_hook else body_px)
        img = base.copy()
        draw = ImageDraw.Draw(img)
        rows = []  # (text, font, gap_after)
        for i, para in enumerate(s["lines"]):
            for ln in wrap(draw, para, f, max_w):
                rows.append((ln, f, 0))
            rows[-1] = (rows[-1][0], f, round(f.size * 0.6))
        if s["source"]:
            sf = font("body", round(body_px * 0.75))
            rows.append((s["source"], sf, 0))
        heights = [r[1].size * 1.3 + r[2] for r in rows]
        total = sum(heights)
        y = max(H * 0.20, min(H * 0.42 - total / 2, H * 0.80 - total))  # mittlere 60 %, über dem Motiv
        shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        text_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        td = ImageDraw.Draw(text_layer)
        for (txt, fnt, _), h in zip(rows, heights):
            w = td.textlength(txt, font=fnt)
            x = (W - w) / 2
            sd.text((x + 2, y + 3), txt, font=fnt, fill=(0, 0, 0, 120))
            td.text((x, y), txt, font=fnt, fill=TEXT_COLOR)
            y += h
        shadow = shadow.filter(ImageFilter.GaussianBlur(4))  # zarter Schatten
        img = Image.alpha_composite(Image.alpha_composite(img.convert("RGBA"), shadow), text_layer)
        p = out_dir / f"slide-{s['nr']}.png"
        img.convert("RGB").save(p, optimize=True)
        written.append(p)
    return written, warnings


# ---------- Ablauf ----------
def qa_passed(path):
    ns = argparse.Namespace(final=True, names=str(ROOT / "data" / "forbidden-names.txt"),
                            history=str(ROOT / "data" / "prompt-history.jsonl"))
    R, *_ = qa_check.run_checks(path.read_text(encoding="utf-8"), ns, path.stem)
    return R.n_fail == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?")
    ap.add_argument("--list-models", action="store_true")
    ap.add_argument("--model", default=os.environ.get("GEMINI_IMAGE_MODEL", DEFAULT_MODEL))
    ap.add_argument("--count", type=int, default=2)
    ap.add_argument("--aspect")
    ap.add_argument("--slides", action="store_true")
    ap.add_argument("--base")
    ap.add_argument("--no-images", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args()

    if args.list_models:
        list_models()
        return
    if not args.file:
        sys.exit("Bitte die Post-Datei angeben, z. B. output/T03-K.md")
    path = Path(args.file)
    if not path.exists():
        sys.exit(f"Datei nicht gefunden: {path}")
    if not args.force and not args.dry_run and not qa_passed(path):
        sys.exit("QA nicht bestanden (qa_check.py --final) – erst prüfen, dann rendern (oder --force)")
    _, clean = load_post(path)
    out_dir = Path(args.out) if args.out else path.parent / path.stem
    model = MODELS.get(args.model, args.model)
    if not 1 <= args.count <= 4:
        sys.exit("--count muss zwischen 1 und 4 liegen")

    if not args.no_images:
        prompt, aspect = image_prompt(clean)
        aspect = args.aspect or aspect
        if aspect not in ASPECTS:
            sys.exit(f"Seitenverhältnis {aspect} wird nicht unterstützt ({', '.join(sorted(ASPECTS))})")
        if len(prompt.split()) > 330:
            print(f"WARN Prompt hat {len(prompt.split())} Wörter – Imagen kürzt sehr lange Prompts")
        url, body, calls = build_request(model, prompt, aspect, args.count)
        if args.dry_run:
            print(f"POST {url}  (×{calls})")
            print(json.dumps(body, ensure_ascii=False, indent=2))
            return
        key = api_key()
        if not key:
            sys.exit("Kein API-Schlüssel: GEMINI_API_KEY in .env eintragen (siehe .env.example)")
        images, notes = [], []
        for _ in range(calls):
            imgs, n = extract_images(post_json(url, body, key))
            images += imgs
            notes += n
        if not images:
            sys.exit("Die API hat kein Bild geliefert" + (f" ({'; '.join(notes)})" if notes else ""))
        out_dir.mkdir(parents=True, exist_ok=True)
        for i, data in enumerate(images, 1):
            p = out_dir / f"bild-{i}.png"
            p.write_bytes(data)
            print(f"Bild gespeichert: {p}")
        for n in notes:
            print(f"WARN Bild gefiltert: {n}")

    if args.slides:
        slides = parse_slides(clean)
        if not slides:
            sys.exit("Keine Slides/Einblendungen in Agent 2 & 3 gefunden")
        base = Path(args.base) if args.base else out_dir / "bild-1.png"
        if not base.exists():
            sys.exit(f"Basisbild fehlt: {base}")
        written, warnings = render_slides(base, slides, out_dir / "slides")
        for w in warnings:
            print(f"WARN {w}")
        for p in written:
            print(f"Slide gespeichert: {p}")


if __name__ == "__main__":
    main()
