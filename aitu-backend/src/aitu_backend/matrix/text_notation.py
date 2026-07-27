"""Convert a human-written time-frame sequence into a sparse 88-key score.

Textual notation — one list item per time frame, ``||`` separates
simultaneous notes, an empty string is a silent frame, and a leading
``*`` marks an **onset** (the key is struck). A note without ``*`` is a
**sustain** (the same key keeps sounding, not struck again)::

    sequence = [
        "*Do-4 || *Mi-4",   # frame 0: chord, both struck
        "*Re-4",            # frame 1: Re-4 struck
        "Re-4",             # frame 2: Re-4 still held (one note, 2 frames)
        "*Re-4",            # frame 3: Re-4 struck again (a new note)
        "",                 # frame 4: silence
    ]

Onset rule — a sustain only continues through frames that contain **no**
new onset. As soon as a frame has any onset, every carried sustain ends
at the previous frame (overlapping sustains are a performance nuance we
deliberately keep out of the score). The builder normalizes input to
honor this, so an illegal "sustain + foreign onset in the same frame"
collapses to "sustain ended, only the onset remains".

The sparse payload carries three parallel arrays sorted by (column,
row): ``rows`` / ``cols`` mark active cells, and ``onset[i]`` is either
``rows[i]`` (this cell is an onset) or ``-1`` (this cell is a sustain).
"""

from __future__ import annotations

from aitu_backend.matrix.keys import CHROMATIC_ES, build_grand_piano_rows

#: Kept as an alias: the key tables now live in `aitu_backend.matrix.keys`,
#: which is the single source of truth for note names and row order.
CHROMATIC_NOTES = CHROMATIC_ES

__all__ = [
    "CHROMATIC_NOTES",
    "build_grand_piano_rows",
    "parse_timeframe_notes",
    "sequence_to_sparse_payload",
    "sequence_to_score",
]


def parse_timeframe_notes(cell: str) -> list[tuple[str, bool]]:
    """Parse one frame into ``(note, is_onset)`` pairs.

    ``"*Do-3 || Mi-3"`` -> ``[("Do-3", True), ("Mi-3", False)]``.
    An empty/blank frame yields ``[]`` (silence).
    """
    if not cell.strip():
        return []

    parsed: list[tuple[str, bool]] = []
    for token in cell.split("||"):
        token = token.strip()
        if not token:
            continue
        if token.startswith("*"):
            parsed.append((token[1:].strip(), True))
        else:
            parsed.append((token, False))
    return parsed


def sequence_to_sparse_payload(
    sequence: list[str],
    rows: list[str] | None = None,
) -> dict:
    """Build the sparse COO payload (with the ``onset`` array) for a sequence.

    Applies the onset rule: a plain (sustain) note only continues a note
    that was already sounding **and** only through frames with no onset.
    A sustain with no note to continue is promoted to an onset (you cannot
    hold a key that was never struck).
    """
    if rows is None:
        rows = build_grand_piano_rows()

    note_to_row = {note: idx for idx, note in enumerate(rows)}

    # cells: (col, row, onset_value) where onset_value == row (onset) or -1.
    cells: list[tuple[int, int, int]] = []
    open_rows: set[int] = set()  # rows with a note still sounding from col-1

    for col, cell in enumerate(sequence):
        items: list[tuple[int, bool]] = []
        for note, is_onset in parse_timeframe_notes(cell):
            if note not in note_to_row:
                raise ValueError(
                    f"Unknown note '{note}'. Expected one of: " f"{rows[0]} ... {rows[-1]}"
                )
            items.append((note_to_row[note], is_onset))

        onset_rows = {r for r, on in items if on}
        plain_rows = {r for r, on in items if not on}
        has_onset = bool(onset_rows)

        next_open: set[int] = set()

        for r in sorted(onset_rows):
            cells.append((col, r, r))  # struck
            next_open.add(r)

        for r in sorted(plain_rows):
            if r in onset_rows:
                continue  # already emitted as an onset this frame
            if has_onset:
                # Onset rule: a new strike anywhere breaks carried sustains.
                continue
            if r in open_rows:
                cells.append((col, r, -1))  # valid sustain
                next_open.add(r)
            else:
                # Cannot sustain a key that was never struck -> treat as onset.
                cells.append((col, r, r))
                next_open.add(r)

        open_rows = next_open

    cells.sort(key=lambda c: (c[0], c[1]))

    return {
        "format": "binary-coo",
        "shape": [len(rows), len(sequence)],
        "rows": [c[1] for c in cells],
        "cols": [c[0] for c in cells],
        "onset": [c[2] for c in cells],
    }


def sequence_to_score(
    sequence: list[str],
    tempo_bpm: float,
    time_step_seconds: float,
    title: str | None = None,
    lyrics: list[str] | None = None,
    key_signature: str | None = None,
    left_sequence: list[str] | None = None,
) -> dict:
    """Build the camelCase score payload consumed by aitu-frontend.

    ``rows`` is intentionally omitted: the 88-key order is canonical and the
    frontend rebuilds it deterministically. Only the sparse matrix travels.

    One hand vs two. With ``left_sequence`` omitted the payload carries a
    single ``matrix`` (treble). With ``left_sequence`` given, ``sequence`` is
    the right hand (treble, ``r_matrix``) and ``left_sequence`` is the left
    hand (bass clef, ``l_matrix``); both must have the same number of time
    frames so the hands stay vertically aligned. The same notation, onset
    rule and key signature apply to the bass clef unchanged.
    """
    score: dict = {
        "title": title,
        "tempoBpm": tempo_bpm,
        "timeStepSeconds": time_step_seconds,
        "matrixEncoding": "sparse-coo",
        "lyrics": lyrics,
        "keySignature": key_signature,
    }

    if left_sequence is None:
        score["matrix"] = sequence_to_sparse_payload(sequence)
        return score

    if len(left_sequence) != len(sequence):
        raise ValueError(
            "Right and left hand must have the same number of time frames "
            f"so they align ({len(sequence)} vs {len(left_sequence)})."
        )
    score["r_matrix"] = sequence_to_sparse_payload(sequence)
    score["l_matrix"] = sequence_to_sparse_payload(left_sequence)
    return score
