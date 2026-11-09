# @zeit.reichtum – Content-Orchestrator

Dieses Repo automatisiert den 11-Agenten-Workflow für den Instagram-Account **@zeit.reichtum** (faceless Reels, Karussells, Stories für Mütter im Mental Load). Absenderin der DMs und Signatur: **Pamina**. Antworte immer auf Deutsch, in **Schweizer Schreibweise (immer „ss“, nie „ß“)** – im Chat wie im Content.

@data/brand-dna.md

## So arbeitest du hier
- **Startsignal** (nur wenn Pamina das Regelwerk lädt oder `/start` nutzt): erzeuge noch keinen Content, antworte nur mit dem Satz aus dem Skill `start`.
- **Einen Post erstellen** („Reel 1 von Tag 5", „Karussell von Tag 3", „Story-Sequenz", „Reel Pitch/Nurture"): nutze den Skill `create-post`. Es wird **nur dieser eine Post** erstellt.
- **Plan** („14-Tage-Plan"): Skill `content-plan`. Paminas Wunschthemen stehen in `data/themen-wuensche.md` und landen über `plan.py themen` in der Spalte „Thema“. Pro Woche 12 Reels + 2 Karussells (Tag 3 und 6) + täglich 1 Story-Sequenz.
- **Woche vorbereiten** (Wochenbeginn): Skill `woche-vorbereiten` – 9 Gemini-Fotos (1 pro Tag, an Karussell-Tagen 2, klar verschiedene Szenen) und 12 Video-Prompts; Pamina erzeugt die Videos selbst und legt sie als `medien/<KW>/videos/<SLOT>.mp4` ab. Posts der Woche nutzen diesen Pool (Pool-Modus), statt neue Bilder zu erzeugen. **Zitat-Ideen**: Skill `quote-pack` (4er-Pack). **Hooks** (Vorrat, Plan-Slots füllen, A/B-Varianten): Skill `hook-generator`, Vorrat in `data/hook-bank.md`.
- Der Workflow läuft **sequenziell** über 11 getrennte Subagenten in `.claude/agents/` (`zr-01-…` bis `zr-11-…`). Jeder Agent hat genau eine Aufgabe und gibt nur seinen eigenen Block zurück. Du (Hauptsession) orchestrierst, übergibst Ergebnisse und setzt den Post zusammen. Du schreibst keine Agenten-Inhalte selbst.
- Qualitätssicherung ist doppelt: Agent 10 (inhaltlich) **und** `scripts/qa_check.py` (deterministisch). Ein Post wird erst ausgegeben, wenn `qa_check.py --final` ohne `FAIL` durchläuft.
- Zufall (Pitch/Nurture, Caption-Variante) kommt aus `scripts/roll.py`, nicht aus dem Bauchgefühl.
- Gedächtnis des Workflows: `data/content-plan.md` (Plan), `data/prompt-history.jsonl` (bisherige Bild-/Video-Variablen, Motive, Audio). Ohne dieses Gedächtnis können Agent 4, 5 und 6 Wiederholungen nicht vermeiden.
- Fertige Posts liegen in `output/<slot>.md`, Slides in `output/<slot>/slides/`. Wochen-Medien (Fotos, Videos, eigene Fotos, `bildliste.jsonl`) liegen in `medien/` – nur lokal, nie im öffentlichen Repo. Fotos im Feed höchstens einmal in 42 Tagen, in Stories beliebig oft.
- Slide-Design: ungerade Plan-Tage „glas“ (sehr transparente Karte), gerade Tage „ohne“ (Text direkt auf dem Foto); nie innerhalb eines Tages mischen.

## Harte Regeln (gelten für alle Agenten)
1. Blacklist niemals verletzen. Kein Name des Erstellers, kein Kursname (`data/forbidden-names.txt`).
2. Nichts erfinden: keine Zitate, keine Einkommens-/Mitgliederzahlen, keine unbelegbaren Zeit- oder Ergebnisversprechen, keine erfundenen persönlichen Rückblicke. Im Zweifel `RÜCKFRAGE:` an Pamina.
3. Wörtliche Formeln (Abdunkelung) niemals umformulieren.
4. Prüfen vor Behaupten: was nicht gelaufen ist (z. B. ein Check), wird nicht als bestanden gemeldet.

## Befehle
- `python3 scripts/qa_check.py output/<slot>.md [--final] [--log]` – deterministische Qualitätsprüfung
- `python3 scripts/plan.py generate | slot T05-R1 | set-hook T05-R1 "Idee" | set-thema T04-S "Thema" | themen [--neu]` – Content-Plan (Slots `Txx-R1/R2`, `Txx-K`, `Txx-S`)
- `python3 scripts/hooks.py check "Hook" | add --stil spiegel --fokus B --trigger Paradoxon "Hook" | list [--frei] | open | use H001 T05-R1` – Hook-Bank
- `python3 scripts/media.py init <KW> --plan-woche 1 | plan | status | scan | add-eigen [--fuer ID] | wunsch | pick <SLOT> | use` – Wochen-Medien-Pool (inkl. Foto-Wünsche an Pamina)
- `python3 scripts/qa_check.py output/woche-<KW>.md --week [--log]` – Wochen-Prompts prüfen
- `python3 scripts/roll.py pitch-nurture | caption-variant` – Zufall 50/50
- `python3 scripts/render_images.py output/woche-<KW>.md --week [--only ID] [--redo] [--dry-run]` – Fotos der Woche erzeugen (Schlüssel `GEMINI_API_KEY` in `.env`)
- `python3 scripts/render_images.py output/<slot>.md --pool [--design glas|ohne]` – Slides aus Pool-Fotos (keine API-Kosten)
- `python3 scripts/render_images.py output/<slot>.md [--slides] [--model gemini-pro|gemini-flash|imagen-4] [--list-models] [--count 2] [--dry-run]` – Bilder direkt erzeugen (ohne Wochen-Pool)
- `python3 scripts/validate_repo.py` und `bash tests/run_tests.sh` – Selbsttest des Repos
