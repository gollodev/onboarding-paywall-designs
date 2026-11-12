# onboarding-paywall-designs

Agent skill that turns an existing app project into **onboarding and subscription paywall design images (PNG)** plus the strategy behind them: `project-brief.md`, `conversion-strategy.md`, screens for iPhone/Android in light/dark with A/B variants, a contact sheet (PNG/PDF), a quality report and a `pending.md` with missing data. It never writes app code and never invents prices, ratings or testimonials.

Works with **Claude Code**, **claude.ai** (ZIP upload) and **GitHub Copilot** (VS Code agent mode, Copilot CLI, cloud agent). It follows the open [Agent Skills](https://agentskills.io) format.

## Install

```bash
# 1. Python deps (Python 3.9+; a virtualenv is recommended)
python3 -m pip install -r onboarding-paywall-designs/requirements.txt
python3 -m playwright install chromium
python3 onboarding-paywall-designs/scripts/check_env.py

# 2. Make the skill discoverable (copies, kept in sync from this canonical folder)
python3 onboarding-paywall-designs/scripts/sync_skill.py                     # into this repo
python3 onboarding-paywall-designs/scripts/sync_skill.py --target ../my-app  # into another project
```

`sync_skill.py` validates `SKILL.md` and then writes:

| Tool | Path |
|------|------|
| Claude Code | `.claude/skills/onboarding-paywall-designs/` |
| GitHub Copilot (Agent Skills) | `.github/skills/onboarding-paywall-designs/` |
| Copilot fallback (prompt file, VS Code) | `.github/prompts/onboarding-paywall.prompt.md` → `/onboarding-paywall` |
| Copilot fallback (always-on instructions) | pointer block in `.github/copilot-instructions.md` |
| claude.ai | `sync_skill.py --zip` → `dist/onboarding-paywall-designs.zip`, upload it in Customize › Skills (needs code execution) |

Edit **only** this canonical folder, then re-run `sync_skill.py`. Run `sync_skill.py --check` (e.g. in CI) to detect copies that drifted. `--link` creates symlinks instead of copies (Claude Code supports them; Copilot/VS Code and Windows checkouts may not).

> Copilot also reads `.claude/skills/`, so in VS Code the skill can appear twice (same name, two locations). Both copies are identical. If that bothers you, use `--only claude`: Claude and Copilot both read that copy.

## Use

- Claude Code: "Design the onboarding and paywall for this app" or `/onboarding-paywall-designs`.
- Copilot (VS Code, agent mode): same request, or `/onboarding-paywall-designs`, or `/onboarding-paywall` (prompt file).
- Manual pipeline (what the agent runs):

```bash
S=.claude/skills/onboarding-paywall-designs   # or .github/skills/...
python3 $S/scripts/discover_project.py --project . --out paywall-designs
python3 $S/scripts/build_screens.py --work paywall-designs --init      # then edit config.json
python3 $S/scripts/build_screens.py --work paywall-designs
python3 $S/scripts/render.py --work paywall-designs                    # PNG + quality checks
python3 $S/scripts/contact_sheet.py --work paywall-designs --pdf
```

## Demo

`examples/demo-app/` is a fictional Expo app ("Brotia"). Its outputs are in `examples/demo-app/paywall-designs/` (see `DEMO.md` there). To regenerate:

```bash
cd onboarding-paywall-designs/examples/demo-app
python3 ../../scripts/build_screens.py --work paywall-designs
python3 ../../scripts/render.py --work paywall-designs
python3 ../../scripts/contact_sheet.py --work paywall-designs --pdf
```

## License

MIT (see `LICENSE`). Bundled third-party assets keep their own licenses:


- Fonts: Inter, Poppins, Manrope (SIL Open Font License 1.1, see `assets/fonts/*-OFL.txt`).
- Icons: subset of [Lucide](https://lucide.dev) (ISC, see `assets/icons/LICENSE-lucide.txt`).
- Phone frames are drawn programmatically (generic, unbranded).
