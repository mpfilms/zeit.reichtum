---
name: quote-pack
description: Liefert Zitat-Ideen für @zeit.reichtum immer als 4er-Pack (2 Leuchttürme mit echten, belegten Zitaten historischer Personen als Wendung einer Alltagsszene, 2 Spiegel) je mit Caption. Nutzen bei Anfragen nach Zitat-Ideen.
argument-hint: "(optional) Thema oder Fokus, z. B. Zeit"
---

# 4er-Pack Zitat-Ideen

1. Rufe `zr-02-hook-quote` im **Ideen-Modus** auf: genau **2 Leuchttürme + 2 Spiegel**, jeweils Szene + Wendung (siehe `data/brand-dna.md`, „Positionierung“), Thema/Fokus laut `$ARGUMENTS` (sonst gemischt über die Fokus-Rotation). Pro Eintrag Hook, Quelle bzw. Trigger.
2. Rufe für jede der 4 Ideen `zr-07-copywriter` auf, um die Caption zu schreiben. Ausrichtung per `python3 scripts/roll.py pitch-nurture`, ausser Pamina gibt sie vor. Übergib Hook und Hand-off.
3. Prüfe jede Caption mit einer temporären Mini-Datei nicht per `qa_check.py` (das prüft vollständige Posts), sondern kontrolliere selbst: erste Zeile exakt „Werbung 🤍“ und letzte Zeile exakt der Folge-Satz (siehe zr-07), Blacklist, kein Hashtag-Block, höchstens 2 Hashtags im Satz, kein Ersteller-/Kursname, bei Nurture Community-Frage am Ende und kein Keyword, bei Pitch genau ein Keyword.
4. Ausgabe: nummerierte Liste 1-4, je Typ, Hook, Quelle („sinngemäss") und Caption. Es werden keine Prompts, kein Manychat-Flow und keine Dateien erzeugt, bis Pamina einen Post auswählt (dann `create-post`).
