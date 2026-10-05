#!/usr/bin/env python3
"""Check every relative link of the documentation.

Reads every Markdown file of `context/` and `documentation/`, and every `README.md` of the
repository, and checks that each relative link points at a file or folder that exists. Links to
the web (`http:`, `https:`, `mailto:`) and links inside code are not checked. A `#section` part is
not checked either: only the file.

Exits 0 when every link resolves, 1 when at least one is broken.

    python3 scripts/docs/check-links.py            # list the broken links
    python3 scripts/docs/check-links.py --summary  # one count per file
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
FOLDERS = ("context", "documentation")

# [text](target) and ![alt](target); the target may be wrapped in <...> and followed by a title.
INLINE_LINK = re.compile(r"!?\[(?:[^\[\]]|\[[^\]]*\])*\]\(\s*(<[^>]*>|[^)\s]+)(?:\s+\"[^\"]*\")?\s*\)")
# [label]: target
REFERENCE_LINK = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(<[^>]*>|\S+)", re.MULTILINE)
# <a href="target"> and <img src="target">
HTML_LINK = re.compile(r"<(?:a|img)\b[^>]*?\b(?:href|src)=\"([^\"]+)\"", re.IGNORECASE)
FENCE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE = re.compile(r"(`+)(?:(?!\1).)+?\1")
SKIP_SCHEMES = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def markdown_files() -> list[Path]:
    """Tracked and untracked (not ignored) Markdown files in scope."""
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", "*.md"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout
    files = []
    for name in sorted(set(filter(None, out.split("\0")))):
        path = Path(name)
        if path.parts[0] in FOLDERS or path.name == "README.md":
            if (ROOT / path).is_file():
                files.append(path)
    return files


def strip_code(text: str) -> list[tuple[int, str]]:
    """The lines of `text` outside fenced code, with inline code blanked, numbered from 1."""
    lines, fence = [], None
    for number, line in enumerate(text.splitlines(), start=1):
        match = FENCE.match(line)
        if match:
            if fence is None:
                fence = match.group(1)
            elif match.group(1) == fence:
                fence = None
            continue
        if fence is None:
            lines.append((number, INLINE_CODE.sub(lambda m: " " * len(m.group(0)), line)))
    return lines


def targets(lines: list[tuple[int, str]]):
    for number, line in lines:
        for pattern in (INLINE_LINK, REFERENCE_LINK, HTML_LINK):
            for match in pattern.finditer(line):
                yield number, match.group(1).strip("<>")


def broken_links(path: Path) -> list[tuple[int, str]]:
    text = (ROOT / path).read_text(encoding="utf-8", errors="replace")
    broken = []
    for number, target in targets(strip_code(text)):
        if not target or target.startswith("#") or SKIP_SCHEMES.match(target):
            continue
        file_part = unquote(target.split("#", 1)[0].split("?", 1)[0])
        if not file_part:
            continue
        base = ROOT if file_part.startswith("/") else (ROOT / path).parent
        if not (base / file_part.lstrip("/")).exists():
            broken.append((number, target))
    return broken


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--summary", action="store_true", help="one count per file")
    args = parser.parse_args()

    files = markdown_files()
    total = 0
    for path in files:
        broken = broken_links(path)
        if not broken:
            continue
        total += len(broken)
        if args.summary:
            print(f"{len(broken):4d}  {path}")
        else:
            for number, target in broken:
                print(f"{path}:{number}: {target}")
    print(f"{len(files)} files checked, {total} broken links", file=sys.stderr)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
