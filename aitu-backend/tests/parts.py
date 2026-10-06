"""Parts for tests that need one to exist before they write its files (implementation 02, Phase 3).

A part is found through the ``parts`` table, so a test that writes a video or notes for a made-up
uuid makes the part first.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.io import wavfile

from aitu_backend.audio import store
from aitu_backend.schemas.metadata import AudioSource


def make_part(part_id: str, title: str = "Test piece") -> str:
    """A project of one part with this id, in the master user's Personal Vault. No audio."""
    if not store.exists(part_id):
        store.create(title, AudioSource.UPLOAD, "wav", audio_uuid=part_id)
    return part_id


def with_audio(part_id: str, folder: Path, seconds: float = 8.0) -> str:
    """Give a part a stored audio file: a silent 16 kHz WAV of ``seconds``, measured, so cuts can
    be saved on it. No ffmpeg needed."""
    rate = 16_000
    source = folder / f"{part_id}-silence.wav"
    wavfile.write(source, rate, np.zeros(int(rate * seconds), dtype=np.int16))
    store.replace_original(part_id, source, "wav", keep_cuts=False)
    return part_id
