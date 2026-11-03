#!/usr/bin/env python3
"""Package hygiene checks for the ee-review skill drop.

Not required for day-to-day schematic/netlist/BOM reviews. CI and maintainers
run this to keep VERSION/CHANGELOG aligned and the PPT template desensitized.
"""

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Build needles without embedding full brand tokens as contiguous literals in
# this file (so the text-tree scan does not false-positive on this script).
_BRAND_PARTS = (("Agi", "lian"), ("Sof", "east"), ("AGI", "LIAN"), ("sof", "east"))
_BRAND_NEEDLES = ["".join(parts) for parts in _BRAND_PARTS]
BRAND_RE = re.compile(("|".join(re.escape(n) for n in _BRAND_NEEDLES)).encode(), re.I)
BRAND_TEXT_RE = re.compile("|".join(re.escape(n) for n in _BRAND_NEEDLES), re.I)
CHANGELOG_HEAD_RE = re.compile(r"^##\s+(\d+\.\d+\.\d+)\b", re.M)
SKIP_BRAND_SCAN = {"scripts/check_package_hygiene.py"}


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}", file=sys.stderr)


def ok(msg: str) -> None:
    print(f"[OK] {msg}")


def check_version_changelog() -> bool:
    version_path = ROOT / "VERSION"
    changelog_path = ROOT / "CHANGELOG.md"
    license_path = ROOT / "LICENSE"
    if not version_path.is_file():
        fail("VERSION missing")
        return False
    if not changelog_path.is_file():
        fail("CHANGELOG.md missing")
        return False
    if not license_path.is_file():
        fail("LICENSE missing")
        return False
    version = version_path.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        fail(f"VERSION not semver x.y.z: {version!r}")
        return False
    changelog = changelog_path.read_text(encoding="utf-8")
    match = CHANGELOG_HEAD_RE.search(changelog)
    if not match:
        fail("CHANGELOG.md has no ## x.y.z heading")
        return False
    head = match.group(1)
    if head != version:
        fail(f"VERSION {version} != latest CHANGELOG heading {head}")
        return False
    ok(f"VERSION/CHANGELOG/LICENSE aligned at {version}")
    return True


def check_pptx_brands() -> bool:
    pptx = ROOT / "assets" / "review-slide-template.pptx"
    if not pptx.is_file():
        fail(f"missing template: {pptx}")
        return False
    hits: list[str] = []
    with zipfile.ZipFile(pptx) as zf:
        for name in zf.namelist():
            data = zf.read(name)
            if BRAND_RE.search(data):
                hits.append(name)
    if hits:
        fail("company brand traces in PPT template: " + ", ".join(hits[:12]))
        return False
    ok("PPT template has no Agilian/Sofeast traces")
    return True


def check_text_tree_brands() -> bool:
    skip_dirs = {".git", ".venv", "node_modules", "__pycache__", "datasheets"}
    hits: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".pptx", ".pdf", ".pyc"}:
            continue
        rel = str(path.relative_to(ROOT))
        if rel in SKIP_BRAND_SCAN:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if BRAND_TEXT_RE.search(text):
            hits.append(rel)
    if hits:
        fail("brand traces in text files: " + ", ".join(hits[:20]))
        return False
    ok("text tree has no Agilian/Sofeast traces")
    return True


def check_skill_size() -> bool:
    skill = ROOT / "SKILL.md"
    size = skill.stat().st_size
    # Soft budget: keep the agent entrypoint lean; details stay in references/.
    if size > 24_000:
        fail(f"SKILL.md is {size} bytes; keep under 24KB and push detail to references/")
        return False
    ok(f"SKILL.md size {size} bytes")
    return True


def check_acceptance_smoke() -> bool:
    xml = ROOT / "examples" / "acceptance-demo" / "demo_board.xml"
    review = ROOT / "examples" / "acceptance-demo" / "ee-review" / "review.json"
    deck = ROOT / "examples" / "acceptance-demo" / "ee-review" / "deck.json"
    for path in (xml, review, deck):
        if not path.is_file():
            fail(f"acceptance fixture missing: {path.relative_to(ROOT)}")
            return False
    import subprocess

    parse = ROOT / "scripts" / "parse_kicad_netlist.py"
    gen_report = ROOT / "scripts" / "generate_report.py"
    gen_pptx = ROOT / "scripts" / "generate_pptx.py"
    out_html = ROOT / "examples" / "acceptance-demo" / "ee-review" / "_ci_smoke.html"
    out_pptx = ROOT / "examples" / "acceptance-demo" / "ee-review" / "_ci_smoke.pptx"
    cmds = [
        [sys.executable, str(parse), str(xml)],
        [sys.executable, str(gen_report), str(review), str(out_html)],
        [sys.executable, str(gen_pptx), str(deck), "-o", str(out_pptx)],
    ]
    for cmd in cmds:
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if proc.returncode != 0:
            fail("cmd failed: " + " ".join(cmd))
            sys.stderr.write(proc.stdout)
            sys.stderr.write(proc.stderr)
            return False
    for path in (out_html, out_pptx):
        if path.is_file():
            path.unlink()
    ok("acceptance parse/report/pptx smoke")
    return True


def main() -> int:
    checks = [
        check_version_changelog,
        check_pptx_brands,
        check_text_tree_brands,
        check_skill_size,
        check_acceptance_smoke,
    ]
    bad = 0
    for check in checks:
        if not check():
            bad += 1
    if bad:
        print(f"{bad} hygiene check(s) failed", file=sys.stderr)
        return 1
    print("all package hygiene checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
