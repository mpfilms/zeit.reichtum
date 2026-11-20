# Post T06-SN · Story-Sequenz · Spiegel · Nurture

## Agent 1 · Strategist
- **Slot:** T06-SN
- **Tag/Format:** Tag 6 (Samstag), Story-Sequenz (Nurture), ca. 08:30
- **Format:** Story-Sequenz
- **Fokus:** A) Erschöpfung am Morgen / Funktionieren-Müssen
- **Typ:** Spiegel
- **Ausrichtung:** Nurture
- **Sunday Mode:** nein
- **Reel-Typ:** –
- **Thema:** Highlight Ehrlich: was ein Affiliate-Link ist, warum „Werbung“ dasteht, was ich davon habe
- **Thema-Hinweise:** Transparent und ruhig, ohne Zahlen. Zeitlos formulieren (bleibt im Highlight „Ehrlich“ stehen). Kein Name des Erstellers, kein Kursname.
- **Highlight:** Ehrlich
- **Quelle:** Plan

## Agent 2 & 3 · Hook & Script
**Trigger:** Umdeutung
<!-- intern: Einstieg: Direkte-Ansprache. Umdeutung: Das Wort „Werbung“ ist kein Makel, sondern das Zeichen, dass hier ehrlich gesagt wird, was ist. | Inhalt laut Thema: was ein Partnerlink ist, warum gekennzeichnet wird, was Pamina davon hat (eine Provision, keine Zahlen). Zeitlos (Highlight „Ehrlich“), kein „heute“, kein Datum. Nurture: keine Keyword-Antwort, kein Info-Video. „in der Regel nicht teurer“ vorsichtig wie in T03-K. -->

**Slide 1:**
# Unter meinen Posts steht „Werbung“. Hier ist, warum.

**Slide 2 (Frage):**
Ich teile Partnerlinks: persönliche Empfehlungen zu Dingen, die ich selbst nutze.
Kauft jemand darüber, erhalte ich eine Provision. Für dich wird es dadurch in der Regel nicht teurer.
Welche Frage hast du dazu noch?

**Slide 3 (CTA):**
Darum steht „Werbung“ bei jedem Post, offen und ehrlich.
Ich empfehle nur, wovon ich selbst überzeugt bin.
Schreib mir deine Frage gern direkt, ich antworte dir persönlich.

<!-- intern Agent 3: Zeitlos für das Highlight „Ehrlich“. Kein Keyword, kein Info-Video, keine Zahlen. „persönlich antworten“ ist durch pamina-fakten.md gedeckt (Aufgaben: Fragen und Kommentare beantworten). -->

## Agent 4 · Audio & Mood
- **Audio:** Leise, durchlaufende Instrumentalmusik aus dem Soundstripe-Pool (`medien/musik/`), die `render_story.py T06-SN` unter das Story-Video legt. Gesucht ist eine helle, klare Akustikgitarre mit einzelnen, gezupften Tönen in mittlerer Lage, sehr ruhig und ohne Rhythmusgruppe. Kein Gesang, kein Höhepunkt. Kein Trend-Audio.
- **Stimmung:** Offenheit am Samstagmorgen. Nichts wird versteckt, alles ist ausgesprochen. Klar, freundlich und entspannt, wie ein ehrliches Gespräch bei einer Tasse Kaffee.
- **Lautstärke:** niedrig (ca. 10-15 %)

## Agent 5 · Art Director
- **Motiv:** aus dem Wochen-Pool – 2026-KW46-F01 (Holztreppe am Vormittag, leerer Notizzettel und Bleistift auf einer Stufe, graues Novemberlicht von oben)
- **Begründung:** Das leere, unbeschriebene Blatt passt zum Thema Offenheit: nichts Verstecktes, nichts Kleingedrucktes. Ruhiges Vormittagslicht für die Morgen-Story.

## Agent 6 · Prompt Engineer
- **Pool:** 2026-KW46-F01
- **Quelle:** output/woche-2026-KW46.md

**Midjourney-Prompt (2026-KW46-F01):**
```
A quiet wooden staircase inside a home on a grey November morning, seen from above at a gentle angle. Soft diffuse daylight falls from a roof window overhead, creating barely visible shadows on the warm brown oak steps. A woven stair runner in muted wheat yellow runs down the steps. On one of the lowest steps, in the lower third of the frame, lies a single blank sheet of unbleached paper and a plain unvarnished wooden pencil. Earthy palette of beige, warm brown wood and a hint of sage green from a painted wall. No people, no text, no logos, no writing on the paper. Extreme negative space in the center and the upper part of the frame: calm empty wall and soft light for text. Slow-life aesthetic, vertical 9:16, high resolution, 1080x1920 or larger, 35mm lens, natural textures. Slightly underexposed by 10-15%, subtle dark cinematic color grading, muted and dimmed natural lighting, soft natural vignette, optimized for white text overlay. The earthy tones remain warm but slightly deepened for a premium look. --ar 9:16 --style raw --v 6.1
```

## Agent 7 · Copywriter
- **Variante:** story
**Caption:**

Werbung 🤍

Sticker: Frage-Sticker „Was möchtest du wissen?“

## Agent 8 · SEO Specialist
- **Eingewebte Keywords:** keine
- **Hashtags:** keine
- **5 Suchphrasen für Bio und Alt-Text:**
  1. was ist ein Partnerlink einfach erklärt
  2. warum steht Werbung unter Instagram-Posts
  3. Empfehlungslink und Provision ehrlich erklärt
  4. transparente Empfehlungen als Mama
  5. Holztreppe mit leerem Notizzettel im Morgenlicht

## Agent 9 · Platform Optimizer (CapCut)
**Allgemein:** Sicherheitsrand mittlere 60 %, nur sanftes Fade (0,5 s), keine zusätzliche Abdunkelung in CapCut. Story als Video mit durchlaufender Musik, 7 s pro Slide (21 s), Format 9:16. Slide-Design „ohne“ (Plan-Tag 6): Text direkt auf dem Foto, ohne Karte. Eine Farbe auf allen drei Slides: Creme #F5EFE6 vor der ruhigen Wand; ist der Hintergrund hinter dem Text hell, Dunkelbraun #2F2620. Bei gemischtem Hintergrund Creme mit weichem, randlosem dunklem Schleier.

| Slide | Element | Schrift |
|---|---|---|
| 1 | Überschrift | Playfair Display Bold, zentriert |
| 2 | Erklärung + Frage | Montserrat Italic; Frage auf eigener Zeile mit kleinem Abstand davor |
| 3 | Einladung | Montserrat Italic, gleiche Farbe |

## Agent 10 · Quality Assurance
**Checkliste (letzte Ausgabe `qa_check.py --checklist`):**
✅ Aufbau, Reihenfolge und Festlegungen (Format, Typ, Ausrichtung) korrekt
✅ Keine Blacklist-Wörter
✅ Alltagssprache: kein „stoisch/Stoiker/Stoizismus“ im Content
✅ Schweizer Schreibweise: „ss“ statt „ß“
✅ Sprache: keine groben Satz-, Wort- oder Satzzeichenfehler im sichtbaren Text
⚠️ Kein Name des Erstellers, kein Kursname
✅ Kennzeichnung „Werbung 🤍“ als erste Zeile, Folge-Satz als letzte Zeile
✅ Kein Hashtag-Block, höchstens 2 Hashtags direkt im Satz
✅ Hook max. 2 Sätze, Struktur passt zum Format
✅ Spiegel-Hook ohne Zitat, mit Trigger
✅ Nurture korrekt: kein Pitch/Keyword/Manychat, Community-Frage am Ende
✅ Caption-Variante und Länge stimmen
✅ Abdunkelungs-Formeln wörtlich, Bild-Formel vor den Parametern, Video-Formel am Ende
✅ Wochen-Pool: Medien-IDs angegeben, Karussell mit zwei verschiedenen Fotos
✅ CapCut-Vorgaben vollständig (Schrift, Farbe, Fade, Sicherheitsrand, keine Abdunkelung)
✅ Keine Einkommens-, Zeit- oder Mitgliederzahlen, keine nicht belegbaren Versprechen



**Sprache Wort für Wort geprüft: ja** (alle sichtbaren Texte, Caption Zeile für Zeile).

**Korrekturen:**
- Slide 3: Emoji 🤍 entfernt (die Schrift kann es nicht darstellen).
- Slide 1 auf die Überschrift gekürzt (vorher 4 Sätze im Hook-Bereich), Erklärung nach Slide 2 verschoben.

**Manuelle Prüfung:**
- Zeitlos für das Highlight „Ehrlich“: kein „heute“, kein Datum. Thema-Hinweise erfüllt: Partnerlink erklärt, warum „Werbung“ dasteht, was Pamina davon hat (eine Provision, ohne Zahl). „in der Regel nicht teurer“ vorsichtig formuliert wie in T03-K.
- „ich antworte dir persönlich“ gedeckt durch `pamina-fakten.md` (Aufgaben: Fragen und Kommentare beantworten).
- WARN Namensliste leer, manuell geprüft: kein Ersteller- und kein Kursname. Akzeptiert.
