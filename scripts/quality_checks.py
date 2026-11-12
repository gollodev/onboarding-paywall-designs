#!/usr/bin/env python3
"""Automated quality checks for built screens (runs inside Chromium via Playwright).

Checks per page:
  overflow      text clipped, outside the viewport, outside its container, or page needs scrolling
  overlap       key elements (headline, CTA, mandatory items) overlapping each other
  contrast      WCAG AA: 4.5:1 normal text, 3:1 large text (>=24px or >=18.66px bold); 3:1 close icon
  min-size      text smaller than 11px (warn) / 10px (fail)
  images        broken <img>, failed requests, missing fonts (fallback rendering)
  cta           exactly one primary CTA, fully inside the viewport (no scroll), >=44px tall, not covered
  required      paywall: close, price, billing-period, trial-terms (if trial), auto-renew, cancel-info,
                restore, terms, privacy; permissions: permission-reason + visible "not now"
  honesty       billed price >= per-month equivalent size; close button not faded/tiny;
                countdown only if urgency is real; no unresolved {{tags}}
  placeholders  visible placeholders ($X.XX, [[...]], pending social proof) -> warning
  png           (after render) file exists, exact size, not blank

Usage:
  quality_checks.py --work paywall-designs            # check HTML pages + existing PNGs from manifest
Exit code 1 if any check fails.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CHROMIUM_ARGS, group_by_viewport, read_json, write_json  # noqa: E402

PAYWALL_REQUIRED = ["close", "price", "billing-period", "auto-renew", "cancel-info", "restore", "terms", "privacy"]

CHECK_JS = r"""
(opts) => {
  const issues = [];
  const add = (check, severity, message, el) => issues.push({check, severity, message,
      selector: el ? describe(el) : null, text: el ? (el.innerText || el.getAttribute('aria-label') || '').trim().slice(0, 80) : null});
  const vw = window.innerWidth, vh = window.innerHeight;
  function describe(el) {
    let s = el.tagName.toLowerCase();
    if (el.dataset.required) s += `[data-required="${el.dataset.required}"]`;
    else if (el.dataset.role) s += `[data-role="${el.dataset.role}"]`;
    else if (el.className && typeof el.className === 'string') s += '.' + el.className.trim().split(/\s+/).join('.');
    return s;
  }
  const visible = (el) => {
    const cs = getComputedStyle(el); const r = el.getBoundingClientRect();
    return cs.display !== 'none' && cs.visibility !== 'hidden' && parseFloat(cs.opacity) > 0.05 && r.width > 0 && r.height > 0;
  };
  const isDecor = (el) => !!el.closest('[data-decor]');
  const parseColor = (s) => {
    const m = s.match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const p = m[1].split(/[\s,\/]+/).filter(Boolean).map(parseFloat);
    return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1];
  };
  const blend = (fg, bg) => { const a = fg[3]; return [0,1,2].map(i => fg[i]*a + bg[i]*(1-a)).concat([1]); };
  const lin = (c) => { c /= 255; return c <= 0.03928 ? c/12.92 : Math.pow((c+0.055)/1.055, 2.4); };
  const lum = (c) => 0.2126*lin(c[0]) + 0.7152*lin(c[1]) + 0.0722*lin(c[2]);
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05); };
  // Background candidates behind an element (handles alpha layers and gradients).
  function backgrounds(el) {
    const chain = []; let n = el;
    while (n && n.nodeType === 1) { chain.unshift(n); n = n.parentElement; }
    let cands = [[255,255,255,1]]; let unknown = false;
    for (const node of chain) {
      const cs = getComputedStyle(node);
      const img = cs.backgroundImage;
      if (img && img !== 'none') {
        if (img.includes('gradient')) {
          const cols = (img.match(/rgba?\([^)]+\)/g) || []).map(parseColor);
          if (cols.length) cands = cols.flatMap(c => cands.map(b => blend(c, b)));
        } else if (node.dataset.bg) {
          cands = [parseColor(node.dataset.bg) || cands[0]];
        } else { unknown = true; }
      }
      const bc = parseColor(cs.backgroundColor);
      if (bc && bc[3] > 0) cands = cands.map(b => blend(bc, b));
    }
    return {cands, unknown};
  }
  function opacityChain(el) { let o = 1; let n = el; while (n && n.nodeType === 1) { o *= parseFloat(getComputedStyle(n).opacity); n = n.parentElement; } return o; }

  // ---------- fonts
  for (const fam of opts.fonts) {
    if (!document.fonts.check(`16px "${fam}"`)) add('images', 'fail', `Font "${fam}" not loaded (fallback font used)`, null);
  }
  // ---------- images
  for (const img of document.images) {
    if (!img.complete || img.naturalWidth === 0) add('images', 'fail', `Broken image: ${img.getAttribute('src')}`, img);
  }
  // ---------- page scroll
  for (const box of document.querySelectorAll('.screen, .content')) {
    if (box.scrollHeight > box.clientHeight + 1) add('overflow', 'fail', `Content taller than available space by ${box.scrollHeight - box.clientHeight}px (needs scrolling)`, box);
  }
  if (document.documentElement.scrollWidth > vw + 1) add('overflow', 'fail', 'Page wider than the viewport', null);

  // ---------- text elements
  const textEls = [...document.querySelectorAll('body *')].filter(el =>
    [...el.childNodes].some(c => c.nodeType === 3 && c.textContent.trim()) && visible(el) && !isDecor(el));
  if (/\{\{|\}\}/.test(document.body.innerText)) add('honesty', 'fail', 'Unresolved template tag {{...}} in visible text', null);

  for (const el of textEls) {
    const cs = getComputedStyle(el);
    const range = document.createRange(); range.selectNodeContents(el);
    const r = range.getBoundingClientRect();
    // viewport
    if (r.left < -0.5 || r.right > vw + 0.5 || r.top < -0.5 || r.bottom > vh + 0.5)
      add('overflow', 'fail', 'Text outside the visible screen', el);
    // clipped by self
    if ((cs.overflow !== 'visible' || cs.textOverflow === 'ellipsis') && (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1))
      add('overflow', 'fail', 'Text clipped inside its element', el);
    // clipped by an ancestor container (badges marked data-overhang may stick out of their card on purpose)
    const overhang = !!el.closest('[data-overhang]');
    let a = el.parentElement;
    while (a && a !== document.body) {
      const acs = getComputedStyle(a);
      if (acs.overflow !== 'visible' || (!overhang && (a.hasAttribute('data-box') || a.tagName === 'BUTTON'))) {
        const ar = a.getBoundingClientRect();
        if (r.left < ar.left - 1 || r.right > ar.right + 1 || r.top < ar.top - 1 || r.bottom > ar.bottom + 1) {
          add('overflow', 'fail', `Text overflows its container ${describe(a)}`, el); break;
        }
      }
      a = a.parentElement;
    }
    // covered by another element (e.g. a decorative shape painted over the text)
    for (const lr of range.getClientRects()) {
      if (lr.width < 2 || lr.height < 2) continue;
      const pts = [[lr.left + lr.width / 2, lr.top + lr.height / 2], [lr.left + 3, lr.top + lr.height / 2], [lr.right - 3, lr.top + lr.height / 2]];
      let covered = null;
      for (const [x, y] of pts) {
        if (x < 0 || y < 0 || x > vw || y > vh) continue;
        const hit = document.elementFromPoint(x, y);
        if (hit && !el.contains(hit) && !hit.contains(el)) { covered = hit; break; }
      }
      if (covered) { add('overlap', 'fail', `Text covered by ${describe(covered)}`, el); break; }
    }
    // font size
    const fs = parseFloat(cs.fontSize);
    if (fs < 10) add('min-size', 'fail', `Text too small (${fs.toFixed(1)}px)`, el);
    else if (fs < 11) add('min-size', 'warn', `Small text (${fs.toFixed(1)}px)`, el);
    // contrast
    const fg = parseColor(cs.color); if (!fg) continue;
    fg[3] *= opacityChain(el);
    const {cands, unknown} = backgrounds(el);
    if (unknown) { add('contrast', 'warn', 'Text over an image: contrast not verifiable (add data-bg="#hex" to the image container)', el); continue; }
    const bold = parseInt(cs.fontWeight, 10) >= 700;
    const large = fs >= 24 || (bold && fs >= 18.66);
    const need = large ? 3 : 4.5;
    const worst = Math.min(...cands.map(b => ratio(blend(fg, b), b)));
    if (worst < need - 0.01) add('contrast', 'fail', `Contrast ${worst.toFixed(2)}:1 < ${need}:1 (WCAG AA ${large ? 'large' : 'normal'} text)`, el);
    // placeholders
    const own = [...el.childNodes].filter(c => c.nodeType === 3).map(c => c.textContent).join(' ');
    if (/\$X\.XX|\[\[[^\]]*\]\]/.test(own)) add('placeholders', 'warn', `Placeholder visible: "${own.trim().slice(0, 60)}"`, el);
  }
  for (const ph of document.querySelectorAll('[data-placeholder]'))
    if (visible(ph)) add('placeholders', 'warn', `Placeholder block visible: ${ph.dataset.placeholder} (needs real data)`, ph);

  // ---------- CTA
  const ctas = [...document.querySelectorAll('[data-role="cta-primary"]')].filter(visible);
  if (ctas.length !== 1) add('cta', 'fail', `Expected exactly 1 primary CTA, found ${ctas.length}`, null);
  for (const cta of ctas) {
    const r = cta.getBoundingClientRect();
    if (r.top < 0 || r.bottom > vh - opts.safeBottom + 0.5 || r.left < 0 || r.right > vw)
      add('cta', 'fail', `Primary CTA not fully visible without scrolling (bottom ${Math.round(r.bottom)} > ${vh - opts.safeBottom})`, cta);
    if (r.height < 44) add('cta', 'fail', `Primary CTA too small (${Math.round(r.height)}px < 44px)`, cta);
    const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    if (hit && !cta.contains(hit)) add('cta', 'fail', 'Primary CTA is covered by another element', cta);
    if (!cta.innerText.trim()) add('cta', 'fail', 'Primary CTA has no text', cta);
  }

  // ---------- required elements
  const required = [...opts.required];
  for (const key of required) {
    const els = [...document.querySelectorAll(`[data-required~="${key}"]`)].filter(visible);
    if (!els.length) { add('required', 'fail', `Mandatory element missing or hidden: ${key}`, null); continue; }
    for (const el of els) {
      const r = el.getBoundingClientRect();
      if (r.top < 0 || r.bottom > vh + 0.5) add('required', 'fail', `Mandatory element "${key}" outside the screen`, el);
      if (key !== 'close' && !el.innerText.trim()) add('required', 'fail', `Mandatory element "${key}" has no text`, el);
    }
  }
  if (opts.kind === 'paywall') {
    const close = document.querySelector('[data-required~="close"]');
    if (close && visible(close)) {
      const r = close.getBoundingClientRect();
      if (r.width < 24 || r.height < 24) add('honesty', 'fail', `Close button too small (${Math.round(r.width)}px)`, close);
      if (opacityChain(close) < 0.85) add('honesty', 'fail', 'Close button is faded (dark pattern)', close);
      const col = parseColor(getComputedStyle(close).color);
      const {cands} = backgrounds(close);
      const w1 = Math.min(...cands.map(b => ratio(blend(col, b), b)));
      if (w1 < 3) add('contrast', 'fail', `Close icon contrast ${w1.toFixed(2)}:1 < 3:1`, close);
    }
    // billed price must be at least as prominent as per-month equivalents
    const priceSizes = [...document.querySelectorAll('[data-required~="price"]')].filter(visible).map(e => parseFloat(getComputedStyle(e).fontSize));
    for (const eq of [...document.querySelectorAll('[data-role="price-equivalent"]')].filter(visible)) {
      const s = parseFloat(getComputedStyle(eq).fontSize);
      if (priceSizes.length && s > Math.min(...priceSizes)) add('honesty', 'fail', 'Per-month equivalent is more prominent than the billed price', eq);
    }
  }
  for (const cd of document.querySelectorAll('[data-role="countdown"]'))
    if (visible(cd) && document.body.dataset.urgencyReal !== 'True') add('honesty', 'fail', 'Countdown/urgency shown but urgency.real is not true (fake urgency)', cd);

  // ---------- overlap among key elements
  const keys = [...document.querySelectorAll('h1, [data-role="cta-primary"], [data-role="cta-secondary"], [data-required], .plan, .plan-row, .option')].filter(visible);
  for (let i = 0; i < keys.length; i++) for (let j = i + 1; j < keys.length; j++) {
    const a = keys[i], b = keys[j];
    if (a.contains(b) || b.contains(a)) continue;
    // compare line boxes (inline spans in one paragraph share lines without overlapping)
    let worst = 0;
    for (const ra of a.getClientRects()) for (const rb of b.getClientRects()) {
      const ox = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left);
      const oy = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
      if (ox > 1 && oy > 1) worst = Math.max(worst, (ox * oy) / Math.max(1, Math.min(ra.width * ra.height, rb.width * rb.height)));
    }
    if (worst > 0.2) add('overlap', 'fail', `Overlaps ${describe(b)} (${Math.round(worst * 100)}% of the smaller box)`, a);
  }
  return {issues, density: document.body.dataset.density || '1'};
}
"""


def required_for(page: dict) -> list[str]:
    if page["kind"] == "paywall":
        req = list(PAYWALL_REQUIRED)
        if page.get("has_trial"):
            req.append("trial-terms")
        return req
    if page["template"].endswith("permissions"):
        return ["permission-reason"]
    return []


def check_page(page_obj, page: dict, fonts: list[str], safe_bottom: int) -> dict:
    """Run DOM checks on an already-loaded Playwright page."""
    opts = {"required": required_for(page), "kind": page["kind"], "fonts": fonts, "safeBottom": 0}
    res = page_obj.evaluate(CHECK_JS, opts)
    issues = res["issues"]
    if page["template"].endswith("permissions"):
        sec = page_obj.query_selector('[data-role="cta-secondary"]')
        if not sec or not sec.is_visible():
            issues.append({"check": "honesty", "severity": "fail", "selector": None, "text": None,
                           "message": "Permission screen must offer a visible 'Not now' option (cta-secondary)"})
    return {"issues": issues, "density": res.get("density")}


def check_png(work: Path, page: dict) -> list[dict]:
    from PIL import Image, ImageStat
    p = work / page["png"]
    if not p.exists():
        return [{"check": "png", "severity": "fail", "message": f"PNG missing: {page['png']}", "selector": None, "text": None}]
    out = []
    with Image.open(p) as im:
        if im.size != (page["width"], page["height"]):
            out.append({"check": "png", "severity": "fail", "selector": None, "text": None,
                        "message": f"PNG size {im.size} != expected {(page['width'], page['height'])}"})
        stat = ImageStat.Stat(im.convert("L").resize((64, 64)))
        if stat.stddev[0] < 2:
            out.append({"check": "png", "severity": "fail", "message": "PNG looks blank", "selector": None, "text": None})
    return out


def summarize(results: list[dict]) -> dict:
    fails = sum(1 for r in results for i in r["issues"] if i["severity"] == "fail")
    warns = sum(1 for r in results for i in r["issues"] if i["severity"] == "warn")
    for r in results:
        sev = {i["severity"] for i in r["issues"]}
        r["status"] = "fail" if "fail" in sev else "warn" if "warn" in sev else "pass"
    return {"pages": len(results), "failed_pages": sum(r["status"] == "fail" for r in results),
            "fail_issues": fails, "warn_issues": warns}


def write_report(work: Path, results: list[dict]) -> dict:
    summary = summarize(results)
    out = work / "output"
    write_json(out / "quality-report.json", {"summary": summary, "results": results})
    lines = ["# Quality report", "",
             f"- Pages: **{summary['pages']}** · failed pages: **{summary['failed_pages']}** · "
             f"fail issues: **{summary['fail_issues']}** · warnings: **{summary['warn_issues']}**", ""]
    lines += ["| Page | Device | Theme | Status | Issues |", "|---|---|---|---|---|"]
    for r in results:
        msgs = "<br>".join(f"{'❌' if i['severity'] == 'fail' else '⚠️'} [{i['check']}] {i['message']}"
                           + (f" — `{i['selector']}`" if i.get("selector") else "")
                           for i in r["issues"][:8]) or "—"
        if len(r["issues"]) > 8:
            msgs += f"<br>… +{len(r['issues']) - 8} more (see quality-report.json)"
        icon = {"pass": "✅ pass", "warn": "⚠️ warn", "fail": "❌ fail"}[r["status"]]
        lines.append(f"| {r['name']} | {r['device']} | {r['theme']} | {icon} | {msgs} |")
    (out / "quality-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def fonts_from_manifest(work: Path) -> list[str]:
    import re
    fams = set()
    for html_file in list((work / "output" / "html").rglob("*.html"))[:1]:
        m = re.search(r"--font-h:'([^']+)';--font-b:'([^']+)'", html_file.read_text(encoding="utf-8"))
        if m:
            fams.update(m.groups())
    return sorted(fams)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", default="paywall-designs")
    ap.add_argument("--only", help="substring filter on page name")
    ap.add_argument("--skip-png", action="store_true", help="only DOM checks, ignore PNG files")
    a = ap.parse_args()
    work = Path(a.work).resolve()
    manifest = read_json(work / "output" / "manifest.json")
    from playwright.sync_api import sync_playwright
    results = []
    fonts = fonts_from_manifest(work)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=CHROMIUM_ARGS)
        ctx, key_open = None, None
        for page in group_by_viewport(manifest["pages"]):
            if a.only and a.only not in page["name"]:
                continue
            key = (page["vw"], page["vh"])
            if key != key_open:
                if ctx:
                    ctx.close()
                ctx = browser.new_context(viewport={"width": page["vw"], "height": page["vh"]})
                pg = ctx.new_page()
                key_open = key
            pg.goto((work / page["html"]).resolve().as_uri())
            pg.wait_for_function("window.__layoutDone === true", timeout=15000)
            r = check_page(pg, page, fonts, 0)
            if not a.skip_png:
                r["issues"] += check_png(work, page)
            results.append({**{k: page[k] for k in ("name", "device", "theme", "variant", "template")}, **r})
        browser.close()
    s = write_report(work, results)
    print(json.dumps(s))
    print(f"Report → {work / 'output' / 'quality-report.md'}")
    return 1 if s["fail_issues"] else 0


if __name__ == "__main__":
    sys.exit(main())
