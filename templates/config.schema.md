# config.json reference

Paths are relative to the folder containing `config.json`. Full working example: `examples/demo-app/paywall-designs/config.json`.
Any string may use `{{answers.<key>}}`, `{{app.name}}`, `{{plan.price}}` (highlighted plan) to echo personalization.

| Key | Type | Default | Notes |
|-----|------|---------|-------|
| `app.name` | string | — | App name as shown to users. |
| `app.logo` | path | null | SVG/PNG of the app's own logo. Missing → monogram with initials (never a third-party logo). |
| `app.premium_name` | string | "Premium" | Name of the paid tier ("Brotia Pro"), used in the trial timeline. |
| `locale` | string | "en" | `es`, `en` have default strings (`templates/i18n/`). Others: English defaults + override in `texts`. |
| `currency` | ISO code | "USD" | Symbol and format derived from it; override with `price_format`. |
| `price_format` | object | auto | `{ "pattern": "{symbol}{amount}", "decimal": ".", "thousands": ",", "symbol": "$", "decimals": 2 }`. |
| `devices` | list | `["iphone","android"]` | Strings `iphone` (1290×2796 @3x) / `android` (1080×2400 @2.5x) or objects `{ "id", "platform": "ios"|"android", "width", "height", "scale", "safe_top", "safe_bottom" }`. CSS viewport = size ÷ scale. |
| `themes` | list | `["light","dark"]` | |
| `frame` | object/bool | false | `{ "enabled": true, "background": "#EEF1F4" }` → generic unbranded phone frame (Pillow), same output size. |
| `show_placeholders` | bool | true | Show dashed "REAL SOCIAL PROOF PENDING" block; false hides the block. |
| `brand.font_heading` / `font_body` | string | Poppins / Inter | Non-bundled fonts map to the closest of Inter/Poppins/Manrope (noted in pending.md). |
| `brand.font_files` | list | [] | `[{ "family": "Gilroy", "path": "fonts/Gilroy.ttf", "weight": "400 800" }]` — only if the license allows it. |
| `brand.radius` | number | 20 | Corner radius in CSS px. |
| `brand.colors.light/dark` | object | defaults | Keys: `primary`, `accent`, `bg`, `surface`, `text`, `muted`, `border`, `success`. Missing dark palette is derived. Colors are nudged to reach WCAG AA (noted in pending.md). |
| `legal.terms_url` / `privacy_url` | string | null | Missing → link text still shown, listed in pending. |
| `trial.days` | int | null | Trial length for plans with `"trial": true`. |
| `trial.reminder_days_before` | int | null | Only if the app really sends a reminder; set `reminder_confirmed: true` once confirmed. |
| `plans[]` | list | — | `{ "id", "period": "year"|"month"|"week"|"lifetime", "price": 29.99 or null, "trial": bool, "label"?, "badge"?, "price_display"?, "product_id"? }`. `null` price → `$X.XX`. |
| `highlight_plan` | plan id | year plan | Recommended plan (border + check). Savings badge only when both year and month prices are real. |
| `social_proof` | object | empty | `{ "rating": 4.7, "rating_count": "1.2k", "users": "…", "testimonials": [{ "quote", "author" }], "press": [] }` — **real data only**. |
| `urgency.real` | bool | false | Countdown/urgency elements fail checks unless true. Use `data.urgency_text` on a paywall only for real, time-limited offers. |
| `answers` | object | {} | Personalization answers echoed in copy. |
| `texts` | object | {} | Override any default string key from `templates/i18n/<lang>.json` (e.g. `cta_trial`, `auto_renew`). |
| `screens[]` | list | — | `{ "id": "10-paywall-trial", "template": "paywall/trial-timeline", "data": {…}, "variants": [ … ] }`. |
| `screens[].variants[]` | list | [] | `{ "id": "B", "hypothesis": "…", "metric": "…", "set": { "data.headline": "…", "highlight_plan": "month" } }`. Keys starting with `data.` change the screen; others change the global config for that variant. |
| `pending_decisions` | list | [] | Decisions the user must confirm; copied into pending.md. |

## `data` per template

| Template | Keys |
|----------|------|
| onboarding/welcome | `headline`, `subhead`, `cta`, `secondary` |
| onboarding/benefit | `step`, `total`, `icon` or `image` (app screenshot), `eyebrow`, `headline`, `subhead`, `bullets[]`, `cta` |
| onboarding/personalization | `step`, `total`, `headline`, `subhead`, `options[{icon,label,selected}]`, `cta` |
| onboarding/permissions | `step`, `total`, `icon`, `headline`, `reason` (required), `preview_title`, `preview_text`, `preview_time`, `cta`, `secondary` (required "Not now") |
| onboarding/bridge | `step`, `total`, `eyebrow`, `headline`, `subhead`, `card_title`, `items[{icon,title,text}]`, `note`, `cta` |
| paywall/side-by-side | `eyebrow`, `headline`, `subhead`, `benefits[{icon,title,text}]` (≤3), `cta`? |
| paywall/trial-timeline | `eyebrow`, `headline`, `subhead`, `cta`? (timeline built from `trial`) |
| paywall/benefits-social | `eyebrow`, `headline`, `benefits[{title,text}]` (≤5), `cta`? |
| paywall/single-plan | `icon`?, `eyebrow`, `headline`, `subhead`, `benefits[{title,text}]`, `cta`? |

Paywall `cta` is optional: by default it is derived from the highlighted plan ("Start my 7-day free trial", "Subscribe for $4.99/month", "Buy for $59.99").
Icons: any file name in `assets/icons/` (Lucide subset, ISC license). Add more SVGs there if needed.
