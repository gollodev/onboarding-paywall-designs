# Paywall & onboarding patterns

## Choosing templates by placement

| Placement | Recommended paywall | Why |
|-----------|--------------------|-----|
| End of onboarding (after personalization + bridge) | `trial-timeline` or `benefits-social` | User just declared a goal; echo it and remove trial risk |
| After a value moment (first result, first plant saved) | `benefits-social` or `single-plan` | Momentum is high; keep the choice simple |
| Tap on a locked feature | `single-plan` (feature-led headline) or `side-by-side` | Intent is specific; name the feature they tapped |
| Price-sensitive audience / many plans | `side-by-side` | Anchoring makes the annual saving obvious |

## Onboarding sequence (5 screens default)

1. **welcome** — Logo, outcome headline, one-line promise, primary CTA "Get started". Optional "I already have an account".
2. **benefit** — The aha moment: one visual (app screenshot or icon composition) + 3 short outcome bullets.
3. **personalization** — One question, 3–5 options with icons; the answer is stored in `answers` and echoed later.
4. **permissions** — Pre-permission explanation: why notifications help the user's goal + preview. Always a visible "Not now".
5. **bridge** — "Your plan for {{answers.goal}} is ready": summary of what they'll get, then CTA to see the plan (paywall).

## Paywall anatomy (top → bottom)

1. Close (corner) + Restore (top or footer).
2. Headline: outcome + personalization ("Keep your {{answers.goal}} on track").
3. 3–5 benefits: icon + outcome title + short feature detail. Only real premium features.
4. Social proof (real) or omitted.
5. Plans: recommended plan highlighted (badge "Best value — save 44%"), billed price prominent, per-month equivalent secondary.
6. Trial transparency line: "No payment today. We'll remind you 2 days before your trial ends."
7. Primary CTA (single).
8. Fine print: trial terms, auto-renew, cancel info. Footer: Restore · Terms · Privacy.

## Copy formulas

- Headline: "[Outcome] without [pain]" / "Your [goal] plan, unlocked" / "Everything you need to [outcome]".
- Benefit: "[Outcome verb] + [object]" — "Never miss a watering" · "Smart reminders per plant".
- CTA (trial): "Start my free week" / "Try 7 days free". (No trial): "Subscribe for $X.XX/year".
- Transparency: "Today: full access, $0" → "Day 5: reminder" → "Day 7: $29.99/year starts. Cancel anytime before."

## Template data contract

Every template marks: `data-role="cta-primary"`, `data-role="cta-secondary"`, `data-required="close|price|billing-period|trial-terms|auto-renew|cancel-info|restore|terms|privacy"`, `data-role="price-equivalent"`, `data-fit` (auto-shrink text), `data-box` (container used for overflow checks). Keep these attributes if you customize a template, or the checks will fail.
