"""The contrast math the palette gates rest on, against published WCAG values."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import gen_palette  # noqa: E402


def test_contrast_matches_wcag_reference_values():
    assert round(gen_palette.contrast("#000000", "#ffffff"), 2) == 21.0
    assert round(gen_palette.contrast("#777777", "#ffffff"), 2) == 4.48   # WebAIM reference
    assert gen_palette.contrast("#123456", "#123456") == 1.0


def test_on_risk_picks_the_readable_end():
    for c in gen_palette.RISK:
        assert gen_palette.contrast(gen_palette.on_risk(c), c) >= 4.5


def test_all_gates_pass():
    assert gen_palette.check() == []
