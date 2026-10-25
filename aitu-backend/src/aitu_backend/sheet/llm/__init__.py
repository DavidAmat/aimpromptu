"""The LLM step: piano matrix notation -> F1 bars sheet, window by window, checked, with the algorithm as fallback.

Entry point: :func:`aitu_backend.sheet.llm.chain.write_song` (``notes``, a ``complete(system, messages) -> text`` function).
Modules: ``song`` (windows, what an accepted answer decides, join), ``prompts`` (frozen instructions in ``prompt/``,
window prompt, feedback), ``windows`` (checker, decided context lines), ``guards`` (phase 14 rules), ``chain``.
"""

from aitu_backend.sheet.llm.chain import Complete, SongSheet, WindowLog, frames_of, write_song

__all__ = ["Complete", "SongSheet", "WindowLog", "frames_of", "write_song"]
