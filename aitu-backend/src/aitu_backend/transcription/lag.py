"""The per-piece timing fix of MuScriptor's onsets, measured on the audio (Phase 1 report 3.3).

MuScriptor's onset times can all carry the same small lag. The lag is constant within a piece but
changes between pieces (Phase 1: from 17 ms late to 22 ms early against ByteDance, on six pieces).
MuScriptor removes it with a beat grid, which rule 3 forbids storing and which refused all six
pieces anyway. So the lag is measured on the audio itself, with no tempo involved:

1. A spectral-flux onset envelope of the audio at a 2 ms hop (``librosa.onset.onset_strength``,
   ``hop_length=32, n_fft=512, lag=5``). It rises where a key is struck.
2. For each candidate lag from -80 to +80 ms, the onsets are moved back by it and the envelope is
   read at the moved onsets. The lag with the highest mean is where the onsets sit best on the
   energy rises (``best``).
3. The envelope itself peaks a little after the physical onset. Measured with ByteDance's onsets,
   whose timing the app has used for months, that bias is 16 to 19 ms on every piece, so 17 ms is
   added back.

``lagCorrectionMs = round(best + 17)``, clipped to +-40 ms, and **subtracted** from every onset and
release before saving. On Superestrella it is +15 ms: the notes move 15 ms earlier. It costs about
one second of CPU for a 3-minute piece. The 2 ms hop matters: MuScriptor's onsets sit on a 10 ms
grid, and a 10 ms envelope could only answer in multiples of 10 ms.

The code is the Phase 1 measurement (``pocs/poc-muscriptor/scripts/11_lag.py``), vectorised.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "ENVELOPE_BIAS_MS",
    "MAX_CORRECTION_MS",
    "MIN_ONSETS",
    "lag_correction_ms",
    "warm_up",
]

#: The envelope's hop, in samples at 16 kHz: 2 ms.
HOP = 32
N_FFT = 512
FLUX_LAG = 5
#: The candidate lags, in ms.
LAGS_MS = np.arange(-80, 81, 1)
#: How late the envelope peaks after a physical onset (Phase 1, ByteDance on six pieces).
ENVELOPE_BIAS_MS = 17.0
#: A larger correction is not a lag, it is a failed measurement.
MAX_CORRECTION_MS = 40.0
#: Fewer distinct onsets than this and the measurement is not trusted: no correction.
#:
#: Measured in Phase 4 on Superestrella (whole song: +15 ms). Excerpts of 20 s (about 70 distinct
#: onsets) gave anything from -7 to +17 ms; excerpts of 60 s (about 220) gave 13 to 15 ms. A wrong
#: correction of 20 ms is worse than none, because the lag itself is at most about 20 ms, so a short
#: piece is left as MuScriptor wrote it.
MIN_ONSETS = 200


def best_lag_ms(samples: np.ndarray, sample_rate: int, onsets_ms: np.ndarray) -> int:
    """The lag (ms) that puts ``onsets_ms`` best on the envelope of ``samples``."""
    import librosa  # noqa: PLC0415 - heavy, and only the engines need it

    y = np.asarray(samples, dtype=np.float32)
    envelope = librosa.onset.onset_strength(
        y=y, sr=sample_rate, hop_length=HOP, n_fft=N_FFT, center=True, lag=FLUX_LAG
    )
    envelope = envelope / (envelope.std() + 1e-9)
    frames = np.arange(len(envelope)) * HOP / sample_rate
    # Onsets de-duplicated to 1 ms, so a chord counts once, as in Phase 1.
    onsets = np.unique(np.round(np.asarray(onsets_ms, dtype=np.float64))) / 1000.0
    moved = onsets[None, :] - LAGS_MS[:, None] / 1000.0
    curve = np.interp(moved.ravel(), frames, envelope).reshape(moved.shape).mean(axis=1)
    return int(LAGS_MS[int(np.argmax(curve))])


def lag_correction_ms(samples: np.ndarray, sample_rate: int, onsets_ms: np.ndarray) -> float:
    """What to subtract from every onset and release of this piece, in whole milliseconds.

    0 when there are fewer than :data:`MIN_ONSETS` distinct onsets (about a minute of music), or
    when librosa is not installed.
    """
    distinct = np.unique(np.round(np.asarray(onsets_ms, dtype=np.float64)))
    if len(distinct) < MIN_ONSETS or len(samples) == 0:
        return 0.0
    try:
        best = best_lag_ms(samples, sample_rate, distinct)
    except ImportError:
        return 0.0
    correction = round(best + ENVELOPE_BIAS_MS)
    return float(np.clip(correction, -MAX_CORRECTION_MS, MAX_CORRECTION_MS))


def warm_up() -> None:
    """Run the measurement once on one second of noise.

    librosa compiles part of its code the first time it runs in a process. Measured in Phase 4 in
    the container: the first lag measurement took about 7.7 s, the next ones 0.3 s. The model
    preload calls this, so the first transcription does not pay it.
    """
    noise = np.random.default_rng(0).standard_normal(16_000).astype(np.float32) * 0.01
    try:
        best_lag_ms(noise, 16_000, np.arange(100.0, 900.0, 10.0))
    except ImportError:
        pass
