#!/usr/bin/env python3
"""Build a contact sheet with every rendered screen (PNG) and an optional multi-page PDF.

Usage:
  contact_sheet.py --work paywall-designs [--pdf] [--thumb 360]
Outputs output/contact-sheet.png (all screens, grouped by device × theme) and, with --pdf,
output/contact-sheet.pdf (one page per device × theme).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FONTS_DIR, read_json  # noqa: E402

STATUS_COLORS = {"pass": (43, 138, 62), "warn": (230, 140, 0), "fail": (201, 42, 42)}


def font(size: int, bold: bool = False):
    from PIL import ImageFont
    f = FONTS_DIR / ("Poppins-SemiBold.ttf" if bold else "Poppins-Regular.ttf")
    try:
        return ImageFont.truetype(str(f), size)
    except OSError:
        return ImageFont.load_default()


def group_sheet(title: str, items: list, thumb: int, cols: int):
    from PIL import Image, ImageDraw
    gap, label_h, head_h = 36, 64, 110
    th = int(thumb * items[0][1].height / items[0][1].width)
    rows = (len(items) + cols - 1) // cols
    W = cols * thumb + (cols + 1) * gap
    H = head_h + rows * (th + label_h + gap) + gap
    sheet = Image.new("RGB", (W, H), (246, 247, 249))
    d = ImageDraw.Draw(sheet)
    d.text((gap, 34), title, fill=(20, 22, 26), font=font(38, True))
    for i, (page, im, status) in enumerate(items):
        r, c = divmod(i, cols)
        x = gap + c * (thumb + gap)
        y = head_h + r * (th + label_h + gap)
        t = im.copy()
        t.thumbnail((thumb, th))
        sheet.paste(t, (x, y))
        d.rectangle([x - 1, y - 1, x + thumb, y + th], outline=(210, 214, 220), width=2)
        label = page["name"]
        size = 20
        while size > 11 and d.textlength(label, font=font(size, True)) > thumb:
            size -= 1
        d.text((x, y + th + 10), label, fill=(20, 22, 26), font=font(size, True))
        if status:
            col = STATUS_COLORS.get(status, (100, 100, 100))
            d.ellipse([x, y + th + 42, x + 12, y + th + 54], fill=col)
            d.text((x + 18, y + th + 38), f"checks: {status}", fill=col, font=font(17))
    return sheet


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", default="paywall-designs")
    ap.add_argument("--pdf", action="store_true")
    ap.add_argument("--thumb", type=int, default=300)
    ap.add_argument("--cols", type=int, default=7)
    a = ap.parse_args()
    from PIL import Image
    work = Path(a.work).resolve()
    out = work / "output"
    manifest = read_json(out / "manifest.json")
    report = read_json(out / "quality-report.json") if (out / "quality-report.json").exists() else {"results": []}
    status = {(r["name"], r["device"], r["theme"]): r.get("status") for r in report["results"]}
    groups: dict = {}
    for page in manifest["pages"]:
        p = work / page["png"]
        if not p.exists():
            continue
        groups.setdefault((page["device"], page["theme"]), []).append(
            (page, Image.open(p).convert("RGB"), status.get((page["name"], page["device"], page["theme"]))))
    if not groups:
        print("No PNG found — run render.py first.", file=sys.stderr)
        return 2
    app = manifest.get("app") or "App"
    sheets = [group_sheet(f"{app} — {dev} · {theme}", items, a.thumb, a.cols) for (dev, theme), items in groups.items()]
    W = max(s.width for s in sheets)
    H = sum(s.height for s in sheets)
    full = Image.new("RGB", (W, H), (246, 247, 249))
    y = 0
    for s in sheets:
        full.paste(s, (0, y))
        y += s.height
    full.save(out / "contact-sheet.png", optimize=True)
    print(f"Contact sheet → {out / 'contact-sheet.png'} ({W}×{H})")
    if a.pdf:
        sheets[0].save(out / "contact-sheet.pdf", save_all=True, append_images=sheets[1:], resolution=150)
        print(f"PDF → {out / 'contact-sheet.pdf'} ({len(sheets)} pages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
