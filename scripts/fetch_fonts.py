"""Vendor the three site typefaces into site/assets/fonts/.

Google Fonts costs the site two preconnects and a render-blocking stylesheet on
every page, and puts a third party in the path of every first paint. The faces
are all OFL, so they can simply live in the repo.

Only the latin and latin-ext subsets are kept: the site is in English with euro
amounts and European names, and shipping Cyrillic and Vietnamese to every
visitor to cover neither is the kind of default nobody checks.

    python scripts/fetch_fonts.py          # download and write fonts.css
    python scripts/fetch_fonts.py --check   # verify the vendored files are present
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "assets" / "fonts"

CSS_URL = (
    "https://fonts.googleapis.com/css2"
    "?family=Hanken+Grotesk:wght@400;500;600;700"
    "&family=Newsreader:ital,wght@0,400;0,500;1,400"
    "&family=IBM+Plex+Mono:wght@400;500;600"
    "&display=swap"
)
# A modern UA is what makes Google serve woff2 rather than legacy formats.
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

KEEP_SUBSETS = {"latin", "latin-ext"}
BLOCK = re.compile(r"/\*\s*([\w-]+)\s*\*/\s*(@font-face\s*\{.*?\})", re.S)
FIELD = {k: re.compile(rf"{k}:\s*([^;]+);") for k in
         ("font-family", "font-style", "font-weight", "unicode-range")}
SRC = re.compile(r"url\((https://[^)]+\.woff2)\)")


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    css_path = OUT / "fonts.css"
    if args.check:
        files = sorted(OUT.glob("*.woff2"))
        if not css_path.exists() or not files:
            print("fonts are not vendored -- run `python scripts/fetch_fonts.py`")
            return 1
        missing = [m for m in SRC_LOCAL.findall(css_path.read_text(encoding="utf-8"))
                   if not (OUT / m).exists()]
        if missing:
            print(f"fonts.css references missing files: {', '.join(missing)}")
            return 1
        total = sum(f.stat().st_size for f in files)
        print(f"fonts OK: {len(files)} woff2 files, {total // 1024} KB total")
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    css = _get(CSS_URL).decode("utf-8")

    # These are variable fonts: Google serves the same file for every weight in
    # a family, so naming by weight would ship four identical copies of Hanken
    # Grotesk. Deduplicate on content and point the faces at one file.
    rules, by_hash = [], {}
    for subset, block in BLOCK.findall(css):
        if subset not in KEEP_SUBSETS:
            continue
        vals = {k: p.search(block).group(1).strip() for k, p in FIELD.items()}
        url = SRC.search(block).group(1)
        family = vals["font-family"].strip("'\"")
        blob = _get(url)
        digest = hashlib.sha256(blob).hexdigest()[:8]
        if digest not in by_hash:
            slug = (f"{family.lower().replace(' ', '-')}"
                    f"{'-italic' if vals['font-style'] == 'italic' else ''}"
                    f"-{subset}-{digest}.woff2")
            (OUT / slug).write_bytes(blob)
            by_hash[digest] = slug
        slug = by_hash[digest]
        rules.append(
            "@font-face {\n"
            f"  font-family: {vals['font-family']};\n"
            f"  font-style: {vals['font-style']};\n"
            f"  font-weight: {vals['font-weight']};\n"
            "  font-display: swap;\n"
            f"  src: url('{slug}') format('woff2');\n"
            f"  unicode-range: {vals['unicode-range']};\n"
            "}"
        )

    css_path.write_text(
        "/* Vendored from Google Fonts by scripts/fetch_fonts.py.\n"
        " * All three families are OFL. Latin and latin-ext subsets only.\n"
        " * Regenerate rather than editing by hand. */\n\n"
        + "\n\n".join(rules) + "\n",
        encoding="utf-8")
    saved = sum((OUT / f).stat().st_size for f in set(by_hash.values()))
    print(f"wrote {len(rules)} faces over {len(by_hash)} files, "
          f"{saved // 1024} KB -> {css_path.relative_to(ROOT)}")
    return 0


SRC_LOCAL = re.compile(r"url\('([^']+\.woff2)'\)")

if __name__ == "__main__":
    sys.exit(main())
