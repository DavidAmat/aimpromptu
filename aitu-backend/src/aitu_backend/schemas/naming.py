"""Slugs and folder codes — the vocabulary the storage tree is built from.

Every folder name under ``data/`` is produced here, so a rename policy is a
one-file change.

The version-folder scheme, decided in P4.4
------------------------------------------

A folder used to be ``v2_gn``: a version number plus a **granularity code**, the
note figure one column stood for. There are no granularities any more (D-01), so
the code had to be replaced with something, and the choice was between dropping
it entirely (``v2``) and putting the frame length in its place (``v2_f40``).

**``v2_f40`` is the scheme**, and the reason is the idea the repository is built
on: *a version is a musical state, and the grid is a view of it*. ``v1_gsc`` and
``v1_gn`` were the same take collapsed two ways, which is why saving at a second
granularity pinned the version number instead of advancing it. That distinction
survives the refactor unchanged — the same recording at 20 ms and at 40 ms is the
same playing on a finer or a coarser grid — so the folder still needs to say
which view it holds. Dropping the suffix would make two views of one state
collide on one folder name.

The suffix is the frame length in milliseconds, so ``v2_f40`` reads directly as
"version 2, forty milliseconds a column". A fractional frame length is written
with the point removed, ``f12_5`` for 12.5 ms, because a dot in a folder name
invites a reader to treat what follows as an extension.
"""

from __future__ import annotations

import re
import unicodedata

#: `v2_f40` — a version number plus a frame length in milliseconds.
VERSION_FOLDER_PATTERN = re.compile(r"^v(?P<version>\d+)_f(?P<frame>\d+(?:_\d+)?)$")

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """Filesystem-safe, lowercase, hyphenated form of a human name.

    Accents are folded (``Beyoncé`` -> ``beyonce``), every other run of
    non-alphanumerics becomes a single hyphen, and the result is trimmed.
    Empty input raises: a nameless folder helps no one.
    """
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = _SLUG_STRIP.sub("-", ascii_only).strip("-")
    if not slug:
        raise ValueError(f"'{value}' has no slug-able characters")
    return slug


def frame_code(frame_ms: float) -> str:
    """``40`` -> ``"f40"``; ``12.5`` -> ``"f12_5"``.

    A whole number of milliseconds writes as itself. A fraction keeps its digits
    with the point replaced, because a dot would read as a file extension.
    """
    if frame_ms <= 0:
        raise ValueError(f"A frame length must be positive, got {frame_ms}")
    rounded = round(float(frame_ms), 3)
    if rounded == int(rounded):
        return f"f{int(rounded)}"
    return "f" + f"{rounded:g}".replace(".", "_")


def frame_from_code(code: str) -> float:
    """``"f40"`` -> ``40.0``. Raises on anything that is not a frame code."""
    if not code.startswith("f"):
        raise ValueError(f"'{code}' is not a frame code (expected e.g. 'f40')")
    try:
        return float(code[1:].replace("_", "."))
    except ValueError as exc:
        raise ValueError(f"'{code}' is not a frame code (expected e.g. 'f40')") from exc


def version_folder(version: int, frame_ms: float) -> str:
    """``(2, 40)`` -> ``"v2_f40"``."""
    if version < 1:
        raise ValueError(f"Version numbers start at 1, got {version}")
    return f"v{version}_{frame_code(frame_ms)}"


def parse_version_folder(folder: str) -> tuple[int, float]:
    """``"v2_f40"`` -> ``(2, 40.0)``. Raises on a malformed name."""
    match = VERSION_FOLDER_PATTERN.match(folder)
    if match is None:
        raise ValueError(f"'{folder}' is not a version folder name (expected e.g. 'v2_f40')")
    version = int(match.group("version"))
    if version < 1:
        raise ValueError(f"'{folder}' has version {version}; version numbers start at 1")
    return version, frame_from_code("f" + match.group("frame"))


def next_version(existing: list[str]) -> int:
    """Highest version number in ``existing`` plus one; 1 when empty.

    Unparseable entries are ignored, so a stray folder never blocks a save. A
    folder written under the old ``v2_gn`` scheme is one of those: it is left
    alone rather than renamed, and it cannot hold back the next number.
    """
    numbers = []
    for folder in existing:
        try:
            numbers.append(parse_version_folder(folder)[0])
        except ValueError:
            continue
    return max(numbers, default=0) + 1


def matrix_filename(version: int, frame_ms: float, hand: str | None = None) -> str:
    """`piano_matrix_v1_f40.npz`, or `piano_matrix_v1_f40_left.npz` per hand."""
    stem = f"piano_matrix_{version_folder(version, frame_ms)}"
    if hand:
        stem = f"{stem}_{hand}"
    return f"{stem}.npz"
