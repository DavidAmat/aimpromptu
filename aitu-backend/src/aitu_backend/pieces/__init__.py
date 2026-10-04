"""A piece as a flow of steps: Source, Audio, Notes, Hands, Sheet (implementation 08, plan section 7).

:mod:`.status` answers which steps are ready, running, stale or missing, from the revisions of plan
section 8. :mod:`.edits` applies the operations of the piano roll visualization to the notes. The
routes are :mod:`aitu_backend.api.pieces`.
"""
