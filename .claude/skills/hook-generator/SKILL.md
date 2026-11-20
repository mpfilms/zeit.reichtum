---
name: hook-generator
description: Erzeugt Hook-Varianten für @zeit.reichtum und pflegt den Hook-Vorrat (data/hook-bank.md) inkl. Messwerten aus den Insights. Drei Modi – Vorrat auffüllen („10 Spiegel-Hooks zu Fokus B"), offene Plan-Slots füllen („Hooks für den Plan"), A/B-Varianten für einen Post („3 Hook-Varianten für T05-R1"). Auch für „welche Hooks funktionieren?" (Auswertung). Nutzen bei Anfragen nach Hooks, Hook-Ideen oder Hook-Varianten.
argument-hint: "vorrat [Anzahl] [Fokus] [Stil] [Typ] | plan | varianten T05-R1 | auswertung"
---

# Hook-Generator

Hooks entscheiden in den ersten 1–2 Sekunden über die Reichweite. Darum: **viele erzeugen, streng prüfen, die stärksten auswählen, danach messen.** Der Vorrat in `data/hook-bank.md` ist das Herzstück; der Plan und Agent 2 bedienen sich daraus, und die Messwerte zeigen, welche Einstiege bei Paminas Frauen wirklich wirken.

Die Inhalte schreibt **immer `zr-02-hook-quote`** (Ideen-Modus). Du orchestrierst, prüfst und zeigst die Ergebnisse. Nichts landet in Bank oder Plan, bevor Pamina auswählt.

## Modus erkennen (`$ARGUMENTS`)
- **vorrat** (Standard): `[Anzahl=12] [Fokus A-D/S] [Stil] [Typ A/B]`. Ohne Vorgaben gemischt: 50/50 Leuchtturm/Spiegel, **mindestens 3 von 4 Hooks als Szene** (Uhrzeit-Szene, Szene, Dialog, POV, Erkennungszeichen, Offene-Schleife), Rohstoff aus `data/situationen.md`, alle Fokusse A, B, C, D, S, etwa halb Typ A, halb Typ B, mindestens 6 verschiedene Einstiege.
- **plan**: `python3 scripts/hooks.py open` ausführen. Slots mit passendem freien Bank-Hook (Fokus, Stil, Reel-Typ) zuerst daraus vorschlagen. Für die übrigen pro Slot **2 Kandidaten** erzeugen.
- **varianten <Slot>**: `python3 scripts/plan.py slot <Slot>` lesen. **3 Varianten** mit 3 verschiedenen Einstiegen (bei Spiegel auch verschiedene Trigger, bei Leuchtturm 3 verschiedene belegte Zitate).
- **auswertung**: `python3 scripts/hooks.py auswertung` ausführen und in 3–5 Sätzen erklären, welche Einstiege, Trigger und Reel-Typen vorne liegen. Ab ca. 3 Posts pro Gruppe sind Aussagen vorsichtig möglich, vorher nur als Tendenz. Wenn genug Daten da sind: im nächsten Vorrat die Gewinner-Einstiege stärker gewichten (etwa 60 %), die anderen weiter testen (40 %).

## Zwei Reel-Typen
Der Plan legt fest: **Morgen-Reel (R1) = Typ A, Abend-Reel (R2) = Typ B** (`reel_typ` in `plan.py slot`).
- **Typ A „Ein Satz"**: Der Hook steht allein, **höchstens ca. 10 Wörter**. Ideal für Leuchtturm-Zitate, ruhig, zum Teilen.
- **Typ B „Schichten"**: Überschrift (= Hook, **höchstens ca. 10 Wörter**) + Textbox (20–35 Wörter, z. B. Liste, Alt vs. Neu, kleine Übung; die Caption wiederholt sie nicht, sondern ergänzt kurz) + Schlusszeile mit Verweis auf die Caption. Der Text ist absichtlich länger, als man in einem Durchlauf liest: Das Reel wird pausiert oder mehrmals geschaut. Die Textbox schreibt Agent 3, nicht Agent 2. Der Hook muss aber eine Fortsetzung **versprechen** (Doppelpunkt, offene Schleife, „probier das:"), die die Textbox einlöst.

## Auftrag an zr-02-hook-quote
Übergib Modus, Anzahl, Fokus, Stil, Reel-Typ und **die vorhandenen Hooks** (Ausgabe von `python3 scripts/hooks.py list`), damit er Wiederholungen vermeidet. Gib ihm diese Handwerksregeln mit:

**Einstiege** (Name exakt so, wie er in die Bank kommt). Pro Batch kein Einstieg öfter als zweimal (ausser „Zitat").

| Einstieg | So klingt er | Passt zu |
|---|---|---|
| Geständnis | „Ich habe nie laut gesagt, dass …" (allgemein, kein erfundener Rückblick von Pamina) | Spiegel, A |
| Szene | ein spürbarer Moment: Küche nach dem Zubettbringen, Kaffeekasse, Handy im Dunkeln | Spiegel, A/B |
| Niemand-sagt-dir | „Niemand sagt dir, dass …" | Spiegel, A/B |
| Direkte-Ansprache | „Du bist nicht faul. …" | Spiegel, A |
| Paradox-Paar | zwei Hälften, die sich widersprechen | Spiegel, A |
| Stille-Frage | eine Frage, die sie sich nachts selbst stellt; „Was würdest du mit einer freien Stunde tun?" | Spiegel, A, Nurture |
| Kontrast | Mythos ruhig brechen: „Unpopuläre Meinung: …", „Selbstfürsorge ist kein Schaumbad." | Spiegel, A/B, Pitch |
| Alltags-Zahl | konkrete, wahre Zahl aus dem Alltag, **nie Geld oder Ergebnis**: „21:40 Uhr. Seit 6 Uhr wach." | Spiegel, A/B |
| Offene-Schleife | Mini-Geschichte in der 3. Person, die genau vor der Auflösung stoppt: „Sie sitzt im Auto vor der Kita. Motor aus." | Spiegel, B, Pitch |
| Quick-Win | verspricht einen Gedanken oder eine kleine Übung zum Speichern, nie ein Ergebnis: „Wenn dein Kopf abends nicht aufhört, probier das:" | beide Stile, B, Nurture |
| Challenge | sanfte Herausforderung auf Identitätsebene: „Kannst du fünf Minuten nichts tun, ohne dich schuldig zu fühlen?" | Spiegel, A |
| Aber-nicht-so | Neugier ohne Clickbait: „Seneca über Reichtum. Aber nicht so, wie du denkst." | beide Stile, A/B |
| Echter-Kommentar | ein **echter** Kommentar oder eine echte Story-Frage, die Pamina mitgibt (anonymisiert). **Nie erfinden** – ohne Input von Pamina diesen Einstieg nicht verwenden. | beide, B |
| Uhrzeit-Szene | Wochentag/Uhrzeit + Mama-Signal, zwei kurze Sätze: „Donnerstag, 20:14 Uhr. Winterjacken für beide Kinder bestellt.“ | beide, A/B |
| Dialog | ein wörtlicher Satz von Partner, Kind oder Kita: „Er sagt: ‚Sag doch, wenn du Hilfe brauchst.‘“ | beide, A/B |
| POV | „POV: Du kommst aus der Einschlafbegleitung und die Küche sieht aus wie vorher.“ | Spiegel, A/B |
| Erkennungszeichen | „Eine Frau, die nur noch funktioniert, erkennst du daran, dass …“ | beide, B |
| Zitat-im-Moment | „Ich habe heute einen Satz gelesen, fast 2000 Jahre alt:“ – das echte Zitat folgt als Wendung | Leuchtturm, A/B |
| Zitat | der Hook ist das Zitat selbst (höchstens 1 von 4 Leuchttürmen, nur Zitate, die die Leserin direkt ansprechen) | Leuchtturm, A/B |

**Spiegel**: genau ein Trigger (Paradoxon · Validierung · Umdeutung), dazu einer der Einstiege oben.

**7-Sekunden-Geschichte (seit 20.11.2026):** Szene → Detail/Dialog → Wendung. Der Hook ist die Szene; die Wendung (Zitat bzw. Umdeutung) kommt als Hand-off an Agent 3. Ausgabezeile deshalb mit Wendung: `… | Hook | Wendung | Hand-off`.

**Leuchtturm**: nur Zitate aus `data/quotes.md` oder per WebSearch verifizierte (Quelle angeben, „sinngemäss"). Standard: Hook = Szene, Zitat = Wendung. Reines Zitat als Hook nur bei höchstens 1 von 4 Leuchttürmen, möglichst kurz (lieber den Kern eines Satzes). Eine moderne Brücke zum Mütteralltag gehört **nicht in den Hook**, sondern als Hand-off in Einblendung 2 (Agent 3). Ein Leuchtturm darf auch mit „Aber-nicht-so" oder „Quick-Win" eingeleitet werden („Was Seneca jeden Abend tat:"), wenn die Fortsetzung das echte Zitat bringt.

**Für alle**
- Die ersten 3–5 Wörter tragen den Hook: ein starkes Bild oder eine Spannung, kein Anlauf („Heute möchte ich …").
- Hook **höchstens ca. 10 Wörter** und 2 Sätze. Leuchtturm-Zitate dürfen knapp darüber liegen, wenn sie sich nicht sinnvoll kürzen lassen.
- **Jede geöffnete Schleife wird im Post aufgelöst** (Hand-off an Agent 3 im Kommentar notieren).
- Identitätsebene, ruhig, empathisch. Keine Ausrufezeichen-Kaskaden, keine Grossbuchstaben-Rufe, keine künstliche Verknappung („noch ist Platz"), keine Angst-Rhetorik („fataler Fehler").
- **Geld:** als Gefühl erlaubt (Kita-Kosten, die alte Jacke), nie Verdienst-Hooks oder Einkommensbehauptungen („X € am Tag“).
- Nichts erfinden: keine Statistiken („90 % aller Mütter"), keine Rechenbeispiele zu Einnahmen, keine Kundinnen-Geschichten. Persönliche Rückblicke von Pamina nur, wenn sie wahr sind (sonst `RÜCKFRAGE:`).
- Alltagssprache, nie „stoisch"/„Stoiker". Schweizer Schreibweise „ss". Blacklist und verbotene Namen beachten.
- Pitch-Slots: Schmerzpunkt oder Kontrast, der zur Erkenntnis „es geht ohne eigenes Produkt" führen kann (Brücke kommt in Caption/Textbox, nicht in den Hook).
- Sunday Mode: Loslassen, Quality Time, Durchatmen.

Ausgabe von Agent 2 pro Hook eine Zeile: `Stil | Fokus | Trigger bzw. Quelle | Einstieg | Typ | Hook | Wendung | Hand-off (Auflösung/Brücke)`.

## Prüfen
Prüfe **jeden** Hook mit `python3 scripts/hooks.py check "<Hook>" --stil <spiegel|leuchtturm>`. Bei `FAIL` gib den Hook mit dem Grund an Agent 2 zurück und lass ihn ersetzen (höchstens 2 Runden), sonst streiche ihn. `WARN` darf bleiben, wird aber angezeigt. Melde nur als bestanden, was wirklich durchgelaufen ist.

## Bewerten und Ausgabe
Bewerte jeden bestandenen Hook kurz selbst auf einer Skala 1–5 nach **Scroll-Stopp** (packen die ersten Wörter, ist sofort klar, dass es um eine Mama geht?), **Wiedererkennen** (fühlt sie sich ertappt, ohne beschämt zu werden?) und **Markenfit** (ruhig, tiefgründig). Sortiere nach Summe. Sag dazu, dass das eine Einschätzung ist – entscheidend sind die Messwerte.

Ausgabe handytauglich, nummeriert:
```
1. „Hook"
   Spiegel · B · Paradoxon · Kontrast · Typ A · 13/15  [WARN …]
```
Danach eine Frage: welche Nummern in den Vorrat bzw. in welche Slots. Erst nach Paminas Auswahl ausführen:
`python3 scripts/hooks.py add --stil … --fokus … --trigger … --einstieg … --typ … "Hook"`, für Slots danach `python3 scripts/hooks.py use H0xx T05-R1`.
Bei Modus **varianten** zusätzlich empfehlen, welche zwei Varianten sich für einen A/B-Test (Trial Reels) am stärksten unterscheiden.

## Messen (nach dem Posten)
Erinnere Pamina, nach ca. 48 Stunden die Insights eines Reels einzutragen:
`python3 scripts/hooks.py messen H0xx --hold <3-Sek.-Rate %> --speichern <n> --teilen <n> --start <n>`.
Ohne diese Zahlen bleibt jede Hook-Bewertung ein Bauchgefühl.

Es werden keine Captions, Prompts oder Posts erzeugt. Für einen vollständigen Post danach `create-post`.
