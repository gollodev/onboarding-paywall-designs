# Conversion principles

Use these to justify every decision in `conversion-strategy.md` (one sentence each).

## Principles

1. **Outcome clarity** — Headline states the result the user wants ("Keep every plant alive"), not the feature list. Benefits are outcomes + the feature that delivers them.
2. **Personalization echo** — Answers from onboarding re-appear on the bridge and paywall ("Based on your goal: fewer lost plants"). Commitment & consistency: the user already said what they want.
3. **Show value before asking** — A quick demo or "aha" preview before the paywall. Paywall after a value moment converts better than a cold paywall.
4. **Price anchoring** — Show monthly next to annual so the annual saving is concrete. Savings % = `1 − annual / (monthly × 12)`, rounded **down**. Only computed from real prices.
5. **Risk reversal** — Free trial, "cancel anytime", reminder before charge, timeline of what happens. Reduces fear of unexpected charges.
6. **Visual hierarchy** — One focal point per screen: headline → benefits → plan → CTA. Recommended plan highlighted with border + badge, not by hiding the others.
7. **One main path** — One primary CTA. Secondary actions (restore, close, "not now") visible but quieter.
8. **Social proof (real only)** — Store rating + count, user counts, testimonials with permission, press with rights. If none exist: omit the block and add to `pending.md`.
9. **Cognitive ease** — ≤ 5 benefits, short lines, plain words, numbers instead of adjectives (only real numbers).
10. **Honest urgency only** — Countdown or "offer ends" only if the offer truly expires (`config.urgency.real = true` with an end condition).

## Objection → design element

| Objection | Design answer |
|-----------|---------------|
| "Too expensive" | Annual per-month equivalent (secondary), savings vs monthly, value framing tied to user goal |
| "I don't trust it / will I be charged by surprise?" | Trial timeline with reminder day, "We'll remind you before your trial ends", visible price and cancel info |
| "I don't need it yet" | Personalized outcome headline, bridge screen showing their plan, free tier stays available ("Continue with free") |
| "I'll forget to cancel" | Reminder notification promise (only if the app really sends it), cancel instructions |
| "Is it worth it vs free?" | Free vs Premium comparison of real features |
| "Does it work?" | Real ratings/testimonials, demo of the aha moment |

## A/B hypotheses (pick 2–3 per paywall)

Format: **Change** → **Expected effect** → **Primary metric** (install→trial, trial→paid, paywall view→purchase, D30 retention).

- Headline: outcome vs. personalized goal echo → paywall CVR.
- Highlighted plan: annual vs monthly → trial start rate vs. revenue per user.
- Benefit order: emotional outcome first vs. top feature first → paywall CVR.
- CTA copy: "Start free trial" vs "Try 7 days free" vs "Continue" → trial start rate (note: "Continue" can be ambiguous; prefer explicit).
- Trial timeline present vs absent → trial→paid and refund rate.
- Placement: end of onboarding vs after first value moment → install→trial.

## Forbidden (dark patterns) — never design these

- Hidden, delayed, tiny, low-contrast, or fake close buttons.
- Unclear charges: price smaller than per-week/per-month equivalents, missing billing period, missing renewal notice.
- Fake scarcity, fake countdown timers, "only 3 left", fake "offer ends today".
- Invented testimonials, ratings, user counts, press mentions, "#1 app" claims.
- Free trial that hides the price after the trial.
- Misleading buttons: "Continue" that starts a purchase without saying so; pre-checked add-ons; confirmshaming ("No, I like losing my plants").
- Trick toggles ("Enable free trial" switches that change the price shown).
