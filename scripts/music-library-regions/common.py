"""Shared pieces of the regional download (implementation 02, Phase 16).

Standard library only, like ``scripts/music-library/`` of the parallel work (02-a). Every page is
saved once under ``<data>/<source>/raw/`` as it arrived; ``manifest.sqlite`` of the source records
each URL, its status and its file, so a stopped run continues where it stopped and a saved page
is never asked for again. One timer per source keeps the gap between two requests.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
USER_AGENT = "AImpromptuMusicLibrary/1.0 (personal local archive)"

# Pages that are not the content but a site's protection asking for a browser.
CHALLENGE_MARKS = (b"Just a moment...", b"cf-challenge", b"Sucuri WebSite Firewall")
REFUSED = {403, 429, 503}
BACKOFF_SECONDS = (60, 120, 240)


def data_dir() -> Path:
    """``MUSIC_LIBRARY_REGIONS_DIR``, else ``data/music-library-regions`` beside the repository."""
    override = os.environ.get("MUSIC_LIBRARY_REGIONS_DIR")
    return Path(override) if override else REPO.parent / "data" / "music-library-regions"


class Refused(RuntimeError):
    """The site refused or challenged us after every wait: stop, keep what is saved."""


@dataclass
class Page:
    url: str
    status: int
    path: Path | None

    def read(self) -> bytes:
        return self.path.read_bytes() if self.path else b""


class Fetcher:
    """One source: its raw folder, its manifest and its timer."""

    def __init__(self, source: str, gap_seconds: float, log=print):
        self.source = source
        self.root = data_dir() / source
        self.raw = self.root / "raw"
        self.raw.mkdir(parents=True, exist_ok=True)
        self.gap = gap_seconds
        self.log = log
        self._last = 0.0
        self.db = sqlite3.connect(self.root / "manifest.sqlite")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS pages (url TEXT PRIMARY KEY, path TEXT, status INTEGER,"
            " bytes INTEGER, fetched_at TEXT)"
        )
        self.db.commit()
        self.requests = 0

    def known(self, url: str) -> Page | None:
        row = self.db.execute("SELECT status, path FROM pages WHERE url = ?", (url,)).fetchone()
        if row is None:
            return None
        status, rel = row
        path = self.raw / rel if rel else None
        if status == 200 and (path is None or not path.exists()):
            return None
        return Page(url, status, path)

    def get(self, url: str, rel: str) -> Page:
        """The page of ``url``, saved at ``raw/<rel>``; asked for only when not saved yet.

        A 404 or 500 is recorded and returned (a week with no chart); a refusal or a challenge
        waits 60, 120 and 240 s, then raises ``Refused``."""
        page = self.known(url)
        if page is not None:
            return page
        for attempt in range(len(BACKOFF_SECONDS) + 1):
            status, body = self._request(url)
            challenged = status == 200 and any(mark in body[:20000] for mark in CHALLENGE_MARKS)
            if status not in REFUSED and not challenged:
                break
            if attempt == len(BACKOFF_SECONDS):
                raise Refused(f"{url}: HTTP {status}{' (challenge page)' if challenged else ''}")
            wait = BACKOFF_SECONDS[attempt]
            self.log(f"  {url}: HTTP {status}, waiting {wait} s")
            time.sleep(wait)
        path = None
        if status == 200:
            path = self.raw / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(path.suffix + ".part")
            tmp.write_bytes(body)
            tmp.replace(path)
        self.db.execute(
            "INSERT OR REPLACE INTO pages VALUES (?, ?, ?, ?, ?)",
            (url, rel if path else None, status, len(body),
             datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        self.db.commit()
        return Page(url, status, path)

    def _request(self, url: str) -> tuple[int, bytes]:
        wait = self._last + self.gap - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()
        self.requests += 1
        # A file name with accents ("Producció") must be quoted before it is sent.
        quoted = urllib.parse.quote(url, safe=":/?&=%#+~,;@!$'()*")
        request = urllib.request.Request(quoted, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.read() or b""
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            self.log(f"  {url}: {error}")
            return 503, b""

    def status(self) -> str:
        rows = self.db.execute("SELECT status, COUNT(*), SUM(bytes) FROM pages GROUP BY status").fetchall()
        parts = [f"HTTP {s}: {n} pages, {(b or 0) / 1e6:.1f} MB" for s, n, b in rows]
        return f"{self.source}: " + ("; ".join(parts) if parts else "nothing saved")


def logger(path: Path):
    """A ``print`` that also appends to ``path``, with the time."""
    path.parent.mkdir(parents=True, exist_ok=True)

    def log(message: str) -> None:
        line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {message}"
        print(line, flush=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    return log


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(1)
