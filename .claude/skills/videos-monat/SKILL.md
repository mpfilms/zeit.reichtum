---
name: videos-monat
description: Erstellt einmal pro Monat die 18 Video-Prompts für alle Reels von @zeit.reichtum (output/videos-<YYYY-MM>.md). Pamina erzeugt die Videos selbst in ihrer App und legt sie in medien/videos/<Monat>/ ab; jedes Video wird bis zu 3× verwendet (original, gespiegelt, gespiegelt + Ausschnitt). Nutzen bei „Videos des Monats", „Video-Prompts für Dezember", „Monat vorbereiten".
argument-hint: "2026-12" | (leer = nächster Monat)
---

# Videos des Monats (Monats-Video-Pool)

Du orchestrierst, du schreibst keine Agenten-Inhalte selbst. Eingabe: `$ARGUMENTS`
Keine Repo-Tests ausführen (`run_tests.sh`, unittest, `validate_repo.py`), nur auf Paminas Wunsch.

**Warum 18:** Der Plan hat ca. 52 Reels im Monat (12 pro Woche). Jedes Video wird bis zu dreimal verwendet – original, gespiegelt, gespiegelt mit leicht anderem Ausschnitt –, immer mit anderem Text und frühestens nach 10 Tagen wieder. 18 × 3 = 54 Verwendungen. Eigene Videos von Pamina (`medien/eigene-videos/`) zählen zusätzlich.

## 1. Monat anlegen
`python3 scripts/media.py monat-init <YYYY-MM>` (ohne Angabe: nächster Monat) → `medien/videos/<Monat>/monat.json` mit 18 IDs (`<Monat>-V01` …) und Fokus: 4× A, 4× B, 3× C, 3× D, 4× S (Sonntag).

## 2. Agent 5 im Monats-Modus (`zr-05-art-director`)
Übergib: Monat und die 18 IDs mit Fokus. Verlange den **Monats-Szenenplan** (Tabelle mit Ort, Motiv, Geräusch).

## 3. Agent 6 im Monats-Modus (`zr-06-prompt-engineer`)
Übergib: Monat, IDs mit Fokus und den Szenenplan von Agent 5. Verlange alle **18 Abschnitte** im Monats-Format (Text-to-Video, 8 Sekunden, 9:16, Naturgeräusch, Video-Formel wörtlich am Ende).

## 4. Datei zusammensetzen: `output/videos-<Monat>.md`
```
# Monats-Videos <Monat>

So gehts: Jeden Prompt in deiner Video-App einfügen (9:16, 1080×1920, ca. 8 Sekunden, mit Ton), das Video als
medien/videos/<Monat>/<ID>.mp4 speichern. Der Rest (Text, Spiegeln, Länge, Titelbild) passiert automatisch.

## Agent 5 · Monats-Szenenplan
<Block von Agent 5 unverändert>

## Agent 6 · Monats-Prompts
<Block von Agent 6 unverändert>
```

## 5. Prüfen
`python3 scripts/qa_check.py output/videos-<Monat>.md --month`
- Bei `FAIL`: Meldungen an Agent 6 (bzw. Agent 5 bei Orten) zurückgeben, nur die betroffenen Abschnitte neu schreiben lassen; höchstens 2 Runden, dann ehrlich melden, was offen ist.
- Bestanden: `python3 scripts/qa_check.py output/videos-<Monat>.md --month --log` (Historie gegen Wiederholungen).

## 6. Ausgabe an Pamina
1. Kurz: Monat, 18 Videos, wofür sie gedacht sind (Fokus-Verteilung).
2. **Die 18 Prompts**, je mit ID, Fokus, Szene und **Zieldatei** `medien/videos/<Monat>/<ID>.mp4` – die Prompts als Codeblöcke, unverändert (Formel wörtlich). Hinweis: in der App 9:16, Auflösung 1080p (1080×1920) und ca. 8 Sekunden wählen, Ton an.
3. `python3 scripts/media.py monat-status <Monat>` zeigt jederzeit, welche Videos noch fehlen und wie viele Verwendungen frei sind.
4. Eigene Videos (Handy) einfach in `medien/eigene-videos/` legen; sie werden beim nächsten Post aufgenommen (9:16, Metadaten/GPS entfernt).
