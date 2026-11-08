# @zeit.reichtum · Content Automation for Claude Code

Automates the 11-agent content workflow for the Instagram account **@zeit.reichtum** (faceless Reels, carousels and stories for mothers in mental load; DM sender/signature: Pamina). Everything the creator said in the rule set lives in this repo as Claude Code instructions, **one subagent per agent**, skills that orchestrate them, and scripts that enforce the hard rules deterministically.

## Quick start
```bash
cd zeit.reichtum
claude                       # open Claude Code in this folder
/start                       # loads the brand DNA, replies with the fixed ready sentence
/content-plan                # 14-day plan (data/content-plan.md)
/create-post Reel 1 von Tag 5
/create-post Karussell von Tag 3
/create-post Story-Sequenz Pitch
/quote-pack Zeit             # 4-pack: 3 lighthouses (real ancient quotes) + 1 mirror, each with caption
```
Before the first real run, **fill `data/forbidden-names.txt`** with the creator's name and the course name (one per line). The QA cannot check those names otherwise and prints a warning.

## Image generation (Google Gemini / Imagen 4)
```bash
cp .env.example .env                      # add GEMINI_API_KEY from Google AI Studio
python3 -m pip install -r requirements.txt  # Pillow, only needed for --slides
python3 scripts/render_images.py --list-models   # which image models your key may use
python3 scripts/render_images.py output/T03-K.md --slides
```
Default model: `gemini-3-pro-image` (`--model gemini-flash` is cheaper). Image models need a Google AI Studio project with **billing enabled**; on the free tier the image quota is 0.
Runs only after `qa_check.py --final` passes. The darkening formula stays verbatim; only the Midjourney parameters are translated (`--ar 9:16` → `aspectRatio`, people generation disabled). Put `PlayfairDisplay-Bold.ttf` and `Montserrat-Italic.ttf` into `assets/fonts/` (Georgia is the fallback).

## How it works
```
 you ──► create-post (skill, main session = orchestrator)
            │  sequential, each call gets only what it needs
            ├─► zr-01-strategist        slot, focus A-D, lighthouse/mirror, pitch/nurture, Sunday Mode
            ├─► zr-02-hook-quote        real quote + source (verified) or psychological hook
            ├─► zr-03-script            2-3 overlays / 4-8 slides / 3 story slides
            ├─► zr-04-audio-mood        audio, mood (alternates), low volume
            ├─► zr-05-art-director      motif rotation 1-4
            ├─► zr-06-prompt-engineer   3+1 new variables, comparison table, Midjourney + Luma/Runway prompts
            ├─► zr-07-copywriter        caption (mandatory header, pitch a/b or nurture)
            ├─► zr-08-seo-specialist    keywords, hashtags, 5 search phrases
            ├─► zr-09-platform-optimizer  CapCut typography and timing
            ├─► zr-11-manychat-texter   2-step DM flow (pitch only)
            └─► zr-10-quality-assurance edits output/<slot>.md until scripts/qa_check.py passes
```
The orchestrator assembles `output/<slot>.md`, runs `qa_check.py --final --log` and only then prints the post in the required order (1, 2 & 3, 4 … 10, + 11 for pitch).

| Path | Purpose |
|---|---|
| `CLAUDE.md` | project rules; imports `data/brand-dna.md` |
| `.claude/agents/zr-01 … zr-11` | the 11 separate subagents (own prompt, own tool permissions) |
| `.claude/skills/{start,create-post,content-plan,quote-pack}` | entry points / orchestration |
| `data/brand-dna.md` | brand DNA, blacklist, wording, 75/25, the two darkening formulas |
| `data/quotes.md` | vetted quote bank (extend only with verified sources) |
| `data/content-plan.md` | 14-day plan, slot IDs like `T05-R1` (day 5, reel 1), `T03-K` (carousel) |
| `data/prompt-history.jsonl` | memory for motif/audio/variables so nothing repeats |
| `data/blacklist.txt`, `data/forbidden-names.txt` | machine-checked word lists |
| `scripts/qa_check.py` | deterministic QA (see below) |
| `scripts/plan.py`, `scripts/roll.py` | plan blueprint, real 50/50 randomness |
| `scripts/render_images.py` | renders the Agent-6 prompt with Google Imagen 4 / Gemini into `output/<slot>/`; `--slides` adds the slide texts (Agent 9 style) |
| `scripts/validate_repo.py`, `tests/` | self-tests (43 tests); CI in `.github/workflows/ci.yml` |

## What the deterministic QA enforces
Blacklist · forbidden names · exact caption header · ≤ 2 hashtags, never a block · hook ≤ 2 sentences · quote has source and "sinngemäß" · pitch = exactly one keyword + Manychat flow, nurture = no keyword/flow and ends with a community question · caption variant (a = exactly 4 sentences, CTA 4th; b = 4 ✨ lines; Sunday ≤ 2 sentences) · both darkening formulas verbatim, image formula directly before `--ar 9:16 --style raw --v 6.1` with nothing after, video formula at the end, no people, static camera · Agent-6 variables listed first and not repeated from the history · CapCut specs · DM transparency + affiliate note · money/time/member numbers raise a **WARN** for human review.

## Interpretation choices (change them in the agent files if you disagree)
- Carousel/story: one Midjourney prompt as base for all slides, no motion prompt.
- Story pitch uses the keyword "INFO" (as in the story spec); reel/carousel pitch uses "START".
- Stories have no caption; Agent 7 outputs the mandatory "Werbung" header (+ optional sticker line).
- Sunday Mode caption: ≤ 2 sentences in total, the CTA counts.
- Audio: Agent 4 names a genre/sound, not a specific track (no invented chart titles).
- Plan: odd days Reel 1 = Pitch, even days Reel 2 = Pitch; every 4th reel is a mirror (75/25).

## Develop
```bash
bash tests/run_tests.sh       # validate repo + 35 tests
```
Only the Python standard library is used.
