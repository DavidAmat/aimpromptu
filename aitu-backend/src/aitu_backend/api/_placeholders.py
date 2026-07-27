"""Helper for endpoints whose implementation lands in a later epic.

The routes exist now — with their final path, method and tag — so the
frontend shell can be wired against real URLs. Calling one answers
``501 Not Implemented`` naming the epic that will fill it.
"""

from fastapi import HTTPException


def not_implemented(epic: str, what: str) -> HTTPException:
    """Build the ``501`` raised by every placeholder endpoint."""
    return HTTPException(
        status_code=501,
        detail=f"Not implemented yet — {what} is delivered by {epic}.",
    )
