#!/usr/bin/env python3
"""Selbsttest der Repo-Struktur: Agenten, Skills, Formeln, Verweise. Exit 1 bei Fehlern."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import qa_check  # noqa: E402

errors = []


def err(msg):
    errors.append(msg)


def frontmatter(path):
    t = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", t, re.S)
    if not m:
        err(f"{path.relative_to(ROOT)}: Frontmatter fehlt")
        return {}, t
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm, t[m.end():]


# 11 getrennte Agenten
EXPECTED = {
    1: "strategist", 2: "hook-quote", 3: "script", 4: "audio-mood", 5: "art-director",
    6: "prompt-engineer", 7: "copywriter", 8: "seo-specialist", 9: "platform-optimizer",
    10: "quality-assurance", 11: "manychat-texter",
}
agent_names = []
for n, slug in EXPECTED.items():
    name = f"zr-{n:02d}-{slug}"
    p = ROOT / ".claude" / "agents" / f"{name}.md"
    if not p.exists():
        err(f"Agent fehlt: {p.relative_to(ROOT)}")
        continue
    fm, body = frontmatter(p)
    agent_names.append(name)
    if fm.get("name") != name:
        err(f"{p.name}: name im Frontmatter ist {fm.get('name')!r}, erwartet {name!r}")
    if len(fm.get("description", "")) < 40:
        err(f"{p.name}: description fehlt/zu kurz")
    if not fm.get("tools"):
        err(f"{p.name}: tools fehlen (Rechte bewusst beschränken)")
    if f"Agent {n}" not in body and f"Agent {n} " not in fm.get("description", ""):
        err(f"{p.name}: nennt sich nicht 'Agent {n}'")
extra = [p.name for p in (ROOT / ".claude" / "agents").glob("*.md") if p.stem not in agent_names]
if extra:
    err(f"Unerwartete Agenten-Dateien: {extra}")

# Skills
skills = {}
for d in sorted((ROOT / ".claude" / "skills").iterdir()):
    p = d / "SKILL.md"
    if not p.exists():
        err(f"{d.name}: SKILL.md fehlt")
        continue
    fm, body = frontmatter(p)
    skills[d.name] = body
    if fm.get("name") != d.name:
        err(f"Skill {d.name}: name im Frontmatter ist {fm.get('name')!r}")
    if len(fm.get("description", "")) < 40:
        err(f"Skill {d.name}: description fehlt/zu kurz")
for must in ("start", "create-post", "content-plan", "quote-pack"):
    if must not in skills:
        err(f"Skill fehlt: {must}")

# Orchestrator ruft jeden Agenten auf (außer 10 in der Tabelle, der separat steht)
cp = skills.get("create-post", "")
for name in agent_names:
    if name not in cp:
        err(f"create-post verweist nicht auf {name}")

# Wörtliche Formeln: brand-dna, Agent 6 und qa_check müssen identisch sein
dna = (ROOT / "data" / "brand-dna.md").read_text(encoding="utf-8")
a6 = (ROOT / ".claude" / "agents" / "zr-06-prompt-engineer.md").read_text(encoding="utf-8")
for label, f in (("Bild", qa_check.IMG_FORMULA), ("Video", qa_check.VID_FORMULA)):
    if f not in dna:
        err(f"{label}-Formel weicht in data/brand-dna.md von qa_check.py ab")
    if f not in a6:
        err(f"{label}-Formel weicht in zr-06-prompt-engineer.md von qa_check.py ab")
if qa_check.PARAMS not in dna or qa_check.PARAMS not in a6:
    err("Midjourney-Parameter weichen ab")
a7 = (ROOT / ".claude" / "agents" / "zr-07-copywriter.md").read_text(encoding="utf-8")
if qa_check.HEADER not in a7:
    err("Pflicht-Kopfzeile fehlt in zr-07-copywriter.md")

# Blacklist
bl = {l.lower() for l in qa_check.lines_of(ROOT / "data" / "blacklist.txt")}
need = {"magie", "magisch", "zaubertrick", "zauberei", "hexenwerk", "karma"}
if not need <= bl:
    err(f"blacklist.txt unvollständig, fehlt: {sorted(need - bl)}")

# CLAUDE.md-Import
cm = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
for ref in re.findall(r"(?m)^@(\S+)", cm):
    if not (ROOT / ref).exists():
        err(f"CLAUDE.md importiert fehlende Datei: {ref}")

# Datendateien/Plan
for f in ("data/quotes.md", "data/forbidden-names.txt", "data/content-plan.md", "data/prompt-history.jsonl"):
    if not (ROOT / f).exists():
        err(f"Datei fehlt: {f}")

if errors:
    print("FEHLER:")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print(f"OK: 11 Agenten, {len(skills)} Skills, Formeln konsistent, Blacklist vollständig.")
