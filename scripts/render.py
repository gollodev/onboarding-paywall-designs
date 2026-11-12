#!/usr/bin/env python3
"""Render built HTML screens to PNG with Playwright (Chromium headless) and run quality checks.

Usage:
  render.py --work paywall-designs              # render all pages in output/manifest.json
  render.py --work paywall-designs --only paywall --no-checks
Exit code 1 if any quality check fails (PNG files are still written so you can inspect them).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CHROMIUM_ARGS, FRAMES_DIR, group_by_viewport, hex_to_rgb, read_json  # noqa: E402
import quality_checks as qc  # noqa: E402


def frame_image(screen_png: Path, out_png: Path, page: dict) -> None:
    """Place the rendered screen inside a generic phone frame on a background of the same output size."""
    from PIL import Image, ImageDraw, ImageFilter
    spec = read_json(FRAMES_DIR / f"{page['device']}.json") if (FRAMES_DIR / f"{page['device']}.json").exists() \
        else read_json(FRAMES_DIR / ("iphone.json" if page["platform"] == "ios" else "android.json"))
    fcfg = page.get("frame") or {}
    W, H = page["width"], page["height"]
    bg = fcfg.get("background", "#EEF1F4")
    canvas = Image.new("RGB", (W, H), hex_to_rgb(bg))
    shot = Image.open(screen_png).convert("RGB")
    ar, b = shot.height / shot.width, spec["bezel_ratio"]
    sw = H * spec["device_height_ratio"] / (ar + 2 * b)
    sw = min(sw, W * 0.9 / (1 + 2 * b))
    sw, bezel = int(sw), int(sw * b)
    sh = int(sw * ar)
    bw, bh = sw + 2 * bezel, sh + 2 * bezel
    x0, y0 = (W - bw) // 2, (H - bh) // 2
    ss = 2  # supersampling for smooth corners
    if spec.get("shadow"):
        sh_layer = Image.new("L", (W, H), 0)
        ImageDraw.Draw(sh_layer).rounded_rectangle([x0, y0 + int(bh * 0.02), x0 + bw, y0 + bh + int(bh * 0.02)],
                                                    radius=int(sw * spec["body_radius_ratio"]), fill=90)
        sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(int(W * 0.03)))
        canvas.paste(Image.new("RGB", (W, H), (0, 0, 0)), (0, 0), sh_layer)
    body_mask = Image.new("L", (bw * ss, bh * ss), 0)
    ImageDraw.Draw(body_mask).rounded_rectangle([0, 0, bw * ss - 1, bh * ss - 1], radius=int(sw * spec["body_radius_ratio"]) * ss, fill=255)
    body_mask = body_mask.resize((bw, bh), Image.LANCZOS)
    canvas.paste(Image.new("RGB", (bw, bh), hex_to_rgb(spec["body_color"])), (x0, y0), body_mask)
    if spec.get("side_buttons"):
        d = ImageDraw.Draw(canvas)
        bwid = max(3, int(sw * 0.012))
        col = hex_to_rgb(spec["body_color"])
        d.rounded_rectangle([x0 + bw - 1, y0 + int(bh * 0.22), x0 + bw + bwid, y0 + int(bh * 0.32)], radius=bwid, fill=col)
        d.rounded_rectangle([x0 - bwid, y0 + int(bh * 0.18), x0 + 1, y0 + int(bh * 0.24)], radius=bwid, fill=col)
    scr = shot.resize((sw, sh), Image.LANCZOS)
    scr_mask = Image.new("L", (sw * ss, sh * ss), 0)
    ImageDraw.Draw(scr_mask).rounded_rectangle([0, 0, sw * ss - 1, sh * ss - 1], radius=int(sw * spec["screen_radius_ratio"]) * ss, fill=255)
    scr_mask = scr_mask.resize((sw, sh), Image.LANCZOS)
    canvas.paste(scr, (x0 + bezel, y0 + bezel), scr_mask)
    canvas.save(out_png, optimize=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", default="paywall-designs")
    ap.add_argument("--only", help="substring filter on page name")
    ap.add_argument("--no-checks", action="store_true", help="skip quality checks (not for delivery)")
    a = ap.parse_args()
    work = Path(a.work).resolve()
    manifest_path = work / "output" / "manifest.json"
    if not manifest_path.exists():
        print("manifest.json not found — run build_screens.py first.", file=sys.stderr)
        return 2
    manifest = read_json(manifest_path)
    fonts = qc.fonts_from_manifest(work)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed: python3 -m pip install -r requirements.txt && python3 -m playwright install chromium",
              file=sys.stderr)
        return 2
    from PIL import Image
    results, rendered = [], 0
    pages = group_by_viewport([p for p in manifest["pages"] if not a.only or a.only in p["name"]])
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=CHROMIUM_ARGS)
        ctx, key_open = None, None  # one tab per viewport, reused (much faster than a context per page)
        failed: list[str] = []
        for page in pages:
            key = (page["vw"], page["vh"], page["scale"])
            if key != key_open:
                if ctx:
                    ctx.close()
                ctx = browser.new_context(viewport={"width": page["vw"], "height": page["vh"]},
                                          device_scale_factor=page["scale"])
                pg = ctx.new_page()
                pg.on("requestfailed", lambda req: failed.append(req.url))
                pg.on("response", lambda resp: failed.append(resp.url) if resp.status >= 400 else None)
                key_open = key
            failed.clear()
            pg.goto((work / page["html"]).resolve().as_uri(), wait_until="load")
            pg.wait_for_function("window.__layoutDone === true", timeout=15000)
            out_png = work / page["png"]
            out_png.parent.mkdir(parents=True, exist_ok=True)
            pg.screenshot(path=str(out_png), full_page=False)
            with Image.open(out_png) as im:
                needs_resize = im.size != (page["width"], page["height"])
                if needs_resize:
                    im.resize((page["width"], page["height"]), Image.LANCZOS).save(out_png)
            if page.get("frame"):
                frame_image(out_png, out_png, page)
            rendered += 1
            if not a.no_checks:
                r = qc.check_page(pg, page, fonts, 0)
                r["issues"] += [{"check": "images", "severity": "fail", "message": f"Failed to load: {u}",
                                 "selector": None, "text": None} for u in failed]
                r["issues"] += qc.check_png(work, page)
                results.append({**{k: page[k] for k in ("name", "device", "theme", "variant", "template")}, **r})
        browser.close()
    print(f"Rendered {rendered} PNG → {work / 'output'}")
    if a.no_checks:
        print("Checks skipped (--no-checks). Run quality_checks.py before delivering.")
        return 0
    s = qc.write_report(work, results)
    print(json.dumps(s))
    print(f"Report → {work / 'output' / 'quality-report.md'}")
    if s["fail_issues"]:
        print("❌ Quality checks failed. Fix config.json, rebuild and re-render.", file=sys.stderr)
        return 1
    print("✅ All quality checks passed" + (f" ({s['warn_issues']} warnings)" if s["warn_issues"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
