"""The static site, checked without a browser. A renamed page, JSON file or
figure path used to break the site silently; each of these fails instead.

- every internal href/src resolves to a file, and every #anchor to an id
- every JSON file a page or script fetches exists in site/data
- every data-fig names a record that exists and carries provenance
"""

import json
import re
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parent.parent / "site"
PAGES = sorted(SITE.glob("*.html"))
SCRIPTS = sorted((SITE / "assets" / "js").glob("*.js"))

REF = re.compile(r'\b(?:href|src)="([^"]+)"')
IDS = re.compile(r'\bid="([^"]+)"')
FIG = re.compile(r'data-fig="([^"]+)"')
DATA = re.compile(r"""(?:loadData|loadFile)\(\s*['"]([\w-]+)['"]|data/([\w-]+)\.json""")


def _ids(page: Path) -> set[str]:
    return set(IDS.findall(page.read_text(encoding="utf-8")))


def _target(page: Path, ref: str) -> tuple[Path, str]:
    path, _, anchor = ref.partition("#")
    if not path:
        return page, anchor
    base = SITE if path.startswith("/") else page.parent
    t = (base / path.lstrip("/")).resolve()
    if t.is_dir():
        t = t / "index.html"
    elif not t.suffix and t.with_suffix(".html").exists():   # clean URLs
        t = t.with_suffix(".html")
    return t, anchor


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_internal_links_and_anchors_resolve(page):
    broken = []
    for ref in REF.findall(page.read_text(encoding="utf-8")):
        if re.match(r"^(https?:|mailto:|data:)", ref) or "${" in ref:
            continue
        target, anchor = _target(page, ref)
        if not target.exists():
            broken.append(ref)
        elif anchor and target.suffix == ".html" and anchor not in _ids(target):
            # glossary entry ids are built by script from glossary.json keys
            if target.name != "glossary.html":
                broken.append(ref)
    assert not broken, f"{page.name}: {broken}"


def test_every_fetched_data_file_exists():
    names = set()
    for f in [*PAGES, *SCRIPTS]:
        for a, b in DATA.findall(f.read_text(encoding="utf-8")):
            names.add(a or b)
    missing = sorted(n for n in names if not (SITE / "data" / f"{n}.json").exists())
    assert names and not missing, missing


def _dig(obj, path):
    for k in path.split("."):
        obj = obj.get(k) if isinstance(obj, dict) else None
    return obj


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_every_figure_has_a_record_with_provenance(page):
    bad = []
    for ref in FIG.findall(page.read_text(encoding="utf-8")):
        name, _, path = ref.partition(":")
        rec = _dig(json.loads((SITE / "data" / f"{name}.json").read_text(encoding="utf-8")), path)
        if not (isinstance(rec, dict) and "provenance" in rec):
            bad.append(ref)
    assert not bad, f"{page.name}: {bad}"
