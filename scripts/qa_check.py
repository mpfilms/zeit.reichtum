#!/usr/bin/env python3
"""Deterministische Qualitätsprüfung für @zeit.reichtum-Posts (Hilfsskript für Agent 10).

  qa_check.py output/T05-R1.md [--final] [--checklist] [--log] [--history PFAD] [--slug NAME] [--names PFAD]
  qa_check.py output/woche-2026-KW47.md --week [--log]   Wochen-Prompts (9 Fotos, 12 Videos) prüfen

--final      verlangt zusätzlich den Abschnitt "Agent 10" (fertige Checkliste)
--checklist  gibt die Checkliste (✅/⚠️/❌) als Markdown aus
--log        schreibt bei bestandener Prüfung Motiv, Audio und Variablen in die Historie
Exit-Code 1, sobald mindestens ein FAIL vorliegt. WARN = von Menschen/Agent 10 zu beurteilen.
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

HEADER = "Werbung 🤍 | Folge mir, wenn du dir als Mama etwas Eigenes aufbauen möchtest."
IMG_FORMULA = (
    "Slightly underexposed by 10-15%, subtle dark cinematic color grading, muted and dimmed natural "
    "lighting, soft natural vignette, optimized for white text overlay. The earthy tones remain warm "
    "but slightly deepened for a premium look."
)
VID_FORMULA = (
    "Subtle 15% dark color grading, slightly dimmed lighting for clear text overlay, cinematic low-key "
    "warmth, maintaining high contrast for white text. Static camera, seamless loop."
)
PARAMS = "--ar 9:16 --style raw --v 6.1"
ORDER = ["1", "2&3", "4", "5", "6", "7", "8", "9", "10", "11"]
VAR_NAMES = ["Licht/Tageszeit", "Requisit", "Stoff-Farbe", "Kamera/Bewegung"]
VAR_KEYS = ["licht", "requisit", "stoff", "kamera"]
ABBREV = ["z. B.", "z.B.", "d. h.", "u. a.", "ggf.", "bzw.", "ca.", "usw.", "etc.", "vs."]


# ---------- Helfer ----------
def strip_comments(t):
    return re.sub(r"<!--.*?-->", "", t, flags=re.S)


def lines_of(path):
    if not path.exists():
        return []
    return [l.strip() for l in path.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.lstrip().startswith("#")]


def split_sections(text):
    ms = list(re.finditer(r"(?m)^## Agent ([0-9][0-9 &]*?) ·[^\n]*$", text))
    secs, order = {}, []
    for i, m in enumerate(ms):
        key = m.group(1).replace(" ", "")
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        secs[key] = re.sub(r"(?m)^---\s*$", "", text[m.end():end])
        order.append(key)
    return secs, order


def field(body, name):
    m = re.search(r"\*\*" + re.escape(name) + r":\*\*[ \t]*(.+)", body or "")
    return m.group(1).strip() if m else None


def sentences(t):
    t = re.sub(r"\s+", " ", t.strip())
    for a in ABBREV:
        t = t.replace(a, a.replace(".", "").replace(" ", ""))
    t = re.sub(r"[„“”\"*_]", "", t)
    return [p for p in re.split(r"(?<=[.!?…])\s+", t) if re.search(r"\w", p)]


def norm(s):
    return re.sub(r"\W+", " ", s.lower()).strip()


class Report:
    def __init__(self):
        self.groups = []

    def group(self, label):
        g = {"label": label, "items": []}
        self.groups.append(g)
        return g

    @staticmethod
    def fail(g, msg):
        g["items"].append(("FAIL", msg))

    @staticmethod
    def warn(g, msg):
        g["items"].append(("WARN", msg))

    def status(self, g):
        lv = {i[0] for i in g["items"]}
        return "❌" if "FAIL" in lv else "⚠️" if "WARN" in lv else "✅"

    @property
    def n_fail(self):
        return sum(1 for g in self.groups for i in g["items"] if i[0] == "FAIL")

    @property
    def n_warn(self):
        return sum(1 for g in self.groups for i in g["items"] if i[0] == "WARN")


def read_history(path):
    out = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return out


def parse_vars(sec6):
    found = dict(re.findall(
        r"(?m)^\s*\d\.\s*\*\*(Licht/Tageszeit|Requisit|Stoff-Farbe|Kamera/Bewegung):\*\*[ \t]*(.+?)[ \t]*$",
        sec6 or ""))
    return found


def check_image_prompt(R, g, p, label=""):
    p = p.strip()
    if p.count(IMG_FORMULA) != 1:
        R.fail(g, f"{label}Bild-Formel nicht (genau einmal) wörtlich im Midjourney-Prompt")
    else:
        tail = p.split(IMG_FORMULA, 1)[1].strip()
        if tail != PARAMS:
            R.fail(g, f"{label}Nach der Bild-Formel müssen direkt die Parameter '{PARAMS}' folgen (gefunden: {tail!r})")
    bad = people_words(p)
    if bad:
        R.fail(g, f"{label}Midjourney-Prompt erwähnt Menschen/Körperteile: {bad}")
    if "negative space" not in p.lower():
        R.fail(g, f"{label}Midjourney-Prompt verlangt keinen 'negative space' für den Text")


def check_video_prompt(R, g, b, label=""):
    if not b.strip().endswith(VID_FORMULA):
        R.fail(g, f"{label}Motion-Prompt endet nicht wörtlich mit der Video-Formel")
    if re.search(r"camera (move|pan|zoom|dolly|tilt)", b.lower()):
        R.fail(g, f"{label}Motion-Prompt bewegt die Kamera (Kamera muss statisch bleiben)")


def people_words(p):
    pre = re.sub(r"\b(no|without|zero)\s+(people|persons?|humans?|figures?)\b", "", p.lower())
    pre = pre.replace(IMG_FORMULA.lower(), "").replace(VID_FORMULA.lower(), "")
    return sorted(set(re.findall(
        r"\b(people|person|woman|women|man|men|child|children|girl|boy|baby|mother|mom|face|faces|hands?)\b", pre)))


# ---------- Wochen-Datei (Medien-Pool) ----------
WEEK_HEAD = re.compile(r"(?m)^### +(\S+) · (Foto|Video) · Tag (\d+)(?: · (.*))?$")


def parse_week(text):
    """→ (kw, items); item = dict(id, art, tag, slots, vars, ort, motiv, datei, prompt)."""
    text = strip_comments(text)
    m = re.search(r"(?m)^# Wochen-Medien (\d{4}-KW\d\d)", text)
    kw = m.group(1) if m else None
    heads = list(WEEK_HEAD.finditer(text))
    items = []
    for i, h in enumerate(heads):
        body = text[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        body = body.split("\n## ", 1)[0]
        codes = re.findall(r"```[^\n]*\n(.*?)```", body, re.S)
        items.append({
            "id": h.group(1), "art": h.group(2).lower(), "tag": int(h.group(3)),
            "slots": [s.strip() for s in (h.group(4) or "").split("+") if s.strip()],
            "vars": parse_vars(body), "ort": field(body, "Ort/Szene"), "motiv": field(body, "Motiv"),
            "datei": (field(body, "Dateiname") or "").strip().strip("`"),
            "prompt": codes[0].strip() if len(codes) == 1 else None, "n_codes": len(codes),
        })
    return kw, items


def run_week_checks(text, args):
    R = Report()
    kw, items = parse_week(text)
    g = R.group("Wochen-Datei vollständig (KW, alle Fotos und Videos der Zuteilung)")
    if not kw:
        R.fail(g, "Titelzeile '# Wochen-Medien 2026-KWxx …' fehlt")
    alloc = ROOT / "medien" / (kw or "-") / "woche.json"
    if alloc.exists():
        w = json.loads(alloc.read_text(encoding="utf-8"))
        want = [f["id"] for f in w["fotos"]] + [v["id"] for v in w["videos"]]
        have = [it["id"] for it in items]
        for i in want:
            if i not in have:
                R.fail(g, f"{i} fehlt")
        for i in have:
            if i not in want:
                R.fail(g, f"{i} gehört nicht zur Zuteilung von {kw}")
    else:
        R.warn(g, f"Keine Zuteilung medien/{kw}/woche.json gefunden (media.py init)")
    if len({it["id"] for it in items}) != len(items):
        R.fail(g, "Doppelte IDs")

    g = R.group("Je Foto/Video: Variablen, Ort, Dateiname und genau ein Prompt mit wörtlicher Formel")
    for it in items:
        lab = f"{it['id']}: "
        miss = [n for n in VAR_NAMES if n not in it["vars"]]
        if miss:
            R.fail(g, f"{lab}Variablen fehlen: {miss}")
        if not it["ort"]:
            R.fail(g, f"{lab}'- **Ort/Szene:**' fehlt")
        if it["n_codes"] != 1:
            R.fail(g, f"{lab}genau ein Prompt-Codeblock erwartet (gefunden: {it['n_codes']})")
            continue
        if it["art"] == "foto":
            if not re.fullmatch(re.escape(it["id"]) + r"_[a-z0-9-]+", it["datei"]):
                R.fail(g, f"{lab}Dateiname muss '{it['id']}_ort-licht-farbe' sein (gefunden: {it['datei']!r})")
            check_image_prompt(R, g, it["prompt"], lab)
        else:
            slot = it["id"].rsplit("-", 2)
            if it["datei"] != f"{slot[-2]}-{slot[-1]}":
                R.fail(g, f"{lab}Dateiname muss der Slot sein ({slot[-2]}-{slot[-1]}), gefunden: {it['datei']!r}")
            if "--ar" in it["prompt"]:
                R.fail(g, f"{lab}Video-Prompt enthält Midjourney-Parameter")
            check_video_prompt(R, g, it["prompt"], lab)
            if people_words(it["prompt"]):
                R.fail(g, f"{lab}Video-Prompt erwähnt Menschen/Körperteile: {people_words(it['prompt'])}")
            if len(it["prompt"].split()) < len(VID_FORMULA.split()) + 25:
                R.warn(g, f"{lab}Video-Prompt beschreibt die Szene kaum (Text-to-Video braucht Ort, Licht, Requisit, Bewegung)")

    g = R.group("Abwechslung: Karussell-Fotos klar verschieden, keine Wiederholung in der Woche und zur Historie")
    fotos = [it for it in items if it["art"] == "foto"]
    by_day = {}
    for it in fotos:
        by_day.setdefault(it["tag"], []).append(it)
    for day, pair in by_day.items():
        if len(pair) == 2:
            a, b = pair
            for what, x, y in (("Ort/Szene", a["ort"], b["ort"]),
                               ("Stoff-Farbe", a["vars"].get("Stoff-Farbe"), b["vars"].get("Stoff-Farbe")),
                               ("Requisit", a["vars"].get("Requisit"), b["vars"].get("Requisit"))):
                if x and y and norm(x) == norm(y):
                    R.fail(g, f"Karussell Tag {day}: {a['id']} und {b['id']} haben dieselbe {what} ({x!r})")
    seen = {}
    for it in items:
        for key, name in zip(VAR_KEYS[:3], VAR_NAMES[:3]):
            v = it["vars"].get(name)
            if v:
                k = (name, norm(v))
                if k in seen:
                    R.fail(g, f"{name} doppelt in der Woche: {seen[k]} und {it['id']} ({v!r})")
                seen.setdefault(k, it["id"])
    orte = {}
    for it in fotos:
        if it["ort"]:
            orte.setdefault(norm(it["ort"]), []).append(it["id"])
    for o, ids in orte.items():
        if len(ids) > 1:
            R.warn(g, f"Gleicher Ort bei {', '.join(ids)} – lieber verschiedene Orte")
    ids = {it["id"] for it in items}
    for rec in read_history(Path(args.history)):
        if rec.get("slug") in ids:
            continue
        for it in items:
            for key, name in zip(VAR_KEYS[:3], VAR_NAMES[:3]):
                v = it["vars"].get(name)
                if v and rec.get(key) and norm(rec[key]) == norm(v):
                    R.fail(g, f"{it['id']}: {name} wiederholt {rec.get('slug')} ({v!r})")
    return R, kw, items


def log_week(path, items):
    ids = {it["id"] for it in items}
    old = [r for r in read_history(path) if r.get("slug") not in ids]
    today = datetime.date.today().isoformat()
    for it in items:
        rec = {"date": today, "slug": it["id"], "art": it["art"], "motiv": it["motiv"], "ort": it["ort"]}
        rec.update({k: it["vars"].get(n) for k, n in zip(VAR_KEYS, VAR_NAMES)})
        old.append(rec)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in old), encoding="utf-8")


# ---------- Prüfungen ----------
def run_checks(text, args, slug):
    R = Report()
    secs, order = split_sections(text)
    clean = {k: strip_comments(v) for k, v in secs.items()}
    s1 = clean.get("1", "")
    fmt_raw = (field(s1, "Format") or "").lower()
    fmt = "story" if fmt_raw.startswith("story") else fmt_raw
    typ = (field(s1, "Typ") or "").strip()
    ausr = (field(s1, "Ausrichtung") or "").strip().lower()
    sunday = (field(s1, "Sunday Mode") or "").lower().startswith("ja")
    pitch = ausr == "pitch"

    # 1 Aufbau
    g = R.group("Aufbau, Reihenfolge und Festlegungen (Format, Typ, Ausrichtung) korrekt")
    if fmt not in ("reel", "karussell", "story"):
        R.fail(g, f"Agent 1: 'Format' muss Reel, Karussell oder Story-Sequenz sein (gefunden: {fmt_raw!r})")
    if typ not in ("Leuchtturm", "Spiegel"):
        R.fail(g, f"Agent 1: 'Typ' muss Leuchtturm oder Spiegel sein (gefunden: {typ!r})")
    if ausr not in ("pitch", "nurture"):
        R.fail(g, f"Agent 1: 'Ausrichtung' muss Pitch oder Nurture sein (gefunden: {ausr!r})")
    required = ["1", "2&3", "4", "5", "6", "7", "8", "9"] + (["11"] if pitch else []) + (["10"] if args.final else [])
    for k in required:
        if k not in secs:
            R.fail(g, f"Abschnitt 'Agent {k}' fehlt")
    if not pitch and "11" in secs:
        R.fail(g, "Nurture-Post enthält Agent 11 (Manychat) – bei Nurture darf es keinen Flow geben")
    idx = [ORDER.index(k) for k in order if k in ORDER]
    if idx != sorted(idx) or len(set(order)) != len(order):
        R.fail(g, f"Reihenfolge/Duplikate falsch: {order} (erwartet 1, 2 & 3, 4 … 10, 11)")
    for k in order:
        if k not in ORDER:
            R.fail(g, f"Unbekannter Abschnitt 'Agent {k}'")
    for k in ("2&3", "4", "5", "6", "7", "8", "9", "11"):
        if k in secs and len(clean[k].strip()) < 20:
            R.fail(g, f"Abschnitt 'Agent {k}' ist praktisch leer")
    left = re.findall(r"<(?!!--)[A-Za-zÄÖÜäöü][^>\n]{2,}>", "\n".join(v for k, v in clean.items() if k != "10"))
    if left:
        R.fail(g, f"Unausgefüllte Platzhalter im Text: {left[:3]}")
    if re.search(r"RÜCKFRAGE:", "\n".join(v for k, v in clean.items() if k != "10")):
        R.fail(g, "Offene RÜCKFRAGE im Post – erst Pamina fragen")

    content = "\n".join(v for k, v in clean.items() if k != "10")
    low = content.lower()

    # 2 Blacklist
    g = R.group("Keine Blacklist-Wörter")
    for w in lines_of(ROOT / "data" / "blacklist.txt"):
        if w.lower() in low:
            ctx = low[max(0, low.index(w.lower()) - 25): low.index(w.lower()) + len(w) + 25].replace("\n", " ")
            R.fail(g, f"Blacklist-Wort '{w}' gefunden: …{ctx}…")
    if "magic words" in low:
        R.warn(g, "Der interne Begriff 'Magic Words' steht im Post-Text (gehört nicht in den Content)")

    # Schweizer Schreibweise
    g = R.group("Schweizer Schreibweise: „ss“ statt „ß“")
    for m in list(re.finditer(r"\S*ß\S*", content))[:5]:
        R.fail(g, f"„ß“ gefunden: {m.group(0)!r} → {m.group(0).replace('ß', 'ss')!r}")

    # 3 Namen
    g = R.group("Kein Name des Erstellers, kein Kursname")
    names = lines_of(Path(args.names))
    if not names:
        R.warn(g, "data/forbidden-names.txt ist leer – Ersteller-/Kursname kann nicht geprüft werden")
    for n in names:
        if n.lower() in low:
            R.fail(g, f"Verbotener Name '{n}' im Post")
    if re.search(r"\bworkshop\b", low):
        R.warn(g, "Wort 'Workshop' gefunden – stattdessen 'kostenloses Info-Video' schreiben")

    # Caption
    s7 = clean.get("7", "")
    cm = re.search(r"\*\*Caption:\*\*\s*(.*)", s7, re.S)
    caption = cm.group(1).strip() if cm else ""
    cap_lines = [l.strip() for l in caption.splitlines() if l.strip()]

    g = R.group("Kopfzeile exakt vorhanden (erste Zeile der Caption)")
    if not cm:
        R.fail(g, "Agent 7: Marker '**Caption:**' fehlt")
    elif not cap_lines or cap_lines[0] != HEADER:
        R.fail(g, f"Erste Caption-Zeile ist nicht exakt die Pflicht-Kopfzeile: {cap_lines[:1]}")

    g = R.group("Kein Hashtag-Block, höchstens 2 Hashtags direkt im Satz")
    tags = re.findall(r"#\w+", caption)
    if len(tags) > 2:
        R.fail(g, f"{len(tags)} Hashtags (max. 2): {tags}")
    for l in cap_lines:
        toks = l.split()
        if toks and all(t.startswith("#") for t in toks):
            R.fail(g, f"Hashtag-Block/-Zeile: {l!r}")
    if cap_lines and re.search(r"#\w+\s*$", cap_lines[-1]):
        R.fail(g, "Caption endet mit einem Hashtag (Hashtags gehören mitten in den Satz)")

    # Hook & Struktur
    s23 = clean.get("2&3", "")
    g = R.group("Hook max. 2 Sätze, Struktur passt zum Format")
    hm = re.search(r"\*\*(?:Einblendung|Slide) 1[^*\n]*\*\*[ \t]*\n?(.+?)(?=\n\s*\n|\n\*\*|\Z)", s23, re.S)
    if not hm:
        R.fail(g, "Hook (Einblendung 1 / Slide 1) nicht gefunden")
    else:
        n = len(sentences(hm.group(1)))
        if n > 2:
            R.fail(g, f"Hook hat {n} Sätze (max. 2)")
    n_ein = len(re.findall(r"\*\*Einblendung \d", s23))
    n_sl = len(re.findall(r"\*\*Slide \d", s23))
    if fmt == "reel":
        if not 2 <= n_ein <= 3:
            R.fail(g, f"Reel braucht 2-3 Einblendungen (gefunden: {n_ein})")
        lm = list(re.finditer(r"\*\*Einblendung \d[^\n]*\n(.+?)(?=\n\s*\n|\Z)", s23, re.S))
        if lm and "caption" not in lm[-1].group(1).lower():
            R.fail(g, "Letzte Einblendung verweist nicht auf die Caption")
    elif fmt == "karussell":
        if not 4 <= n_sl <= 8:
            R.fail(g, f"Karussell braucht 4-8 Slides (gefunden: {n_sl})")
    elif fmt == "story":
        if n_sl != 3:
            R.fail(g, f"Story-Sequenz braucht genau 3 Slides (gefunden: {n_sl})")

    g = R.group("Zitat mit Quelle zugeordnet und als sinngemäss markiert" if typ == "Leuchtturm"
                else "Spiegel-Hook ohne Zitat, mit Trigger")
    if typ == "Leuchtturm":
        if not (field(s23, "Quelle") or field(s23, "Zitat")):
            R.fail(g, "Leuchtturm ohne Quellenangabe (**Quelle:** / **Zitat:**)")
        if "sinngemäss" not in s23.lower():
            R.fail(g, "Übersetzung nicht als 'sinngemäss' markiert")
    elif typ == "Spiegel":
        if field(s23, "Quelle"):
            R.warn(g, "Spiegel enthält eine Quellenzeile – im Spiegel keine bekannten Zitate")
        if not field(s23, "Trigger"):
            R.warn(g, "Spiegel ohne '**Trigger:**'-Zeile (Paradoxon/Validierung/Umdeutung)")

    # Pitch / Nurture
    kw = re.findall(r'[„"“]([A-ZÄÖÜ]{3,})[“"”]', caption)
    story_kw = re.findall(r"Antworte mit\s+[„\"“]?([A-ZÄÖÜ]{3,})", s23)
    if pitch:
        g = R.group("Pitch korrekt: genau ein Keyword, CTA vorhanden, Manychat-Flow vorhanden")
        if fmt == "story":
            if len(story_kw) != 1:
                R.fail(g, f"Story-Pitch: Slide 3 braucht genau einen 'Antworte mit …'-CTA (gefunden: {story_kw})")
        else:
            if len(kw) != 1:
                R.fail(g, f"Pitch braucht genau ein Keyword in Anführungszeichen (gefunden: {kw})")
            elif kw[0] != "START":
                R.warn(g, f"Keyword ist '{kw[0]}' statt Standard 'START' (nur auf Wunsch)")
            if "kommentiere" not in caption.lower():
                R.fail(g, "CTA 'Kommentiere „START“ …' fehlt")
        if "11" not in secs:
            R.fail(g, "Agent 11 fehlt")
    else:
        g = R.group("Nurture korrekt: kein Pitch/Keyword/Manychat, Community-Frage am Ende")
        if kw or story_kw:
            R.fail(g, f"Nurture enthält ein Keyword: {kw or story_kw}")
        if "kommentiere" in caption.lower():
            R.fail(g, "Nurture enthält einen Kommentiere-CTA")
        if re.search(r"info-video|affiliate|automatisierte(s|n)? system", caption, re.I):
            R.fail(g, "Nurture-Caption enthält Pitch-Sprache (Info-Video/System/Affiliate)")
        if fmt != "story" and not re.search(r"\?[^\w]*$", caption.rstrip()):
            R.fail(g, "Nurture-Caption endet nicht mit einer Community-Frage (…?)")

    # Caption-Variante
    g = R.group("Caption-Variante und Länge stimmen")
    variant = (field(s7, "Variante") or "").strip().lower().lstrip("(")[:7]
    body = [l for l in cap_lines[1:]] if cap_lines else []
    body_text = " ".join(body)
    if fmt == "story":
        if variant and not variant.startswith("story"):
            R.warn(g, f"Story-Sequenz mit Variante '{variant}'")
    elif not variant:
        R.fail(g, "Agent 7: '- **Variante:**' fehlt (a | b | nurture)")
    elif pitch and variant[0] not in "ab":
        R.fail(g, f"Pitch braucht Variante a oder b (gefunden: {variant!r})")
    elif not pitch and not variant.startswith("nurture"):
        R.fail(g, f"Nurture braucht Variante 'nurture' (gefunden: {variant!r})")
    if fmt != "story" and cap_lines:
        ns = len(sentences(body_text))
        if sunday and ns > 2:
            R.fail(g, f"Sunday Mode: Caption darf nur 1-2 sehr kurze Sätze haben (gefunden: {ns})")
        elif pitch and variant.startswith("a") and not sunday:
            if ns != 4:
                R.fail(g, f"Variante a = 4-Sätze-Caption, gefunden: {ns} Sätze")
            elif "kommentiere" not in sentences(body_text)[3].lower():
                R.fail(g, "Variante a: der CTA muss der 4. Satz sein")
        elif pitch and variant.startswith("b") and not sunday:
            nb = sum(1 for l in body if l.startswith("✨"))
            if nb != 4:
                R.fail(g, f"Variante b = Vorteilsliste mit genau 4 ✨-Zeilen (gefunden: {nb})")

    # Formeln
    s6 = clean.get("6", "")
    blocks = re.findall(r"```[^\n]*\n(.*?)```", s6, re.S)
    mj = [b for b in blocks if "--ar" in b]
    motion = [b for b in blocks if "--ar" not in b]
    pool = [x.strip() for x in re.split(r"[,;]", field(s6, "Pool") or "") if x.strip()]
    g = R.group("Abdunkelungs-Formeln wörtlich, Bild-Formel vor den Parametern, Video-Formel am Ende")
    if not mj and not (pool and fmt in ("reel", "story")):
        R.fail(g, "Midjourney-Prompt (Codeblock mit --ar) fehlt")
    for p in mj:
        check_image_prompt(R, g, p)
    if fmt == "reel" and not motion:
        R.fail(g, "Motion-Prompt (Luma/Runway) fehlt")
    for b in motion[:1] if not pool else motion:
        check_video_prompt(R, g, b)

    if pool:
        # Medien aus dem Wochen-Pool: Prompts sind schon in der Wochen-Datei geprüft und geloggt
        g = R.group("Wochen-Pool: Medien-IDs angegeben, Karussell mit zwei verschiedenen Fotos")
        vars_ = {}
        if fmt == "karussell" and (len(set(pool)) < 2 or len(mj) < 2):
            R.fail(g, f"Karussell braucht zwei verschiedene Pool-Fotos mit je eigenem Prompt (Pool: {pool}, Prompts: {len(mj)})")
        if fmt == "story" and not [i for i in pool if not re.search(r"-T\d\d-R[12]$", i)]:
            R.fail(g, f"Story braucht mindestens ein Foto aus dem Pool (gefunden: {pool})")
        if fmt == "reel" and not any(re.search(r"-T\d\d-R[12]$", i) for i in pool):
            R.fail(g, f"Reel braucht die Video-ID aus dem Pool (z. B. 2026-KW47-T01-R1), gefunden: {pool}")
    else:
        # Variablen
        g = R.group("Agent-6-Variablen vorab auf Deutsch, vollständig und neu gegenüber der Historie")
        vars_ = parse_vars(s6)
        missing = [n for n in VAR_NAMES if n not in vars_]
        if missing:
            R.fail(g, f"Variablen fehlen: {missing}")
        first_code = s6.find("```")
        var_pos = s6.find("**Licht/Tageszeit:**")
        if var_pos == -1 or (first_code != -1 and var_pos > first_code):
            R.fail(g, "Die Variablen müssen VOR dem englischen Prompt stehen")
        if not re.search(r"(?m)^\|.*\|\s*$", s6) or s6.count("\n|") < 3:
            R.fail(g, "Vergleichstabelle zu den bisherigen Prompts fehlt")
        for n in VAR_NAMES:
            if re.search(r"\b(the|with|and|of)\b", vars_.get(n, "").lower()):
                R.warn(g, f"'{n}' wirkt englisch – Variablen stehen auf Deutsch")
        for rec in read_history(Path(args.history)):
            if rec.get("slug") == slug:
                continue
            for key, name in zip(VAR_KEYS, VAR_NAMES):
                if name in vars_ and rec.get(key) and norm(rec[key]) == norm(vars_[name]):
                    R.fail(g, f"{name} wiederholt einen früheren Post ({rec.get('slug')}): {vars_[name]!r}")

    # CapCut
    s9 = clean.get("9", "")
    g = R.group("CapCut-Vorgaben vollständig (Schrift, Farbe, Fade, Sicherheitsrand, keine Abdunkelung)")
    for token in ["Playfair Display Bold", "#F5EFE6", "Montserrat Italic", "0,5 s", "60 %"]:
        if token not in s9:
            R.fail(g, f"Agent 9: '{token}' fehlt")
    if "keine zusätzliche abdunkelung" not in s9.lower():
        R.fail(g, "Agent 9: Hinweis 'keine zusätzliche Abdunkelung in CapCut' fehlt")

    # Manychat
    s11 = clean.get("11", "")
    if pitch:
        g = R.group("Manychat-Flow vollständig (Transparenz, Affiliate-Hinweis, Buttons, Signatur)")
        need = {
            "{{Vorname}}": "Begrüssung mit {{Vorname}}",
            "automatisch": "Hinweis, dass die Nachricht automatisch ist",
            "Affiliate-Link, ich erhalte ggf. eine Provision. Für dich bleibt es kostenlos.": "Affiliate-Hinweis (wörtlich)",
            "Ich war anfangs selbst total planlos.": "Pflichtsatz 'Ich war anfangs selbst total planlos.'",
            "Auf deine innere Ruhe.": "Abschluss 'Auf deine innere Ruhe.'",
            "Deine Pamina 🤍": "Signatur 'Deine Pamina 🤍'",
            "Nachricht 1": "Block 'Nachricht 1'",
            "Nachricht 2": "Block 'Nachricht 2'",
        }
        for k, v in need.items():
            if k not in s11:
                R.fail(g, f"Agent 11: {v} fehlt")
        if s11.count("**Button:**") != 2:
            R.fail(g, f"Agent 11: genau 2 Buttons erwartet (gefunden: {s11.count('**Button:**')})")
        if "Info-Video" not in s11:
            R.warn(g, "Agent 11: 'kostenloses Info-Video' wird nicht erwähnt")

    # Zahlen & Versprechen
    g = R.group("Keine Einkommens-, Zeit- oder Mitgliederzahlen, keine nicht belegbaren Versprechen")
    claim_text = "\n".join(clean.get(k, "") for k in ("2&3", "7", "11"))
    claim_text = claim_text.replace("0€-Info-Video", "")
    for pat, what in [
        (r"\d[\d.,]*\s?(?:€|Euro|EUR)\b|€\s?\d", "Geldbetrag"),
        (r"\b\d[\d.]*\s*(?:Mitglieder|Frauen|Mütter|Mamas|Follower|Teilnehmerinnen)\b", "Mitglieder-/Community-Zahl"),
        (r"\b\d+(?:\s*[-–]\s*\d+)?\s*(?:Stunden|Std\.?|Minuten|Wochen|Monate|Monaten|Tage|Tagen)\b", "Zeitangabe"),
    ]:
        for m in re.finditer(pat, claim_text):
            R.warn(g, f"{what} im Text: {m.group(0)!r} – nur mit Pamina-Bestätigung zulässig")

    # Final
    if args.final:
        g = R.group("Agent 10: Checklisten-Abschnitt vorhanden")
        if "10" in secs and "✅" not in secs["10"] and "❌" not in secs["10"]:
            R.fail(g, "Agent 10: Abschnitt enthält keine Checkliste (✅/❌)")

    return R, secs, clean, vars_


def log_history(path, slug, secs, clean, vars_):
    rec = {
        "date": datetime.date.today().isoformat(),
        "slug": slug,
        "motiv": field(clean.get("5", ""), "Motiv"),
        "audio": field(clean.get("4", ""), "Audio"),
        "stimmung": field(clean.get("4", ""), "Stimmung"),
    }
    rec.update({k: vars_.get(n) for k, n in zip(VAR_KEYS, VAR_NAMES)})
    pool = [x.strip() for x in re.split(r"[,;]", field(clean.get("6", ""), "Pool") or "") if x.strip()]
    if pool:
        rec["pool"] = pool
    old = [r for r in read_history(path) if r.get("slug") != slug]
    old.append(rec)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in old), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--checklist", action="store_true")
    ap.add_argument("--log", action="store_true")
    ap.add_argument("--history", default=str(ROOT / "data" / "prompt-history.jsonl"))
    ap.add_argument("--slug")
    ap.add_argument("--names", default=str(ROOT / "data" / "forbidden-names.txt"))
    ap.add_argument("--week", action="store_true", help="Wochen-Datei (output/woche-<KW>.md) prüfen")
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        sys.exit(f"Datei nicht gefunden: {path}")
    if args.week:
        R, kw, items = run_week_checks(path.read_text(encoding="utf-8"), args)
        for g in R.groups:
            for level, msg in g["items"]:
                print(f"{level} [{g['label']}] {msg}")
        print(f"\n{kw}: {len(items)} Prompts · Ergebnis: {R.n_fail} FAIL, {R.n_warn} WARN → "
              f"{'NICHT bestanden' if R.n_fail else 'bestanden'}")
        if args.log and not R.n_fail:
            log_week(Path(args.history), items)
            print(f"Historie aktualisiert: {args.history}")
        sys.exit(1 if R.n_fail else 0)
    slug = args.slug or path.stem
    R, secs, clean, vars_ = run_checks(path.read_text(encoding="utf-8"), args, slug)

    if args.checklist:
        for g in R.groups:
            print(f"{R.status(g)} {g['label']}")
        print()
    for g in R.groups:
        for level, msg in g["items"]:
            print(f"{level} [{g['label']}] {msg}")
    print(f"\nErgebnis: {R.n_fail} FAIL, {R.n_warn} WARN → {'NICHT bestanden' if R.n_fail else 'bestanden'}")

    if args.log and not R.n_fail:
        log_history(Path(args.history), slug, secs, clean, vars_)
        print(f"Historie aktualisiert: {args.history}")
    elif args.log:
        print("Historie NICHT aktualisiert (Prüfung fehlgeschlagen).")
    sys.exit(1 if R.n_fail else 0)


if __name__ == "__main__":
    main()
