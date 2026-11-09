---
name: hook-generator
description: Erzeugt Hook-Varianten für @zeit.reichtum und pflegt den Hook-Vorrat (data/hook-bank.md). Drei Modi – Vorrat auffüllen („10 Spiegel-Hooks zu Fokus B"), offene Plan-Slots füllen („Hooks für den Plan"), A/B-Varianten für einen Post („3 Hook-Varianten für T05-R1"). Nutzen bei Anfragen nach Hooks, Hook-Ideen oder Hook-Varianten.
argument-hint: "vorrat [Anzahl] [Fokus] [Stil] | plan | varianten T05-R1"
---

# Hook-Generator

Hooks entscheiden in den ersten 1–2 Sekunden über die Reichweite. Darum: **viele erzeugen, streng prüfen, die stärksten auswählen**, statt pro Post einen einzigen Schuss. Der Vorrat in `data/hook-bank.md` ist das Herzstück; der Plan und Agent 2 bedienen sich daraus.

Die Inhalte schreibt **immer `zr-02-hook-quote`** (Ideen-Modus). Du orchestrierst, prüfst und zeigst die Ergebnisse. Nichts landet in Bank oder Plan, bevor Pamina auswählt.

## Modus erkennen (`$ARGUMENTS`)
- **vorrat** (Standard): `[Anzahl=12] [Fokus A-D/S] [Stil]`. Ohne Vorgaben gemischt: 75/25 Leuchtturm/Spiegel, alle Fokusse A, B, C, D, S abgedeckt.
- **plan**: `python3 scripts/hooks.py open` ausführen. Slots mit passendem freien Bank-Hook zuerst daraus vorschlagen. Für die übrigen pro Slot **2 Kandidaten** erzeugen (Fokus und Stil wie im Plan).
- **varianten <Slot>**: `python3 scripts/plan.py slot <Slot>` lesen. **3 Varianten** erzeugen, bei Spiegel je ein anderer Trigger, bei Leuchtturm 3 verschiedene belegte Zitate.

## Auftrag an zr-02-hook-quote
Übergib Modus, Anzahl, Fokus, Stil und **die vorhandenen Hooks** (Ausgabe von `python3 scripts/hooks.py list`), damit er Wiederholungen vermeidet. Gib ihm diese Handwerksregeln mit:

**Spiegel** – genau ein Trigger (Paradoxon · Validierung · Umdeutung). Variiere zusätzlich den **Einstieg**, kein Muster öfter als zweimal pro Batch:
1. *Geständnis* – „Ich habe nie laut gesagt, dass …" (nur allgemein, nicht als erfundener Rückblick von Pamina)
2. *Konkrete Szene* – ein spürbarer Moment: Küche nach dem Zubettbringen, Kaffeekasse, Handy im Dunkeln
3. *Unausgesprochene Wahrheit* – „Niemand sagt dir, dass …"
4. *Direkte Ansprache* – „Du bist nicht faul. …"
5. *Paradox-Paar* – zwei Hälften, die sich widersprechen
6. *Stille Frage* – eine Frage, die sie sich nachts selbst stellt

**Leuchtturm** – nur Zitate aus `data/quotes.md` oder per WebSearch verifizierte (Quelle angeben, „sinngemäss"). Der Hook ist das Zitat selbst. Optional als zweite Zeile eine kurze **moderne Brücke** (max. 8 Wörter), die das Zitat in den Mütteralltag holt.

**Für alle**
- Die ersten 3–5 Wörter tragen den Hook: ein starkes Bild oder eine Spannung, keine Anlaufsätze wie „Heute möchte ich …".
- Maximal 2 Sätze, ideal unter 15 Wörter (On-Screen-Text).
- Identitätsebene statt Tipps. Ruhig, empathisch, keine Ausrufezeichen-Kaskaden, keine künstliche Verknappung.
- Schweizer Schreibweise „ss". Blacklist und verbotene Namen beachten. Keine Zahlen zu Einkommen oder Mitgliedern.
- Pitch-Slots: Schmerzpunkt, der zur Erkenntnis „es geht ohne eigenes Produkt" führen kann (die Brücke kommt später in die Caption, nicht in den Hook).
- Sunday Mode: Loslassen, Quality Time, Durchatmen.

Ausgabe von Agent 2 pro Hook eine Zeile: `Stil | Fokus | Trigger bzw. Quelle | Einstieg | Hook`.

## Prüfen
Prüfe **jeden** Hook mit `python3 scripts/hooks.py check "<Hook>" --stil <spiegel|leuchtturm>`. Bei `FAIL` gib den Hook mit dem Grund an Agent 2 zurück und lass ihn ersetzen (höchstens 2 Runden), sonst streiche ihn. `WARN` darf bleiben, wird aber angezeigt. Melde nur als bestanden, was wirklich durchgelaufen ist.

## Bewerten und Ausgabe
Bewerte jeden bestandenen Hook kurz selbst auf einer Skala 1–5 nach: **Scroll-Stopp** (packen die ersten Wörter?), **Wiedererkennen** (fühlt sie sich ertappt, ohne beschämt zu werden?), **Markenfit** (ruhig, tiefgründig). Sortiere nach Summe.

Ausgabe handytauglich, nummeriert:
```
1. „Hook" 
   Spiegel · B · Paradoxon · Szene · 13/15  [WARN …]
```
Danach eine Frage: welche Nummern in den Vorrat (`hooks.py add …`) bzw. in welche Slots (`hooks.py add …` und dann `hooks.py use H0xx T05-R1`). Erst nach Paminas Auswahl ausführen. Bei Modus **varianten** zusätzlich empfehlen, welche zwei Varianten sich für einen A/B-Test (z. B. Trial Reels) am stärksten unterscheiden.

Es werden keine Captions, Prompts oder Posts erzeugt. Für einen vollständigen Post danach `create-post`.
