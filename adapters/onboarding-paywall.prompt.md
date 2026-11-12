---
name: onboarding-paywall
description: Design honest, high-converting onboarding and paywall screens (PNG) for this app using the onboarding-paywall-designs skill
argument-hint: Optional — devices, theme, number of variants, where the paywall appears
agent: agent
---
Read and follow [SKILL.md](../skills/onboarding-paywall-designs/SKILL.md) step by step (the skill folder is `.github/skills/onboarding-paywall-designs/`; use it as SKILL_DIR).

- Start with Phase 1 (discover the project with `scripts/discover_project.py`) before asking anything.
- Ask only what the code cannot answer, in short blocks with suggested options.
- Write `project-brief.md` and `conversion-strategy.md`, then build, render and check the PNG screens until all quality checks pass.
- Never invent prices, ratings, testimonials or user counts; never promise features the app does not have; never write app code.

Extra instructions from the user: ${input:details:devices, theme, variants, paywall placement (optional)}
