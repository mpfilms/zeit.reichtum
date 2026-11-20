---
name: woche-vorbereiten
description: Bereitet zu Wochenbeginn die Fotos einer @zeit.reichtum-Woche vor – 18 Gemini-Fotos (2 pro Tag für Nurture- und Verkaufs-Story, an Karussell-Tagen zusätzlich 2 fürs Karussell, klar verschiedene Szenen) für Stories, Karussells und Reel-Titelbilder. Die Reel-Videos kommen aus dem Monats-Pool (Skill videos-monat). Nutzen bei „Woche vorbereiten“, „Bilder der Woche“.
argument-hint: "2026-KW47 Plan-Woche 1" | (leer = nächste KW)
---

# Woche vorbereiten (Medien-Pool)

Du orchestrierst, du schreibst keine Agenten-Inhalte selbst. Eingabe: `$ARGUMENTS`
Keine Repo-Tests ausführen (`run_tests.sh`, unittest, `validate_repo.py`), nur auf Paminas Wunsch.

## 1. Woche festlegen
- Kalenderwoche aus der Eingabe (`2026-KW47`, `KW47`) oder die nächste KW. Plan-Woche: 1 = Tag 1-7, 2 = Tag 8-14. Fehlt sie, nimm die Plan-Woche, die auf die zuletzt vorbereitete folgt (`ls medien/*/woche.json`), sonst 1; sag in einem Satz, was du angenommen hast.
- Existiert `data/content-plan.md` nicht: `python3 scripts/plan.py generate`.
- `python3 scripts/media.py init <KW> --plan-woche <1|2>` legt `medien/<KW>/{fotos,videos}` und die Zuteilung an und zeigt sie: **18 Foto-IDs** (`<KW>-F01` …, je Tag eines für `SN` und eines für `SP`, an Karussell-Tagen 2 weitere für `K`). Videos gehören nicht mehr zur Woche: prüfe mit `python3 scripts/media.py monat-status`, ob der Monats-Pool steht; fehlt er, weise Pamina auf den Skill `videos-monat` hin.
- Plan-Zeilen der Woche: `python3 scripts/plan.py slot <SLOT>` für jeden Slot der Woche (Format, Fokus, Stil, Hook-Idee, Sunday Mode).

## 2. Agent 5 im Wochen-Modus (`zr-05-art-director`)
Übergib: KW, die Zuteilung (alle IDs mit Tag und Zweck), die Plan-Zeilen der Woche (inkl. Thema). Verlange den **Wochen-Bildplan** (Tabelle, eine Zeile pro ID, mit Spalte „Eigenes Foto“).
Für jede Zeile mit Foto-Wunsch: `python3 scripts/media.py wunsch <KW> <ID> "<Wunsch>" --bis "Tag <n-1>"` (einen Tag vor der Verwendung; bei Tag 1 „Tag 1 früh“). Diese IDs erzeugt Schritt 6 nicht mit Gemini.

## 3. Agent 6 im Wochen-Modus (`zr-06-prompt-engineer`)
Übergib: KW, Zuteilung, Plan-Zeilen und den Wochen-Bildplan von Agent 5. Verlange alle **18 Foto-Abschnitte** im Wochen-Format.

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
- Sieh dir jedes Foto an (Read): keine Menschen ausser der Frau von hinten (immer dieselbe, kein Gesicht), kein Text, keine Logos im Bild, Erdtöne, die beiden Karussell-Fotos eines Tages klar verschieden. Ein misslungenes Foto einmal neu: `--only <ID> --redo`.
- Kosten: Richtwert ca. 0,14 $ pro Foto (gemini-pro, 2K), die Zeile „neue Fotos“ und `medien/<KW>/render-log.json` nennen die Menge.

## 7. Ausgabe an Pamina
1. Kurz: KW, Plan-Woche, wie viele Fotos erzeugt wurden (oder warum nicht), ungefähre Kosten.
2. **Deine Foto-Wünsche** (aus `python3 scripts/media.py status <KW>`): je Wunsch was, wofür (Slot) und bis wann; Fotos einfach in `medien/eigene/` legen. Kommt keins, nehme ich beim Post das Gemini-Ersatzbild (ca. 0,14 $).
3. Stand des Monats-Video-Pools in einem Satz (`media.py monat-status`).
4. Hinweis: Eigene Fotos einfach in `medien/eigene/` legen, eigene Videos in `medien/eigene-videos/` – du nimmst sie beim nächsten Post auf (siehe create-post).
