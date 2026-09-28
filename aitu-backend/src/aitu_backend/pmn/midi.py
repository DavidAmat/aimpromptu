"""The sparse form to a Standard MIDI File, and back.

For export, and for reading a MIDI file in the future. A MIDI file needs a tempo to turn ticks into
time. Rule 3 forbids a BPM in the piece, so the file uses one fixed timing unit and no metre: 500
ticks per beat at 500,000 microseconds per beat, which makes **one tick one millisecond**. The
120 BPM a MIDI editor shows is that unit, not a reading of the music. No time signature is written.

Each hand is its own track, named ``right hand``, ``left hand`` or ``no hand``, on channels 0, 1
and 2, so the hand survives the round trip. Reading a file from elsewhere follows its own tempo map,
and a track whose name says neither hand gives notes with no hand.

MIDI cannot hold two sounding notes of one key on one channel, so before writing, a note ends at the
next onset of the same key in its hand (the rule of :mod:`aitu_backend.pmn.dense`). Times are whole
milliseconds in the file. Notes marked removed are not written.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Callable

import numpy as np

from aitu_backend.pmn.notes import (
    HAND_LEFT,
    HAND_NONE,
    HAND_RIGHT,
    KEY_COUNT,
    LOWEST_MIDI,
    Notes,
)

__all__ = ["TICKS_PER_BEAT", "from_midi", "to_midi", "to_midi_bytes", "write_midi"]

#: With :data:`TEMPO_US_PER_BEAT`, one tick is one millisecond.
TICKS_PER_BEAT = 500
TEMPO_US_PER_BEAT = 500_000

TRACK_NAMES = {HAND_RIGHT: "right hand", HAND_LEFT: "left hand", HAND_NONE: "no hand"}
CHANNELS = {HAND_RIGHT: 0, HAND_LEFT: 1, HAND_NONE: 2}
#: General MIDI channel 10 (index 9) is percussion: its note numbers are drums, not keys.
PERCUSSION_CHANNEL = 9


def _hand_track(notes: Notes, hand: int) -> Any:
    import mido  # noqa: PLC0415 - only the MIDI adapter needs it

    chosen = notes.of_hand(hand).sorted()
    track = mido.MidiTrack()
    track.append(mido.MetaMessage("track_name", name=TRACK_NAMES[hand], time=0))
    track.append(mido.Message("program_change", channel=CHANNELS[hand], program=0, time=0))

    on = np.rint(chosen.on_ms).astype(np.int64)
    end = np.maximum(on + 1, np.rint(chosen.end_ms).astype(np.int64))
    # One sounding note per key: cut each note at the next onset of its key.
    order = np.lexsort((on, chosen.key))
    same_key = chosen.key[order][1:] == chosen.key[order][:-1]
    following = np.full(order.size, np.iinfo(np.int64).max)
    following[:-1][same_key] = on[order][1:][same_key]
    end[order] = np.minimum(end[order], np.maximum(on[order] + 1, following))

    # (tick, 0 = off before 1 = on at the same tick, message)
    timeline: list[tuple[int, int, int, Any]] = []
    for key, start, stop, velocity in zip(
        chosen.key.tolist(), on.tolist(), end.tolist(), chosen.velocity.tolist()
    ):
        midi = key + LOWEST_MIDI
        channel = CHANNELS[hand]
        timeline.append(
            (
                start,
                1,
                midi,
                mido.Message("note_on", channel=channel, note=midi, velocity=max(1, velocity)),
            )
        )
        timeline.append(
            (stop, 0, midi, mido.Message("note_off", channel=channel, note=midi, velocity=0))
        )
    timeline.sort(key=lambda item: (item[0], item[1], item[2]))
    tick = 0
    for at, _, _, message in timeline:
        message.time = at - tick
        tick = at
        track.append(message)
    track.append(mido.MetaMessage("end_of_track", time=0))
    return track


def to_midi(notes: Notes, *, title: str | None = None) -> Any:
    """A type 1 ``mido.MidiFile``: one timing track, then one track per hand that has notes."""
    import mido  # noqa: PLC0415

    live = notes.live()
    midi = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)
    conductor = mido.MidiTrack()
    conductor.append(mido.MetaMessage("track_name", name=title or "aimpromptu", time=0))
    conductor.append(mido.MetaMessage("set_tempo", tempo=TEMPO_US_PER_BEAT, time=0))
    conductor.append(mido.MetaMessage("end_of_track", time=0))
    midi.tracks.append(conductor)
    for hand in (HAND_RIGHT, HAND_LEFT, HAND_NONE):
        if (live.hand == hand).any():
            midi.tracks.append(_hand_track(live, hand))
    return midi


def to_midi_bytes(notes: Notes, *, title: str | None = None) -> bytes:
    buffer = io.BytesIO()
    to_midi(notes, title=title).save(file=buffer)
    return buffer.getvalue()


def write_midi(notes: Notes, path: Path, *, title: str | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    to_midi(notes, title=title).save(str(path))
    return path


def _tempo_map(midi: Any) -> list[tuple[int, int]]:
    """``(absolute tick, microseconds per beat)`` of every tempo change, from every track."""
    changes: list[tuple[int, int]] = [(0, 500_000)]
    for track in midi.tracks:
        tick = 0
        for message in track:
            tick += message.time
            if message.type == "set_tempo":
                changes.append((tick, message.tempo))
    changes.sort(key=lambda item: item[0])
    return changes


def _ms_of_tick(changes: list[tuple[int, int]], ticks_per_beat: int) -> Callable[[int], float]:
    starts = np.array([tick for tick, _ in changes], dtype=np.float64)
    tempos = np.array([tempo for _, tempo in changes], dtype=np.float64)
    ms_per_tick = tempos / ticks_per_beat / 1000.0
    offsets = np.concatenate([[0.0], np.cumsum(np.diff(starts) * ms_per_tick[:-1])])

    def convert(tick: int) -> float:
        index = int(np.searchsorted(starts, tick, side="right")) - 1
        return float(offsets[index] + (tick - starts[index]) * ms_per_tick[index])

    return convert


def _hand_of_track(name: str) -> int:
    lowered = name.lower()
    if "right" in lowered:
        return HAND_RIGHT
    if "left" in lowered:
        return HAND_LEFT
    return HAND_NONE


def from_midi(source: Path | bytes | object, *, first_id: int = 0) -> Notes:
    """The notes of a MIDI file (a path, its bytes, or a ``mido.MidiFile``), in canonical order.

    Notes outside the 88 keys and the percussion channel are left out. A note still open at the end
    of its track ends at the last event of that track.
    """
    import mido  # noqa: PLC0415

    if isinstance(source, (bytes, bytearray)):
        midi = mido.MidiFile(file=io.BytesIO(source))
    elif isinstance(source, (str, Path)):
        midi = mido.MidiFile(str(source))
    else:
        midi = source
    to_ms = _ms_of_tick(_tempo_map(midi), midi.ticks_per_beat)

    keys: list[int] = []
    starts: list[float] = []
    ends: list[float] = []
    hands: list[int] = []
    velocities: list[int] = []
    for track in midi.tracks:
        hand = HAND_NONE
        tick = 0
        # (channel, note) -> the ticks and velocities of the notes still sounding, oldest first
        sounding: dict[tuple[int, int], list[tuple[int, int]]] = {}

        def close(channel: int, note: int, at: int) -> None:
            opened = sounding.get((channel, note))
            if not opened:
                return
            begin, velocity = opened.pop(0)
            if LOWEST_MIDI <= note < LOWEST_MIDI + KEY_COUNT and at > begin:
                keys.append(note - LOWEST_MIDI)
                starts.append(to_ms(begin))
                ends.append(to_ms(at))
                hands.append(hand)
                velocities.append(velocity)

        for message in track:
            tick += message.time
            if message.type == "track_name":
                hand = _hand_of_track(message.name)
            elif message.type in ("note_on", "note_off") and message.channel != PERCUSSION_CHANNEL:
                if message.type == "note_on" and message.velocity > 0:
                    sounding.setdefault((message.channel, message.note), []).append(
                        (tick, message.velocity)
                    )
                else:
                    close(message.channel, message.note, tick)
        for channel, note in list(sounding):
            while sounding[(channel, note)]:
                close(channel, note, tick)

    # Six decimals take away the float noise of the tempo arithmetic (1000.0000000000001 ms).
    start_ms = np.round(np.array(starts, dtype=np.float64), 6)
    notes = Notes(
        id=np.arange(len(keys)),
        key=keys,
        on_ms=start_ms,
        len_ms=np.round(np.array(ends, dtype=np.float64), 6) - start_ms,
        hand=hands,
        velocity=velocities,
    ).sorted()
    return Notes.build(
        key=notes.key,
        on_ms=notes.on_ms,
        len_ms=notes.len_ms,
        hand=notes.hand,
        velocity=notes.velocity,
        first_id=first_id,
    )
