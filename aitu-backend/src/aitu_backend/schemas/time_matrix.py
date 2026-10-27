"""The figures and the frame length of the time model, and two marks of the old sheet's ``sheet.json``.

This module held the schema 2.0 contracts between the backend and ``@aimpromptu/grid-notation`` (the vexflow-v2
sheet): the time matrix envelope, the figure ladder, the passages, the printed notes and the score payload
(``context/implementations/time-based-concept/contract.md``). Implementation 03, Phase 10 removed them with that
sheet. What stays is read by the new sheet and by the reader of the old ``sheet.json``
(``schemas/rhythm.py``, ``part_sheet/legacy.py``): the column length, the figure names and their length in negras,
and the shapes of a figure set by hand and a beam break.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.matrix.keys import KEY_COUNT

#: Length of one matrix column in milliseconds (D-01). Provisional: 40 ms is right for a slow
#: passage and coarse for a fast one, so it is configurable per piece.
DEFAULT_FRAME_MS = 40.0

#: The window that groups near-simultaneous onsets into one attack follows the frame length (D-04),
#: so a piece rendered at 20 ms groups at 20 ms. There is no second window: onsets that share a frame
#: already share one x on the page (D-24), which is why ``alignWindowMs`` no longer exists.


class FigureName(str, Enum):
    """The closed figure vocabulary (D-12).

    Dots exist on ``blanca`` and ``negra`` only. That restriction is deliberate: with the dotted
    corchea banned, a swing pair of 211 ms and 125 ms both resolve to ``corchea``, which is what the
    printed sheet shows. Allowing the dot pulls the long half of the pair to a dotted corchea and
    recreates the ragged mix this refactor removes.

    This is not the same vocabulary as ``Granularity`` in ``schemas/matrix.py``. That enum names the
    resolution of a column and disappears from the grid in Phase 4; this one names a printed figure.
    """

    REDONDA = "redonda"
    BLANCA = "blanca"
    DOTTED_BLANCA = "dottedBlanca"
    NEGRA = "negra"
    DOTTED_NEGRA = "dottedNegra"
    CORCHEA = "corchea"
    SEMICORCHEA = "semicorchea"
    FUSA = "fusa"
    SEMIFUSA = "semifusa"


#: Length of each figure in negras: the old sheet's reference figure (``anchorFigure``) is read through it.
FIGURE_NEGRAS: dict[FigureName, float] = {
    FigureName.REDONDA: 4.0,
    FigureName.BLANCA: 2.0,
    FigureName.DOTTED_BLANCA: 3.0,
    FigureName.NEGRA: 1.0,
    FigureName.DOTTED_NEGRA: 1.5,
    FigureName.CORCHEA: 0.5,
    FigureName.SEMICORCHEA: 0.25,
    FigureName.FUSA: 0.125,
    FigureName.SEMIFUSA: 0.0625,
}

#: Which staff a printed note belongs to. Unlike ``Hand`` in ``schemas/matrix.py`` there is no
#: ``single`` member: a mark of the old sheet always names one staff.
PrintedHand = Literal["right", "left"]


class FigureOverride(BaseModel):
    """A figure the user set by hand for one note (D-17).

    It changes that one glyph and nothing else: no reflow, no renumbering, no effect on any other
    note. That is only possible because the figure no longer decides where anything sits.
    """

    model_config = ConfigDict(populate_by_name=True)

    hand: PrintedHand
    row: int = Field(..., ge=0, lt=KEY_COUNT)
    start_frame: int = Field(..., alias="startFrame", ge=0)
    figure: FigureName


class BeamBreak(BaseModel):
    """A note the reader asked to start a new beam group (D-34).

    The twin of :class:`FigureOverride`, and kept for the same reason: it changes how the page is
    grouped and nothing about the music. A long run climbing through an arpeggio has no boundary any
    rule can find — one hand, one key, one clef, no tuplet — so it beams as a single shapeless slope
    with stems reaching across two octaves. Where the phrase actually restarts is a reading of the
    music, not a property of it, and this is the only place that reading can come from.

    Keyed by the note's own column, not by its position in the run, so it survives a ladder change:
    renaming the figures moves nothing in time, and the break stays where the reader put it.
    """

    model_config = ConfigDict(populate_by_name=True)

    hand: PrintedHand
    start_frame: int = Field(..., alias="startFrame", ge=0)
