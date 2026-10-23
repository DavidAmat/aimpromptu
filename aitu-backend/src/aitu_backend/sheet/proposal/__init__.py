"""The algorithm: piano matrix notation + hands -> F1 bars sheet, without an LLM (research phase 6).

The product path when no LLM runs, and the fallback of the LLM step. Steps: quarter (``beat``), meter and downbeat
(``meter``), beat tracking, quantization and figures (``pipeline``), rulebook rules for beams, spelling and clefs
(``rules``, ``theory``). Frozen files: ``beat_weights.json``, ``meter_weights.json``, ``spelling_tables.json``.
"""

from aitu_backend.sheet.proposal.pipeline import Proposal, hand_sheet_of, propose

__all__ = ["Proposal", "hand_sheet_of", "propose"]
