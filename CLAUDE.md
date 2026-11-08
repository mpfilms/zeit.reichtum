# @zeit.reichtum – Content-Orchestrator

Dieses Repo automatisiert den 11-Agenten-Workflow für den Instagram-Account **@zeit.reichtum** (faceless Reels, Karussells, Stories für Mütter im Mental Load). Absenderin der DMs und Signatur: **Pamina**. Antworte immer auf Deutsch.

@data/brand-dna.md

## So arbeitest du hier
- **Startsignal** (nur wenn Pamina das Regelwerk lädt oder `/start` nutzt): erzeuge noch keinen Content, antworte nur mit dem Satz aus dem Skill `start`.
- **Einen Post erstellen** („Reel 1 von Tag 5", „Karussell von Tag 3", „Story-Sequenz", „Reel Pitch/Nurture"): nutze den Skill `create-post`. Es wird **nur dieser eine Post** erstellt.
- **Plan** („14-Tage-Plan"): Skill `content-plan`. **Zitat-Ideen**: Skill `quote-pack` (4er-Pack).
- Der Workflow läuft **sequenziell** über 11 getrennte Subagenten in `.claude/agents/` (`zr-01-…` bis `zr-11-…`). Jeder Agent hat genau eine Aufgabe und gibt nur seinen eigenen Block zurück. Du (Hauptsession) orchestrierst, übergibst Ergebnisse und setzt den Post zusammen. Du schreibst keine Agenten-Inhalte selbst.
- Qualitätssicherung ist doppelt: Agent 10 (inhaltlich) **und** `scripts/qa_check.py` (deterministisch). Ein Post wird erst ausgegeben, wenn `qa_check.py --final` ohne `FAIL` durchläuft.
- Zufall (Pitch/Nurture, Caption-Variante) kommt aus `scripts/roll.py`, nicht aus dem Bauchgefühl.
- Gedächtnis des Workflows: `data/content-plan.md` (Plan), `data/prompt-history.jsonl` (bisherige Bild-/Video-Variablen, Motive, Audio). Ohne dieses Gedächtnis können Agent 4, 5 und 6 Wiederholungen nicht vermeiden.
- Fertige Posts liegen in `output/<slot>.md`.

## Harte Regeln (gelten für alle Agenten)
1. Blacklist niemals verletzen. Kein Name des Erstellers, kein Kursname (`data/forbidden-names.txt`).
2. Nichts erfinden: keine Zitate, keine Einkommens-/Mitgliederzahlen, keine unbelegbaren Zeit- oder Ergebnisversprechen, keine erfundenen persönlichen Rückblicke. Im Zweifel `RÜCKFRAGE:` an Pamina.
3. Wörtliche Formeln (Abdunkelung) niemals umformulieren.
4. Prüfen vor Behaupten: was nicht gelaufen ist (z. B. ein Check), wird nicht als bestanden gemeldet.

## Befehle
- `python3 scripts/qa_check.py output/<slot>.md [--final] [--log]` – deterministische Qualitätsprüfung
- `python3 scripts/plan.py generate | slot T05-R1 | set-hook T05-R1 "Idee"` – Content-Plan
- `python3 scripts/roll.py pitch-nurture | caption-variant` – Zufall 50/50
- `python3 scripts/validate_repo.py` und `bash tests/run_tests.sh` – Selbsttest des Repos
