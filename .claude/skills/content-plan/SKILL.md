---
name: content-plan
description: Erstellt oder aktualisiert den 14-Tage-Content-Plan für @zeit.reichtum (Start Montag, Sunday Mode an Tag 7 und 14, 2 Reels pro Tag, Karussell jeden 3. Tag) als Tabelle mit Tag & Uhrzeit, Format & Typ, Fokus und kurzer Hook-Idee.
argument-hint: "(optional) neu erzeugen"
---

# 14-Tage-Plan

1. Prüfe, ob `data/content-plan.md` existiert und Hook-Ideen enthält. Existiert er und Pamina verlangt keinen neuen, zeige ihn nur an (Tabelle ausgeben).
2. Sonst Gerüst erzeugen: `python3 scripts/plan.py generate` (deterministisch: Start Montag, Tag 7 und 14 Sonntag/Sunday Mode, pro Tag 1 Morgen-Reel ca. 06:45 und 1 Abend-Reel ca. 20:00, jeden 3. Tag zusätzlich ein Karussell ca. 12:30, pro Tag je 1 Pitch- und 1 Nurture-Reel in wechselnder Reihenfolge, Fokus-Rotation A-D, 75/25 Leuchtturm/Spiegel).
3. Hook-Ideen: Rufe `zr-02-hook-quote` im **Ideen-Modus** auf. Übergib die Zeilen der Tabelle (Slot, Fokus, Stil, Ausrichtung, Sunday Mode) und verlange pro Slot eine Zeile `SLOT | Idee`. Leuchttürme dürfen nur Zitate nennen, die der Agent belegen kann.
4. Trage jede Idee ein: `python3 scripts/plan.py set-hook <SLOT> "<Idee>"`.
5. Zeige die Tabelle (Spalten: Tag & Uhrzeit, Format & Typ, Fokus, Hook-Idee) und weise darauf hin, dass einzelne Posts mit „Reel 1 von Tag 5" angefordert werden. Du erstellst dabei keine Posts.
