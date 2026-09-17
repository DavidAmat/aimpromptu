"""Decorative notes: the short ornament printed right before a real note.

A sixteenth, a thirty-second or a sixty-fourth that sits immediately before an
eighth, a quarter or a half in the same hand is an ornament — a grace note the
player slipped in, or a blur the transcriber turned into a note — and on a
page read by time it costs more than it says. The reader may ask for them to be
left off. Nothing is written in their place: this notation has no rests (D-16),
and the note before an ornament simply runs on to the next onset, which is what
D-14 says a printed length is.

The rule is on the *printed* figures, so it is applied after the figures are
named, and taking an ornament off changes the figure of the note before it —
so the caller names the figures again and asks again, until nothing is left to
take off.
"""

from __future__ import annotations

from aitu_backend.schemas.rhythm import HiddenNote
from aitu_backend.schemas.time_matrix import FigureName, PrintedNote

#: The figures short enough to be an ornament.
SHORT: frozenset[FigureName] = frozenset(
    {FigureName.SEMICORCHEA, FigureName.FUSA, FigureName.SEMIFUSA}
)
#: The figures an ornament leans on.
LONG: frozenset[FigureName] = frozenset(
    {
        FigureName.CORCHEA,
        FigureName.NEGRA,
        FigureName.DOTTED_NEGRA,
        FigureName.BLANCA,
        FigureName.DOTTED_BLANCA,
        FigureName.REDONDA,
    }
)


def decorative_notes(notes: list[PrintedNote]) -> list[HiddenNote]:
    """Every printed note that is an ornament before a longer note in the same hand.

    A chord struck together shares one figure, so a decorative chord goes whole:
    one ``HiddenNote`` per member. The note it leans on is the next onset in the
    same hand, whatever its row.
    """
    out: list[HiddenNote] = []
    for hand in ("right", "left"):
        by_frame: dict[int, list[PrintedNote]] = {}
        for note in notes:
            if note.hand == hand:
                by_frame.setdefault(note.start_frame, []).append(note)
        frames = sorted(by_frame)
        for here, following in zip(frames, frames[1:]):
            chord = by_frame[here]
            if chord[0].figure not in SHORT:
                continue
            if by_frame[following][0].figure not in LONG:
                continue
            out.extend(HiddenNote(start_frame=note.start_frame, row=note.row) for note in chord)
    return out
