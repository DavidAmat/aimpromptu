"""Passages: stretches of the piece that carry their own ladder.

A passage is drawn by hand (D-19). There is no automatic segmentation in this version, and that is
deliberate: a wrong hand-drawn boundary spoils one section, while a wrong automatic one scatters
tempo changes through the piece and makes the sheet unreadable for the player.

Passages **tile** the piece: no gaps, no overlaps, every frame belongs to exactly one. That is what
makes D-21 true. Changing a passage's ladder relabels the notes inside it and cannot touch anything
outside, because the frames are absolute wall clock and never move.

This module replaces `matrix/tempo_map.py`. The seam logic there existed because changing a tempo
moved every column after the seam. Nothing moves now, so there is no seam to manage.
"""

from __future__ import annotations

from aitu_backend.matrix.ladder import build_ladder, header_label, shift_ladder
from aitu_backend.schemas.time_matrix import FigureLadder, FigureName, Passage

__all__ = [
    "ladder_ranges",
    "one_passage",
    "passages_from_boundaries",
    "shift_passage",
    "split_passage",
    "with_ladder",
]


def one_passage(
    frame_count: int,
    ladder: FigureLadder,
    *,
    passage_id: str = "p1",
) -> list[Passage]:
    """The starting point for every piece: one passage covering everything.

    A piece only needs more than one when the playing changes speed enough that a single ladder
    labels part of it badly.
    """
    if frame_count <= 0:
        raise ValueError(f"A piece needs at least one frame, got {frame_count}")
    return [
        Passage(
            id=passage_id,
            start_frame=0,
            end_frame=frame_count,
            ladder=ladder,
            header_label=header_label(ladder),
        )
    ]


def passages_from_boundaries(
    frame_count: int,
    boundaries: list[int],
    ladders: list[FigureLadder],
) -> list[Passage]:
    """Build a tiling passage list from the frames the user drew and one ladder per section.

    ``boundaries`` are the frames where a new passage starts, not counting 0. Three boundaries mean
    four passages, so ``ladders`` must have one more entry than ``boundaries``.
    """
    if frame_count <= 0:
        raise ValueError(f"A piece needs at least one frame, got {frame_count}")
    ordered = sorted(set(boundaries))
    if ordered and (ordered[0] <= 0 or ordered[-1] >= frame_count):
        raise ValueError(
            f"Passage boundaries must fall inside the piece, between 1 and {frame_count - 1}; "
            f"got {ordered}"
        )
    if len(ladders) != len(ordered) + 1:
        raise ValueError(
            f"{len(ordered)} boundary/boundaries make {len(ordered) + 1} passages, "
            f"but {len(ladders)} ladder(s) were given"
        )

    edges = [0, *ordered, frame_count]
    return [
        Passage(
            id=f"p{index + 1}",
            start_frame=start,
            end_frame=end,
            ladder=ladder,
            header_label=header_label(ladder),
        )
        for index, (start, end, ladder) in enumerate(zip(edges, edges[1:], ladders))
    ]


def ladder_ranges(passages: list[Passage]) -> list[tuple[int, int, FigureLadder]]:
    """The form the figure selection reads: ``(startFrame, endFrame, ladder)`` per passage."""
    return [(passage.start_frame, passage.end_frame, passage.ladder) for passage in passages]


def with_ladder(
    passages: list[Passage],
    passage_id: str,
    ladder: FigureLadder,
) -> list[Passage]:
    """Replace one passage's ladder, leaving every frame boundary where it was (D-21).

    Nothing outside the named passage changes, and nothing inside it moves either: the notes keep
    their columns and only their printed figures are chosen again.
    """
    found = False
    updated: list[Passage] = []
    for passage in passages:
        if passage.id == passage_id:
            found = True
            updated.append(
                passage.model_copy(update={"ladder": ladder, "header_label": header_label(ladder)})
            )
        else:
            updated.append(passage)
    if not found:
        raise ValueError(f"No passage with id {passage_id!r}; there are {[p.id for p in passages]}")
    return updated


def shift_passage(passages: list[Passage], passage_id: str, steps: int) -> list[Passage]:
    """ "Make everything in this passage one step longer or shorter" (D-18).

    A pure relabelling: `negra = 300 ms` becomes `dottedNegra = 300 ms`, every millisecond value
    stays, and no note moves. Used to rewrite a fast section as corcheas instead of semicorcheas.
    """
    target = next((passage for passage in passages if passage.id == passage_id), None)
    if target is None:
        raise ValueError(f"No passage with id {passage_id!r}; there are {[p.id for p in passages]}")
    return with_ladder(passages, passage_id, shift_ladder(target.ladder, steps))


def split_passage(
    passages: list[Passage],
    passage_id: str,
    at_frame: int,
    ladder: FigureLadder | None = None,
) -> list[Passage]:
    """Cut one passage in two at a frame the user picked, keeping the tiling intact.

    The second half starts with the same ladder unless a different one is given, so drawing a
    boundary and naming its ladder are two separate actions in the UI.
    """
    target = next((passage for passage in passages if passage.id == passage_id), None)
    if target is None:
        raise ValueError(f"No passage with id {passage_id!r}; there are {[p.id for p in passages]}")
    if not target.start_frame < at_frame < target.end_frame:
        raise ValueError(
            f"Frame {at_frame} is not inside passage {passage_id!r}, which covers "
            f"[{target.start_frame}, {target.end_frame})"
        )
    second_ladder = ladder or target.ladder
    result: list[Passage] = []
    for passage in passages:
        if passage.id != passage_id:
            result.append(passage)
            continue
        result.append(passage.model_copy(update={"end_frame": at_frame}))
        result.append(
            Passage(
                id=f"{passage_id}b",
                start_frame=at_frame,
                end_frame=passage.end_frame,
                ladder=second_ladder,
                header_label=header_label(second_ladder),
            )
        )
    return _renumber(result)


def _renumber(passages: list[Passage]) -> list[Passage]:
    """Give the passages plain sequential ids again, in time order.

    Ids are labels for the UI, not addresses of anything stored, so renaming them is safe. Frame
    boundaries are the addresses, and those never change here.
    """
    ordered = sorted(passages, key=lambda passage: passage.start_frame)
    return [
        passage.model_copy(update={"id": f"p{index + 1}"}) for index, passage in enumerate(ordered)
    ]


def default_ladder(negra_ms: float) -> FigureLadder:
    """A ladder from one negra, for the common case where the user names the dominant peak."""
    return build_ladder(FigureName.NEGRA, negra_ms)
