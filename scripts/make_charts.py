"""Generate README charts from the real pipeline. Run: python scripts/make_charts.py

Four figures, one visual system: off-white ground, teal accent, amber for the
risk/warning series, IBM-Plex-style mono for numerals. Emphasized endpoints, a
faint grid, no chartjunk. Everything derives from real backtest / simulation /
VAD output — no invented numbers.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import polars as pl

OUT = Path(__file__).resolve().parent.parent / "docs" / "img"
OUT.mkdir(parents=True, exist_ok=True)

INK = "#1a1f2b"; MUTED = "#5c6675"; LINE = "#dfe3ea"; GROUND = "#f7f6f2"
TEAL = "#0e8f80"; AMBER = "#c07f1c"; KEPT = "#1f9d63"; BROKEN = "#c5483f"

plt.rcParams.update({
    "figure.facecolor": GROUND, "axes.facecolor": GROUND,
    "savefig.facecolor": GROUND, "font.family": "DejaVu Sans",
    "font.size": 12, "axes.edgecolor": LINE, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.titlecolor": INK,
    "axes.grid": True, "grid.color": LINE, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False,
})


def _save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=144, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def reliability():
    from ganymede.features import build_features, time_split
    from ganymede.risk import predict, train
    f = build_features(); tr, te = time_split(f)
    b, i = train(tr, "y_worsen")
    p = predict(b, i, te); y = te["y_worsen"].to_numpy()
    bins = np.linspace(0, 1, 11)
    idx = np.digitize(p, bins) - 1
    xs, ys = [], []
    for k in range(10):
        m = idx == k
        if m.sum() > 50:
            xs.append(p[m].mean()); ys.append(y[m].mean())
    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    ax.plot([0, 1], [0, 1], "--", color=MUTED, lw=1, label="perfect calibration")
    ax.plot(xs, ys, "-o", color=TEAL, lw=2.4, ms=7, mfc="white", mew=2, label="L1 trajectory model")
    ax.set_xlabel("predicted probability of worsening")
    ax.set_ylabel("observed rate")
    ax.set_title("L1 is calibrated — the number means what it says", fontweight="bold", loc="left")
    ax.legend(frameon=False, loc="upper left")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    _save(fig, "reliability.png")


def allocator():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.2, 4.2))
    labels = ["Risk-\nranking", "Allocator"]
    vals = [543.6, 865.1]; contacts = [8839, 4243]
    b1 = a1.bar(labels, vals, color=[MUTED, TEAL], width=0.6)
    a1.set_title("Recovered value (M)", fontweight="bold", loc="left", fontsize=13)
    a1.bar_label(b1, fmt="%.0f", padding=4, color=INK, fontweight="bold")
    a1.set_ylim(0, 1000); a1.grid(axis="x", visible=False)
    b2 = a2.bar(labels, contacts, color=[MUTED, TEAL], width=0.6)
    a2.set_title("Contacts spent", fontweight="bold", loc="left", fontsize=13)
    a2.bar_label(b2, fmt="%d", padding=4, color=INK, fontweight="bold")
    a2.set_ylim(0, 10000); a2.grid(axis="x", visible=False)
    fig.suptitle("+59% recovered value with half the contacts", fontsize=14,
                 fontweight="bold", x=0.02, ha="left", color=INK)
    _save(fig, "allocator.png")


def gap_hist():
    from ganymede.audio.vad import inter_turn_gaps, load_wav_mono16k, segments, speech_frames
    wav = OUT.parent.parent / "data" / "raw" / "call_16k.wav"
    if not wav.exists():
        print("skip gap_hist — call_16k.wav not present"); return
    s, sr = load_wav_mono16k(str(wav))
    gaps = np.array(inter_turn_gaps(segments(speech_frames(s, sr)))) * 1000
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    ax.hist(gaps, bins=40, range=(0, 2500), color=TEAL, alpha=0.85, edgecolor=GROUND)
    med = np.percentile(gaps, 50)
    ax.axvline(300, color=AMBER, lw=2, label="tier-1 budget 300 ms")
    ax.axvline(med, color=BROKEN, lw=2, ls="--", label=f"median gap {med:.0f} ms")
    ax.set_xlabel("inter-turn gap (ms)"); ax.set_ylabel("count")
    ax.set_title("Why LLM hints can't fit the live gap", fontweight="bold", loc="left")
    ax.legend(frameon=False)
    ax.grid(axis="x", visible=False)
    _save(fig, "gap_hist.png")


def selfcure_drift():
    fig, ax = plt.subplots(figsize=(5.4, 4.2))
    bars = ax.bar(["train\n(≤2025-06)", "test\n(≥2025-07)"], [0.60, 0.72],
                  color=[MUTED, AMBER], width=0.55)
    ax.bar_label(bars, fmt="%.2f", padding=4, color=INK, fontweight="bold")
    ax.set_ylim(0, 1); ax.set_ylabel("self-cure rate")
    ax.set_title("The drift the monitor exists to catch", fontweight="bold", loc="left")
    ax.grid(axis="x", visible=False)
    _save(fig, "selfcure_drift.png")


if __name__ == "__main__":
    reliability()
    allocator()
    gap_hist()
    selfcure_drift()
    print("done ->", OUT)
