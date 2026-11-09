#!/usr/bin/env python3
"""Erzeugt die Bilder eines fertigen Posts direkt mit Google Imagen 4 / Gemini.

  render_images.py output/T03-K.md [--model gemini-pro] [--count 3] [--size 2K] [--aspect 4:5]
                   [--slides] [--base PFAD] [--no-images] [--dry-run] [--force]

Ablauf: nimmt den Midjourney-Prompt aus Agent 6 (wörtliche Abdunkelungs-Formel bleibt erhalten),
entfernt nur die Midjourney-Parameter (--ar/--style/--v) und übersetzt sie in API-Einstellungen.
Bilder landen in output/<slot>/bild-1.jpg … ; mit --slides entstehen fertige Slides im Karten-Design
(output/<slot>/slides/slide-1.png …). Auszeichnung der Slide-Texte: siehe parse_slides().

--model     gemini-pro (Standard) | gemini-flash | imagen-4 | imagen-4-ultra | imagen-4-fast | volle ID
--list-models  zeigt, welche Bildmodelle dein Schlüssel nutzen darf
--count     Anzahl Varianten (1-4, Standard 3); jede Variante mit eigener Komposition
--size      Bildgrösse bei Gemini 3: 1K | 2K (Standard) | 4K
--aspect    Seitenverhältnis (Standard nach Format: Karussell 4:5, Story und Reel 9:16)
--slides    Slides im Karten-Design (braucht Pillow und die Schriften in assets/fonts/);
            die Slides wechseln zwischen den Bildvarianten, Rahmen und Typografie bleiben gleich
--base      Basisbild(er) für --slides, kommagetrennt (Standard: alle output/<slot>/bild-*)
--no-images keine API-Anfrage, nur --slides auf ein vorhandenes Bild
--dry-run   zeigt die Anfrage, ruft die API nicht auf (kein Schlüssel nötig)
--force     auch ohne bestandene QA (--final) rendern
--week      Datei ist die Wochen-Datei (output/woche-<KW>.md): erzeugt alle Fotos der Woche (je 1 Bild, 9:16)
            nach medien/<KW>/fotos/<Dateiname>.jpg und trägt sie in medien/bildliste.jsonl ein
            (--only ID,ID … einzelne Fotos, --redo vorhandene neu)
--pool      Slides aus den Pool-Fotos, die Agent 6 unter „- **Pool:**“ nennt (keine neue API-Anfrage);
            Karussell 4:5 wird aus dem 9:16-Foto geschnitten, die Verwendung wird eingetragen
--design    glas | ohne | karte (Standard: aus dem Plan-Tag – ungerade Tage glas, gerade ohne)

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
import media  # noqa: E402
import plan  # noqa: E402

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
ASPECTS = {  # was das jeweilige Modell kann
    "imagen": {"1:1", "3:4", "4:3", "9:16", "16:9"},
    "gemini": {"1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"},
}
FORMAT_ASPECT = {"karussell": "4:5", "story": "9:16", "reel": "9:16"}
SLIDE_SIZE = {"4:5": (1080, 1350), "9:16": (1080, 1920), "3:4": (1080, 1440), "1:1": (1080, 1080)}
# Jede Variante bekommt eine eigene Bildkomposition, damit die Bilder nicht fast gleich aussehen.
# Steht am Anfang des Prompts (Vorrang vor der Kameraangabe von Agent 6); die Formel bleibt wörtlich am Ende.
VARIANTS = [
    "Composition for this variant: a calm wide view of the whole scene with generous empty space above,",
    "Composition for this variant: an intimate close-up of the main object from a low side angle, "
    "the background dissolving into soft blur,",
    "Composition for this variant: an overhead top-down flat lay of the surface, objects arranged "
    "loosely with plenty of empty surface around them,",
    "Composition for this variant: the scene seen from further back at a gentle diagonal, light falling "
    "across it in long soft stripes,",
]


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
    return mj_to_api(mj[0])


def mj_to_api(p):
    """Midjourney-Prompt → (API-Prompt ohne Parameter, Seitenverhältnis); Formel bleibt wörtlich."""
    m = re.search(r"--ar\s+(\d+:\d+)", p)
    aspect = m.group(1) if m else "9:16"
    prompt = re.sub(r"\s--\w+(?:\s+[^\s-][^\s]*)?", "", " " + p.strip()).strip()
    if qa_check.IMG_FORMULA not in prompt:
        raise SystemExit("Die Bild-Formel ist im Prompt nicht mehr wörtlich enthalten – Abbruch")
    return prompt, aspect


def parse_slides(clean):
    """Slides/Einblendungen aus Agent 2 & 3 → [{'nr', 'label', 'blocks': [(art, text)]}].

    Auszeichnung pro Zeile (Agent 3):  '# Überschrift'  |  '> Akzentzeile'  |  '**Quelle:** …'  |  Fliesstext.
    Im Text: **fett** (Schlüsselwort), ==markiert== (salbeigrün hinterlegt), _Akzent_ (Playfair kursiv).
    Ältere Posts (ganze Zeile in *…*) werden als normaler Fliesstext gelesen.
    """
    slides, cur = [], None
    for raw in clean.get("2&3", "").splitlines():
        line = raw.strip()
        h = re.match(r"^\*\*(?:Slide|Einblendung) (\d+)\b([^*]*)\*\*\s*(.*)$", line)
        if h:
            label = h.group(2).strip(" :·()-–")
            cur = {"nr": int(h.group(1)), "label": label, "blocks": []}
            slides.append(cur)
            if h.group(3).strip():
                cur["blocks"].append(("p", unwrap_line(h.group(3))))
            continue
        if cur is None:
            continue
        if not line:
            if cur["blocks"]:
                cur = None
            continue
        if line.startswith("**Quelle:**"):
            cur["blocks"].append(("src", strip_marks(line[len("**Quelle:**"):])))
        elif line.startswith("# "):
            cur["blocks"].append(("h", line[2:].strip()))
        elif line.startswith("> "):
            cur["blocks"].append(("k", strip_marks(line[2:])))
        elif re.match(r"^\*\*[^*]+:\*\*", line):
            cur = None
        else:
            cur["blocks"].append(("p", unwrap_line(line)))
    out = [s for s in slides if s["blocks"]]
    for s in out:  # alter Hook ohne Überschrift: erste Zeile wird zur Überschrift
        if s["nr"] == 1 and not any(a == "h" for a, _ in s["blocks"]):
            a, t = s["blocks"][0]
            s["blocks"][0] = ("h", t)
    return out


def unwrap_line(s):
    """'*ganze Zeile kursiv*' (altes Format) → Inhalt; Inline-Auszeichnung bleibt erhalten."""
    s = s.strip()
    if re.fullmatch(r"\*(?!\*)(.+?)(?<!\*)\*", s):
        s = s[1:-1].strip()
    return s


def strip_marks(s):
    s = re.sub(r"\*\*([^*]+)\*\*|==([^=]+)==|(?<!\w)_([^_]+)_(?!\w)|\*([^*]+)\*",
               lambda m: next(g for g in m.groups() if g is not None), s.strip())
    return s.strip("*_ ").strip()


def runs(text):
    """Inline-Auszeichnung → [(wort, stil)], stil: n (normal) | b (fett) | m (markiert) | a (Akzent)."""
    out = []
    for m in re.finditer(r"\*\*(.+?)\*\*|==(.+?)==|(?<!\w)_(.+?)_(?!\w)|([^*=_]+|[*=_])", text):
        b, mk, a, n = m.groups()
        style, chunk = ("b", b) if b is not None else ("m", mk) if mk is not None else \
            ("a", a) if a is not None else ("n", n)
        for i, w in enumerate(chunk.split()):
            glue = i == 0 and out and not chunk[:1].isspace()  # z. B. '**Minijob**.' → kein Leerzeichen
            if glue and style == "n" and re.fullmatch(r"[.,:;!?…“”\"')]+", w):
                out[-1] = (out[-1][0], out[-1][1], (out[-1][2] if len(out[-1]) > 2 else "") + w)
                continue
            out.append((w, style, ""))
    return out


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


def variant_prompts(prompt, count):
    """Gleiche Szene, verschiedene Kompositionen; die Formel bleibt wörtlich am Ende."""
    head, sep, tail = prompt.partition(qa_check.IMG_FORMULA)
    if not sep:
        raise SystemExit("Die Bild-Formel fehlt im Prompt – Abbruch")
    out = []
    for i in range(count):
        v = VARIANTS[i % len(VARIANTS)].replace("Composition for this variant:",
                                                 "Camera and framing for this image (this overrides any angle "
                                                 "or framing described later):").rstrip(",") + "."
        p = f"{v} {head.strip()} {sep}{tail}"
        out.append(p)
    return out


def post_format(clean):
    f = (qa_check.field(clean.get("1", ""), "Format") or "").lower()
    return "story" if f.startswith("story") else f.split()[0] if f else ""


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


def image_ext(data):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return ".png"


# ---------- Slide-Design (Karte auf Foto) ----------
# Erdige Markenfarben: Creme-Karte, Dunkelbraun, Salbei, warmes Braun.
PALETTE = {
    "card": (243, 236, 225),
    "head": (47, 38, 32),
    "text": (74, 63, 54),
    "accent": (138, 106, 79),
    "marker": (201, 211, 188),
    "tape": (169, 181, 154),
    "muted": (122, 106, 92),
}
FONT_FILES = {  # (Dateinamen, Gewicht der variablen Schrift)
    "head": (["PlayfairDisplay-VariableFont_wght.ttf", "PlayfairDisplay-Bold.ttf"], 700),
    "accent": (["PlayfairDisplay-Italic-VariableFont_wght.ttf", "PlayfairDisplay-Italic.ttf"], 500),
    "text": (["Montserrat-VariableFont_wght.ttf", "Montserrat-Regular.ttf"], 400),
    "bold": (["Montserrat-VariableFont_wght.ttf", "Montserrat-SemiBold.ttf"], 650),
    "small": (["Montserrat-Italic-VariableFont_wght.ttf", "Montserrat-Italic.ttf"], 400),
}
FONT_FALLBACK = {
    "head": "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    "accent": "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
    "text": "/System/Library/Fonts/Supplemental/Arial.ttf",
    "bold": "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "small": "/System/Library/Fonts/Supplemental/Arial Italic.ttf",
}
HANDLE = "@zeit.reichtum"


def find_font(kind):
    names, _ = FONT_FILES[kind]
    for d in (ROOT / "assets" / "fonts", Path.home() / "Library" / "Fonts", Path("/Library/Fonts")):
        for name in names:
            if (d / name).exists():
                return d / name, False
    fb = Path(FONT_FALLBACK[kind])
    return (fb if fb.exists() else None), True


class Fonts:
    def __init__(self, ImageFont):
        self.IF, self.cache, self.paths, self.warnings = ImageFont, {}, {}, []
        for kind in FONT_FILES:
            path, fallback = find_font(kind)
            self.paths[kind] = path
            if fallback:
                self.warnings.append(f"Schrift '{kind}' nicht in assets/fonts/ – Ersatz: {path or 'Pillow-Standard'}")

    def get(self, kind, px):
        key = (kind, int(px))
        if key not in self.cache:
            p = self.paths[kind]
            if p is None:
                f = self.IF.load_default(size=int(px))
            else:
                f = self.IF.truetype(str(p), int(px))
                if "Variable" in p.name:
                    try:
                        f.set_variation_by_axes([FONT_FILES[kind][1]])
                    except (OSError, ValueError):
                        pass
            self.cache[key] = f
        return self.cache[key]


STYLE_FONT = {"n": "text", "b": "bold", "m": "bold", "a": "accent"}


def layout_block(draw, fonts, art, text, scale, W, max_w):
    """→ (zeilen, zeilenhöhe, abstand_danach); zeile = [(wort, stil, font, breite)]."""
    base = {"h": 0.074, "k": 0.052, "p": 0.046, "src": 0.029}[art] * W * scale
    if art == "h":
        words = [(w, "h") for w in strip_marks(text).split()]
        fmap = {"h": fonts.get("head", base)}
    elif art == "k":
        words = [(w, "k") for w in text.split()]
        fmap = {"k": fonts.get("accent", base)}
    elif art == "src":
        words = [(w, "s") for w in text.split()]
        fmap = {"s": fonts.get("small", base)}
    else:
        words = runs(text)
        fmap = {k: fonts.get(v, base * (1.08 if k == "a" else 1)) for k, v in STYLE_FONT.items()}
        fmap["tail"] = fonts.get("text", base)
    space = draw.textlength(" ", font=fmap.get("n", next(iter(fmap.values()))))
    lines, cur, cur_w = [], [], 0
    for item in words:
        w, st, tail = (item + ("",))[:3]
        f = fmap[st]
        ww = draw.textlength(w, font=f)
        tw = draw.textlength(tail, font=fmap["tail"]) if tail else 0
        ww_total = ww + tw
        add = ww_total + (space if cur else 0)
        if cur and cur_w + add > max_w:
            lines.append(cur)
            cur, cur_w = [], 0
            add = ww_total
        cur.append((w, st, f, ww, tail, fmap.get("tail"), tw))
        cur_w += add
    if cur:
        lines.append(cur)
    lh = base * (1.18 if art == "h" else 1.42)
    gap = base * (0.55 if art in ("h", "k") else 0.75)
    return lines, lh, gap, space


def card_box(W, H):
    tall = H / W >= 1.5
    cx0, cx1 = round(W * 0.075), round(W * 0.925)
    cy0, cy1 = round(H * (0.12 if tall else 0.085)), round(H * (0.80 if tall else 0.84))
    pad, footer_h = round(W * 0.075), round(W * 0.075)
    return cx0, cy0, cx1, cy1, pad, footer_h, cy0 + round(W * 0.07), cy1 - footer_h - round(W * 0.03)


def fit_scale(draw, fonts, slide, W, H, start):
    cx0, _, cx1, _, pad, _, top, bot = card_box(W, H)
    scale = start
    while True:
        laid = [(art, *layout_block(draw, fonts, art, t, scale, W, (cx1 - cx0) - 2 * pad)) for art, t in slide["blocks"]]
        total_h = sum(len(lines) * lh + gap for _, lines, lh, gap, _ in laid) - (laid[-1][3] if laid else 0)
        if total_h <= (bot - top) * 0.92 or scale < 0.55:
            return scale, laid, total_h
        scale *= 0.95


DESIGNS = ("glas", "ohne", "karte")
# Helle Schrift für „glas“ und „ohne“ (Creme wie in CapCut, #F5EFE6), dunkle für die alte deckende „karte“.
LIGHT = {"h": (245, 239, 230), "k": (226, 205, 178), "s": (214, 202, 188), "n": (240, 233, 222),
         "b": (250, 245, 238), "m": (47, 38, 32), "a": (226, 205, 178), "line": (214, 202, 188)}
DARK = {"h": PALETTE["head"], "k": PALETTE["accent"], "s": PALETTE["muted"], "n": PALETTE["text"],
        "b": PALETTE["head"], "m": PALETTE["head"], "a": PALETTE["accent"], "line": PALETTE["tape"]}


def draw_text(draw, laid, colors, y, W, marker=True, only_color=None):
    """Zeichnet die gesetzten Blöcke; only_color = alles einfarbig (für den Schatten)."""
    for art, lines, lh, gap, space in laid:
        for line in lines:
            lw = sum(it[3] + it[6] for it in line) + space * (len(line) - 1)
            x = (W - lw) / 2
            for i, (word, st, f, ww, tail, tf, tw) in enumerate(line):
                if st == "m" and marker and only_color is None:
                    nxt = i + 1 < len(line) and line[i + 1][1] == "m"
                    asc, desc = f.getmetrics()
                    draw.rounded_rectangle((x - 6, y + asc * 0.18, x + ww + (space if nxt else 0) + 6, y + asc + desc * 0.6),
                                           6, fill=PALETTE["marker"])
                fill = only_color or colors[st]
                if only_color is not None and st == "m":
                    fill = (0, 0, 0, 0)  # markiertes Wort steht auf dem Marker, braucht keinen Schatten
                draw.text((x, y), word, font=f, fill=fill)
                if tail:
                    draw.text((x + ww, y + f.getmetrics()[0] - tf.getmetrics()[0]), tail, font=tf,
                              fill=only_color or colors["n"])
                x += ww + tw + space
            y += lh
        y += gap


def render_slide(img, slide, total, fonts, Image, ImageDraw, ImageFilter, scale, design="glas"):
    """design: „glas“ = sehr transparente Milchglas-Karte, „ohne“ = Text direkt auf dem Foto,
    „karte“ = alte deckende Creme-Karte. Innerhalb eines Posts immer derselbe Look."""
    W, H = img.size
    img = img.convert("RGBA")
    cx0, cy0, cx1, cy1, pad, footer_h, avail_top, avail_bot = card_box(W, H)
    colors = DARK if design == "karte" else LIGHT

    if design == "karte":
        img = Image.alpha_composite(img, Image.new("RGBA", img.size, (30, 22, 16, 38)))
        shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle((cx0 + 6, cy0 + 10, cx1 + 6, cy1 + 10), 18, fill=(0, 0, 0, 90))
        img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(14)))
        card = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(card).rounded_rectangle((cx0, cy0, cx1, cy1), 18, fill=PALETTE["card"] + (246,))
        img = Image.alpha_composite(img, card)
    elif design == "glas":
        # Milchglas: Foto hinter der Karte weichzeichnen, nur leicht abdunkeln, feiner Creme-Rand
        mask = Image.new("L", img.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((cx0, cy0, cx1, cy1), 22, fill=255)
        blurred = img.filter(ImageFilter.GaussianBlur(18))
        img = Image.composite(blurred, img, mask)
        tint = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(tint)
        d.rounded_rectangle((cx0, cy0, cx1, cy1), 22, fill=(40, 30, 22, 70), outline=(245, 239, 230, 110), width=2)
        img = Image.alpha_composite(img, tint)
    else:  # ohne: weicher Verlauf nur hinter dem Text, keine Fläche
        veil = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(veil).ellipse((cx0 - W * 0.15, avail_top - H * 0.04, cx1 + W * 0.15, avail_bot + H * 0.04),
                                     fill=(25, 18, 12, 95))
        img = Image.alpha_composite(img, veil.filter(ImageFilter.GaussianBlur(W * 0.08)))

    if design == "karte":  # Klebestreifen nur bei der deckenden Karte
        tw, th = round(W * 0.22), round(W * 0.055)
        tape = Image.new("RGBA", (tw, th), PALETTE["tape"] + (190,))
        tape = tape.rotate(-5 if slide["nr"] % 2 else 5, expand=True, resample=Image.BICUBIC)
        tx = round(W * 0.16) if slide["nr"] % 2 else round(W * 0.84) - tape.width
        img.alpha_composite(tape, (tx, cy0 - th // 2))

    draw = ImageDraw.Draw(img)
    _, laid, total_h = fit_scale(draw, fonts, slide, W, H, scale)
    y = avail_top + (avail_bot - avail_top - total_h) / 2
    if design != "karte":  # weicher Schatten für Lesbarkeit auf dem Foto
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw_text(ImageDraw.Draw(sh), laid, colors, y + 2, W, only_color=(0, 0, 0, 150))
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(5)))
        draw = ImageDraw.Draw(img)
    draw_text(draw, laid, colors, y, W)

    # Fusszeile: Handle links, Seitenzahl + Wisch-Hinweis rechts
    fy = cy1 - footer_h
    draw.line((cx0 + pad, fy, cx1 - pad, fy), fill=colors["line"], width=2)
    small = fonts.get("text", W * 0.026)
    ty = fy + (footer_h - small.size) / 2 - 2
    draw.text((cx0 + pad, ty), HANDLE, font=small, fill=colors["s"])
    page = f"{slide['nr']}/{total}" + ("  →" if slide["nr"] < total else "")
    draw.text((cx1 - pad - draw.textlength(page, font=small), ty), page, font=small, fill=colors["s"])
    return img.convert("RGB")


def cover(img, size, Image, anchor_y=0.5):
    """Füllt das Format; anchor_y > 0.5 behält eher den unteren Bildteil (dort stehen die Objekte)."""
    W, H = size
    s = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    l, t = (img.width - W) // 2, round((img.height - H) * anchor_y)
    return img.crop((l, t, l + W, t + H))


def render_slides(images, slides, out_dir, size=(1080, 1350), design="glas"):
    """images: ein Pfad oder Liste; Slide n nutzt Bild ((n-1) mod Anzahl) – Abwechslung, gleicher Rahmen."""
    try:
        from PIL import Image, ImageDraw, ImageFilter, ImageFont
    except ImportError:
        raise SystemExit("Für --slides fehlt Pillow: python3 -m pip install -r requirements.txt")
    images = [images] if isinstance(images, (str, Path)) else list(images)
    if design not in DESIGNS:
        raise SystemExit(f"Unbekanntes Slide-Design {design!r} ({', '.join(DESIGNS)})")
    bases = [cover(Image.open(p).convert("RGB"), size, Image, 0.7) for p in images]
    fonts = Fonts(ImageFont)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("slide-*.png"):
        old.unlink()
    # Eine gemeinsame Schriftgrösse für alle Folgeslides (wirkt wie aus einem Guss); Slide 1 darf grösser sein.
    probe = ImageDraw.Draw(Image.new("RGB", size))
    W, H = size
    rest = [fit_scale(probe, fonts, s, W, H, 1.4)[0] for s in slides if s["nr"] != 1]
    common = min(rest) if rest else 1.0
    written = []
    for i, s in enumerate(slides):
        start = fit_scale(probe, fonts, s, W, H, 1.5)[0] if s["nr"] == 1 else common
        img = render_slide(bases[i % len(bases)].copy(), s, len(slides), fonts, Image, ImageDraw, ImageFilter, start,
                           design)
        p = out_dir / f"slide-{s['nr']}.png"
        img.save(p, optimize=True)
        written.append(p)
    return written, fonts.warnings


# ---------- Wochen-Pool ----------
def call_api(model, prompt, aspect, size, key):
    url, body, _ = build_request(model, prompt, aspect, 1)
    if size and model.startswith("gemini-3"):
        body["generationConfig"]["imageConfig"]["imageSize"] = size
    resp = post_json(url, body, key)
    imgs, notes = extract_images(resp)
    return imgs, notes, resp.get("usageMetadata")


def render_week(path, args, model):
    """Erzeugt die Fotos der Wochen-Datei (je 1 Bild, 9:16) nach medien/<KW>/fotos/ und trägt sie ein."""
    text = path.read_text(encoding="utf-8")
    ns = argparse.Namespace(history=str(ROOT / "data" / "prompt-history.jsonl"))
    R, kw, items = qa_check.run_week_checks(text, ns)
    if R.n_fail and not args.force and not args.dry_run:
        sys.exit("Wochen-QA nicht bestanden (qa_check.py --week) – erst prüfen, dann rendern (oder --force)")
    only = {x.strip() for x in args.only.split(",")} if args.only else None
    fotos = [it for it in items if it["art"] == "foto" and (not only or it["id"] in only)]
    out = ROOT / "medien" / kw / "fotos"
    alloc = {}
    wf = media.week_file(kw)
    if wf.exists():
        alloc = {f["id"]: f for f in json.loads(wf.read_text(encoding="utf-8"))["fotos"]}
    wished = {i for i, f in alloc.items() if (f.get("wunsch") or f.get("eigen")) and not only}
    for i in sorted(wished & {it["id"] for it in fotos}):
        print(f"übersprungen: {i} (Foto-Wunsch an Pamina; Ersatz später mit --only {i})")
    fotos = [it for it in fotos if it["id"] not in wished]
    todo = [it for it in fotos if args.redo or not list(out.glob(f"{it['datei']}.*"))]
    if not todo:
        print(f"Alle {len(fotos)} Fotos von {kw} sind schon da (--redo erzeugt sie neu).")
    if args.dry_run:
        for it in todo:
            prompt, aspect = mj_to_api(it["prompt"])
            url, body, _ = build_request(model, prompt, aspect, 1)
            print(f"POST {url}  → {out / it['datei']}.jpg")
            print(json.dumps(body, ensure_ascii=False, indent=2))
        return
    key = api_key()
    if todo and not key:
        sys.exit("Kein API-Schlüssel: GEMINI_API_KEY in .env eintragen (siehe .env.example)")
    out.mkdir(parents=True, exist_ok=True)
    log_path = ROOT / "medien" / kw / "render-log.json"
    log = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else []
    errors = []
    for it in todo:
        prompt, aspect = mj_to_api(it["prompt"])
        try:
            imgs, notes, usage = call_api(model, prompt, aspect, args.size, key)
        except SystemExit as e:  # einzelner Fehler stoppt nicht die ganze Woche
            errors.append(f"{it['id']}: {e}")
            continue
        if not imgs:
            errors.append(f"{it['id']}: kein Bild ({'; '.join(notes) or 'ohne Begründung'})")
            continue
        for old in out.glob(f"{it['datei']}.*"):
            old.unlink()
        f = out / f"{it['datei']}{image_ext(imgs[0])}"
        f.write_bytes(imgs[0])
        media.register_photo(it["id"], f, {
            "kw": kw, "tag": it["tag"], "zweck": alloc.get(it["id"], {}).get("zweck", it["slots"]),
            "ort": it["ort"], "licht": it["vars"].get("Licht/Tageszeit"), "requisit": it["vars"].get("Requisit"),
            "stoff": it["vars"].get("Stoff-Farbe"), "motiv": it["motiv"]})
        log.append({"id": it["id"], "model": model, "aspect": aspect, "size": args.size, "usage": usage})
        print(f"Foto gespeichert: {f.relative_to(ROOT)}")
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    done = len(todo) - len(errors)
    print(f"{done} neue Fotos (Richtwert ca. {done * 0.14:.2f} $ bei gemini-pro 2K). Log: {log_path.relative_to(ROOT)}")
    for e in errors:
        print(f"FEHLER {e}")
    if errors:
        sys.exit(1)


def pool_bases(clean):
    """Pool-IDs aus Agent 6 (- **Pool:** …) → Bildpfade (Fotos), Videos werden übersprungen."""
    ids = [x.strip() for x in re.split(r"[,;]", qa_check.field(clean.get("6", ""), "Pool") or "") if x.strip()]
    recs = {r["id"]: r for r in media.read_list()}
    paths, fotos = [], []
    for i in ids:
        if re.search(r"-T\d\d-R[12]$", i):
            continue
        r = recs.get(i)
        pth = media.photo_path(r) if r else None
        if not pth:
            sys.exit(f"Pool-Foto {i} ist nicht in medien/bildliste.jsonl oder die Datei fehlt")
        paths.append(pth)
        fotos.append(i)
    return paths, fotos


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
    ap.add_argument("--count", type=int, default=3)
    ap.add_argument("--size", default="2K", help="Bildgrösse bei Gemini 3 (1K | 2K | 4K)")
    ap.add_argument("--aspect")
    ap.add_argument("--slides", action="store_true")
    ap.add_argument("--base")
    ap.add_argument("--no-images", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--week", action="store_true", help="Wochen-Datei: alle Fotos der Woche erzeugen")
    ap.add_argument("--only", help="mit --week: nur diese IDs (kommagetrennt)")
    ap.add_argument("--redo", action="store_true", help="mit --week: vorhandene Fotos neu erzeugen")
    ap.add_argument("--pool", action="store_true", help="Slides aus den Pool-Fotos (Agent 6: - **Pool:** …)")
    ap.add_argument("--design", choices=DESIGNS, help="Slide-Look (Standard: aus dem Plan-Tag)")
    args = ap.parse_args()

    if args.list_models:
        list_models()
        return
    if not args.file:
        sys.exit("Bitte die Post-Datei angeben, z. B. output/T03-K.md")
    path = Path(args.file)
    if not path.exists():
        sys.exit(f"Datei nicht gefunden: {path}")
    model = MODELS.get(args.model, args.model)
    if args.week:
        render_week(path, args, model)
        return
    if args.pool:
        args.no_images = args.slides = True
    if not args.force and not args.dry_run and not qa_passed(path):
        sys.exit("QA nicht bestanden (qa_check.py --final) – erst prüfen, dann rendern (oder --force)")
    _, clean = load_post(path)
    out_dir = Path(args.out) if args.out else path.parent / path.stem
    if not 1 <= args.count <= 4:
        sys.exit("--count muss zwischen 1 und 4 liegen")

    fmt = post_format(clean)
    if not args.no_images:
        prompt, mj_aspect = image_prompt(clean)
        aspect = args.aspect or FORMAT_ASPECT.get(fmt, mj_aspect)
        family = "imagen" if model.startswith("imagen") else "gemini"
        if aspect not in ASPECTS[family]:
            sys.exit(f"Seitenverhältnis {aspect} kann {model} nicht ({', '.join(sorted(ASPECTS[family]))})")
        if len(prompt.split()) > 330:
            print(f"WARN Prompt hat {len(prompt.split())} Wörter – Imagen kürzt sehr lange Prompts")
        requests = []
        for vp in variant_prompts(prompt, args.count):
            url, body, _ = build_request(model, vp, aspect, 1)
            if args.size and model.startswith("gemini-3"):
                body["generationConfig"]["imageConfig"]["imageSize"] = args.size
            requests.append((url, body))
        calls = len(requests)
        if args.dry_run:
            for url, body in requests:
                print(f"POST {url}")
                print(json.dumps(body, ensure_ascii=False, indent=2))
            return
        key = api_key()
        if not key:
            sys.exit("Kein API-Schlüssel: GEMINI_API_KEY in .env eintragen (siehe .env.example)")
        images, notes, usage = [], [], []
        for url, body in requests:
            resp = post_json(url, body, key)
            imgs, n = extract_images(resp)
            images += imgs
            notes += n
            if resp.get("usageMetadata"):
                usage.append(resp["usageMetadata"])
        if not images:
            sys.exit("Die API hat kein Bild geliefert" + (f" ({'; '.join(notes)})" if notes else ""))
        out_dir.mkdir(parents=True, exist_ok=True)
        for old in out_dir.glob("bild-*.*"):
            old.unlink()
        for i, data in enumerate(images, 1):
            p = out_dir / f"bild-{i}{image_ext(data)}"
            p.write_bytes(data)
            print(f"Bild gespeichert: {p}")
        for n in notes:
            print(f"WARN Bild gefiltert: {n}")
        log = {"model": model, "aspect": aspect, "size": args.size, "calls": calls, "images": len(images), "usage": usage}
        (out_dir / "render-log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
        if usage:
            tot = lambda k: sum(u.get(k, 0) for u in usage)  # noqa: E731
            print(f"Verbrauch: {tot('promptTokenCount')} Eingabe-Tokens, "
                  f"{tot('candidatesTokenCount')} Ausgabe-Tokens (Details: {out_dir / 'render-log.json'})")

    if args.slides:
        slides = parse_slides(clean)
        if not slides:
            sys.exit("Keine Slides/Einblendungen in Agent 2 & 3 gefunden")
        pool_ids = []
        if args.base:
            bases = [Path(b) for b in args.base.split(",")]
        elif args.pool:
            bases, pool_ids = pool_bases(clean)
        else:
            bases = sorted(p for p in out_dir.glob("bild-*.*") if p.suffix in (".png", ".jpg", ".webp"))
        if not bases or not all(b.exists() for b in bases):
            sys.exit(f"Basisbild fehlt in {out_dir} (erst Bilder erzeugen oder --base angeben)")
        size = SLIDE_SIZE.get(args.aspect or FORMAT_ASPECT.get(fmt, "9:16"), (1080, 1350))
        m = re.match(r"T(\d\d)-", path.stem)
        design = args.design or (plan.slide_design(int(m.group(1))) if m else "glas")
        written, warnings = render_slides(bases, slides, out_dir / "slides", size, design)
        print(f"Slide-Design: {design}")
        if pool_ids and m:
            media.cmd_use(path.stem, pool_ids, args.force)
        for w in warnings:
            print(f"WARN {w}")
        for p in written:
            print(f"Slide gespeichert: {p}")


if __name__ == "__main__":
    main()
