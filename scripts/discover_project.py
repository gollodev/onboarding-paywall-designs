#!/usr/bin/env python3
"""Phase 1 — explore an app project and write project-brief.md (+ discovery.json, brand.json).

Usage:
  discover_project.py --project <root> --out paywall-designs

Reads README, manifests (package.json, app.json, pubspec.yaml, Info.plist, AndroidManifest.xml, build.gradle),
navigation/routes, screen files, i18n strings, tests, payment SDKs, product IDs and .storekit files.
Every finding carries its source ("path:line"). Anything inferred is tagged [ASSUMPTION]; anything
unknown is tagged [TO CONFIRM]. The agent must then read the cited files and refine the brief.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_json  # noqa: E402
from extract_brand import iter_files, read, extract as extract_brand  # noqa: E402

PAY_SDKS = OrderedDict([
    ("RevenueCat", [r"react-native-purchases", r"purchases_flutter", r"RevenueCat", r"com\.revenuecat", r"Purchases\.configure"]),
    ("StoreKit", [r"import StoreKit", r"SKProduct", r"Product\.products\(", r"\.storekit\b"]),
    ("Google Play Billing", [r"com\.android\.billingclient", r"BillingClient"]),
    ("Stripe", [r"@stripe/", r"stripe-react-native", r"flutter_stripe", r"com\.stripe", r"import Stripe"]),
    ("react-native-iap", [r"react-native-iap"]), ("expo-in-app-purchases", [r"expo-in-app-purchases"]),
    ("in_app_purchase (Flutter)", [r"in_app_purchase:"]), ("Adapty", [r"adapty"]), ("Qonversion", [r"qonversion"]),
    ("Superwall", [r"superwall"]),
])
STACKS = [
    ("Expo / React Native", lambda f: "expo" in f.get("deps", "")),
    ("React Native", lambda f: "react-native" in f.get("deps", "")),
    ("Flutter", lambda f: f.get("pubspec")),
    ("iOS native (Swift/SwiftUI)", lambda f: f.get("swift")),
    ("Android native (Kotlin/Java)", lambda f: f.get("kotlin")),
    ("Capacitor / Ionic", lambda f: "@capacitor" in f.get("deps", "")),
    ("Web (React/Next/Vue)", lambda f: any(k in f.get("deps", "") for k in ('"next"', '"react-dom"', '"vue"'))),
]
SCREEN_FILE_RE = re.compile(r"(Screen|Page|View|Activity|Fragment|_screen|_page|_view)\.(tsx|ts|jsx|js|swift|kt|java|dart|vue)$")
ROUTE_RES = [
    re.compile(r"<\w*\.?Screen\s+name=[\"']([^\"']+)[\"']"),
    re.compile(r"composable\(\s*(?:route\s*=\s*)?\"([^\"]+)\""),
    re.compile(r"GoRoute\(\s*path:\s*'([^']+)'"),
    re.compile(r"path:\s*[\"'](/[^\"']*)[\"']"),
    re.compile(r"NavigationLink\([^)]*destination:\s*(\w+)"),
]
PREMIUM_RE = re.compile(r"\b(premium|isPro|is_pro|pro_?user|paywall|subscription|subscribe|entitlement|unlock|locked|"
                        r"upgrade|plus\b|free_limit|freeLimit|maxFree|MAX_FREE|isSubscribed)\b", re.I)
PRODUCT_RE = re.compile(r"[\"']([a-z0-9_]+(?:\.[a-z0-9_]+){1,6})[\"']")
PRODUCT_HINT = re.compile(r"(month|year|annual|anual|week|seman|lifetime|vitalic|premium|pro|plus|sub)", re.I)
PRICE_RE = re.compile(r"(?:[\$€£]|US\$|R\$)\s?\d{1,4}(?:[.,]\d{2})|\d{1,4}[.,]\d{2}\s?(?:€|USD|EUR|MXN)")
TEST_RE = re.compile(r"\b(?:it|test|describe)\(\s*[\"'`]([^\"'`]{6,120})[\"'`]|func (test\w+)\(|fun `([^`]+)`")
LOCALE_DIR_RE = re.compile(r"(?:^|/)(?:locales?|i18n|lang|translations|l10n)/([a-z]{2}(?:[-_][A-Z]{2})?)(?:\.json|/)")
LANG_FILE_RES = [re.compile(r"values-([a-z]{2})(?:-r[A-Z]{2})?/strings\.xml$"), re.compile(r"([a-z]{2}(?:-[A-Z]{2})?)\.lproj/"),
                 re.compile(r"app_([a-z]{2}(?:_[A-Z]{2})?)\.arb$")]


def ln(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def cite(root: Path, p: Path, text: str = "", idx: int = 0) -> str:
    return f"{p.relative_to(root).as_posix()}:{ln(text, idx) if text else 1}"


def first_match(text: str, pattern: str):
    m = re.search(pattern, text, re.M)
    return m


def discover(root: Path) -> dict:
    files = list(iter_files(root))
    rel = {p: p.relative_to(root).as_posix() for p in files}
    d: dict = {"project": str(root), "app_name": None, "app_name_candidates": [], "stack": [], "platforms": [],
               "problem": None, "features_readme": [], "screens": [], "routes": [], "tests": [],
               "premium_signals": [], "payment_sdks": [], "products": [], "prices_found": [],
               "languages": [], "strings_sample": [], "store_hints": []}
    flags: dict = {"deps": ""}
    readme = next((p for p in files if p.name.lower() in ("readme.md", "readme") and len(p.relative_to(root).parts) == 1), None)

    def add_name(value, source, prio):
        if value and isinstance(value, str) and "$(" not in value and "@string" not in value:
            d["app_name_candidates"].append({"value": value.strip(), "source": source, "priority": prio})

    for p in files:
        r = rel[p]
        name = p.name
        text = None
        if name == "app.json" or name == "app.config.json":
            text = read(p)
            try:
                j = json.loads(text)
                e = j.get("expo", j)
                add_name(e.get("name"), cite(root, p, text, text.find('"name"')), 1)
                if e.get("ios", {}).get("bundleIdentifier"):
                    d["store_hints"].append({"value": f"iOS bundle id {e['ios']['bundleIdentifier']}", "source": cite(root, p, text, text.find("bundleIdentifier"))})
                if e.get("android", {}).get("package"):
                    d["store_hints"].append({"value": f"Android package {e['android']['package']}", "source": cite(root, p, text, text.find('"package"'))})
                if e.get("userInterfaceStyle"):
                    d["store_hints"].append({"value": f"userInterfaceStyle={e['userInterfaceStyle']}", "source": cite(root, p, text, text.find("userInterfaceStyle"))})
            except ValueError:
                pass
        elif name == "package.json" and "node_modules" not in r:
            text = read(p)
            try:
                j = json.loads(text)
                deps = {**j.get("dependencies", {}), **j.get("devDependencies", {})}
                flags["deps"] += json.dumps(deps)
                add_name(j.get("displayName"), cite(root, p, text, text.find('"displayName"')), 2)
                add_name(j.get("name"), cite(root, p, text, text.find('"name"')), 6)
                if j.get("description") and not d["problem"]:
                    d["problem"] = {"value": j["description"], "source": cite(root, p, text, text.find('"description"'))}
            except ValueError:
                pass
        elif name == "pubspec.yaml":
            text = read(p)
            flags["pubspec"] = True
            flags["deps"] += text
            m = first_match(text, r"^name:\s*(\S+)")
            if m:
                add_name(m.group(1), cite(root, p, text, m.start()), 5)
            m = first_match(text, r"^description:\s*[\"']?(.+?)[\"']?$")
            if m and not d["problem"]:
                d["problem"] = {"value": m.group(1), "source": cite(root, p, text, m.start())}
        elif name == "Info.plist":
            text = read(p)
            m = re.search(r"<key>CFBundleDisplayName</key>\s*<string>([^<]+)</string>", text)
            if m:
                add_name(m.group(1), cite(root, p, text, m.start()), 1)
            for m in re.finditer(r"<key>CFBundleLocalizations</key>\s*<array>(.*?)</array>", text, re.S):
                for lm in re.finditer(r"<string>([^<]+)</string>", m.group(1)):
                    d["languages"].append({"value": lm.group(1), "source": cite(root, p, text, m.start())})
        elif name == "strings.xml" and "/values/" in f"/{r}":
            text = read(p)
            m = re.search(r'<string name="app_name">([^<]+)</string>', text)
            if m:
                add_name(m.group(1), cite(root, p, text, m.start()), 2)
        elif name in ("build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts"):
            text = read(p)
            flags["kotlin"] = True
            flags["deps"] += text
            m = re.search(r"rootProject\.name\s*=\s*[\"']([^\"']+)", text)
            if m:
                add_name(m.group(1), cite(root, p, text, m.start()), 7)
        elif name.endswith(".storekit"):
            text = read(p)
            try:
                j = json.loads(text)
                for grp in j.get("subscriptionGroups", []):
                    for sub in grp.get("subscriptions", []):
                        d["products"].append({"id": sub.get("productID"), "price": _num(sub.get("displayPrice")),
                                              "period": sub.get("recurringSubscriptionPeriod"),
                                              "trial": (sub.get("introductoryOffer") or {}).get("subscriptionPeriod"),
                                              "source": cite(root, p, text, text.find(sub.get("productID") or ""))})
                for prod in j.get("products", []):
                    d["products"].append({"id": prod.get("productID"), "price": _num(prod.get("displayPrice")),
                                          "period": prod.get("type"), "source": cite(root, p, text, text.find(prod.get("productID") or ""))})
            except ValueError:
                pass
        if p.suffix == ".swift":
            flags["swift"] = True
        if p.suffix in (".kt", ".java"):
            flags["kotlin"] = True
        # screens
        if SCREEN_FILE_RE.search(name) and "test" not in r.lower():
            d["screens"].append({"value": re.sub(SCREEN_FILE_RE, r"\1", name), "file": p.stem, "source": f"{r}:1"})
        elif re.search(r"(^|/)(app|pages|screens|views|routes)/", r) and p.suffix in (".tsx", ".jsx", ".vue", ".svelte") \
                and not name.startswith("_") and "test" not in r.lower() and "components" not in r:
            d["screens"].append({"value": p.stem, "file": p.stem, "source": f"{r}:1"})
        # languages
        m = LOCALE_DIR_RE.search(r)
        if m:
            d["languages"].append({"value": m.group(1).replace("_", "-"), "source": f"{r}:1"})
        for lre in LANG_FILE_RES:
            m = lre.search(r)
            if m:
                d["languages"].append({"value": m.group(1).replace("_", "-"), "source": f"{r}:1"})
        if p.suffix.lower() not in (".ts", ".tsx", ".js", ".jsx", ".swift", ".kt", ".java", ".dart", ".json", ".vue",
                                    ".xml", ".strings", ".arb", ".yaml", ".yml", ".gradle", ".kts", ".plist", ".md", ".py"):
            continue
        text = text if text is not None else read(p)
        if not text:
            continue
        for sdk, pats in PAY_SDKS.items():
            for pat in pats:
                m = re.search(pat, text)
                if m and not any(s["value"] == sdk for s in d["payment_sdks"]):
                    d["payment_sdks"].append({"value": sdk, "source": cite(root, p, text, m.start())})
        is_code = p.suffix not in (".md", ".json") or "locale" in r or "i18n" in r
        if is_code:
            for rre in ROUTE_RES:
                for m in rre.finditer(text):
                    d["routes"].append({"value": m.group(1), "source": cite(root, p, text, m.start())})
            for m in PREMIUM_RE.finditer(text):
                line_start = text.rfind("\n", 0, m.start()) + 1
                line_end = text.find("\n", m.end())
                snippet = text[line_start:line_end if line_end > 0 else None].strip()[:140]
                where = cite(root, p, text, m.start())
                if len(d["premium_signals"]) < 60 and snippet and not any(x["source"] == where for x in d["premium_signals"]):
                    d["premium_signals"].append({"value": snippet, "source": where})
            for m in PRODUCT_RE.finditer(text):
                pid = m.group(1)
                if PRODUCT_HINT.search(pid) and not re.search(r"\.(png|svg|json|js|ts|tsx|css|com/|io/)$", pid) \
                        and not pid.startswith(("react", "expo", "com.android", "androidx", "org.", "io.flutter")) \
                        and not any(x["id"] == pid for x in d["products"]):
                    d["products"].append({"id": pid, "price": None, "source": cite(root, p, text, m.start())})
            for m in PRICE_RE.finditer(text):
                if len(d["prices_found"]) < 20:
                    d["prices_found"].append({"value": m.group(0), "source": cite(root, p, text, m.start())})
        if "test" in r.lower() or "spec" in r.lower():
            for m in TEST_RE.finditer(text):
                v = next(g for g in m.groups() if g)
                d["tests"].append({"value": v, "source": cite(root, p, text, m.start())})

    # README
    if readme:
        text = read(readme)
        m = re.search(r"^#\s+(.+)$", text, re.M)
        if m:
            add_name(re.sub(r"[*_`]", "", m.group(1)).split(" — ")[0].split(" - ")[0], cite(root, readme, text, m.start()), 3)
        paras = [(pm.group(0), pm.start()) for pm in re.finditer(r"(?m)^(?![#>\-*!\[|<`\s]).{40,}$", text)]
        if paras:
            d["problem"] = {"value": paras[0][0].strip(), "source": cite(root, readme, text, paras[0][1])}
        fm = re.search(r"(?im)^#+\s*(features|funciones|características|caracteristicas|what it does|qué hace)\s*$", text)
        if fm:
            block = text[fm.end():]
            nxt = re.search(r"(?m)^#", block)
            block = block[:nxt.start()] if nxt else block
            for bm in re.finditer(r"(?m)^[ \t]*[-*][ \t]+(.+)$", block):
                d["features_readme"].append({"value": bm.group(1).strip(), "source": cite(root, readme, text, fm.end() + bm.start())})
    # strings sample (main locale file)
    for p in files:
        r = rel[p]
        if p.suffix == ".json" and LOCALE_DIR_RE.search(r):
            try:
                j = json.loads(read(p))
            except ValueError:
                continue
            flat = _flatten(j)
            d["strings_sample"] = [{"key": k, "value": v, "source": f"{r}:1"} for k, v in list(flat.items())[:40]]
            break
    d["stack"] = [name for name, test in STACKS if test(flags)]
    if "Expo / React Native" in d["stack"] and "React Native" in d["stack"]:
        d["stack"].remove("React Native")
    plats = set()
    if any(s in d["stack"] for s in ("Expo / React Native", "React Native", "Flutter", "Capacitor / Ionic")):
        plats |= {"iOS", "Android"}
    if flags.get("swift"):
        plats.add("iOS")
    if flags.get("kotlin"):
        plats.add("Android")
    d["platforms"] = sorted(plats)
    d["app_name_candidates"].sort(key=lambda c: c["priority"])
    d["app_name"] = d["app_name_candidates"][0] if d["app_name_candidates"] else None
    d["languages"] = list({l["value"]: l for l in d["languages"]}.values())
    d["screens"] = list({s["value"]: s for s in d["screens"]}.values())[:40]
    d["routes"] = list({r["value"]: r for r in d["routes"]}.values())[:40]
    d["tests"] = d["tests"][:30]
    return d


def _num(v):
    if v is None:
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def _flatten(j, prefix=""):
    out = {}
    if isinstance(j, dict):
        for k, v in j.items():
            out.update(_flatten(v, f"{prefix}{k}."))
    elif isinstance(j, str):
        out[prefix.rstrip(".")] = j
    return out


def row(label, item, fallback="[TO CONFIRM]"):
    if not item:
        return f"| {label} | {fallback} | — |"
    return f"| {label} | {item['value']} | `{item['source']}` |"


def esc(s: str) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def write_brief(d: dict, b: dict, out: Path) -> Path:
    L = [f"# Project brief — {d['app_name']['value'] if d['app_name'] else '[TO CONFIRM]'}", "",
         "> Auto-generated by `discover_project.py`. **The agent must review it**: open the cited files, fix mistakes,",
         "> fill gaps, and keep every statement either cited (`path:line`) or tagged **[ASSUMPTION]** / **[TO CONFIRM]**.", "",
         "## 1. App", "", "| Field | Value | Source |", "|---|---|---|",
         row("Name", d["app_name"]),
         f"| Other name candidates | {esc(', '.join(c['value'] for c in d['app_name_candidates'][1:5])) or '—'} | — |",
         f"| Platform(s) | {', '.join(d['platforms']) or '[TO CONFIRM]'} | [ASSUMPTION] inferred from stack |",
         f"| Stack | {', '.join(d['stack']) or '[TO CONFIRM]'} | manifests (package.json / pubspec / gradle / swift files) |",
         row("Problem it solves", {"value": esc(d["problem"]["value"]), "source": d["problem"]["source"]} if d["problem"] else None), "",
         "## 2. Main screens & features", "", "| Screen / feature | Evidence | Source |", "|---|---|---|"]
    for s in d["screens"]:
        L.append(f"| {esc(s['value'])} | screen file | `{s['source']}` |")
    for r in d["routes"][:20]:
        L.append(f"| {esc(r['value'])} | route / navigation | `{r['source']}` |")
    for f in d["features_readme"]:
        L.append(f"| {esc(f['value'])} | README feature | `{f['source']}` |")
    for t in d["tests"][:12]:
        L.append(f"| {esc(t['value'])} | test name | `{t['source']}` |")
    if not (d["screens"] or d["routes"] or d["features_readme"]):
        L.append("| [TO CONFIRM] | no screens found automatically | — |")
    L += ["", "## 3. Free vs premium", "",
          "Signals found in code (the agent must interpret them; anything unclear stays **[TO CONFIRM]**):", "",
          "| Snippet | Source |", "|---|---|"]
    for s in d["premium_signals"][:25]:
        L.append(f"| `{esc(s['value'])}` | `{s['source']}` |")
    if not d["premium_signals"]:
        L.append("| No premium/paywall signals found — free vs premium split is **[TO CONFIRM]** | — |")
    pal = b.get("palette_suggestion", {})
    psrc = b.get("palette_sources", {})
    L += ["", "## 4. Visual identity", "", "| Item | Value | Source |", "|---|---|---|",
          f"| Logo | {b.get('logo') or '[TO CONFIRM] not found (monogram will be used)'} | "
          f"{'`' + b['logo_candidates'][0]['path'] + '`' if b.get('logo_candidates') else '—'} |"]
    for theme in ("light", "dark"):
        for role, hx in pal.get(theme, {}).items():
            L.append(f"| Color {theme}.{role} | `{hx}` | `{psrc.get(theme, {}).get(role, '—')}` |")
    if not pal.get("light"):
        L.append("| Palette | [TO CONFIRM] no theme colors found | — |")
    for c in b.get("colors_frequent", [])[:6]:
        L.append(f"| Frequent color | `{c['hex']}` ×{c['count']} | `{c['source']}` |")
    for f in b.get("fonts_used", [])[:4]:
        L.append(f"| Font used | {esc(f['family'])} ×{f['count']} | `{f['source']}` |")
    L.append(f"| Fonts for designs | heading **{b.get('font_heading_bundled')}**, body **{b.get('font_body_bundled')}** "
             f"(bundled) | {esc('; '.join(b.get('font_notes') or [])) or 'exact match'} |")
    L.append(f"| Light / dark | {'dark mode signals found' if b.get('dark_mode_evidence') else '[TO CONFIRM] no dark mode found'} | "
             f"{', '.join('`' + e + '`' for e in b.get('dark_mode_evidence', [])[:3]) or '—'} |")
    for i in b.get("icon_style", [])[:3]:
        L.append(f"| Icon style | {i['library']} | `{i['source']}` |")
    L.append("| Copy tone | [AGENT] describe from the strings sample below | strings files |")
    L += ["", "## 5. Payments", "", "| Item | Value | Source |", "|---|---|---|"]
    for s in d["payment_sdks"]:
        L.append(f"| SDK | {s['value']} | `{s['source']}` |")
    if not d["payment_sdks"]:
        L.append("| SDK | [TO CONFIRM] none detected | — |")
    for pr in d["products"][:10]:
        L.append(f"| Product ID | `{pr['id']}`{' · price ' + str(pr['price']) if pr.get('price') else ''}"
                 f"{' · ' + str(pr.get('period')) if pr.get('period') else ''} | `{pr['source']}` |")
    for pr in d["prices_found"][:8]:
        L.append(f"| Price literal | {esc(pr['value'])} | `{pr['source']}` [ASSUMPTION: confirm it is the real store price] |")
    if not d["products"]:
        L.append("| Product IDs / prices | [TO CONFIRM] | — |")
    L += ["", "## 6. Languages & markets", "", "| Item | Value | Source |", "|---|---|---|"]
    for l in d["languages"]:
        L.append(f"| Language | {l['value']} | `{l['source']}` |")
    if not d["languages"]:
        L.append("| Language | [TO CONFIRM] | — |")
    L.append("| Likely markets | [ASSUMPTION] derived from languages above — confirm with the user | — |")
    for h in d["store_hints"]:
        L.append(f"| Store hint | {esc(h['value'])} | `{h['source']}` |")
    if d["strings_sample"]:
        L += ["", "### Strings sample (for copy tone)", "", "| Key | Text | Source |", "|---|---|---|"]
        for s in d["strings_sample"][:20]:
            L.append(f"| `{s['key']}` | {esc(s['value'])} | `{s['source']}` |")
    L += ["", "## 7. Open questions for Phase 2", "",
          "- [AGENT] list only what the code could not answer (see references/questions-bank.md).", ""]
    # Never overwrite a brief the agent already reviewed.
    target = out / "project-brief.md"
    if target.exists():
        target = out / "project-brief.auto.md"
    target.write_text("\n".join(L), encoding="utf-8")
    return target


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".")
    ap.add_argument("--out", default="paywall-designs")
    a = ap.parse_args()
    root = Path(a.project).resolve()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    d = discover(root)
    b = extract_brand(root)
    if b.get("logo_abs"):
        b["logo"] = os.path.relpath(b.pop("logo_abs"), out)
    d["project"] = os.path.relpath(root, out)
    write_json(out / "discovery.json", d)
    write_json(out / "brand.json", b)
    brief = write_brief(d, b, out)
    print(f"{brief.name}, discovery.json, brand.json → {out}")
    if brief.name != "project-brief.md":
        print("project-brief.md already exists (reviewed) — fresh scan written to project-brief.auto.md; merge what changed.")
    print(f"App: {d['app_name']['value'] if d['app_name'] else '?'} | stack: {', '.join(d['stack']) or '?'} | "
          f"screens: {len(d['screens'])} | SDKs: {', '.join(s['value'] for s in d['payment_sdks']) or 'none'} | "
          f"products: {len(d['products'])} | languages: {', '.join(l['value'] for l in d['languages']) or '?'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
