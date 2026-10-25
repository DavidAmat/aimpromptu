"""The new piano sheet of a part in the app (implementation 03, Phase 5).

* :mod:`.store`: ``sheet.f1``, the sheet as it was last written, with a record of how;
* :mod:`.build`: the sheet of a part at any moment (stored, laid again on changed notes, or the algorithm) and its
  drawing for a page;
* :mod:`.job`: Sonnet writing the sheet in the background, window by window.

The routes are ``api/sheet.py``. The modules are imported one by one (``aitu_backend.part_sheet.store``): the
transcription pipeline clears the stored sheet, and :mod:`.build` reads the pipeline.
"""
