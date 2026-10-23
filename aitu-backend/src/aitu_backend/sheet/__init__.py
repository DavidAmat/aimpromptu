"""The product core of the new piano sheet chain: ``aitu_notation`` of the research (plan 01, phase 15), copied in
implementation 03, Phase 1. ``aitu_notation.X`` of the research is ``aitu_backend.sheet.X`` here.

    piano matrix notation --(proposal: the algorithm | llm: the LLM step)--> F1 bars --(engrave)--> SVG + cursor map

Modules (imports go one way: ``sheet`` <- ``proposal``, ``llm``, ``engrave``; ``llm`` -> ``proposal`` for the
fallback only):

* ``sheet``: the sheet data, F1 read / write, matrix -> frames sheet, the ``notes.pmn`` loader (the piano matrix
  notation itself is the backend's ``aitu_backend.pmn`` and ``aitu_backend.matrix.keys``);
* ``proposal``: the algorithm (matrix + hands -> F1 bars sheet), no LLM;
* ``llm``: the LLM step (windows, frozen prompt, checker, chain, fallback) behind one ``complete`` function;
* ``engrave``: F1 bars sheet -> SVG, cursor map and note ids.

Run time: the standard library, numpy and those two backend modules; every asset is a frozen file inside the
package. Contracts: ``README.md`` next to this file and the research's ``synthesis/06-modules.md``.
"""

__version__ = "0.1.0"
