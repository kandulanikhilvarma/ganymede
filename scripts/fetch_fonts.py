"""Vendor the site typefaces into site/assets/fonts/ and point the pages at them.

Google Fonts costs every page a render-blocking stylesheet behind two
preconnects, and puts a third party in the path of first paint on a site whose
whole argument is about what you can verify. All three families are OFL, so
they live in the repo instead.

Fraunces carries the argument and Geist carries the readout. The contrast
between an editorial serif and a grotesk built for data is the concept.

Only latin and latin-ext are kept. The site is English with euro amounts and
European names, and shipping Cyrillic and Vietnamese to cover neither is a
default nobody checks.

    python scripts/fetch_fonts.py           # download, write fonts.css, fix preloads
    python scripts/fetch_fonts.py --check   # verify what the pages reference exists
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import pathlib
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "assets" / "fonts"

CSS_URL = (
    "https://fonts.googleapis.com/css2"
    "?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;0,9..144,600;1,9..144,400"
    "&family=Geist:wght@300;400;500;600;700"
    "&family=Geist+Mono:wght@400;500;600"
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
SRC_LOCAL = re.compile(r"url\('([^']+\.woff2)'\)")

PRELOAD_START = "<!-- font-preload -->"
PRELOAD_END = "<!-- /font-preload -->"
PRELOAD_TAGS = re.compile(r'(?:[ \t]*<link rel="preload" as="font"[^>]*>\n?)+')


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def _preload_names(files: list[str]) -> list[str]:
    """The two faces worth preloading: body text and the display serif."""
    ui = next((f for f in files if f.startswith("geist-latin")), None)
    display = next((f for f in files if f.startswith("fraunces-latin")), None)
    return [f for f in (ui, display) if f]


def rewrite_preloads(files: list[str]) -> int:
    """Point every page at files that actually exist.

    Preload hrefs are content-hashed, so changing a typeface renames them and
    any hand-written href silently 404s. That happened once. Generating the
    tags from what is on disk is the only version that stays true.
    """
    picks = _preload_names(files)
    if not picks:
        return 0
    touched = 0
    for f in sorted(glob.glob(str(ROOT / "site" / "*.html"))):
        path = pathlib.Path(f)
        html = path.read_text(encoding="utf-8")
        prefix = "/assets" if path.stem == "404" else "assets"
        tags = "\n".join(
            '<link rel="preload" as="font" type="font/woff2" crossorigin '
            f'href="{prefix}/fonts/{name}">' for name in picks)
        block = f"{PRELOAD_START}\n{tags}\n{PRELOAD_END}"

        if PRELOAD_START in html:
            a = html.index(PRELOAD_START)
            b = html.index(PRELOAD_END) + len(PRELOAD_END)
            new = html[:a] + block + html[b:]
        elif PRELOAD_TAGS.search(html):
            new = PRELOAD_TAGS.sub(block + "\n", html, count=1)
        else:
            anchor = f'<link rel="stylesheet" href="{prefix}/fonts/fonts.css">'
            new = html.replace(anchor, block + "\n" + anchor, 1)

        if new != html:
            path.write_text(new, encoding="utf-8")
            touched += 1
    return touched


def check() -> int:
    css_path = OUT / "fonts.css"
    files = sorted(p.name for p in OUT.glob("*.woff2"))
    if not css_path.exists() or not files:
        print("fonts are not vendored, run `python scripts/fetch_fonts.py`")
        return 1

    missing = [m for m in SRC_LOCAL.findall(css_path.read_text(encoding="utf-8"))
               if not (OUT / m).exists()]
    if missing:
        print(f"fonts.css references missing files: {', '.join(missing)}")
        return 1

    # every preload href a page asks for has to exist, or first paint stalls
    stale = []
    for f in sorted(glob.glob(str(ROOT / "site" / "*.html"))):
        html = pathlib.Path(f).read_text(encoding="utf-8")
        for href in re.findall(r'<link rel="preload" as="font"[^>]*href="([^"]+)"', html):
            name = href.rsplit("/", 1)[-1]
            if name not in files:
                stale.append(f"{pathlib.Path(f).name} -> {name}")
    if stale:
        print("stale font preloads:\n  " + "\n  ".join(stale))
        print("run `python scripts/fetch_fonts.py` to regenerate them")
        return 1

    total = sum((OUT / f).stat().st_size for f in files)
    print(f"fonts OK: {len(files)} woff2 files, {total // 1024} KB, preloads current")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.check:
        return check()

    OUT.mkdir(parents=True, exist_ok=True)
    css = _get(CSS_URL).decode("utf-8")

    faces, by_hash = {}, {}
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

        # These are variable fonts, so Google emits one @font-face per weight
        # all pointing at the same file. Collapsing them into one rule with a
        # weight range is what lets the weight axis actually interpolate.
        key = (vals["font-family"], vals["font-style"], by_hash[digest])
        face = faces.setdefault(key, {"unicode-range": vals["unicode-range"], "w": set()})
        face["w"].add(int(vals["font-weight"].split()[0]))

    rules = []
    for (family, style, slug), face in faces.items():
        ws = sorted(face["w"])
        weight = f"{ws[0]} {ws[-1]}" if len(ws) > 1 else str(ws[0])
        rules.append(
            "@font-face {\n"
            f"  font-family: {family};\n"
            f"  font-style: {style};\n"
            f"  font-weight: {weight};\n"
            "  font-display: swap;\n"
            f"  src: url('{slug}') format('woff2');\n"
            f"  unicode-range: {face['unicode-range']};\n"
            "}")

    (OUT / "fonts.css").write_text(
        "/* Vendored from Google Fonts by scripts/fetch_fonts.py.\n"
        " * All three families are OFL. Latin and latin-ext subsets only.\n"
        " * Regenerate rather than editing by hand. */\n\n"
        + "\n\n".join(rules) + "\n", encoding="utf-8")

    files = sorted(by_hash.values())
    saved = sum((OUT / f).stat().st_size for f in files)
    print(f"wrote {len(rules)} rules over {len(files)} files, {saved // 1024} KB")
    print(f"  preloads rewritten in {rewrite_preloads(files)} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
