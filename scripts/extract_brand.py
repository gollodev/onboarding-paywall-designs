#!/usr/bin/env python3
"""Extract visual identity evidence from an app project: logo, palette, fonts, light/dark, icon style.

Usage:
  extract_brand.py --project <root> [--out paywall-designs]   # writes <out>/brand.json
Every finding includes its source as "path:line". Nothing is invented: if a value is not found,
it is reported as missing so the agent can ask the user.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import hex_to_rgb, luminance, rgb_to_hex, write_json  # noqa: E402

SKIP_DIRS = {"node_modules", ".git", "build", "dist", "Pods", ".gradle", ".dart_tool", ".venv", "venv", "__pycache__",
             "DerivedData", ".next", ".expo", "vendor", ".idea", ".vscode", "coverage", ".claude", ".github",
             "paywall-designs", ".turbo", ".cache", "out", "target", "android/app/build"}
TEXT_EXT = {".ts", ".tsx", ".js", ".jsx", ".json", ".swift", ".kt", ".kts", ".java", ".dart", ".xml", ".css", ".scss",
            ".less", ".html", ".vue", ".svelte", ".md", ".yaml", ".yml", ".plist", ".strings", ".arb", ".gradle", ".m",
            ".storekit", ".txt", ".properties", ".toml", ".py", ".rb", ".cs"}
IMG_EXT = {".svg", ".png", ".jpg", ".jpeg", ".webp"}

HEX_RE = re.compile(r"(?<![\w&])#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-fA-F\w])")
ARGB_RE = re.compile(r"0x([fF]{2})([0-9a-fA-F]{6})\b")
NAMED_RE = re.compile(r"""["']?([A-Za-z_][\w\-]*)["']?\s*[:=]\s*["']?(?:Color\()?\s*["']?(#[0-9a-fA-F]{3,8}|0x[fF]{2}[0-9a-fA-F]{6})""")
XML_COLOR_RE = re.compile(r'<color\s+name="([^"]+)"\s*>\s*(#[0-9a-fA-F]{6,8})\s*<')
FONT_PATTERNS = [
    re.compile(r"fontFamily\s*[:=]\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"Font\.custom\(\s*\"([^\"]+)\""),
    re.compile(r"GoogleFonts\.([a-zA-Z]+)\("),
    re.compile(r"font-family\s*:\s*['\"]?([A-Za-z0-9 \-]+)"),
    re.compile(r"@expo-google-fonts/([a-z\-]+)"),
    re.compile(r"^\s*-\s*family:\s*([A-Za-z0-9 ]+)", re.M),
    re.compile(r"FontFamily\(\s*Font\(R\.font\.([a-z_]+)"),
]
GENERIC_FONTS = {"system-ui", "sans-serif", "serif", "monospace", "inherit", "-apple-system", "blinkmacsystemfont",
                 "system", "var", "initial"}
ICON_LIBS = {
    "lucide": "Lucide (outline, 2px stroke)", "@expo/vector-icons": "Expo vector icons (Ionicons/Material/Feather)",
    "react-native-vector-icons": "react-native-vector-icons", "heroicons": "Heroicons", "phosphor": "Phosphor",
    "tabler": "Tabler icons", "fontawesome": "Font Awesome", "feather": "Feather (outline)",
    "systemName:": "SF Symbols", "Image(systemName": "SF Symbols", "Icons.Filled": "Material Icons (Compose)",
    "Icons.Outlined": "Material Icons Outlined (Compose)", "Icons.": "Material Icons (Flutter)",
    "material-symbols": "Material Symbols", "CupertinoIcons": "Cupertino icons",
}
DARK_SIGNALS = ["useColorScheme", "userInterfaceStyle", "prefers-color-scheme", "ThemeMode.dark", "darkTheme",
                "isSystemInDarkTheme", "values-night", "\"luminosity\"", "Appearance.getColorScheme", "dark:"]


def iter_files(root: Path, limit: int = 8000):
    n = 0
    for p in root.rglob("*"):
        rel = p.relative_to(root).parts
        if any(part in SKIP_DIRS for part in rel[:-1]) or (p.is_dir()):
            continue
        n += 1
        if n > limit:
            break
        yield p


def read(p: Path) -> str:
    try:
        if p.stat().st_size > 1_500_000:
            return ""
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def norm_hex(h: str, argb: bool = False) -> str | None:
    """Normalize #RGB/#RRGGBB/#RRGGBBAA (CSS) or #AARRGGBB/0xAARRGGBB (Android/Flutter) to #RRGGBB."""
    h = h.strip()
    if h.lower().startswith("0x"):
        return "#" + h[4:].upper()
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) == 8:
        h = h[2:] if argb else h[:6]
    return "#" + h.upper() if len(h) == 6 else None


def colorset_component(v) -> float:
    v = str(v).strip()
    if v.lower().startswith("0x"):
        return int(v, 16)
    f = float(v)
    return f * 255 if ("." in v and f <= 1) else f


def saturation(hx: str) -> float:
    r, g, b = [c / 255 for c in hex_to_rgb(hx)]
    mx, mn = max(r, g, b), min(r, g, b)
    return 0 if mx == 0 else (mx - mn) / mx


def src(root: Path, p: Path, text: str, idx: int) -> str:
    return f"{p.relative_to(root).as_posix()}:{text.count(chr(10), 0, idx) + 1}"


def extract(root: Path, files: list[Path] | None = None) -> dict:
    root = root.resolve()
    files = files if files is not None else list(iter_files(root))
    logos, colors_named, color_counts, color_src = [], [], Counter(), {}
    fonts, font_files, dark, icons = Counter(), [], [], {}
    font_src: dict = {}
    for p in files:
        rel = p.relative_to(root).as_posix()
        low = rel.lower()
        ext = p.suffix.lower()
        if ext in IMG_EXT and re.search(r"(logo|brand|app[-_]?icon|ic_launcher|appicon|icon)", low):
            score = (3 if "logo" in low else 0) + (2 if ext == ".svg" else 0) + (1 if "appicon" in low or "ic_launcher" in low else 0)
            score -= 2 if re.search(r"(tab|nav|small|16|24|32|favicon)", low) else 0
            logos.append({"path": rel, "score": score, "size": p.stat().st_size})
        if ext in (".ttf", ".otf", ".woff", ".woff2"):
            fam = re.split(r"[-_ ](?:regular|bold|medium|light|semibold|black|thin|italic|variable|extrabold|\[)", p.stem, flags=re.I)[0]
            font_files.append({"family": fam, "path": rel})
        if "values-night" in low:
            dark.append(rel)
        if ext not in TEXT_EXT:
            continue
        text = read(p)
        if not text:
            continue
        if p.name == "Contents.json" and ".colorset" in low:
            try:
                data = json.loads(text)
                for c in data.get("colors", []):
                    comp = c.get("color", {}).get("components", {})
                    vals = [comp.get(k) for k in ("red", "green", "blue")]
                    if all(v is not None for v in vals):
                        hx = rgb_to_hex([colorset_component(v) for v in vals])
                        is_dark = any(a.get("value") == "dark" for a in c.get("appearances", []))
                        name = p.parent.name.replace(".colorset", "")
                        colors_named.append({"name": name + (" (dark)" if is_dark else ""), "hex": hx, "dark": is_dark,
                                             "source": f"{rel}:1"})
                        if is_dark:
                            dark.append(f"{rel}:1")
            except (ValueError, TypeError):
                pass
            continue
        is_theme = bool(re.search(r"(color|colour|theme|palette|token|tailwind|style|brand|\.css|\.scss|values)", low))
        for m in XML_COLOR_RE.finditer(text):
            colors_named.append({"name": m.group(1), "hex": norm_hex(m.group(2), argb=True), "dark": "night" in low,
                                 "source": src(root, p, text, m.start())})
        if is_theme:
            for m in NAMED_RE.finditer(text):
                hx = norm_hex(m.group(2))
                if hx:
                    ctx = text[max(0, m.start() - 160):m.start()].lower()
                    colors_named.append({"name": m.group(1), "hex": hx,
                                         "dark": "dark" in m.group(1).lower() or bool(re.search(r"dark\s*[:=]\s*\{[^}]*$", ctx)),
                                         "source": src(root, p, text, m.start())})
        for m in list(HEX_RE.finditer(text)) + list(ARGB_RE.finditer(text)):
            hx = norm_hex(m.group(0))
            if hx:
                color_counts[hx] += 2 if is_theme else 1
                color_src.setdefault(hx, src(root, p, text, m.start()))
        for fp in FONT_PATTERNS:
            for m in fp.finditer(text):
                fam = m.group(1).split(",")[0].strip().strip("'\"")
                fam = re.sub(r"[_-]?\d{3}\w*$", "", fam)
                fam = re.sub(r"[_-](regular|bold|medium|semibold|extrabold|light|black|italic|thin)$", "", fam, flags=re.I).replace("-", " ")
                fam = re.sub(r"\b(\w)", lambda x: x.group(1).upper(), fam) if fam.islower() else fam
                if fam.lower() in GENERIC_FONTS or fam.startswith("var") or len(fam) < 3:
                    continue
                fonts[fam] += 1
                font_src.setdefault(fam, src(root, p, text, m.start()))
        for sig in DARK_SIGNALS:
            i = text.find(sig)
            if i >= 0 and (sig != "dark:" or is_theme):
                dark.append(src(root, p, text, i) + f" ({sig})")
        for key, label in ICON_LIBS.items():
            i = text.find(key)
            if i >= 0 and label not in icons:
                if key == "Icons." and ext != ".dart":
                    continue
                icons[label] = src(root, p, text, i)

    logos.sort(key=lambda x: (-x["score"], -x["size"]))
    # palette suggestion from named colors first
    def pick(names, want_dark=False):
        for c in colors_named:
            n = c["name"].lower()
            if c["dark"] == want_dark and any(re.search(rf"(^|[^a-z]){k}($|[^a-z])", n) or n == k for k in names):
                return c
        return None
    sugg: dict = {"light": {}, "dark": {}}
    sources: dict = {"light": {}, "dark": {}}
    roles = {"primary": ["primary", "brand", "tint", "main", "colorprimary", "accentcolor"],
             "accent": ["accent", "secondary", "highlight", "coloraccent", "colorsecondary"],
             "bg": ["background", "bg", "backgroundcolor", "surface0", "windowbackground"],
             "surface": ["surface", "card", "secondarybackground"],
             "text": ["text", "foreground", "ontext", "textprimary", "label", "onbackground"],
             "muted": ["muted", "subtle", "textsecondary", "secondarytext", "gray", "secondarylabel"]}
    for theme in ("light", "dark"):
        for role, names in roles.items():
            c = pick(names, theme == "dark")
            if c:
                sugg[theme][role] = c["hex"]
                sources[theme][role] = c["source"]
    if "primary" not in sugg["light"]:
        sat = [(hx, n) for hx, n in color_counts.most_common(40) if saturation(hx) > 0.35 and 0.05 < luminance(hex_to_rgb(hx)) < 0.75]
        if sat:
            sugg["light"]["primary"] = sat[0][0]
            sources["light"]["primary"] = f"{color_src[sat[0][0]]} [ASSUMPTION: most frequent saturated color]"
    # discard dark suggestions with unreadable combos
    if sugg["dark"].get("bg") and luminance(hex_to_rgb(sugg["dark"]["bg"])) > 0.3:
        sugg["dark"].pop("bg")
    top_fonts = [f for f, _ in fonts.most_common(4)]
    try:
        from build_screens import substitute_font
    except Exception:  # pragma: no cover
        substitute_font = None
    notes: list = []
    heading = top_fonts[0] if top_fonts else (font_files[0]["family"] if font_files else None)
    body = top_fonts[1] if len(top_fonts) > 1 else heading
    result = {
        "logo": logos[0]["path"] if logos else None,
        "logo_candidates": logos[:6],
        "colors_named": colors_named[:60],
        "colors_frequent": [{"hex": hx, "count": n, "source": color_src[hx]} for hx, n in color_counts.most_common(15)],
        "palette_suggestion": sugg, "palette_sources": sources,
        "fonts_used": [{"family": f, "count": n, "source": font_src[f]} for f, n in fonts.most_common(8)],
        "font_files": font_files[:20],
        "font_heading": heading, "font_body": body,
        "font_heading_bundled": substitute_font(heading, notes) if substitute_font else "Poppins",
        "font_body_bundled": substitute_font(body, notes) if substitute_font else "Inter",
        "font_notes": list(dict.fromkeys(notes)),
        "dark_mode_evidence": sorted(set(dark))[:12],
        "icon_style": [{"library": k, "source": v} for k, v in icons.items()],
    }
    if result["logo"]:
        result["logo_abs"] = str((root / result["logo"]).resolve())
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".")
    ap.add_argument("--out", default="paywall-designs")
    a = ap.parse_args()
    root = Path(a.project).resolve()
    res = extract(root)
    out = Path(a.out).resolve()
    if res.get("logo_abs"):
        import os
        res["logo"] = os.path.relpath(res.pop("logo_abs"), out)
    write_json(out / "brand.json", res)
    print(f"brand.json → {out / 'brand.json'}")
    print(json.dumps({k: res[k] for k in ("logo", "palette_suggestion", "font_heading", "font_body", "icon_style")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
