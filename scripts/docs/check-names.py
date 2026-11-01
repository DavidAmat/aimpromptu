#!/usr/bin/env python3
"""Check the names in backticks of the documentation against the code.

Each name in backticks (inline code, not fenced code) is checked by its kind:

- a path (it has `/`, or ends in .py, .ts, .tsx, .md, .json, .mjs) must exist: from the repo root, from
  the two code roots, from the folder of the doc, or as the end of a tracked path (`api/sheet.py`);
- a route (`/llm/runs`, `GET /x`) must appear, by its last literal part, in `aitu-backend/src/aitu_backend/api/`;
- an identifier (`snake_case` with `_`, `CamelCase`, `camelCase`, or `name()`) must appear as a whole word in the
  code roots, the tests and `scripts/`.

Not checked: names with spaces, names under 3 characters, names of only numbers, and names with placeholders
(`<id>`, `*`, `...`, `~`). The report is for the reader: the script exits 0 even when names are missing.
Check-links is the gate.

    python3 scripts/docs/check-names.py                      # every doc in scope
    python3 scripts/docs/check-names.py context/ai/whole-run.md
    python3 scripts/docs/check-names.py --summary            # one count per doc
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE_ROOTS = ("aitu-backend/src", "aitu-frontend/src")
SEARCH_ROOTS = ("aitu-backend/src", "aitu-frontend/src", "aitu-backend/tests", "aitu-frontend/scripts", "scripts")
# Repo-level configuration that names settings (`WEB_BIND`, `Makefile` targets) lives outside the code roots.
SEARCH_ROOTS = SEARCH_ROOTS + ("compose.yaml", "Makefile", "aitu-backend/pyproject.toml", "aitu-frontend/package.json")
ROUTE_ROOT = "aitu-backend/src/aitu_backend/api"
# Machine paths and outside names: not a route, not a path of this repo.
NOT_CHECKED_PREFIXES = (
    "/home/", "/work/", "/mnt/", "/dev/", "/etc/", "/Volumes/", "/System/", "/usr/", "/var/", "/opt/", "@",
)
NOT_CHECKED_NAMES = {"node_modules"}
SCOPE_FOLDERS = ("app", "backend", "frontend", "music", "music-library", "colors")
SCOPE_FILES = (
    "documentation/README.md",
    "aitu-backend/src/aitu_backend/sheet/README.md",
    "aitu-backend/README.md",
    "aitu-frontend/README.md",
    "README.md",
)
PATH_ENDINGS = (".py", ".ts", ".tsx", ".md", ".json", ".mjs")

CODE_SPAN = re.compile(r"`([^`\n]+)`")
FENCE = re.compile(r"^\s*(```|~~~)")
ROUTE = re.compile(r"^(?:(?:GET|POST|PUT|PATCH|DELETE)\s+)?(/\S*)$")
PLACEHOLDER = re.compile(r"[<>*~]|\.\.\.|–|(?:^|[-/.])N{1,2}(?=$|[-/.])|0N")
CALL = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\(\)$")
SNAKE = re.compile(r"^[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+$")
CAMEL = re.compile(r"^[A-Z][a-z0-9]+(?:[A-Z][A-Za-z0-9]*)+$|^[a-z]+(?:[A-Z][A-Za-z0-9]*)+$")


def classify(name: str) -> str | None:
    """The kind of a name (`route`, `path`, `identifier`), or None when the name is not checked."""
    if "://" in name or name in NOT_CHECKED_NAMES or name.startswith(NOT_CHECKED_PREFIXES):
        return None
    route = ROUTE.match(name)
    # A "." in the path means a file path such as x.py, not a route.
    if route and route.group(1) != "/" and "." not in route.group(1):
        return "route"
    if len(name) < 3 or re.search(r"\s", name) or re.fullmatch(r"[\d.]+", name) or PLACEHOLDER.search(name):
        return None
    if "{" in name or "}" in name:
        return None
    if "/" in name or name.endswith(PATH_ENDINGS):
        return "path"
    if CALL.match(name) or SNAKE.match(name) or CAMEL.match(name):
        return "identifier"
    return None


def tracked_files() -> list[str]:
    """Every tracked and untracked (not ignored) file of the repository, as repo-relative paths."""
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout
    return [name for name in out.split("\0") if name]


def scope_docs(tracked: list[str]) -> list[Path]:
    """The Markdown files of the documentation scope (plan 05, Phase 1)."""
    docs = []
    for name in tracked:
        if not name.endswith(".md"):
            continue
        parts = Path(name).parts
        in_scope = (
            (len(parts) == 2 and parts[0] == "context")
            or (len(parts) >= 3 and parts[0] == "context" and parts[1] in SCOPE_FOLDERS)
            or (parts[0] == "documentation" and len(parts) >= 3 and parts[1] == "services")
            or name in SCOPE_FILES
        )
        if in_scope and (ROOT / name).is_file():
            docs.append(Path(name))
    return sorted(set(docs))


def path_exists(doc: Path, name: str, tracked: list[str]) -> bool:
    rel = re.sub(r":\d+$", "", name.split("#", 1)[0]).rstrip("/")
    if not rel:
        return False
    candidates = [ROOT / rel, ROOT / doc.parent / rel] + [ROOT / root / rel for root in CODE_ROOTS]
    if any(candidate.exists() for candidate in candidates):
        return True
    # By the end of a tracked path (a file name such as `api/sheet.py`), or a folder inside one.
    return any(
        path == rel or path.endswith("/" + rel) or ("/" + rel + "/") in path or path.startswith(rel + "/")
        for path in tracked
    )


def route_segment(name: str) -> str | None:
    """The last literal part of a route: `/sheet/{uuid}/llm/runs` gives `runs`."""
    path = name.split()[-1].split("?", 1)[0]
    parts = [part for part in path.split("/") if part and not re.search(r"[{}<>:]", part)]
    return parts[-1] if parts else None


def git_grep(args: list[str]) -> bool:
    """True when `git grep` finds a match. The searched paths are the ones that exist here."""
    return subprocess.run(["git", "grep", "-q", "--untracked", *args], cwd=ROOT).returncode == 0


def code_has(kind: str, text: str) -> bool:
    if kind == "route":
        return git_grep(["-F", "-e", text, "--", ROUTE_ROOT])
    roots = [root for root in SEARCH_ROOTS if (ROOT / root).exists()]
    if kind == "path":
        # A runtime file (`sheet.json`, `.database/`) is not in git: the code names it, so its literal is searched.
        return git_grep(["-F", "-e", text, "--", *roots])
    return git_grep(["-F", "-w", "-e", text, "--", *roots])


def search_key(kind: str, name: str) -> tuple[str, str] | None:
    """What to search in the code for a name: (kind, text) or None. A path is searched by its file name."""
    if kind == "route":
        segment = route_segment(name)
        return ("route", segment) if segment else None
    if kind == "identifier":
        call = CALL.match(name)
        return ("identifier", call.group(1) if call else name)
    if kind == "path":
        base = re.sub(r":\d+$", "", name).rstrip("/").rsplit("/", 1)[-1]
        return ("path", base) if len(base) >= 3 else None
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("docs", nargs="*", help="doc paths (default: every doc in scope)")
    parser.add_argument("--summary", action="store_true", help="one count per doc")
    args = parser.parse_args()

    tracked = tracked_files()
    if args.docs:
        docs = [(Path.cwd() / doc).resolve().relative_to(ROOT) for doc in args.docs]
    else:
        docs = scope_docs(tracked)

    # Collect the names of every doc: (doc, line, kind, name).
    refs = []
    for doc in docs:
        fence = None
        lines = (ROOT / doc).read_text(encoding="utf-8", errors="replace").splitlines()
        for number, line in enumerate(lines, start=1):
            match = FENCE.match(line)
            if match:
                if fence is None:
                    fence = match.group(1)
                elif match.group(1) == fence:
                    fence = None
                continue
            if fence is not None:
                continue
            for span in CODE_SPAN.finditer(line):
                name = span.group(1).strip()
                kind = classify(name)
                if kind:
                    refs.append((doc, number, kind, name))

    # Search the code once per distinct text; the searches run in parallel.
    keys = {search_key(kind, name) for _, _, kind, name in refs}
    keys.discard(None)
    with ThreadPoolExecutor(max_workers=8) as pool:
        found = dict(zip(keys, pool.map(lambda key: code_has(*key), keys)))

    missing = []
    for doc, number, kind, name in refs:
        key = search_key(kind, name)
        if kind == "path":
            ok = path_exists(doc, name, tracked) or bool(key and found[key])
        else:
            ok = key is None or found[key]
        if not ok:
            missing.append((doc, number, kind, name))

    if args.summary:
        counts = {}
        for doc, *_ in missing:
            counts[doc] = counts.get(doc, 0) + 1
        for doc in docs:
            print(f"{counts.get(doc, 0):4d}  {doc}")
    else:
        for doc, number, kind, name in missing:
            print(f"{doc}:{number}  {kind}  {name}")
    print(f"{len(docs)} docs, {len(refs)} names checked, {len(missing)} missing", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
