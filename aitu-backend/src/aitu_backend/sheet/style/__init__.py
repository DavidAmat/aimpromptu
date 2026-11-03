"""Copy this style (implementation 06): the user edits a stretch of the sheet by hand (the reference), and every other
place of the song that plays the same kind of passage is written again the way the reference is written.

* ``match``: the passages of the song like the reference (code, no AI): the rhythm on the song's grid, the shape of
  the pitches, the harmony, and a repeat in another key (``shift``).

The run itself (the check by the AI, the batches, the marks the code copies) is ``sheet.llm.style`` (Phase 2).
"""
