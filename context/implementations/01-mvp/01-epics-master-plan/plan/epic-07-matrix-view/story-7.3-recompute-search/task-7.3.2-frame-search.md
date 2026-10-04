# Task 7.3.2 — Frame and timestamp search

## Subtask 7.3.2.1 — Search box

Accepts a frame number (`120`) or timestamp (`01:50`); scrolls the grid so the row is visible with
some preceding context. For a segment, timestamp search is explicitly local to the segment.

## Subtask 7.3.2.2 — Cross-tab deep link

The Piano Roll tab links here with a `?frame=` query param — the "go fix that frame in the Matrix tab" flow. On load with a param, jump straight to it.

## Acceptance

Manual trial: from Piano Roll at 01:50, click through to Matrix and land on the right row.
