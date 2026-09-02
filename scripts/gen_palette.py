"""Generate the Ganymede colour ramps and emit site/assets/tokens.css.

Ramps are built in OKLCH so the steps are perceptually even, then converted to
sRGB hex. Hand-tuned hex cannot hold that property across eleven steps, and the
one property the risk ramp must have -- monotonic lightness, so it survives
greyscale and deuteranopia -- is a lightness invariant, not a hue one.

Run `python scripts/gen_palette.py --check` to re-emit and verify contrast.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "assets" / "tokens.css"

STEPS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]


def _srgb_encode(c: float) -> float:
    c = max(0.0, min(1.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def oklch_to_hex(L: float, C: float, H: float) -> str:
    a, b = C * math.cos(math.radians(H)), C * math.sin(math.radians(H))
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    rgb = (
        4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
        -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
        -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_,
    )
    return "#" + "".join(f"{round(_srgb_encode(c) * 255):02x}" for c in rgb)


def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_colour: str) -> float:
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(fg: str, bg: str) -> float:
    a, b = luminance(fg), luminance(bg)
    lo, hi = sorted((a, b))
    return (hi + 0.05) / (lo + 0.05)


def ramp(lightness: list[float], chroma: list[float], hue: list[float]) -> dict[int, str]:
    return {s: oklch_to_hex(l, c, h) for s, l, c, h in zip(STEPS, lightness, chroma, hue)}


def _lerp(a: float, b: float, n: int = 11) -> list[float]:
    return [a + (b - a) * i / (n - 1) for i in range(n)]


# Lightness curve shared by every chromatic ramp: even in OKLab L, which is what
# makes a step from 400 to 500 read as the same jump as 700 to 800.
L_CURVE = [0.972, 0.938, 0.878, 0.806, 0.726, 0.646, 0.566, 0.482, 0.398, 0.312, 0.252]

RAMPS = {
    # Ice -- the system's own signal. Chroma peaks mid-ramp where teal can carry it.
    "ice": ramp(L_CURVE,
                [0.020, 0.036, 0.062, 0.086, 0.104, 0.112, 0.104, 0.088, 0.070, 0.052, 0.041],
                _lerp(186.0, 178.0)),
    # Ember -- magnitude of a prediction. Hue rotates amber -> rust as it darkens;
    # the rotation buys discrimination that lightness alone cannot at 11 steps.
    "ember": ramp(L_CURVE,
                  [0.024, 0.044, 0.076, 0.108, 0.130, 0.142, 0.138, 0.124, 0.104, 0.082, 0.068],
                  _lerp(85.0, 38.0)),
    # Outcome pair -- realised results only, never a prediction.
    "kept": ramp(L_CURVE,
                 [0.022, 0.040, 0.068, 0.094, 0.114, 0.124, 0.118, 0.100, 0.082, 0.062, 0.050],
                 _lerp(155.0, 148.0)),
    "broken": ramp(L_CURVE,
                   [0.022, 0.042, 0.072, 0.100, 0.124, 0.138, 0.134, 0.118, 0.098, 0.076, 0.062],
                   _lerp(32.0, 24.0)),
    # Slate -- all structure. Warm paper at the light end, cool ink at the dark end,
    # which reconciles the two neutrals the old case/desk pages each had separately.
    "slate": ramp([0.976, 0.951, 0.902, 0.826, 0.740, 0.652, 0.556, 0.452, 0.352, 0.248, 0.176],
                  [0.004, 0.005, 0.006, 0.008, 0.010, 0.012, 0.014, 0.016, 0.018, 0.020, 0.020],
                  _lerp(80.0, 258.0)),
}

# The risk ramp: eleven ember stops indexed 0..100 by decile of p(worsen).
# Deliberately the same family as ember -- a probability never gets its own hue.
RISK = [RAMPS["ember"][s] for s in STEPS]

# Contrast pairs that must hold. (fg, bg, minimum, why)
GATES = [
    ("slate.900", "slate.50", 4.5, "body text on light ground"),
    ("slate.700", "slate.50", 4.5, "muted text on light ground"),
    ("slate.100", "slate.950", 4.5, "body text on dark ground"),
    ("slate.400", "slate.950", 4.5, "muted text on dark ground"),
    ("ice.700", "slate.50", 4.5, "link on light ground"),
    ("ice.300", "slate.950", 4.5, "link on dark ground"),
    ("ember.800", "slate.50", 4.5, "prediction figure on light ground"),
    ("ember.300", "slate.950", 4.5, "prediction figure on dark ground"),
    ("kept.700", "slate.50", 4.5, "kept-promise text, light"),
    ("kept.300", "slate.950", 4.5, "kept-promise text, dark"),
    ("broken.700", "slate.50", 4.5, "broken-promise text, light"),
    ("broken.300", "slate.950", 4.5, "broken-promise text, dark"),
    ("ice.600", "slate.50", 3.0, "focus ring / UI bound, light"),
    ("ice.400", "slate.950", 3.0, "focus ring / UI bound, dark"),
]


def resolve(ref: str) -> str:
    family, step = ref.split(".")
    return RAMPS[family][int(step)]


def check() -> list[str]:
    failures = []
    for fg, bg, floor, why in GATES:
        ratio = contrast(resolve(fg), resolve(bg))
        if ratio < floor:
            failures.append(f"{fg} on {bg} = {ratio:.2f}:1, needs {floor}:1 ({why})")
    # The risk ramp must be monotonic in luminance or it stops encoding magnitude.
    lums = [luminance(c) for c in RISK]
    if any(b >= a for a, b in zip(lums, lums[1:])):
        failures.append("risk ramp is not monotonically darkening -- it no longer encodes magnitude")
    return failures


# Semantic layer. Each name says what the colour is *for*; nothing in the site's
# CSS may reference a raw ramp step, which is what keeps the meanings enforceable.
SEMANTIC = {
    "light": {
        "ground": "slate.50", "surface": "slate.100", "surface-2": "slate.200",
        "line": "slate.300", "line-strong": "slate.400",
        "text": "slate.900", "muted": "slate.700", "faint": "slate.600",
        "signal": "ice.700", "signal-strong": "ice.800", "signal-quiet": "ice.200",
        "on-signal": "slate.50",
        "predict": "ember.800", "predict-quiet": "ember.200",
        "kept": "kept.700", "kept-quiet": "kept.200",
        "broken": "broken.700", "broken-quiet": "broken.200",
        "focus": "ice.600",
    },
    "dark": {
        "ground": "slate.950", "surface": "slate.900", "surface-2": "slate.800",
        "line": "slate.800", "line-strong": "slate.700",
        "text": "slate.100", "muted": "slate.400", "faint": "slate.500",
        "signal": "ice.300", "signal-strong": "ice.200", "signal-quiet": "ice.900",
        "on-signal": "slate.950",
        "predict": "ember.300", "predict-quiet": "ember.900",
        "kept": "kept.300", "kept-quiet": "kept.900",
        "broken": "broken.300", "broken-quiet": "broken.900",
        "focus": "ice.400",
    },
}

STATIC = """
  /* ---- type ------------------------------------------------------------ */
  --font-display:"Newsreader",Georgia,"Times New Roman",serif;
  --font-ui:"Hanken Grotesk",system-ui,-apple-system,"Segoe UI",sans-serif;
  --font-mono:"IBM Plex Mono",ui-monospace,"SF Mono",Menlo,monospace;

  /* 1.200 minor third from a 16px base; --fs-0 is body */
  --fs--2:0.694rem; --fs--1:0.833rem; --fs-0:1rem;    --fs-1:1.2rem;
  --fs-2:1.44rem;   --fs-3:1.728rem;  --fs-4:2.074rem; --fs-5:2.488rem;
  --fs-6:2.986rem;  --fs-7:3.583rem;  --fs-8:4.3rem;

  --lh-tight:1.06; --lh-snug:1.3; --lh-normal:1.6; --lh-loose:1.75;
  --tracking-tight:-0.018em; --tracking-normal:0; --tracking-wide:0.08em;

  /* ---- space: 4pt base ------------------------------------------------- */
  --s-1:4px;  --s-2:8px;  --s-3:12px; --s-4:16px; --s-5:20px; --s-6:24px;
  --s-7:32px; --s-8:40px; --s-9:56px; --s-10:72px; --s-11:96px; --s-12:128px;

  /* ---- form ------------------------------------------------------------ */
  --r-1:4px; --r-2:7px; --r-3:11px; --r-4:16px; --r-full:999px;
  --measure:65ch; --measure-tight:52ch;

  /* ---- motion ---------------------------------------------------------- */
  --dur-fast:120ms; --dur:220ms; --dur-slow:420ms;
  --ease-out:cubic-bezier(.2,.8,.2,1);
  --ease-in-out:cubic-bezier(.6,0,.2,1);
"""


def emit() -> str:
    out = [
        "/* Ganymede design tokens.",
        " * GENERATED by scripts/gen_palette.py -- do not edit by hand.",
        " * Ramps are built in OKLCH for perceptually even steps; every pair in the",
        " * script's GATES list is contrast-verified on generation.",
        " */",
        "",
        ":root {",
        "  /* ---- ramps ----------------------------------------------------------- */",
    ]
    for family, stops in RAMPS.items():
        for step, hexv in stops.items():
            out.append(f"  --{family}-{step}:{hexv};")
        out.append("")
    out.append("  /* ---- risk ramp: p(worsen) by decile. Ember only -- a probability")
    out.append("     never gets red/amber/green, which would invent categories from a scalar. */")
    for i, hexv in enumerate(RISK):
        out.append(f"  --risk-{i * 10}:{hexv};")
    out.append(STATIC)
    out.append("}")
    out.append("")

    for theme, mapping in SEMANTIC.items():
        selector = (
            ':root, :root[data-theme="light"]' if theme == "light" else ':root[data-theme="dark"]'
        )
        out.append(f"/* ---- semantic: {theme} ---- */")
        out.append(f"{selector} {{")
        out.append(f"  color-scheme:{theme};")
        for name, ref in mapping.items():
            out.append(f"  --{name}:{resolve(ref)};")
        out.append(_shadows(theme))
        out.append("}")
        out.append("")

    dark = SEMANTIC["dark"]
    out.append("@media (prefers-color-scheme:dark) {")
    out.append('  :root:not([data-theme="light"]) {')
    out.append("    color-scheme:dark;")
    for name, ref in dark.items():
        out.append(f"    --{name}:{resolve(ref)};")
    out.append("  " + _shadows("dark").strip())
    out.append("  }")
    out.append("}")
    out.append("")
    return "\n".join(out)


def _shadows(theme: str) -> str:
    if theme == "light":
        return ("  --shadow-1:0 1px 2px rgba(20,26,40,.06);\n"
                "  --shadow-2:0 1px 2px rgba(20,26,40,.06),0 2px 8px rgba(20,26,40,.05);\n"
                "  --shadow-3:0 2px 4px rgba(20,26,40,.06),0 12px 32px rgba(20,26,40,.10);")
    return ("  --shadow-1:0 1px 2px rgba(0,0,0,.45);\n"
            "  --shadow-2:0 1px 2px rgba(0,0,0,.4),0 4px 16px rgba(0,0,0,.32);\n"
            "  --shadow-3:0 2px 6px rgba(0,0,0,.45),0 16px 40px rgba(0,0,0,.42);")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify contrast gates and that the emitted file is current")
    args = ap.parse_args()

    failures = check()
    for f in failures:
        print(f"  FAIL {f}")
    if failures:
        print(f"contrast gate FAILED: {len(failures)} pair(s)")
        return 1

    css = emit()
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != css:
            print("tokens.css is stale -- run `python scripts/gen_palette.py`")
            return 1
        print(f"palette OK: {len(GATES)} contrast gates pass, tokens.css current")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(css, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} -- {len(GATES)} contrast gates pass")
    for fg, bg, floor, why in GATES:
        print(f"  {contrast(resolve(fg), resolve(bg)):5.2f}:1  {fg:<12} on {bg:<12} ({why})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
