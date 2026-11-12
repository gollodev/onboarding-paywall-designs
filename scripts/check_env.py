#!/usr/bin/env python3
"""Check that this skill can run here: Python version, Pillow, Playwright, Chromium, bundled fonts.

Usage: check_env.py   (exit code 0 = ready, 1 = something missing; prints how to fix it)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FONTS_DIR, SKILL_DIR  # noqa: E402

ok = True


def report(name: str, good: bool, fix: str = "") -> None:
    global ok
    ok &= good
    print(f"{'✅' if good else '❌'} {name}" + ("" if good else f"\n   fix: {fix}"))


report(f"Python {sys.version.split()[0]} (>= 3.9)", sys.version_info >= (3, 9), "install Python 3.9+")
try:
    import PIL  # noqa: F401
    report("Pillow", True)
except ImportError:
    report("Pillow", False, f"python3 -m pip install -r {SKILL_DIR / 'requirements.txt'}")
try:
    from playwright.sync_api import sync_playwright
    report("playwright (python)", True)
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            b.close()
        report("Chromium for Playwright", True)
    except Exception as e:  # noqa: BLE001
        report("Chromium for Playwright", False, f"python3 -m playwright install chromium   ({str(e).splitlines()[0][:120]})")
except ImportError:
    report("playwright (python)", False, f"python3 -m pip install -r {SKILL_DIR / 'requirements.txt'}")
fonts = sorted(p.name for p in FONTS_DIR.glob("*.ttf"))
report(f"Bundled fonts ({len(fonts)} files)", len(fonts) >= 3, "re-copy assets/fonts from the canonical skill folder")
print(f"\nSKILL_DIR = {SKILL_DIR}")
sys.exit(0 if ok else 1)
