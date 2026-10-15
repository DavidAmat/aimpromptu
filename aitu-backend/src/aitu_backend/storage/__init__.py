"""Local persistence: the paths of ``.database/`` and the project bundles (implementation 02,
plan section 8).

:mod:`aitu_backend.storage.paths` builds every path; nothing else does.
:mod:`aitu_backend.storage.locate` finds the project of a part. :mod:`aitu_backend.storage.bundle`
reads and writes a project bundle, and :mod:`aitu_backend.storage.audio_files` the audio store.
A passage being re-recorded and its takes (Phase 9) are hidden projects of the vault
(``kind = 'passage'``), not files of the project they are about.

The old Piano Library (``.npz`` matrices, playground tracks, promotions, tags and playlists) was
deleted in implementation 02, Phase 3; git history keeps it.
"""
