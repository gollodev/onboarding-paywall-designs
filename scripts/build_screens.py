#!/usr/bin/env python3
"""Build HTML screens from config.json.

Usage:
  build_screens.py --work paywall-designs            # config.json -> output/html + manifest.json + pending.md
  build_screens.py --work paywall-designs --init     # create config.json skeleton from discovery.json/brand.json
  build_screens.py --config path/to/config.json      # explicit config (work dir = its folder)

Never invents data: missing prices become "$X.XX", missing social proof becomes a visible
placeholder (or is hidden with show_placeholders=false), and every gap is listed in pending.md.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    BUNDLED_FONTS, DEFAULT_DEVICES, ICONS_DIR, TEMPLATES_DIR, best_on, contrast, ensure_contrast, file_uri, floor2, interpolate_strings, mix, read_json,
    render_template, set_dotted, write_json,
)

PERIODS = ("year", "month", "week", "lifetime")
CURRENCY_SYMBOLS = {"USD": "$", "MXN": "$", "COP": "$", "ARS": "$", "CLP": "$", "CAD": "$", "AUD": "$",
                    "EUR": "€", "GBP": "£", "BRL": "R$", "PEN": "S/", "JPY": "¥", "INR": "₹"}
PRICE_PLACEHOLDER = "$X.XX"

# Closest bundled substitute for common app fonts.
FONT_SUBSTITUTES = {
    "Poppins": ["poppins", "montserrat", "futura", "gilroy", "avenir", "circular", "product sans", "nunito",
                "quicksand", "comfortaa", "gotham", "proxima", "sofia", "lexend", "raleway", "josefin"],
    "Manrope": ["manrope", "dm sans", "plus jakarta", "outfit", "sora", "urbanist", "work sans", "rubik",
                "space grotesk", "satoshi", "general sans", "figtree", "red hat", "be vietnam"],
    "Inter": ["inter", "sf pro", "san francisco", "-apple-system", "system", "roboto", "helvetica", "arial",
              "open sans", "lato", "source sans", "ibm plex", "noto sans", "segoe", "pt sans", "barlow"],
}

LIGHT_DEFAULTS = {"bg": "#FFFFFF", "surface": "#F4F5F7", "text": "#12151A", "muted": "#5A626C",
                  "border": "#E2E5EA", "primary": "#3B5BDB", "accent": "#F59F00", "success": "#2B8A3E"}
DARK_DEFAULTS = {"bg": "#0E1013", "surface": "#191C21", "text": "#F2F4F6", "muted": "#A4ABB5",
                 "border": "#2B3037", "accent": "#FFB938", "success": "#5CC27A"}


# --------------------------------------------------------------------------- helpers
def substitute_font(name: str | None, notes: list) -> str:
    if not name:
        return "Inter"
    if name in BUNDLED_FONTS:
        return name
    low = name.lower()
    for bundled, keys in FONT_SUBSTITUTES.items():
        if any(k in low for k in keys):
            notes.append(f"Font '{name}' is not bundled; using closest bundled font '{bundled}'.")
            return bundled
    notes.append(f"Font '{name}' is not bundled and has no known match; using 'Inter'. "
                 "Provide the font file (permissive license) in brand.font_files to use it.")
    return "Inter"


def fmt_amount(value: float, locale: str, currency: str, pf: dict | None) -> str:
    pf = pf or {}
    decimals = pf.get("decimals", 0 if currency in ("CLP", "JPY", "COP") else 2)
    dec_sep = pf.get("decimal", "," if (currency == "EUR" or locale.lower() in ("es-es", "pt-br", "de", "fr", "it")) else ".")
    thou_sep = pf.get("thousands", "." if dec_sep == "," else ",")
    amount = f"{value:,.{decimals}f}".replace(",", "\0").replace(".", dec_sep).replace("\0", thou_sep)
    symbol = pf.get("symbol", CURRENCY_SYMBOLS.get(currency, currency + " "))
    pattern = pf.get("pattern", "{amount} {symbol}" if currency == "EUR" else "{symbol}{amount}")
    return pattern.format(amount=amount, symbol=symbol, code=currency)


def tr(t: dict, key: str, **kw) -> str:
    s = t.get(key, key)
    kw.setdefault("premium", t.get("_premium", "Premium"))
    try:
        return s.format(**kw)
    except (KeyError, IndexError):
        return s


def load_icon(name: str) -> str:
    p = ICONS_DIR / f"{name}.svg"
    if not p.exists():
        return ""
    svg = p.read_text(encoding="utf-8")
    svg = re.sub(r"<!--.*?-->", "", svg, flags=re.S).strip()
    svg = re.sub(r'\s(width|height)="[^"]*"', "", svg, count=2)
    return svg.replace("<svg", '<svg aria-hidden="true" class="icon"', 1)


def resolve_icons(obj, missing: set):
    if isinstance(obj, dict):
        out = {k: resolve_icons(v, missing) for k, v in obj.items()}
        if isinstance(obj.get("icon"), str):
            svg = load_icon(obj["icon"])
            if not svg:
                missing.add(obj["icon"])
            out["icon_svg"] = svg
        return out
    if isinstance(obj, list):
        return [resolve_icons(x, missing) for x in obj]
    return obj


def resolve_path(base: Path, p: str | None) -> Path | None:
    if not p:
        return None
    path = Path(p)
    if not path.is_absolute():
        path = (base / path).resolve()
    return path if path.exists() else None


def build_palette(brand: dict, theme: str, notes: list) -> dict:
    colors = (brand.get("colors") or {})
    given = colors.get(theme) or {}
    if theme == "dark" and not given:
        light_primary = (colors.get("light") or {}).get("primary", LIGHT_DEFAULTS["primary"])
        given = {"primary": mix(light_primary, "#FFFFFF", 0.15)}
        notes.append("Dark palette derived automatically from the light brand colors (no dark theme found).")
    base = LIGHT_DEFAULTS if theme == "light" else {**DARK_DEFAULTS, "primary": LIGHT_DEFAULTS["primary"]}
    p = {**base, **{k: v for k, v in given.items() if v}}
    adjusted = []
    # Button fill must carry readable text: move primary until white or black reaches 4.5:1.
    on = best_on(p["primary"])
    if contrast(on, p["primary"]) < 4.5:
        newp = ensure_contrast(p["primary"], on, 4.5)
        adjusted.append(f"primary {p['primary']}→{newp} (button text contrast)")
        p["primary"] = newp
    p["on_primary"] = best_on(p["primary"])
    p["on_accent"] = best_on(p["accent"])
    surfaces = [p["bg"], p["surface"]]
    for key in ("text", "muted"):
        fixed = p[key]
        for s in surfaces:
            fixed = ensure_contrast(fixed, s, 4.6)
        if fixed.upper() != p[key].upper():
            adjusted.append(f"{key} {p[key]}→{fixed} (WCAG AA on background)")
            p[key] = fixed
    pt = p["primary"]
    for s in surfaces + [mix(p["bg"], p["primary"], 0.10)]:
        pt = ensure_contrast(pt, s, 4.6)
    p["primary_text"] = pt
    p["primary_soft"] = mix(p["bg"], p["primary"], 0.10)
    p["surface_2"] = mix(p["surface"], p["text"], 0.06)
    p["accent_text"] = ensure_contrast(p["accent"], p["bg"], 4.6)
    p["success_text"] = ensure_contrast(p["success"], p["surface"], 4.6)
    if adjusted:
        notes.append(f"[{theme}] colors adjusted for WCAG AA: " + "; ".join(adjusted))
    return p


def css_vars(p: dict, brand: dict, fonts: dict, device: dict) -> str:
    v = {
        "--bg": p["bg"], "--surface": p["surface"], "--surface-2": p["surface_2"], "--text": p["text"],
        "--muted": p["muted"], "--border": p["border"], "--primary": p["primary"], "--on-primary": p["on_primary"],
        "--primary-text": p["primary_text"], "--primary-soft": p["primary_soft"], "--accent": p["accent"],
        "--on-accent": p["on_accent"], "--accent-text": p["accent_text"], "--success": p["success"],
        "--success-text": p["success_text"], "--radius": f"{brand.get('radius', 20)}px",
        "--font-h": f"'{fonts['heading']}'", "--font-b": f"'{fonts['body']}'",
        "--safe-top": f"{device['safe_top']}px", "--safe-bottom": f"{device['safe_bottom']}px",
    }
    return ";".join(f"{k}:{val}" for k, val in v.items())


# --------------------------------------------------------------------------- plans
def build_plans(cfg: dict, t: dict, pending: list) -> tuple[list, dict | None]:
    locale, currency = cfg.get("locale", "en"), cfg.get("currency", "USD")
    pf = cfg.get("price_format")
    trial = cfg.get("trial") or {}
    trial_days = trial.get("days")
    plans_in = cfg.get("plans") or []
    by_period = {pl.get("period"): pl for pl in plans_in}
    month_price = (by_period.get("month") or {}).get("price")
    highlight_id = cfg.get("highlight_plan") or (by_period.get("year") or (plans_in[0] if plans_in else {})).get("id")
    out = []
    for pl in plans_in:
        period = pl.get("period")
        if period not in PERIODS:
            raise SystemExit(f"Plan '{pl.get('id')}': period must be one of {PERIODS}")
        price = pl.get("price")
        known = isinstance(price, (int, float))
        if not known:
            pending.append(f"Real price for plan '{pl.get('id')}' ({period}) — shown as {PRICE_PLACEHOLDER}.")
        price_display = pl.get("price_display") or (fmt_amount(price, locale, currency, pf) if known else PRICE_PLACEHOLDER)
        d = {
            "id": pl.get("id"), "period": period,
            "name": pl.get("label") or t[f"plan_name_{period}"],
            "price": price_display, "price_known": known,
            "period_label": t[f"per_{period}"], "billed": t[f"billed_{period}"],
            "highlighted": pl.get("id") == highlight_id,
            "product_id": pl.get("product_id"),
        }
        if period == "year" and known:
            d["equivalent"] = tr(t, "per_month_equiv", price=fmt_amount(floor2(price / 12), locale, currency, pf))
            if isinstance(month_price, (int, float)) and month_price > 0:
                pct = math.floor((1 - price / (month_price * 12)) * 100)
                if pct > 0:
                    d["save_pct"] = pct
                    d["badge"] = tr(t, "save_badge", pct=pct)
        if pl.get("badge"):
            d["badge"] = pl["badge"]
        if pl.get("trial") and trial_days:
            d["trial_days"] = trial_days
            d["trial_badge"] = tr(t, "trial_badge", days=trial_days)
        elif pl.get("trial") and not trial_days:
            pending.append(f"Plan '{pl.get('id')}' has trial=true but trial.days is missing.")
        out.append(d)
    hl = next((p for p in out if p["highlighted"]), out[0] if out else None)
    if hl:
        hl["highlighted"] = True
    return out, hl


def fine_print(cfg: dict, t: dict, plans: list, hl: dict | None, device: dict) -> dict:
    trial = cfg.get("trial") or {}
    fp: dict = {}
    if hl and hl.get("trial_days"):
        days = hl["trial_days"]
        fp["trial_terms"] = tr(t, "trial_terms", days=days, price=hl["price"], period=hl["period_label"])
        fp["no_payment_today"] = t["no_payment_today"]
        rem = trial.get("reminder_days_before")
        if rem:
            fp["reminder"] = tr(t, "reminder_line", n=rem)
        tl = [{"label": t["timeline_today"], "text": tr(t, "timeline_today_text"), "icon_svg": load_icon("lock-open")}]
        if rem and days - rem > 0:
            tl.append({"label": tr(t, "timeline_day", day=days - rem), "text": t["timeline_reminder_text"],
                       "icon_svg": load_icon("bell")})
        tl.append({"label": tr(t, "timeline_day", day=days),
                   "text": tr(t, "timeline_charge_text", price=hl["price"], period=hl["period_label"]),
                   "icon_svg": load_icon("calendar")})
        fp["timeline"] = tl
    all_lifetime = plans and all(p["period"] == "lifetime" for p in plans)
    fp["auto_renew"] = t["auto_renew_lifetime"] if all_lifetime else t["auto_renew"]
    if all_lifetime:
        fp["cancel"] = t["no_cancel_needed"]
    else:
        fp["cancel"] = t["cancel_ios"] if device["platform"] == "ios" else t["cancel_android"]
    if hl:
        if hl.get("trial_days"):
            fp["cta"] = tr(t, "cta_trial", days=hl["trial_days"])
        elif hl["period"] == "lifetime":
            fp["cta"] = tr(t, "cta_lifetime", price=hl["price"])
        else:
            fp["cta"] = tr(t, "cta_subscribe", price=hl["price"], period=hl["period_label"])
    return fp


def social_block(cfg: dict, t: dict, pending: list) -> dict:
    sp = cfg.get("social_proof") or {}
    out: dict = {"items": []}
    rating, count = sp.get("rating"), sp.get("rating_count")
    if rating:
        full = int(float(rating))
        half = (float(rating) - full) >= 0.5
        out["rating"] = {"value": rating, "stars": [{"on": i < full or (i == full and half)} for i in range(5)],
                         "label": tr(t, "rating_label", rating=rating, count=count) if count else str(rating)}
    if sp.get("users"):
        out["users"] = sp["users"]
    if sp.get("testimonials"):
        out["testimonials"] = sp["testimonials"][:2]
    if sp.get("press"):
        out["press"] = sp["press"]
    out["has"] = bool(out.get("rating") or out.get("users") or out.get("testimonials") or out.get("press"))
    if not out["has"]:
        pending.append("Real social proof (store rating + count, user count, testimonials with permission). "
                       "Block is hidden or shown as a placeholder until provided.")
        out["placeholder"] = bool(cfg.get("show_placeholders", True))
    return out


# --------------------------------------------------------------------------- devices / variants
def get_devices(cfg: dict) -> list[dict]:
    devs = []
    for d in cfg.get("devices") or ["iphone", "android"]:
        if isinstance(d, str):
            if d not in DEFAULT_DEVICES:
                raise SystemExit(f"Unknown device '{d}'. Use iphone/android or an object with width/height/scale/platform.")
            devs.append(dict(DEFAULT_DEVICES[d]))
        else:
            base = dict(DEFAULT_DEVICES.get(d.get("id"), DEFAULT_DEVICES["iphone" if d.get("platform") == "ios" else "android"]))
            base.update(d)
            devs.append(base)
    for d in devs:
        d["vw"] = round(d["width"] / d["scale"])
        d["vh"] = round(d["height"] / d["scale"])
        d["is_ios"] = d["platform"] == "ios"
        d["is_android"] = not d["is_ios"]
    return devs


def expand_variants(screen: dict, cfg: dict):
    yield "A", screen, cfg, None
    for v in screen.get("variants") or []:
        s2, c2 = copy.deepcopy(screen), copy.deepcopy(cfg)
        for path, val in (v.get("set") or {}).items():
            if path.startswith("data."):
                set_dotted(s2, path, val)
            else:
                set_dotted(c2, path, val)
        yield v.get("id", "B"), s2, c2, v


# --------------------------------------------------------------------------- main build
def build(work: Path, config_path: Path) -> dict:
    cfg = read_json(config_path)
    base = config_path.parent
    locale = cfg.get("locale", "en")
    lang = locale.split("-")[0].lower()
    i18n_file = TEMPLATES_DIR / "i18n" / f"{lang}.json"
    notes: list[str] = []
    if not i18n_file.exists():
        notes.append(f"No default strings for '{lang}'; using English defaults. Override them in config.texts.")
        i18n_file = TEMPLATES_DIR / "i18n" / "en.json"
    brand = cfg.get("brand") or {}
    fonts = {"heading": substitute_font(brand.get("font_heading"), notes),
             "body": substitute_font(brand.get("font_body"), notes)}
    font_faces = []
    for ff in brand.get("font_files") or []:
        fp = resolve_path(base, ff.get("path"))
        if fp:
            font_faces.append(f"@font-face{{font-family:'{ff['family']}';src:url('{file_uri(fp)}');"
                              f"font-weight:{ff.get('weight', '100 900')};font-style:{ff.get('style', 'normal')};}}")
            for role in ("heading", "body"):
                if brand.get(f"font_{role}") == ff["family"]:
                    fonts[role] = ff["family"]
                    notes[:] = [n for n in notes if f"'{ff['family']}'" not in n]
        else:
            notes.append(f"Font file not found: {ff.get('path')}")

    logo = resolve_path(base, (cfg.get("app") or {}).get("logo"))
    app = dict(cfg.get("app") or {})
    app["logo_uri"] = file_uri(logo) if logo else ""
    app["initials"] = "".join(w[0] for w in str(app.get("name", "App")).split()[:2]).upper()
    if not logo:
        notes.append("App logo not found; a monogram with the app initials is used instead.")

    out_dir = work / "output"
    html_dir = out_dir / "html"
    pages, missing_icons = [], set()
    pending_global: list[str] = []
    themes = cfg.get("themes") or ["light", "dark"]
    devices = get_devices(cfg)
    frame = cfg.get("frame") or {}
    if isinstance(frame, bool):
        frame = {"enabled": frame}
    fit_js = (TEMPLATES_DIR / "partials" / "fit.js").read_text(encoding="utf-8")
    legal = cfg.get("legal") or {}
    for key in ("terms_url", "privacy_url"):
        if not legal.get(key):
            pending_global.append(f"legal.{key} is missing (link text is shown; add the real URL).")
    trial = cfg.get("trial") or {}
    if trial.get("reminder_days_before") and not trial.get("reminder_confirmed"):
        pending_global.append("Confirm the app really sends a reminder before the trial ends "
                              "(the paywall promises it). Set trial.reminder_confirmed=true once confirmed.")

    screens = cfg.get("screens") or []
    if not screens:
        raise SystemExit("config.screens is empty")
    pending_plans: list[str] = []
    for screen in screens:
        tpl_name = screen["template"]
        tpl_path = TEMPLATES_DIR / f"{tpl_name}.html"
        if not tpl_path.exists():
            raise SystemExit(f"Template not found: {tpl_path}")
        kind = tpl_name.split("/")[0]
        for vid, s, c, vmeta in expand_variants(screen, cfg):
            t = {**read_json(i18n_file), "_premium": (c.get("app") or {}).get("premium_name") or "Premium",
                 **(c.get("texts") or {})}
            plist: list[str] = []
            plans, hl = build_plans(c, t, plist)
            social = social_block(c, t, plist)
            if kind == "paywall":
                pending_plans.extend(plist)
            for device in devices:
                fp = fine_print(c, t, plans, hl, device)
                for theme in themes:
                    pal = build_palette(c.get("brand") or brand, theme, notes)
                    ctx_base = {"app": app, "answers": c.get("answers") or {}, "t": t, "plan": hl or {},
                                "trial": c.get("trial") or {}}
                    data = interpolate_strings(s.get("data") or {}, ctx_base)
                    data = resolve_icons(data, missing_icons)
                    if "step" in data and "total" in data:
                        data["step_label"] = tr(t, "step", n=data["step"], total=data["total"])
                        data["progress_pct"] = round(100 * data["step"] / data["total"])
                        data["dots"] = [{"on": i < data["step"], "current": i == data["step"] - 1}
                                        for i in range(data["total"])]
                    img = resolve_path(base, data.get("image"))
                    if data.get("image") and not img:
                        notes.append(f"Image not found for {s['id']}: {data.get('image')}")
                    data["image_uri"] = file_uri(img) if img else ""
                    urgency = c.get("urgency") or {}
                    ctx = {
                        **ctx_base, "s": data, "plans": plans, "hl": hl or {}, "fine": fp, "social": social,
                        "legal": legal, "device": device, "theme": theme, "lang": lang,
                        "kind": kind, "screen_id": s["id"], "variant": vid,
                        "has_trial": bool(hl and hl.get("trial_days")),
                        "urgency_real": bool(urgency.get("real")),
                        "plans_count": len(plans),
                        "css_vars": css_vars(pal, brand, fonts, device),
                        "font_faces": "\n".join(font_faces),
                        "base_css": file_uri(TEMPLATES_DIR / "base.css"),
                        "fonts_css": file_uri(TEMPLATES_DIR / "fonts.css"),
                        "fit_js": fit_js,
                        "icons": {n: load_icon(n) for n in ("x", "check", "star", "circle-check", "lock", "sparkles", "bell")},
                        "frame": bool(frame.get("enabled")),
                    }
                    html = render_template(tpl_path.read_text(encoding="utf-8"), ctx, TEMPLATES_DIR / "partials")
                    name = s["id"] + ("" if vid == "A" else f"--{vid}")
                    html_path = html_dir / device["id"] / theme / f"{name}.html"
                    html_path.parent.mkdir(parents=True, exist_ok=True)
                    html_path.write_text(html, encoding="utf-8")
                    pages.append({
                        "screen": s["id"], "name": name, "template": tpl_name, "kind": kind, "variant": vid,
                        "hypothesis": (vmeta or {}).get("hypothesis"), "metric": (vmeta or {}).get("metric"),
                        "device": device["id"], "platform": device["platform"], "theme": theme,
                        "width": device["width"], "height": device["height"], "scale": device["scale"],
                        "vw": device["vw"], "vh": device["vh"],
                        "html": str(html_path.relative_to(work)),
                        "png": str((out_dir / device["id"] / theme / f"{name}.png").relative_to(work)),
                        "has_trial": ctx["has_trial"], "urgency_real": ctx["urgency_real"],
                        "frame": frame if frame.get("enabled") else None,
                    })
    if missing_icons:
        notes.append("Unknown icons (not in assets/icons): " + ", ".join(sorted(missing_icons)))
    manifest = {"work": str(work), "config": str(config_path), "pages": pages,
                "app": app.get("name"), "locale": locale}
    write_json(out_dir / "manifest.json", manifest)
    write_pending(work, cfg, list(dict.fromkeys(pending_plans + pending_global)), list(dict.fromkeys(notes)))
    return manifest


def scan_placeholders(cfg) -> list[str]:
    found = []

    def walk(o, path=""):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, f"{path}.{k}" if path else k)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}.{i}")
        elif isinstance(o, str) and ("[[" in o or PRICE_PLACEHOLDER in o):
            found.append(f"`{path}` = \"{o}\"")
    walk(cfg)
    return found


def write_pending(work: Path, cfg: dict, missing: list, notes: list) -> None:
    lines = ["# Pending items", "",
             "> Auto-generated by `build_screens.py` on every build. Edit `config.json` (not this file) to resolve.",
             "", "## Missing data (placeholders in the designs)", ""]
    ph = scan_placeholders({k: v for k, v in cfg.items() if k != "pending_decisions"})
    items = missing + [f"Placeholder text: {p}" for p in ph]
    lines += [f"- [ ] {m}" for m in items] or ["- None"]
    lines += ["", "## Decisions to confirm", ""]
    lines += [f"- [ ] {d}" for d in (cfg.get("pending_decisions") or [])] or ["- None"]
    lines += ["", "## Automatic adjustments (review)", ""]
    lines += [f"- {n}" for n in notes] or ["- None"]
    (work / "pending.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- init
def init_config(work: Path) -> Path:
    disc = read_json(work / "discovery.json") if (work / "discovery.json").exists() else {}
    brand_j = read_json(work / "brand.json") if (work / "brand.json").exists() else {}
    cfg_path = work / "config.json"
    if cfg_path.exists():
        raise SystemExit(f"{cfg_path} already exists; refusing to overwrite.")
    name = (disc.get("app_name") or {}).get("value") or "[[APP NAME]]"
    langs = [l["value"] for l in disc.get("languages", [])] or ["en"]
    colors = brand_j.get("palette_suggestion") or {}
    products = disc.get("products", [])
    plans = []
    for pr in products[:3]:
        pid = pr.get("id", "")
        period = "year" if re.search(r"year|annual|anual|12", pid, re.I) else \
                 "week" if re.search(r"week|seman", pid, re.I) else \
                 "lifetime" if re.search(r"life|vitalic|forever", pid, re.I) else "month"
        plans.append({"id": period, "product_id": pid, "period": period, "price": pr.get("price"),
                      "trial": period == "year"})
    if not plans:
        plans = [{"id": "year", "period": "year", "price": None, "trial": True},
                 {"id": "month", "period": "month", "price": None, "trial": False}]
    cfg = {
        "app": {"name": name, "logo": brand_j.get("logo")},
        "locale": langs[0], "currency": "USD", "devices": ["iphone", "android"], "themes": ["light", "dark"],
        "frame": {"enabled": False}, "show_placeholders": True,
        "brand": {"font_heading": brand_j.get("font_heading_bundled", "Poppins"),
                  "font_body": brand_j.get("font_body_bundled", "Inter"), "radius": 20,
                  "colors": {"light": colors.get("light", {}), "dark": colors.get("dark", {})}},
        "legal": {"terms_url": None, "privacy_url": None},
        "trial": {"days": None, "reminder_days_before": None, "reminder_confirmed": False},
        "plans": plans, "highlight_plan": "year",
        "social_proof": {"rating": None, "rating_count": None, "users": None, "testimonials": [], "press": []},
        "urgency": {"real": False},
        "answers": {"goal": "[[USER GOAL]]"},
        "texts": {},
        "screens": json.loads((TEMPLATES_DIR / "default-screens.json").read_text(encoding="utf-8")),
        "pending_decisions": ["Confirm audience, outcome and aha moment (Phase 2).",
                              "Confirm free vs premium split.", "Confirm real prices and trial length."],
    }
    write_json(cfg_path, cfg)
    return cfg_path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", default="paywall-designs", help="work folder (default: paywall-designs)")
    ap.add_argument("--config", help="config.json path (default: <work>/config.json)")
    ap.add_argument("--init", action="store_true", help="create config.json skeleton and exit")
    a = ap.parse_args()
    work = Path(a.work).resolve()
    if a.config:
        config_path = Path(a.config).resolve()
        if not a.work or a.work == "paywall-designs":
            work = config_path.parent
    else:
        config_path = work / "config.json"
    work.mkdir(parents=True, exist_ok=True)
    if a.init:
        print(f"Created {init_config(work)} — edit it, then run build_screens.py --work {work}")
        return 0
    if not config_path.exists():
        print(f"Config not found: {config_path}. Run with --init first.", file=sys.stderr)
        return 2
    m = build(work, config_path)
    print(f"Built {len(m['pages'])} HTML pages → {work / 'output' / 'html'}")
    print(f"Pending items → {work / 'pending.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
