---
name: create-post
description: Erstellt genau einen @zeit.reichtum-Post (Reel, Karussell, Nurture- oder Verkaufs-Story) über den sequenziellen 11-Agenten-Workflow, z. B. "Reel 1 von Tag 5", "Karussell von Tag 3", "Story-Sequenz", "Reel Nurture". Nutzen, sobald Pamina einen einzelnen Post verlangt.
argument-hint: "Reel 1 von Tag 5" | "Karussell von Tag 3" | "Verkaufs-Story von Tag 5" | "Nurture-Story von Tag 5" | "Erfolg von Tag 6"
---

# Post erstellen (Orchestrator)

Du orchestrierst, du schreibst keine Agenten-Inhalte selbst. Erstelle **nur den einen genannten Post**. Eingabe: `$ARGUMENTS`

## 0. Task-Liste
Lege mit TaskCreate je einen Schritt (Slot klären, Agenten 1-11, Zusammensetzen, QA, Ausgabe) an und hake sie ab.

## 1. Anfrage auflösen
- Slot-ID: „Reel 1 von Tag 5" → `T05-R1`, „Reel 2 von Tag 12" → `T12-R2`, „Karussell von Tag 3" → `T03-K`. Wochentag aus `python3 scripts/plan.py slot <SLOT>`. Existiert noch kein Plan (`data/content-plan.md` fehlt), erzeuge ihn mit `python3 scripts/plan.py generate` (Hook-Ideen kannst du danach mit dem Skill `content-plan` füllen lassen).
- Stories (seit 2026-11-19 zwei pro Tag): „Nurture-Story von Tag 2“ → `T02-SN` (08:30), „Verkaufs-Story von Tag 2“ → `T02-SP` (20:30). Nur „Story von Tag 2“ ohne Angabe → beide nacheinander anbieten, erst `SN`. Alte Slots `T0x-S` gibt es nur noch bei bereits erstellten Posts.
- **Erfolgs-Story** („Erfolg von Tag 2“ → `T02-SE`, Di und Sa 18:30) läuft **nicht** über die Agenten: `python3 scripts/erfolg.py T02-SE` nimmt den nächsten unbenutzten echten Erfolg aus `medien/erfolge/neu/`, baut die Story (mit Musik) und schreibt `output/T02-SE.md`. Jeder Erfolg wird nur einmal verwendet. Fehlt Material, sag es Pamina in einem Satz.
- **Verkaufs-Story `SP`:** Slide 3 endet mit „Antworte mit „START“ …“ (Manychat-Story-Antwort). Nach `render_story.py` zusätzlich `python3 scripts/erfolg.py link-slide <SLOT>` → `output/<SLOT>/link-slide.jpg` (rendert den Text aus `**Link-Slide:**` ohne „START“, darunter Platz für den Link-Sticker; fehlt der Block, eine Kopie der letzten Slide), die Pamina um 20:30 selbst mit Link-Sticker postet.
- Ziel-Highlight steht in `plan.py slot` (`highlight`); nenne es in der Ausgabe an Pamina („danach ins Highlight START legen“).
- Story-Sequenz oder Posts ohne Plan-Slot: Slot-ID `ADHOC-<YYYYMMDD>-<HHMM>`; Format, Pitch/Nurture usw. kommen aus Paminas Vorgaben oder aus Agent 1.
- Vorgaben von Pamina (Fokus, Typ, Pitch/Nurture, Keyword, Caption-Variante) notieren; sie schlagen den Plan. Ist die Anfrage mehrdeutig *und* teuer zu wiederholen, frage kurz nach, sonst entscheide und sage in einem Satz, was du angenommen hast.

## 1b. Wochen-Pool prüfen
`python3 scripts/media.py pick <SLOT>` (nur bei Plan-Slots).
- Liefert es Fotos bzw. ein Video (Woche mit dem Skill `woche-vorbereiten` vorbereitet), läuft der Post im **Pool-Modus**: Agent 5 und 6 bekommen die Ausgabe von `pick` und den Pfad `output/woche-<KW>.md` und arbeiten im Pool-Modus (keine neuen Bilder, keine neuen Prompts). Fehlt ein Foto/Video noch, sag es Pamina in einem Satz; der Post kann trotzdem entstehen.
- Liefert es nichts (Woche nicht vorbereitet, ADHOC): normaler Modus wie bisher (Agent 5/6 entwerfen neu; Karussell = zwei getrennte Prompts mit klar verschiedenen Szenen).
- **Foto-Wunsch offen** (Hinweis in `pick`): Liegt in `medien/eigene/` ein passendes neues Foto, nimm es mit `add-eigen … --fuer <ID>` auf und rufe `pick` erneut auf. Sonst frage Pamina kurz, ob noch eins kommt; wenn nicht: `python3 scripts/render_images.py output/woche-<KW>.md --week --only <ID>` (Gemini-Ersatz) und `pick` erneut.
- **Reels:** `pick` liefert das Video aus dem Monats-Pool (`video`: ID, Datei, Variante original/spiegel/ausschnitt; Fokus passend, höchstens 3×, 10 Tage Pause). Agent 5 und 6 bekommen es im Pool-Modus; Agent 6 übernimmt den Prompt dieses Videos wörtlich aus `output/videos-<Monat>.md`. Ist kein Video frei, sag es Pamina in einem Satz (Skill `videos-monat` oder eigenes Video).
- **Eigene Videos:** Zeigt `scan` neue Dateien in `medien/eigene-videos/`, sieh dir ein Standbild an (`ffmpeg -ss 1 -i <Datei> -frames:v 1 <scratchpad>/x.jpg`, dann Read) und nimm sie auf: `python3 scripts/media.py add-video <Datei> --ort <ort> --stimmung <…> [--fokus A-D|S]` (9:16, Metadaten/GPS entfernt). Keine erkennbaren Gesichter von Kindern, keine Hinweise auf den Wohnort.
- **Eigene Fotos:** Zeigt `python3 scripts/media.py scan` neue Dateien in `medien/eigene/`, sieh sie dir an (Read) und nimm sie auf: `python3 scripts/media.py add-eigen <Datei> --ort <ort> --licht <licht> [--farbe <farbe>] [--stimmung <…>]` (sprechender Name, Metadaten/GPS werden entfernt). Fotos mit erkennbaren Gesichtern von Kindern oder Hinweisen auf den Wohnort (Strassenschilder, Hausnummern) nicht aufnehmen, sondern Pamina darauf hinweisen.

## 2. Agenten nacheinander aufrufen (Agent-Tool, jeweils `subagent_type` = Agentenname)
Gib jedem Agenten **den Slot, das Format, die Vorgaben und die bisherigen Agenten-Ergebnisse** im Prompt mit (Subagenten sehen den Chat nicht). Reihenfolge strikt:

| # | subagent_type | Eingabe zusätzlich | Hinweis |
|---|---|---|---|
| 1 | `zr-01-strategist` | Slot, Format, Vorgaben | liefert Typ, Ausrichtung, Fokus, Sunday Mode |
| 2 | `zr-02-hook-quote` | Block 1 | Hook, Zitat/Trigger, internes Hand-off |
| 3 | `zr-03-script` | Blöcke 1, 2 | Einblendungen/Slides |
| 4 | `zr-04-audio-mood` | Block 1 | |
| 5 | `zr-05-art-director` | Blöcke 1, 4 (+ `pick`-Ausgabe im Pool-Modus) | Pool-Modus: übernimmt die Pool-Medien |
| 6 | `zr-06-prompt-engineer` | Blöcke 1, 5 (+ `pick`-Ausgabe und Wochen-Datei im Pool-Modus) | liest die Historie selbst; Pool-Modus: Prompts wörtlich aus der Wochen-Datei |
| 7 | `zr-07-copywriter` | Blöcke 1, 2 (inkl. Hand-off), 3 | Caption |
| 8 | `zr-08-seo-specialist` | Block 7 | |
| 9 | `zr-09-platform-optimizer` | Blöcke 1, 3 | |
| 11 | `zr-11-manychat-texter` | Blöcke 1, 2, 3, 7 | **nur bei Pitch** |

Meldet ein Agent `RÜCKFRAGE: …`, stoppe und frage Pamina (AskUserQuestion oder Text); erfinde nichts. Ist Pamina nicht erreichbar, nimm die sicherste Variante ohne persönliche Behauptung und markiere das im Post.

## 3. Post-Datei zusammensetzen: `output/<SLOT>.md`
Schreibe die Datei mit **exakt diesen Überschriften** (die Prüfung hängt daran):

```
# Post <SLOT> · <Format> · <Typ> · <Ausrichtung>

## Agent 1 · Strategist
<Block 1>

## Agent 2 & 3 · Hook & Script
<Zeile **Zitat:** bzw. **Trigger:** aus Agent 2>
<Block 3>          (Agent 2s **Hook:**-Zeile entfällt, weil Einblendung 1 sie wörtlich enthält)

## Agent 4 · Audio & Mood
## Agent 5 · Art Director
## Agent 6 · Prompt Engineer
## Agent 7 · Copywriter
## Agent 8 · SEO Specialist
## Agent 9 · Platform Optimizer (CapCut)
## Agent 11 · Manychat-Flow (Absender: PAMINA)     ← nur bei Pitch
```
Übernimm die Blöcke **unverändert**. HTML-Kommentare (`<!-- intern: … -->`) darfst du in der Datei lassen; sie werden nicht angezeigt.

## 4. Qualitätssicherung
Rufe `zr-10-quality-assurance` mit dem Dateipfad auf. Danach selbst:
`python3 scripts/qa_check.py output/<SLOT>.md --final --log`
- Bei `FAIL`: gib die Meldungen an `zr-10-quality-assurance` zurück bzw. den verursachenden Agenten (z. B. Agent 6 bei Formeln/Wiederholungen) und baue neu; höchstens 2 Runden, dann melde ehrlich, was offen ist. **Gib nie einen Post als „geprüft" aus, wenn `--final` fehlgeschlagen ist.**
- **Sprache:** Der Lint in `qa_check.py` stoppt grobe Fehler (z. B. „deine heute“ statt „deine Zeit heute“). Zusätzlich liest `zr-10-quality-assurance` jede Überschrift und jede Zeile einzeln als Satz. Wird ein Text nach dem Rendern geändert, rendere die betroffene Slide neu (`--slides --no-images`).
- `--log` schreibt Motiv, Audio und Variablen in `data/prompt-history.jsonl` (nur bei bestandener QA). So wiederholt sich nichts im nächsten Post.

## 4b. Bilder und Slides
Erst **nach** bestandenem `--final`.

**Pool-Modus (Woche vorbereitet) – keine neuen Bilder, keine API-Kosten:**
- Karussell und Story-Sequenz: `python3 scripts/render_images.py output/<SLOT>.md --pool` → fertige Slides in `output/<SLOT>/slides/` aus den Pool-Fotos (Karussell 4:5 aus dem 9:16-Foto geschnitten, Story 9:16). Die Verwendung wird automatisch in `medien/bildliste.jsonl` eingetragen; ein Foto, das in den letzten 42 Tagen schon im Feed war, wird abgelehnt.
- **Story-Sequenz mit Ton (Standard ab 19.11.2026, Lernregel):** Nach den Slides `python3 scripts/render_story.py <SLOT>` ausführen. Es macht je Slide ein Video `story-N.mp4` (7 s) mit einem durchlaufenden Musikabschnitt, `publish.py` erkennt die Videos automatisch. Ohne Videos (oder mit `--bilder`) werden Storys ohne Ton veröffentlicht, das nur als Notlösung.
- Slide-Design kommt aus dem Plan-Tag (ungerade Tage `glas` = sehr transparente Karte, gerade Tage `ohne` = Text direkt auf dem Foto); nie innerhalb eines Tages mischen. Nur auf Paminas Wunsch `--design`.
- **Reel:** `python3 scripts/render_reel.py output/<SLOT>.md` → `output/<SLOT>/reel.mp4` (Text im Slide-Look, Typ A/B, Loop auf 9-10 s, Variante gespiegelt usw.) und `output/<SLOT>/cover.jpg` (Titelbild aus dem Foto-Pool, 42-Tage-Regel). Verwendung von Video und Foto wird eingetragen. Sieh dir 2-3 Standbilder an (`ffmpeg -ss <t> -i output/<SLOT>/reel.mp4 -frames:v 1 …`, dann Read): Text lesbar, nichts abgeschnitten, Text nicht im unteren Fünftel. Fehlt das Video noch, sag es in einem Satz.

**Normaler Modus (ohne Wochen-Pool):** Gibt es keinen API-Schlüssel (`GEMINI_API_KEY` in `.env`), überspringe den Schritt und sage es Pamina in einem Satz.
- Reel: `python3 scripts/render_images.py output/<SLOT>.md --count 1` → `output/<SLOT>/bild-1.jpg` (Hintergrund für CapCut).
- Karussell: `python3 scripts/render_images.py output/<SLOT>.md --count 2 --slides` (zwei Bilder, Slides wechseln zwischen ihnen). Story: `--count 1 --slides`.
- Vorgaben von Pamina (Modell, Anzahl, Seitenverhältnis) über `--model`, `--count`, `--aspect` durchreichen.
- Sieh dir die Bilder an (Read), bevor du sie meldest: keine Menschen ausser der Frau von hinten (immer dieselbe, kein Gesicht), kein Text, keine Logos im Bild, Erdtöne erhalten. Ist eines davon verletzt, rendere einmal neu und nimm dann das beste Bild mit `--base`.
- Standard ist `gemini-pro` (`gemini-3-pro-image`); `--model gemini-flash` ist günstiger. Meldet die API 404, zeigt `--list-models` die verfügbaren Modelle.
- Schlägt die API fehl oder filtert sie das Bild, melde die Fehlermeldung ehrlich; der Post bleibt trotzdem gültig (der Prompt steht in Agent 6).

## 5. Ausgabe an Pamina
- Ein Satz vorab zu Annahmen (z. B. aus welchem Plan-Slot Typ/Fokus stammen).
- Danach die Post-Datei **vollständig und unverändert** in der Reihenfolge 1, 2 & 3, 4, 5, 6, 7, 8, 9, 10 (bei Pitch + 11), gut lesbar auf dem Handy (die Codeblöcke der Prompts bleiben Codeblöcke).
- Ohne HTML-Kommentare. Am Ende der Hinweis, wo die Datei und die Bilder liegen (oder warum keine erzeugt wurden), und was als Nächstes passt (z. B. „Reel 2 von Tag 5").
- **Bei Reels zusätzlich die Hochlade-Schritte:** `reel.mp4` in Instagram hochladen → Titelbild `cover.jpg` wählen → Musik: Trend-Sound aus „Gespeichert“ im Klangbild von Agent 4 → Lautstärke mischen (Originalton ca. 60-70 %, Trend ca. 10-20 %) → Caption einfügen.
