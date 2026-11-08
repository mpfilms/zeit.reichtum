---
name: create-post
description: Erstellt genau einen @zeit.reichtum-Post (Reel, Karussell oder Story-Sequenz) über den sequenziellen 11-Agenten-Workflow, z. B. "Reel 1 von Tag 5", "Karussell von Tag 3", "Story-Sequenz", "Reel Nurture". Nutzen, sobald Pamina einen einzelnen Post verlangt.
argument-hint: "Reel 1 von Tag 5" | "Karussell von Tag 3" | "Story-Sequenz Pitch" | "Reel Nurture Fokus B"
---

# Post erstellen (Orchestrator)

Du orchestrierst, du schreibst keine Agenten-Inhalte selbst. Erstelle **nur den einen genannten Post**. Eingabe: `$ARGUMENTS`

## 0. Task-Liste
Lege mit TaskCreate je einen Schritt (Slot klären, Agenten 1-11, Zusammensetzen, QA, Ausgabe) an und hake sie ab.

## 1. Anfrage auflösen
- Slot-ID: „Reel 1 von Tag 5" → `T05-R1`, „Reel 2 von Tag 12" → `T12-R2`, „Karussell von Tag 3" → `T03-K`. Wochentag aus `python3 scripts/plan.py slot <SLOT>`. Existiert noch kein Plan (`data/content-plan.md` fehlt), erzeuge ihn mit `python3 scripts/plan.py generate` (Hook-Ideen kannst du danach mit dem Skill `content-plan` füllen lassen).
- Story-Sequenz oder Posts ohne Plan-Slot: Slot-ID `ADHOC-<YYYYMMDD>-<HHMM>`; Format, Pitch/Nurture usw. kommen aus Paminas Vorgaben oder aus Agent 1.
- Vorgaben von Pamina (Fokus, Typ, Pitch/Nurture, Keyword, Caption-Variante) notieren; sie schlagen den Plan. Ist die Anfrage mehrdeutig *und* teuer zu wiederholen, frage kurz nach, sonst entscheide und sage in einem Satz, was du angenommen hast.

## 2. Agenten nacheinander aufrufen (Agent-Tool, jeweils `subagent_type` = Agentenname)
Gib jedem Agenten **den Slot, das Format, die Vorgaben und die bisherigen Agenten-Ergebnisse** im Prompt mit (Subagenten sehen den Chat nicht). Reihenfolge strikt:

| # | subagent_type | Eingabe zusätzlich | Hinweis |
|---|---|---|---|
| 1 | `zr-01-strategist` | Slot, Format, Vorgaben | liefert Typ, Ausrichtung, Fokus, Sunday Mode |
| 2 | `zr-02-hook-quote` | Block 1 | Hook, Zitat/Trigger, internes Hand-off |
| 3 | `zr-03-script` | Blöcke 1, 2 | Einblendungen/Slides |
| 4 | `zr-04-audio-mood` | Block 1 | |
| 5 | `zr-05-art-director` | Blöcke 1, 4 | |
| 6 | `zr-06-prompt-engineer` | Blöcke 1, 5 | liest die Historie selbst |
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
- `--log` schreibt Motiv, Audio und Variablen in `data/prompt-history.jsonl` (nur bei bestandener QA). So wiederholt sich nichts im nächsten Post.

## 4b. Bilder erzeugen (Google Gemini / Imagen 4)
Erst **nach** bestandenem `--final`. Gibt es keinen API-Schlüssel (`GEMINI_API_KEY` in `.env`), überspringe den Schritt und sage es Pamina in einem Satz.
- Reel: `python3 scripts/render_images.py output/<SLOT>.md` → `output/<SLOT>/bild-1.png …` (Hintergrund für CapCut).
- Karussell und Story-Sequenz: `python3 scripts/render_images.py output/<SLOT>.md --slides` → zusätzlich fertige Slides mit Text in `output/<SLOT>/slides/`.
- Vorgaben von Pamina (Modell, Anzahl, Seitenverhältnis) über `--model`, `--count`, `--aspect` durchreichen.
- Sieh dir `bild-1.png` an (Read), bevor du es meldest: keine Menschen, keine Hände, kein Text im Bild, Erdtöne erhalten. Ist eines davon verletzt, rendere einmal neu und nimm dann das beste Bild mit `--base`.
- Standard ist `gemini-pro` (`gemini-3-pro-image`); `--model gemini-flash` ist günstiger. Meldet die API 404, zeigt `--list-models` die verfügbaren Modelle.
- Schlägt die API fehl oder filtert sie das Bild, melde die Fehlermeldung ehrlich; der Post bleibt trotzdem gültig (der Prompt steht in Agent 6).

## 5. Ausgabe an Pamina
- Ein Satz vorab zu Annahmen (z. B. aus welchem Plan-Slot Typ/Fokus stammen).
- Danach die Post-Datei **vollständig und unverändert** in der Reihenfolge 1, 2 & 3, 4, 5, 6, 7, 8, 9, 10 (bei Pitch + 11), gut lesbar auf dem Handy (die Codeblöcke der Prompts bleiben Codeblöcke).
- Ohne HTML-Kommentare. Am Ende der Hinweis, wo die Datei und die Bilder liegen (oder warum keine erzeugt wurden), und was als Nächstes passt (z. B. „Reel 2 von Tag 5").
