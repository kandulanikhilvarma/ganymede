"""VAD gap detection on synthetic audio with known structure — offline, fast."""

import numpy as np

from ganymede.audio.vad import inter_turn_gaps, segments, speech_frames


def _tone(dur_s, sr=16000, freq=200, amp=8000):
    t = np.arange(int(dur_s * sr))
    return (amp * np.sin(2 * np.pi * freq * t / sr)).astype(np.float32)


def _silence(dur_s, sr=16000):
    return np.zeros(int(dur_s * sr), dtype=np.float32)


def test_detects_a_known_gap():
    # speech 1s, silence 0.6s, speech 1s -> exactly one inter-turn gap ~0.6s
    sr = 16000
    sig = np.concatenate([_tone(1.0), _silence(0.6), _tone(1.0)])
    mask = speech_frames(sig, sr)
    segs = segments(mask)
    gaps = inter_turn_gaps(segs)
    assert len(segs) == 2
    assert len(gaps) == 1
    assert 0.45 < gaps[0] < 0.75  # ~0.6s, allowing frame/hangover slack


def test_micro_pause_is_not_a_turn_gap():
    # 100ms silence is below MIN_GAP_MS (200) -> not counted as a boundary
    sr = 16000
    sig = np.concatenate([_tone(1.0), _silence(0.1), _tone(1.0)])
    segs = segments(speech_frames(sig, sr))
    gaps = inter_turn_gaps(segs)
    assert gaps == []


def test_budget_is_measured_not_none():
    from ganymede.config import LATENCY_BUDGET_MS, require_latency_budget
    assert LATENCY_BUDGET_MS is not None
    assert require_latency_budget() == 300
