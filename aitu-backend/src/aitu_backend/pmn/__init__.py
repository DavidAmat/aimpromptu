"""The piano matrix notation (pmn): the stored form, the wire form, and every conversion.

Implementation 08, plan section 6. One module holds the format and every adapter, so any future
export uses the same underlying notation. The specification is
``context/backend/piano-matrix-notation.md``.

========================  ==========  ===============================================
Module                    Direction   What
========================  ==========  ===============================================
:mod:`.notes`             -           The sparse form: one rectangle per note, NumPy arrays
:mod:`.events_file`       both        ``events.json``, the stored piece, with ids and header
:mod:`.dense`             both        The 88 x N matrix at any ``frameMs``, whole or per hand
:mod:`.coo`               out         The COO payload of the piano sheet (and back, for tests)
:mod:`.columns`           both        The wire form for the browser
:mod:`.midi`              both        A Standard MIDI File
:mod:`.muscriptor`        in          MuScriptor's note events
:mod:`.portable`          both        The portable ``.pmn.json`` file
========================  ==========  ===============================================
"""

from aitu_backend.pmn.notes import HAND_LEFT, HAND_NONE, HAND_RIGHT, Notes

__all__ = ["HAND_LEFT", "HAND_NONE", "HAND_RIGHT", "Notes"]
