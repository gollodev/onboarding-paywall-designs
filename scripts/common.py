"""Shared helpers: tiny mustache-like template engine, colors/contrast, paths, JSON IO.

Dependency-free on purpose so every script can import it.
"""
from __future__ import annotations

import html
import json
import math
import re
from pathlib import Path
from typing import Any

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = SKILL_DIR / "templates"
ASSETS_DIR = SKILL_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
ICONS_DIR = ASSETS_DIR / "icons"
FRAMES_DIR = ASSETS_DIR / "device-frames"

BUNDLED_FONTS = {"Inter", "Poppins", "Manrope"}

DEFAULT_DEVICES = {
    "iphone": {"id": "iphone", "platform": "ios", "width": 1290, "height": 2796, "scale": 3,
               "safe_top": 54, "safe_bottom": 34, "label": "iPhone 6.9\""},
    "android": {"id": "android", "platform": "android", "width": 1080, "height": 2400, "scale": 2.5,
                "safe_top": 36, "safe_bottom": 24, "label": "Android 20:9"},
}


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- template engine
# Supported: {{name}} (escaped), {{{name}}} (raw), {{#name}}..{{/name}} (truthy / list loop),
# {{^name}}..{{/name}} (inverted), {{> partial}}, {{.}} (current item), dotted names.

_TAG = re.compile(r"\{\{\{\s*([\w.\-]+)\s*\}\}\}|\{\{\s*([#^/>!]?)\s*([\w.\-]+)\s*\}\}")


class TemplateError(Exception):
    pass


def _parse(src: str):
    root: list = []
    stack: list = [("root", root)]
    pos = 0
    for m in _TAG.finditer(src):
        cur = stack[-1][1]
        if m.start() > pos:
            cur.append(("text", src[pos:m.start()]))
        pos = m.end()
        if m.group(1):
            cur.append(("raw", m.group(1)))
            continue
        sigil, name = m.group(2), m.group(3)
        if sigil in ("#", "^"):
            node = ("section" if sigil == "#" else "inverted", name, [])
            cur.append(node)
            stack.append((name, node[2]))
        elif sigil == "/":
            if len(stack) == 1 or stack[-1][0] != name:
                raise TemplateError(f"Unexpected closing tag {{{{/{name}}}}}")
            stack.pop()
        elif sigil == ">":
            cur.append(("partial", name))
        elif sigil == "!":
            pass
        else:
            cur.append(("var", name))
    if len(stack) != 1:
        raise TemplateError(f"Unclosed section {{{{#{stack[-1][0]}}}}}")
    if pos < len(src):
        root.append(("text", src[pos:]))
    return root


def _lookup(stack: list, name: str):
    if name == ".":
        return stack[-1]
    parts = name.split(".")
    for ctx in reversed(stack):
        if isinstance(ctx, dict) and parts[0] in ctx:
            val = ctx[parts[0]]
            for p in parts[1:]:
                if isinstance(val, dict):
                    val = val.get(p)
                elif isinstance(val, list) and p.isdigit() and int(p) < len(val):
                    val = val[int(p)]
                else:
                    return None
            return val
    return None


def _to_str(val) -> str:
    if val is None or val is False:
        return ""
    if isinstance(val, float) and val.is_integer():
        return str(int(val))
    return str(val)


def render_template(src: str, context: dict, partials_dir: Path | None = None, escape: bool = True) -> str:
    tree = _parse(src)
    out: list[str] = []

    def walk(nodes, stack):
        for node in nodes:
            kind = node[0]
            if kind == "text":
                out.append(node[1])
            elif kind == "var":
                val = _to_str(_lookup(stack, node[1]))
                out.append(html.escape(val, quote=True) if escape else val)
            elif kind == "raw":
                out.append(_to_str(_lookup(stack, node[1])))
            elif kind == "partial":
                if partials_dir is None:
                    raise TemplateError("Partials directory not configured")
                p = partials_dir / f"{node[1]}.html"
                if not p.exists():
                    raise TemplateError(f"Missing partial {p}")
                walk(_parse(p.read_text(encoding="utf-8")), stack)
            elif kind == "section":
                val = _lookup(stack, node[1])
                if isinstance(val, list):
                    for item in val:
                        walk(node[2], stack + [item])
                elif val:
                    walk(node[2], stack + [val] if isinstance(val, dict) else stack)
            elif kind == "inverted":
                val = _lookup(stack, node[1])
                if not val:
                    walk(node[2], stack)

    walk(tree, [context])
    return "".join(out)


def interpolate_strings(obj, context: dict):
    """Resolve {{...}} placeholders inside config strings (e.g. headline uses {{answers.goal}})."""
    if isinstance(obj, str):
        if "{{" in obj:
            return render_template(obj, context, escape=False)
        return obj
    if isinstance(obj, list):
        return [interpolate_strings(x, context) for x in obj]
    if isinstance(obj, dict):
        return {k: interpolate_strings(v, context) for k, v in obj.items()}
    return obj


def deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def set_dotted(obj: dict, path: str, value) -> None:
    parts = path.split(".")
    cur = obj
    for i, p in enumerate(parts[:-1]):
        nxt = parts[i + 1]
        if isinstance(cur, list):
            cur = cur[int(p)]
            continue
        if p not in cur or cur[p] is None:
            cur[p] = [] if nxt.isdigit() else {}
        cur = cur[p]
    last = parts[-1]
    if isinstance(cur, list):
        cur[int(last)] = value
    else:
        cur[last] = value


# --------------------------------------------------------------------------- colors
def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) == 8:
        h = h[:6]
    if not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        raise ValueError(f"Invalid hex color: {h}")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb_to_hex(rgb) -> str:
    return "#" + "".join(f"{max(0, min(255, round(c))):02X}" for c in rgb[:3])


def _lin(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb) -> float:
    r, g, b = rgb[:3]
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(a, b) -> float:
    if isinstance(a, str):
        a = hex_to_rgb(a)
    if isinstance(b, str):
        b = hex_to_rgb(b)
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def mix(a: str, b: str, t: float) -> str:
    ra, rb = hex_to_rgb(a), hex_to_rgb(b)
    return rgb_to_hex([ra[i] + (rb[i] - ra[i]) * t for i in range(3)])


def rgba(h: str, alpha: float) -> str:
    r, g, b = hex_to_rgb(h)
    return f"rgba({r}, {g}, {b}, {alpha})"


def best_on(bg: str, light: str = "#FFFFFF", dark: str = "#111111") -> str:
    return light if contrast(light, bg) >= contrast(dark, bg) else dark


def ensure_contrast(fg: str, bg: str, target: float = 4.5) -> str:
    """Move fg towards black or white until it reaches target contrast against bg."""
    if contrast(fg, bg) >= target:
        return fg
    toward = "#000000" if luminance(hex_to_rgb(bg)) > 0.4 else "#FFFFFF"
    for i in range(1, 21):
        cand = mix(fg, toward, i / 20)
        if contrast(cand, bg) >= target:
            return cand
    return toward


def hsl_lighten(h: str, amount: float) -> str:
    return mix(h, "#FFFFFF", amount) if amount >= 0 else mix(h, "#000000", -amount)


# --------------------------------------------------------------------------- misc
def floor2(x: float) -> float:
    return math.floor(x * 100 + 1e-9) / 100


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def file_uri(p: Path) -> str:
    return Path(p).resolve().as_uri()


CHROMIUM_ARGS = ["--disable-renderer-backgrounding", "--disable-background-timer-throttling",
                 "--disable-backgrounding-occluded-windows"]


def group_by_viewport(pages: list) -> list:
    """Order pages so each viewport is processed in one go (one active tab at a time)."""
    return sorted(pages, key=lambda p: (p["vw"], p["vh"], p["scale"]))
