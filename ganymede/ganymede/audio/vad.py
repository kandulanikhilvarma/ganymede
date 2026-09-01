"""Voice-activity detection for turn-boundary timing.

Timing comes from VAD, content from ASR — two signals at two latencies. This is
what lets a deterministic hint render the instant a speaker stops, without
waiting for a transcript.

Implementation is an energy VAD with hangover smoothing: no torch, no C
extension, runs anywhere. It is a deliberate stand-in for silero-VAD, which is
more robust on noisy telephony but drags in torch for what is, at Phase 0, a
gap-measurement job. The VADEngine interface keeps the swap to silero a
one-class change, exactly as ASREngine does for Whisper.

The number Phase 0 needs is the distribution of INTER-TURN gaps — the silences
between one speaker stopping and the next starting. That silence is the window a
coaching hint has to land in. Its p50/p95 is the latency budget (I4), measured
rather than guessed.
"""

from __future__ import annotations

import wave
from dataclasses import dataclass

import numpy as np

FRAME_MS = 30
MIN_GAP_MS = 200      # a silence shorter than this is a within-speech micro-pause
HANGOVER_FRAMES = 3   # frames of agreement before flipping speech<->silence


@dataclass
class Segment:
    start_s: float
    end_s: float


def load_wav_mono16k(path: str) -> tuple[np.ndarray, int]:
    w = wave.open(path, "rb")
    sr = w.getframerate()
    n = w.getnframes()
    raw = w.readframes(n)
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    if w.getnchannels() == 2:
        samples = samples.reshape(-1, 2).mean(axis=1)
    return samples, sr


def _frame_energy(samples: np.ndarray, sr: int, frame_ms: int) -> np.ndarray:
    flen = int(sr * frame_ms / 1000)
    n = len(samples) // flen
    frames = samples[: n * flen].reshape(n, flen)
    return np.sqrt((frames ** 2).mean(axis=1) + 1e-9)


def speech_frames(samples: np.ndarray, sr: int, frame_ms: int = FRAME_MS) -> np.ndarray:
    """Boolean speech mask per frame. Threshold is adaptive: a noise floor from
    the quiet end of the energy distribution, scaled up. Hangover debounces so a
    breath mid-sentence does not read as a turn boundary."""
    energy = _frame_energy(samples, sr, frame_ms)
    floor = np.percentile(energy, 20)
    peak = np.percentile(energy, 95)
    thresh = floor + 0.15 * (peak - floor)  # between quiet floor and speech peak

    raw = energy > thresh
    # hangover smoothing: require HANGOVER_FRAMES consecutive agreeing frames
    out = raw.copy()
    state = False
    run = 0
    for i, v in enumerate(raw):
        if v == state:
            run = 0
        else:
            run += 1
            if run >= HANGOVER_FRAMES:
                state = v
                run = 0
        out[i] = state
    return out


def segments(mask: np.ndarray, frame_ms: int = FRAME_MS) -> list[Segment]:
    segs = []
    start = None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        elif not v and start is not None:
            segs.append(Segment(start * frame_ms / 1000, i * frame_ms / 1000))
            start = None
    if start is not None:
        segs.append(Segment(start * frame_ms / 1000, len(mask) * frame_ms / 1000))
    return segs


def inter_turn_gaps(segs: list[Segment], min_gap_ms: int = MIN_GAP_MS) -> list[float]:
    """Silence durations (seconds) between consecutive speech segments, keeping
    only gaps long enough to be real turn boundaries rather than micro-pauses."""
    gaps = []
    for a, b in zip(segs, segs[1:]):
        gap = b.start_s - a.end_s
        if gap * 1000 >= min_gap_ms:
            gaps.append(gap)
    return gaps


def analyse(path: str) -> dict:
    samples, sr = load_wav_mono16k(path)
    mask = speech_frames(samples, sr)
    segs = segments(mask)
    gaps = inter_turn_gaps(segs)
    g = np.array(gaps) if gaps else np.array([0.0])
    speech_s = sum(s.end_s - s.start_s for s in segs)
    return {
        "duration_s": round(len(samples) / sr, 1),
        "speech_s": round(speech_s, 1),
        "n_segments": len(segs),
        "n_gaps": len(gaps),
        "gap_p50_ms": int(np.percentile(g, 50) * 1000),
        "gap_p25_ms": int(np.percentile(g, 25) * 1000),
        "gap_p10_ms": int(np.percentile(g, 10) * 1000),
        "gap_mean_ms": int(g.mean() * 1000),
    }
