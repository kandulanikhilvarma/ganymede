"""Render the social card at site/assets/img/og.png.

Same ingredients as the hero: the mark, the headline, and real borrower
trajectories from site/data/trajectories.json. A social card built from stock
shapes would be the one image on the site that is not evidence of anything.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "assets" / "img" / "og.png"
DATA = ROOT / "site" / "data" / "trajectories.json"

W, H = 1200, 630
GROUND = (11, 17, 26)        # slate-950, the dark ground
TEXT = (239, 239, 235)       # slate-100
MUTED = (154, 163, 178)
ICE = (124, 210, 197)        # ice-300
EMBER = (236, 180, 111)      # ember-300
FAINT = (91, 101, 119)


def _font(names: list[str], size: int) -> ImageFont.FreeTypeFont:
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def trajectories(d: ImageDraw.ImageDraw) -> None:
    """The field, in the right half, behind nothing."""
    if not DATA.exists():
        return
    t = json.loads(DATA.read_text(encoding="utf-8"))
    quiet = list(t["quiet"][:160:4])
    bend = list(t["bending"][:60:3])
    # Interleave, so the bending paths run through the field instead of stacking
    # at the bottom -- the picture is "most are quiet, a few are not", and the
    # concatenation order would say something else.
    rows = []
    while quiet or bend:
        for _ in range(3):
            if quiet:
                rows.append((quiet.pop(0), False))
        if bend:
            rows.append((bend.pop(0), True))

    x0, x1 = 300, W
    lanes = len(rows)
    lane_h = H / lanes
    for i, (path, bend) in enumerate(rows):
        base = lane_h * (i + 0.5)
        n = len(path)
        pts = [
            (x0 + (j / (n - 1)) * (x1 - x0), base - min(v, 6) / 6 * lane_h * 2.4)
            for j, v in enumerate(path)
        ]
        d.line(pts, fill=EMBER if bend else FAINT, width=2 if bend else 1, joint="curve")


def mark(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int) -> None:
    """The terminator line: a disc split by a bent boundary."""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(19, 44, 43))
    # The lit half, clipped to the disc by sampling the boundary per scanline.
    for y in range(-r, r + 1):
        half = math.sqrt(max(0.0, r * r - y * y))
        t = (y + r) / (2 * r)
        # an S-curve boundary rather than a straight terminator
        bx = math.sin(t * math.pi * 1.15 - 0.18) * r * 0.42
        left = max(-half, bx)
        if left < half:
            d.line([(cx + left, cy + y), (cx + half, cy + y)], fill=ICE)


def main() -> int:
    img = Image.new("RGB", (W, H), GROUND)
    d = ImageDraw.Draw(img)

    trajectories(d)
    # fade the field out under the text column
    fade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fade)
    for x in range(0, 900):
        a = int(255 * max(0.0, min(1.0, (900 - x) / 560)) ** 0.85)
        fd.line([(x, 0), (x, H)], fill=GROUND + (a,))
    img = Image.alpha_composite(img.convert("RGBA"), fade).convert("RGB")
    d = ImageDraw.Draw(img)

    serif = _font(["Georgia.ttf", "georgia.ttf", "times.ttf", "DejaVuSerif.ttf"], 62)
    serif_i = _font(["Georgiai.ttf", "georgiai.ttf", "timesi.ttf", "DejaVuSerif-Italic.ttf"], 62)
    sans = _font(["segoeui.ttf", "Arial.ttf", "arial.ttf", "DejaVuSans.ttf"], 25)
    mono = _font(["consola.ttf", "cour.ttf", "DejaVuSansMono.ttf"], 20)

    mark(d, 96, 92, 26)
    d.text((136, 78), "Ganymede", font=_font(["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"], 27), fill=TEXT)

    y = 190
    d.text((72, y), "Predict the wobble.", font=serif, fill=TEXT)
    y += 76
    w_shape = d.textlength("Shape", font=serif_i)
    d.text((72, y), "Shape", font=serif_i, fill=EMBER)
    d.text((72 + w_shape + 14, y), "the call.", font=serif, fill=TEXT)
    y += 76
    d.text((72, y), "Keep the book.", font=serif, fill=TEXT)

    d.text((72, 460),
           "Recovery intelligence for lending,\nreceivables and investor-funded credit books.",
           font=sans, fill=MUTED, spacing=8)

    d.text((72, 560), "risk lens  ·  coach lens  ·  one outcome loop", font=mono, fill=ICE)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)}  {OUT.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
