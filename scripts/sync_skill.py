#!/usr/bin/env python3
"""Keep the canonical skill folder and its Claude / Copilot copies in sync (one source of truth).

Default (run from the canonical folder's parent repo):
  sync_skill.py                      # validate SKILL.md, copy to .claude/skills/ and .github/skills/,
                                     # write .github/prompts/onboarding-paywall.prompt.md and the
                                     # pointer line in .github/copilot-instructions.md
  sync_skill.py --check              # exit 1 if any copy differs from the canonical folder (CI friendly)
  sync_skill.py --target ../my-app   # install into another project (repeatable)
  sync_skill.py --only claude        # only .claude/skills (or: --only copilot)
  sync_skill.py --link               # symlinks instead of copies (Claude Code documents symlink support;
                                     # Copilot/VS Code and Windows checkouts may not follow them)
  sync_skill.py --zip [path]         # ZIP for claude.ai (Customize > Skills > Upload), default dist/<name>.zip
  sync_skill.py --validate           # only validate the SKILL.md frontmatter

Edit ONLY the canonical folder. Copies are overwritten (files not in the canonical folder are deleted).
Excluded from copies/ZIP: .git, caches, .DS_Store, examples/*/output/html and individual example PNGs
(the example contact sheet is kept).
"""
from __future__ import annotations

import argparse
import filecmp
import fnmatch
import hashlib
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
NAME = SKILL_DIR.name
EXCLUDE = [".git", ".ruff_cache", ".pytest_cache", "__pycache__", "*.pyc", ".DS_Store", ".venv", "dist", "examples/*/output/html",
           "examples/*/output/iphone", "examples/*/output/android", "examples/*/output/*/*",
           "examples/*/output/manifest.json", "examples/*/output/quality-report.json", "node_modules"]
ALLOWED_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
PROMPT_NAME = "onboarding-paywall.prompt.md"
MARK_START, MARK_END = "<!-- onboarding-paywall-designs:start -->", "<!-- onboarding-paywall-designs:end -->"


def is_copy(path: Path) -> bool:
    return path.parent.name == "skills" and path.parent.parent.name in (".claude", ".github", ".agents", ".copilot")


def excluded(rel: str) -> bool:
    parts = rel.split("/")
    for pat in EXCLUDE:
        if "/" in pat:
            if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(rel, pat + "/*") or any(
                    fnmatch.fnmatch("/".join(parts[:i]), pat) for i in range(1, len(parts) + 1)):
                return True
        elif any(fnmatch.fnmatch(p, pat) for p in parts):
            return True
    return False


def skill_files(src: Path) -> list[str]:
    out = []
    for p in sorted(src.rglob("*")):
        if p.is_file():
            rel = p.relative_to(src).as_posix()
            if not excluded(rel):
                out.append(rel)
    return out


# --------------------------------------------------------------------------- validation
def parse_frontmatter(text: str) -> tuple[dict, list[str]]:
    errs = []
    if not text.startswith("---\n"):
        return {}, ["SKILL.md must start with '---' on the first line (YAML frontmatter)"]
    end = text.find("\n---", 4)
    if end < 0:
        return {}, ["Frontmatter closing '---' not found"]
    fm: dict = {}
    cur = None
    for line in text[4:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t")):
            if cur is None:
                errs.append(f"Unexpected indented line: {line!r}")
            else:
                fm.setdefault(cur + ".__children", []).append(line.strip())
            continue
        m = re.match(r"^([A-Za-z0-9_\-]+):\s*(.*)$", line)
        if not m:
            errs.append(f"Unparseable frontmatter line: {line!r}")
            continue
        cur = m.group(1)
        val = m.group(2).strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        fm[cur] = val
    return fm, errs


def validate(skill_dir: Path) -> list[str]:
    md = skill_dir / "SKILL.md"
    if not md.exists():
        return [f"{md} not found"]
    text = md.read_text(encoding="utf-8")
    fm, errs = parse_frontmatter(text)
    name, desc = fm.get("name", ""), fm.get("description", "")
    keys = {k for k in fm if not k.endswith(".__children")}
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name or "") or len(name) > 64:
        errs.append(f"name '{name}' must be 1-64 chars, lowercase a-z 0-9 and single hyphens (Agent Skills spec)")
    if name != skill_dir.name:
        errs.append(f"name '{name}' must equal the folder name '{skill_dir.name}' (Copilot silently skips mismatches)")
    if re.search(r"anthropic|claude", name or ""):
        errs.append("name must not contain reserved words 'anthropic' or 'claude'")
    if not desc or len(desc) > 1024:
        errs.append(f"description must be 1-1024 chars (has {len(desc)})")
    if re.search(r"<[A-Za-z/][^>]*>", desc):
        errs.append("description must not contain XML/HTML tags")
    if len(fm.get("compatibility", "")) > 500:
        errs.append("compatibility must be <= 500 chars")
    extra = keys - ALLOWED_KEYS
    if extra:
        errs.append(f"non-standard frontmatter keys {sorted(extra)} (portable skills use only {sorted(ALLOWED_KEYS)})")
    body_lines = text[text.find("\n---", 4) + 4:].count("\n")
    if body_lines > 500:
        errs.append(f"SKILL.md body has {body_lines} lines; keep it under 500 and move detail to references/")
    return errs


# --------------------------------------------------------------------------- sync
def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def diff_dirs(src: Path, dst: Path) -> list[str]:
    if dst.is_symlink():
        return [] if dst.resolve() == src.resolve() else [f"{dst} is a symlink to another location"]
    if not dst.exists():
        return [f"{dst} missing"]
    s_files, d_files = set(skill_files(src)), set(skill_files(dst))
    out = [f"missing in copy: {f}" for f in sorted(s_files - d_files)]
    out += [f"extra in copy: {f}" for f in sorted(d_files - s_files)]
    out += [f"differs: {f}" for f in sorted(s_files & d_files)
            if not filecmp.cmp(src / f, dst / f, shallow=False)]
    return out


def copy_skill(src: Path, dst: Path, link: bool) -> None:
    if dst.is_symlink() or (dst.exists() and link):
        dst.unlink() if dst.is_symlink() else shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if link:
        dst.symlink_to(os.path.relpath(src, dst.parent), target_is_directory=True)
        return
    wanted = set(skill_files(src))
    if dst.exists():
        for p in sorted(dst.rglob("*"), reverse=True):
            rel = p.relative_to(dst).as_posix()
            if p.is_file() and rel not in wanted:
                p.unlink()
            elif p.is_dir() and not any(p.iterdir()):
                p.rmdir()
    for rel in wanted:
        s, d = src / rel, dst / rel
        if d.exists() and filecmp.cmp(s, d, shallow=False):
            continue
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s, d)


def write_fallback(root: Path, src: Path, check: bool) -> list[str]:
    problems = []
    gh = root / ".github"
    prompt_src = (src / "adapters" / PROMPT_NAME).read_text(encoding="utf-8")
    prompt_dst = gh / "prompts" / PROMPT_NAME
    snippet = (src / "adapters" / "copilot-instructions.snippet.md").read_text(encoding="utf-8").strip()
    instr = gh / "copilot-instructions.md"
    current = instr.read_text(encoding="utf-8") if instr.exists() else ""
    if MARK_START in current:
        new = re.sub(re.escape(MARK_START) + r".*?" + re.escape(MARK_END), snippet, current, flags=re.S)
    else:
        new = (current.rstrip() + "\n\n" if current.strip() else "# Copilot instructions\n\n") + snippet + "\n"
    if check:
        if not prompt_dst.exists() or prompt_dst.read_text(encoding="utf-8") != prompt_src:
            problems.append(f"{prompt_dst} missing or outdated")
        if new != current:
            problems.append(f"{instr} missing the skill pointer")
        return problems
    prompt_dst.parent.mkdir(parents=True, exist_ok=True)
    prompt_dst.write_text(prompt_src, encoding="utf-8")
    instr.write_text(new, encoding="utf-8")
    return problems


def make_zip(src: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in skill_files(src):
            z.write(src / rel, f"{NAME}/{rel}")
    return dest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", action="append", help="project root to install into (default: repo containing the skill)")
    ap.add_argument("--only", choices=["claude", "copilot"])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--link", action="store_true")
    ap.add_argument("--no-fallback", action="store_true", help="do not write the Copilot prompt file / instructions line")
    ap.add_argument("--zip", nargs="?", const="", default=None, metavar="PATH")
    ap.add_argument("--validate", action="store_true")
    a = ap.parse_args()

    if is_copy(SKILL_DIR):
        print(f"This is a synced copy ({SKILL_DIR}). Edit and run sync_skill.py from the canonical folder instead.",
              file=sys.stderr)
        return 2
    errs = validate(SKILL_DIR)
    if errs:
        print("❌ SKILL.md validation failed:\n  - " + "\n  - ".join(errs), file=sys.stderr)
        return 1
    print(f"✅ SKILL.md valid ({NAME})")
    if a.validate:
        return 0
    if a.zip is not None:
        dest = Path(a.zip) if a.zip else SKILL_DIR.parent / "dist" / f"{NAME}.zip"
        print(f"📦 ZIP for claude.ai → {make_zip(SKILL_DIR, dest.resolve())}")
        return 0

    roots = [Path(t).resolve() for t in a.target] if a.target else [SKILL_DIR.parent]
    kinds = {"claude": ".claude/skills", "copilot": ".github/skills"}
    if a.only:
        kinds = {a.only: kinds[a.only]}
    problems: list[str] = []
    for root in roots:
        for kind, sub in kinds.items():
            dst = root / sub / NAME
            if a.check:
                d = diff_dirs(SKILL_DIR, dst)
                problems += [f"[{kind}] {x}" for x in d]
                print(f"{'✅' if not d else '❌'} {dst}" + ("" if not d else f" ({len(d)} differences)"))
            else:
                copy_skill(SKILL_DIR, dst, a.link)
                print(f"{'🔗' if a.link else '📁'} {dst}")
        if "copilot" in kinds and not a.no_fallback:
            p = write_fallback(root, SKILL_DIR, a.check)
            problems += p
            if not a.check:
                print(f"📝 {root / '.github' / 'prompts' / PROMPT_NAME}\n📝 {root / '.github' / 'copilot-instructions.md'}")
            else:
                print(f"{'✅' if not p else '❌'} Copilot fallback (prompt file + instructions)")
    if a.check and problems:
        print("\n".join(problems[:40]), file=sys.stderr)
        print("Out of sync — run: python3 " + str(Path(__file__).relative_to(SKILL_DIR.parent)), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
