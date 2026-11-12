# Store rules — mandatory paywall elements

> **Indicative checklist only.** Store policies change. Before publishing, confirm against the current
> Apple App Store Review Guidelines (section 3.1.2 Subscriptions, 3.1.1 In-App Purchase), Apple's
> Human Interface Guidelines (In-app purchase), and Google Play's Subscriptions policy and
> Payments policy. This skill produces design images; legal compliance is the app owner's responsibility.

## Checklist (enforced by `quality_checks.py` on every paywall)

| # | Element | `data-required` key | What must be visible |
|---|---------|---------------------|----------------------|
| 1 | Close / dismiss | `close` | Visible close button (≥ 24 CSS px icon, ≥ 3:1 contrast, not faded, in a corner). If the paywall is a hard paywall by design, document it in the strategy; the image still shows a way back. |
| 2 | Price | `price` | Full billed amount per plan in local currency (e.g. "$29.99"). The **billed amount must be the most prominent price**; per-month equivalents are smaller and secondary. |
| 3 | Billing period | `billing-period` | "per year", "/month", "one-time" next to each price. |
| 4 | Trial terms (if any trial) | `trial-terms` | Trial length **and** when/what will be charged: "7 days free, then $29.99/year. You'll be charged on day 7 unless you cancel." |
| 5 | Auto-renewal notice | `auto-renew` | "Subscription renews automatically unless cancelled at least 24 hours before the end of the current period." |
| 6 | How to cancel | `cancel-info` | "Cancel anytime in Settings › Subscriptions" (iOS) / "Play Store › Subscriptions" (Android). |
| 7 | Restore purchases | `restore` | "Restore purchases" link/button (required on iOS; recommended on Android). |
| 8 | Terms of use | `terms` | Link text to Terms (EULA). URL in `config.legal.terms_url`. |
| 9 | Privacy policy | `privacy` | Link text to Privacy Policy. URL in `config.legal.privacy_url`. |
| 10 | Single primary CTA | `cta-primary` (role) | Fully visible without scrolling, ≥ 48 CSS px tall, text describes the action ("Start free trial", "Subscribe for $29.99/year"). |

Missing URLs → shown as link text anyway, and listed in `pending.md`.

## Copy guidance

- CTA with a trial: "Start my 7-day free trial" (the price stays visible right next to it).
- Never say "Free" alone when a charge follows; always pair with the post-trial price.
- Lifetime/one-time purchases: state "one-time payment, no subscription"; restore still required.
- Introductory/discount offers: show original and discounted price, the duration of the discount, and the price after it ends.
- Family sharing, upgrades/downgrades, and regional pricing: confirm with the app owner; mark `[TO CONFIRM]`.

## Platform notes (confirm in current docs)

- **iOS**: Apple requires clear disclosure of what users get for the price, subscription length, and price; links to Terms of Use (EULA) and Privacy Policy in the app (and in App Store metadata); a way to restore purchases.
- **Android / Google Play**: Clear disclosure of price, billing frequency, free-trial length and what happens after; easy cancellation information; no misleading offer presentation.
- Both stores reject misleading designs (hidden close buttons, confusing pricing, fake urgency).
