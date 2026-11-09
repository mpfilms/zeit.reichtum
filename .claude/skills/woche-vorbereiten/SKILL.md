---
name: woche-vorbereiten
description: Bereitet zu Wochenbeginn alle Medien einer @zeit.reichtum-Woche vor – 9 Gemini-Fotos (1 pro Tag, an Karussell-Tagen 2, klar verschiedene Szenen) und 12 Video-Prompts für die Reels, die Pamina selbst in Luma/Runway erzeugt. Nutzen bei „Woche vorbereiten“, „Bilder der Woche“, „Video-Prompts der Woche“.
argument-hint: "2026-KW47 Plan-Woche 1" | (leer = nächste KW)
---

# Woche vorbereiten (Medien-Pool)

Du orchestrierst, du schreibst keine Agenten-Inhalte selbst. Eingabe: `$ARGUMENTS`
Keine Repo-Tests ausführen (`run_tests.sh`, unittest, `validate_repo.py`), nur auf Paminas Wunsch.

## 1. Woche festlegen
- Kalenderwoche aus der Eingabe (`2026-KW47`, `KW47`) oder die nächste KW. Plan-Woche: 1 = Tag 1-7, 2 = Tag 8-14. Fehlt sie, nimm die Plan-Woche, die auf die zuletzt vorbereitete folgt (`ls medien/*/woche.json`), sonst 1; sag in einem Satz, was du angenommen hast.
- Existiert `data/content-plan.md` nicht: `python3 scripts/plan.py generate`.
- `python3 scripts/media.py init <KW> --plan-woche <1|2>` legt `medien/<KW>/{fotos,videos}` und die Zuteilung an und zeigt sie: **9 Foto-IDs** (`<KW>-F01` …, je Tag 1, an Karussell-Tagen 2) und **12 Video-IDs** (`<KW>-T01-R1` …).
- Plan-Zeilen der Woche: `python3 scripts/plan.py slot <SLOT>` für jeden Slot der Woche (Format, Fokus, Stil, Hook-Idee, Sunday Mode).

## 2. Agent 5 im Wochen-Modus (`zr-05-art-director`)
Übergib: KW, die Zuteilung (alle IDs mit Tag und Zweck), die Plan-Zeilen der Woche. Verlange den **Wochen-Bildplan** (Tabelle, eine Zeile pro ID).

## 3. Agent 6 im Wochen-Modus (`zr-06-prompt-engineer`)
Übergib: KW, Zuteilung, Plan-Zeilen und den Wochen-Bildplan von Agent 5. Verlange alle **21 Abschnitte** (9 Fotos, 12 Videos) im Wochen-Format.

## 4. Wochen-Datei zusammensetzen: `output/woche-<KW>.md`
```
# Wochen-Medien <KW> · Plan-Woche <n> (Tag a-b)

## Agent 5 · Wochen-Bildplan
<Block von Agent 5 unverändert>

## Agent 6 · Wochen-Prompts
<Block von Agent 6 unverändert>
```

## 5. Prüfen
`python3 scripts/qa_check.py output/woche-<KW>.md --week`
- Bei `FAIL`: Meldungen an Agent 6 (bzw. Agent 5 bei zu ähnlichen Orten) zurückgeben, nur die betroffenen Abschnitte neu schreiben lassen und ersetzen; höchstens 2 Runden, dann ehrlich melden, was offen ist.
- Bestanden: `python3 scripts/qa_check.py output/woche-<KW>.md --week --log` (Historie, damit sich nichts in späteren Wochen wiederholt).

## 6. Fotos erzeugen
Nur nach bestandener Prüfung und nur mit `GEMINI_API_KEY` in `.env` (sonst überspringen und sagen).
`python3 scripts/render_images.py output/woche-<KW>.md --week`
- Erzeugt pro Foto-ID **ein** Bild (9:16) nach `medien/<KW>/fotos/<Dateiname>.jpg` und trägt es in `medien/bildliste.jsonl` ein. Bereits vorhandene Fotos werden übersprungen.
- Sieh dir jedes Foto an (Read): keine Menschen/Hände, kein Text im Bild, Erdtöne, die beiden Karussell-Fotos eines Tages klar verschieden. Ein misslungenes Foto einmal neu: `--only <ID> --redo`.
- Kosten: Richtwert ca. 0,14 $ pro Foto (gemini-pro, 2K), die Zeile „neue Fotos“ und `medien/<KW>/render-log.json` nennen die Menge.

## 7. Ausgabe an Pamina
1. Kurz: KW, Plan-Woche, wie viele Fotos erzeugt wurden (oder warum nicht), ungefähre Kosten.
2. **Die 12 Video-Prompts**, je mit Slot, Tag, Fokus und dem **Zieldateinamen** `medien/<KW>/videos/<SLOT>.mp4` – die Prompts als Codeblöcke, unverändert (Formel wörtlich).
3. Hinweis: Videos genau so benennen; `python3 scripts/media.py status <KW>` zeigt, was noch fehlt. Eigene Fotos einfach in `medien/eigene/` legen – du benennst sie beim nächsten Post (siehe create-post).
