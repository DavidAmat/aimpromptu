"""Notes transposition: every note of a part moved by the same number of semitones.

The sheet toolbox's **Transpose → Notes** (implementation 02, plan section 11.4). It changes the
recorded notes, not the drawing: every key of ``notes.pmn`` moves by the interval between the two
keys the reader picked, and the piano matrix, the gaps and the sheet follow by the ordinary path.
Times do not move, so no column moves and every mark keyed by a column stays on its music. The
hand of each note stays as it is: it is pinned on the note, and a hand is a fact about the playing.

A note that would leave the 88 keys cannot be moved. It is **taken off** (``removed``, as a note
taken off the page is) and stays on its old key, so nothing is lost and an undo puts it back
exactly. Notes already taken off are moved with the others when they can be, so putting one back
later brings it back in the new key.

Undo is the same operation the other way, told which notes did not move and which were taken off:
moving the rest back by the opposite interval and putting those back on gives the notes as they
were, note for note.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from aitu_backend.matrix.keys import KEY_COUNT, LOWEST_MIDI
from aitu_backend.transcription.engine import NoteEvent

HIGHEST_MIDI = LOWEST_MIDI + KEY_COUNT - 1


@dataclass
class Transposed:
    """What a transposition did, or would do."""

    events: list[NoteEvent]
    #: Notes on the page that moved to their new key.
    moved: int = 0
    #: The ids of the notes that stayed where they were: they would have left the keyboard, or the
    #: caller asked for them to stay (an undo).
    held: list[int] = field(default_factory=list)
    #: The ids of the notes this transposition took off the page, because they would have left
    #: the keyboard. An undo puts them back.
    taken_off: list[int] = field(default_factory=list)
    #: The ids of the notes put back on the page (an undo).
    put_back: list[int] = field(default_factory=list)


def transpose_events(
    events: list[NoteEvent],
    semitones: int,
    *,
    hold: frozenset[int] = frozenset(),
    restore: frozenset[int] = frozenset(),
) -> Transposed:
    """Move every note by ``semitones``; a new list, the input untouched.

    ``hold`` names notes that stay on their key (and are not counted as leaving the keyboard).
    ``restore`` names notes to put back on the page after the move. Both are by note id, and both
    are what an undo passes: the ``held`` and ``taken_off`` of the transposition it takes back.
    """
    result = Transposed(events=[])
    for event in events:
        note_id = event.id
        target = event.midi_note + semitones
        if note_id is not None and note_id in hold:
            copy = event.model_copy()
            result.held.append(note_id)
        elif LOWEST_MIDI <= target <= HIGHEST_MIDI:
            copy = event.model_copy(update={"midi_note": target})
            if not event.removed:
                result.moved += 1
        else:
            copy = event.model_copy(update={"removed": True})
            if note_id is not None:
                result.held.append(note_id)
                if not event.removed:
                    result.taken_off.append(note_id)
        if note_id is not None and note_id in restore and copy.removed:
            copy = copy.model_copy(update={"removed": False})
            result.put_back.append(note_id)
        result.events.append(copy)
    return result
