"""Slugs and folder codes — the vocabulary the storage tree is built from.

Every folder name under ``data/`` is produced here, so a rename policy is a
one-file change. Granularity codes come from
:mod:`aitu_backend.schemas.matrix`; this module only combines them.
"""

from __future__ import annotations

import re
import unicodedata

from aitu_backend.schemas.matrix import CODE_TO_GRANULARITY, GRANULARITY_CODES, Granularity

#: `v2_gn` — a version number plus a granularity code.
VERSION_FOLDER_PATTERN = re.compile(r"^v(?P<version>\d+)_(?P<granularity>g[a-z]+)$")

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


def granularity_code(granularity: Granularity) -> str:
    """``Granularity.NEGRA`` -> ``"gn"``."""
    return GRANULARITY_CODES[granularity]


def granularity_from_code(code: str) -> Granularity:
    """``"gn"`` -> ``Granularity.NEGRA``. Raises on an unknown code."""
    try:
        return CODE_TO_GRANULARITY[code]
    except KeyError as exc:
        known = ", ".join(sorted(CODE_TO_GRANULARITY))
        raise ValueError(f"Unknown granularity code '{code}'. Known: {known}") from exc


def version_folder(version: int, granularity: Granularity) -> str:
    """``(2, Granularity.NEGRA)`` -> ``"v2_gn"``."""
    if version < 1:
        raise ValueError(f"Version numbers start at 1, got {version}")
    return f"v{version}_{granularity_code(granularity)}"


def parse_version_folder(folder: str) -> tuple[int, Granularity]:
    """``"v2_gn"`` -> ``(2, Granularity.NEGRA)``. Raises on a malformed name."""
    match = VERSION_FOLDER_PATTERN.match(folder)
    if match is None:
        raise ValueError(f"'{folder}' is not a version folder name (expected e.g. 'v2_gn')")
    version = int(match.group("version"))
    if version < 1:
        raise ValueError(f"'{folder}' has version {version}; version numbers start at 1")
    return version, granularity_from_code(match.group("granularity"))


def next_version(existing: list[str]) -> int:
    """Highest version number in ``existing`` plus one; 1 when empty.

    Unparseable entries are ignored, so a stray folder never blocks a save.
    """
    numbers = []
    for folder in existing:
        try:
            numbers.append(parse_version_folder(folder)[0])
        except ValueError:
            continue
    return max(numbers, default=0) + 1


def matrix_filename(version: int, granularity: Granularity, hand: str | None = None) -> str:
    """`piano_matrix_v1_gsc.npz`, or `piano_matrix_v1_gsc_left.npz` per hand."""
    stem = f"piano_matrix_{version_folder(version, granularity)}"
    if hand:
        stem = f"{stem}_{hand}"
    return f"{stem}.npz"
