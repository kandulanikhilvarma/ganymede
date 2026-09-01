"""Drift monitors (I12). Static panel, live world — a model rots when the world
moves under it. These watch input, score, and outcome distributions and flag a
breach; the nightly eval runs them and exits non-zero on a flag.

PSI (population stability index) is the standard measure of distribution shift
between a reference window and a current one. Rule of thumb: <0.1 stable,
0.1-0.25 moderate shift, >0.25 significant. The self-cure drift found in Phase 3
(rate 0.60 -> 0.72) is exactly the kind of shift PSI on the outcome rate catches.
"""

from __future__ import annotations

import numpy as np


def psi(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """Population Stability Index between two samples of a continuous quantity."""
    ref = np.asarray(reference, dtype=float)
    cur = np.asarray(current, dtype=float)
    edges = np.quantile(ref, np.linspace(0, 1, bins + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    ref_frac = np.histogram(ref, edges)[0] / len(ref)
    cur_frac = np.histogram(cur, edges)[0] / len(cur)
    eps = 1e-6
    ref_frac = np.clip(ref_frac, eps, None)
    cur_frac = np.clip(cur_frac, eps, None)
    return float(np.sum((cur_frac - ref_frac) * np.log(cur_frac / ref_frac)))


PSI_ALERT = 0.25
RATE_ALERT = 0.10  # absolute change in a binary rate that trips an alert


def check_drift(reference: np.ndarray, current: np.ndarray, name: str) -> dict:
    val = psi(reference, current)
    level = "stable" if val < 0.1 else "moderate" if val < PSI_ALERT else "significant"
    return {"metric": name, "psi": round(val, 4), "level": level, "alert": val >= PSI_ALERT}


def check_rate_drift(reference: np.ndarray, current: np.ndarray, name: str) -> dict:
    """For a binary outcome, PSI underweights a base-rate shift. Watch the rate
    directly — this is what catches the self-cure drift (0.60 -> 0.72) that PSI
    on the 0/1 labels misses."""
    ref_rate = float(np.mean(reference))
    cur_rate = float(np.mean(current))
    delta = abs(cur_rate - ref_rate)
    return {
        "metric": name, "ref_rate": round(ref_rate, 3), "cur_rate": round(cur_rate, 3),
        "delta": round(delta, 3), "alert": delta >= RATE_ALERT,
    }
