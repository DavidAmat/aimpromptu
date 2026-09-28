"""The sparse form of the piano matrix notation: one rectangle per note, as NumPy arrays.

A row of the piano matrix notation is a sequence of runs: silence, an onset followed by some
sustain, silence again. One run is one rectangle, and storing each rectangle as
``(key, onset time, length)`` instead of every cell loses nothing: the 88-row matrix at any
``frameMs`` is rebuilt from it in one pass (:mod:`aitu_backend.pmn.dense`).

Times are **milliseconds of the original audio**, not columns, so the same notes are viewed at
10 ms on the piano roll and at 40 ms on the piano sheet (D-03, rule 4). They are held as ``float64``
because the pieces transcribed by ByteDance carry 0.1 ms in ``events.json``, and a column is chosen
by rounding: rounding the stored time to a whole millisecond could move an onset to the next column
and detach the reader's marks keyed on it. MuScriptor times are whole numbers, so for every new piece
the floats hold integers exactly. The wire form (:mod:`aitu_backend.pmn.columns`) sends integers.

The arrays are parallel: index ``i`` of every field is one note. The order is whatever the source
gave; :meth:`Notes.sorted` gives the canonical order, by onset and then key.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import numpy.typing as npt

from aitu_backend.matrix.keys import KEY_COUNT, LOWEST_MIDI

__all__ = [
    "DEFAULT_VELOCITY",
    "HAND_CODES",
    "HAND_LEFT",
    "HAND_NAMES",
    "HAND_NONE",
    "HAND_RIGHT",
    "KEY_COUNT",
    "LOWEST_MIDI",
    "Notes",
    "hand_code",
]

#: The hand of a note, as one small integer per note. ``HAND_NONE`` until the hand split runs.
HAND_NONE = 0
HAND_RIGHT = 1
HAND_LEFT = 2

#: ``events.json`` and ``NoteEvent`` spell the hand as a word; the arrays hold the code.
HAND_CODES: dict[str | None, int] = {None: HAND_NONE, "right": HAND_RIGHT, "left": HAND_LEFT}
HAND_NAMES: dict[int, str | None] = {code: name for name, code in HAND_CODES.items()}

#: What a note gets when its source has no loudness. MuScriptor has none (Phase 1 report 3.1).
DEFAULT_VELOCITY = 64


def hand_code(hand: str | None) -> int:
    """``"right"`` -> 1, ``"left"`` -> 2, ``None`` -> 0."""
    try:
        return HAND_CODES[hand]
    except KeyError as exc:
        raise ValueError(f"Unknown hand {hand!r}; expected 'right', 'left' or None") from exc


def _array(
    values: npt.ArrayLike, dtype: npt.DTypeLike, count: int = -1, default: object = None
) -> np.ndarray:
    """A contiguous 1-D array of ``dtype``. Empty ``values`` with a ``count`` gives the default."""
    array = np.asarray(values, dtype=dtype).reshape(-1)
    if count >= 0 and array.size == 0 and count:
        array = np.full(count, default, dtype=dtype)
    return np.ascontiguousarray(array)


class Notes:
    """Every note of a piece, one entry per note in each array.

    ``id`` is the stable identity of a note: given by the backend, kept across edits and saves, and
    never reused in a piece. ``removed`` marks a note a reader said was never played; it stays so it
    can be put back, and every view (the dense matrix, the wire, the exports) leaves it out.

    The constructor takes anything NumPy can read (arrays, lists) and stores contiguous arrays of
    fixed types. ``hand``, ``velocity`` and ``removed`` may be left empty: no hand, 64, not removed.
    """

    #: Stable identity, ``int64``.
    id: np.ndarray
    #: 0..87, the row of the piano matrix notation, ``int16``. MIDI is ``key + 21``.
    key: np.ndarray
    #: The onset, in milliseconds of the original audio, ``float64``.
    on_ms: np.ndarray
    #: Onset plus sustain, in milliseconds, ``float64``. The release is ``on_ms + len_ms``.
    len_ms: np.ndarray
    #: ``HAND_NONE``, ``HAND_RIGHT`` or ``HAND_LEFT``, ``int8``.
    hand: np.ndarray
    #: 1..127, ``uint8``. 64 when the source has no loudness.
    velocity: np.ndarray
    #: ``bool``.
    removed: np.ndarray

    def __init__(
        self,
        id: npt.ArrayLike,  # noqa: A002 - the field is called id everywhere, on disk and on the wire
        key: npt.ArrayLike,
        on_ms: npt.ArrayLike,
        len_ms: npt.ArrayLike,
        hand: npt.ArrayLike = (),
        velocity: npt.ArrayLike = (),
        removed: npt.ArrayLike = (),
    ) -> None:
        self.id = _array(id, np.int64)
        count = self.id.size
        self.key = _array(key, np.int16)
        self.on_ms = _array(on_ms, np.float64)
        self.len_ms = _array(len_ms, np.float64)
        self.hand = _array(hand, np.int8, count, HAND_NONE)
        self.velocity = _array(velocity, np.uint8, count, DEFAULT_VELOCITY)
        self.removed = _array(removed, bool, count, False)
        self.validate()

    # ------------------------------------------------------------ construction

    @classmethod
    def empty(cls) -> "Notes":
        return cls(id=[], key=[], on_ms=[], len_ms=[])

    @classmethod
    def build(
        cls,
        key: npt.ArrayLike,
        on_ms: npt.ArrayLike,
        len_ms: npt.ArrayLike,
        *,
        hand: npt.ArrayLike = (),
        velocity: npt.ArrayLike = (),
        removed: npt.ArrayLike = (),
        first_id: int = 0,
    ) -> "Notes":
        """Notes with fresh ids ``first_id, first_id + 1, ...`` in the order given."""
        count = np.asarray(key).size
        return cls(
            id=np.arange(first_id, first_id + count),
            key=key,
            on_ms=on_ms,
            len_ms=len_ms,
            hand=hand,
            velocity=velocity,
            removed=removed,
        )

    # -------------------------------------------------------------- inspection

    def __len__(self) -> int:
        return int(self.id.size)

    @property
    def midi(self) -> np.ndarray:
        return self.key.astype(np.int16) + LOWEST_MIDI

    @property
    def end_ms(self) -> np.ndarray:
        """The release of every note."""
        return self.on_ms + self.len_ms

    @property
    def next_id(self) -> int:
        """The smallest id no note has used. A new note takes this one."""
        return int(self.id.max()) + 1 if len(self) else 0

    def validate(self) -> None:
        """Raise ``ValueError`` when the arrays do not describe a set of notes."""
        count = self.id.size
        for name in ("key", "on_ms", "len_ms", "hand", "velocity", "removed"):
            if getattr(self, name).size != count:
                raise ValueError(
                    f"Notes fields must be parallel arrays: id has {count} entries, "
                    f"{name} has {getattr(self, name).size}"
                )
        if not count:
            return
        if self.key.min() < 0 or self.key.max() >= KEY_COUNT:
            raise ValueError(f"key must be 0..{KEY_COUNT - 1} (MIDI 21..108)")
        if not np.all(np.isfinite(self.on_ms)) or not np.all(np.isfinite(self.len_ms)):
            raise ValueError("onMs and lenMs must be finite numbers")
        if self.on_ms.min() < 0:
            raise ValueError("onMs cannot be negative")
        if self.len_ms.min() <= 0:
            raise ValueError("lenMs must be positive: a rectangle has an onset and some length")
        if not np.isin(self.hand, (HAND_NONE, HAND_RIGHT, HAND_LEFT)).all():
            raise ValueError("hand must be 0 (none), 1 (right) or 2 (left)")
        if np.unique(self.id).size != count:
            raise ValueError("id must be unique: two notes cannot share an identity")

    # --------------------------------------------------------------- selection

    def take(self, index: Any) -> "Notes":
        """The notes at ``index`` (positions or a boolean mask), ids kept."""
        return Notes(
            id=self.id[index],
            key=self.key[index],
            on_ms=self.on_ms[index],
            len_ms=self.len_ms[index],
            hand=self.hand[index],
            velocity=self.velocity[index],
            removed=self.removed[index],
        )

    def copy(self) -> "Notes":
        """An independent copy: changing its arrays does not change this one."""
        return self.take(np.arange(len(self)))

    def live(self) -> "Notes":
        """The notes that were played: everything not marked removed."""
        return self if not self.removed.any() else self.take(~self.removed)

    def of_hand(self, hand: int) -> "Notes":
        return self.take(self.hand == hand)

    def sorted(self) -> "Notes":
        """Canonical order: by onset, then key, then id."""
        order = np.lexsort((self.id, self.key, self.on_ms))
        return self.take(order)

    def equals(self, other: "Notes", *, ids: bool = True, atol_ms: float = 1e-6) -> bool:
        """Same notes in the same order. ``ids=False`` compares everything but the identity."""
        if len(self) != len(other):
            return False
        same = (
            np.array_equal(self.key, other.key)
            and np.allclose(self.on_ms, other.on_ms, rtol=0, atol=atol_ms)
            and np.allclose(self.len_ms, other.len_ms, rtol=0, atol=atol_ms)
            and np.array_equal(self.hand, other.hand)
            and np.array_equal(self.velocity, other.velocity)
            and np.array_equal(self.removed, other.removed)
        )
        return bool(same and (not ids or np.array_equal(self.id, other.id)))

    def __repr__(self) -> str:
        live = int((~self.removed).sum())
        return f"Notes({len(self)} notes, {live} live)"
