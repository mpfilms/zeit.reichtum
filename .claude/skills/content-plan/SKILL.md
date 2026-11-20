---
name: content-plan
description: Erstellt oder aktualisiert den 14-Tage-Content-Plan für @zeit.reichtum (Start Montag, Sunday Mode an Tag 7 und 14, pro Woche 12 Reels + 2 Karussells an Tag 3 und 6, täglich 1 Story-Sequenz) als Tabelle mit Tag & Uhrzeit, Format & Typ, Fokus und kurzer Hook-Idee.
argument-hint: "(optional) neu erzeugen"
---

# 14-Tage-Plan

1. Prüfe, ob `data/content-plan.md` existiert und Hook-Ideen enthält. Existiert er und Pamina verlangt keinen neuen, zeige ihn nur an (Tabelle ausgeben).
2. Sonst Gerüst erzeugen: `python3 scripts/plan.py generate` (deterministisch: Start Montag, Tag 7 und 14 Sonntag/Sunday Mode, Morgen-Reel ca. 06:45; an Tag 3, 6, 10, 13 Karussell ca. 12:30, an allen anderen Tagen Abend-Reel ca. 20:00; täglich Story-Sequenz ca. 17:30 (Slot `Txx-S`); im Feed pro Tag je 1 Pitch und 1 Nurture in wechselnder Reihenfolge, Fokus-Rotation A-D, Reels und Storys abwechselnd Leuchtturm/Spiegel (50/50); Slide-Design ungerade Tage „glas“, gerade Tage „ohne“).
3. Themen: `python3 scripts/plan.py themen` verteilt Paminas Wünsche aus `data/themen-wuensche.md` auf freie, passende Slots (Format, Wochentag, Anzahl pro 14 Tage; Sunday Mode bleibt frei). Melde, welche Themen wo gelandet sind und welche keinen Platz fanden. Ein bewusst gesetztes Thema (`set-thema`) wird nicht überschrieben; alles neu verteilen nur auf Paminas Wunsch mit `themen --neu`.
4. Hook-Ideen: Rufe `zr-02-hook-quote` im **Ideen-Modus** auf. Übergib die Zeilen der Tabelle (Slot, Fokus, Stil, Ausrichtung, Sunday Mode, Thema + Hinweise aus `data/themen-wuensche.md`) und verlange pro Slot eine Zeile `SLOT | Idee`. Leuchttürme dürfen nur Zitate nennen, die der Agent belegen kann.
5. Trage jede Idee ein: `python3 scripts/plan.py set-hook <SLOT> "<Idee>"`.
6. Zeige die Tabelle (Spalten: Tag & Uhrzeit, Format & Typ, Fokus, Thema, Hook-Idee) und weise darauf hin, dass einzelne Posts mit „Reel 1 von Tag 5" angefordert werden. Du erstellst dabei keine Posts. Für die Medien der Woche (9 Fotos, 12 Video-Prompts) gibt es den Skill `woche-vorbereiten`.
