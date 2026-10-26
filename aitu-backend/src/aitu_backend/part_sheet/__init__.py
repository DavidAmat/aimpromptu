"""The new piano sheet of a part in the app (implementation 03, Phases 5 to 7).

* :mod:`.store`: ``sheet.f1``, the sheet as it was last written, with a record of how;
* :mod:`.build`: the sheet of a part at any moment (stored, laid again on changed notes, or the algorithm) and its
  drawing for a page;
* :mod:`.job`: Sonnet writing the sheet in the background, window by window;
* :mod:`.edits` (Phase 6): editing the sheet (a hand moved in ``notes.pmn``, ``sheet.f1`` laid again on it), with
  undo and redo from the part's log; Phase 7 adds the reading edits, notes taken off the page and a stretch the AI
  wrote again;
* :mod:`.reading` (Phase 7): the reading edits of the two toolboxes, as functions on a frames sheet;
* :mod:`.lengths` (Phase 8B): ``sheet.f1`` through every change of a part's length (a paste, a promotion, a split, a
  join), the new sheet's version of ``editing.marks``; :mod:`.edits` makes a paste one step of undo.

The routes are ``api/sheet.py``. The modules are imported one by one (``aitu_backend.part_sheet.store``): the
transcription pipeline clears the stored sheet, and :mod:`.build` reads the pipeline.
"""
