"""Build one database per regional source from its saved pages (implementation 02, Phase 16).

    python3 scripts/music-library-regions/build.py <source>...   # or: all

Writes ``<data>/<source>/<source>.sqlite`` again from ``raw/`` (the old file is replaced), with the
same tables for every source, so the app's import (``make regional-import``) reads them all alike:

    charts   code, name, region, period (week | month | number_one | totals), source
    songs    id, key (the source's identity of the song), title, artist (as printed),
             youtube_id, apple_id, spotify_id
    entries  song_id, chart, start, end (dates, both included), rank, size (the list's length)
    totals   song_id, chart, weeks, top10_weeks, peak, peak_times, peak_streams, streams, year
    notes    what the build could not read, one line each
"""

from __future__ import annotations

import argparse
import sqlite3
import subprocess
from datetime import date, timedelta
from pathlib import Path

import parse
from common import data_dir

SCHEMA = """
CREATE TABLE charts (code TEXT PRIMARY KEY, name TEXT, region TEXT, period TEXT, source TEXT);
CREATE TABLE songs (id INTEGER PRIMARY KEY, key TEXT UNIQUE, title TEXT, artist TEXT,
                    youtube_id TEXT, apple_id TEXT, spotify_id TEXT);
CREATE TABLE entries (song_id INTEGER REFERENCES songs(id), chart TEXT REFERENCES charts(code),
                      start TEXT, end TEXT, rank INTEGER, size INTEGER,
                      PRIMARY KEY (chart, start, rank));
CREATE TABLE totals (song_id INTEGER REFERENCES songs(id), chart TEXT REFERENCES charts(code),
                     weeks INTEGER, top10_weeks INTEGER, peak INTEGER, peak_times INTEGER,
                     peak_streams INTEGER, streams INTEGER, year INTEGER,
                     PRIMARY KEY (song_id, chart));
CREATE TABLE notes (text TEXT);
CREATE INDEX entries_song ON entries(song_id);
"""


class Out:
    """The database being written, with a song looked up or made by its key."""

    def __init__(self, source: str):
        self.path = data_dir() / source / f"{source}.sqlite"
        tmp = self.path.with_suffix(".sqlite.part")
        tmp.unlink(missing_ok=True)
        self.tmp = tmp
        self.db = sqlite3.connect(tmp)
        self.db.executescript(SCHEMA)
        self.ids: dict[str, int] = {}

    def chart(self, code: str, name: str, region: str, period: str, source: str) -> None:
        self.db.execute("INSERT INTO charts VALUES (?, ?, ?, ?, ?)", (code, name, region, period, source))

    def song(self, row: parse.Row) -> int:
        key = row.key or f"{parse.compared(row.title)}|{parse.compared(row.artist)}"
        if key in self.ids:
            song_id = self.ids[key]
            # a later row may know an id the first did not
            self.db.execute(
                "UPDATE songs SET youtube_id = COALESCE(youtube_id, ?), apple_id = COALESCE(apple_id, ?),"
                " spotify_id = COALESCE(spotify_id, ?) WHERE id = ?",
                (row.youtube_id, row.apple_id, row.spotify_id, song_id),
            )
            return song_id
        cur = self.db.execute(
            "INSERT INTO songs (key, title, artist, youtube_id, apple_id, spotify_id) VALUES (?, ?, ?, ?, ?, ?)",
            (key, row.title, row.artist, row.youtube_id, row.apple_id, row.spotify_id),
        )
        self.ids[key] = cur.lastrowid
        return cur.lastrowid

    def entries(self, chart: str, start: date, end: date, rows: list[parse.Row]) -> int:
        size = max(row.rank for row in rows)  # a page that repeats a date gives more rows than places
        written = 0
        for row in rows:
            cur = self.db.execute(
                "INSERT OR IGNORE INTO entries VALUES (?, ?, ?, ?, ?, ?)",
                (self.song(row), chart, start.isoformat(), end.isoformat(), row.rank, size),
            )
            written += cur.rowcount
        return written

    def note(self, text: str) -> None:
        self.db.execute("INSERT INTO notes VALUES (?)", (text,))

    def close(self) -> str:
        counts = {t: self.db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in ("charts", "songs", "entries", "totals", "notes")}
        self.db.commit()
        self.db.close()
        self.tmp.replace(self.path)
        return ", ".join(f"{n} {t}" for t, n in counts.items())


def raw(source: str) -> Path:
    return data_dir() / source / "raw"


# ------------------------------------------------------------------------------------- sources


def build_spanishcharts(out: Out) -> None:
    out.chart("promusicae-singles", "PROMUSICAE singles (spanishcharts.com)", "spain", "week",
              "spanishcharts.com")
    for path in sorted(raw("spanishcharts").glob("*/*.html")):
        rows = parse.spanishcharts_week(path.read_bytes())
        if not rows:
            out.note(f"{path.name}: no rows")
            continue
        week = date(int(path.stem[:4]), int(path.stem[4:6]), int(path.stem[6:]))
        out.entries("promusicae-singles", week, parse.week_end(week), rows)


def build_los40(out: Out) -> None:
    out.chart("los40", "Lista LOS40 (los40.com)", "spain", "week", "los40.com")
    out.chart("los40-number-ones", "Lista LOS40, number ones (los40.com)", "spain", "number_one", "los40.com")
    full_lists_from = date(2004, 1, 3)
    ones = []
    for path in sorted(raw("los40").glob("years/*.html")):
        ones.extend(pair for pair in parse.los40_number_ones(path.read_bytes()) if pair[0] < full_lists_from)
    ones.sort(key=lambda pair: pair[0])
    for i, (week, row) in enumerate(ones):
        # a list ran until the next one (a gap of more than a week is a week without a list)
        nxt = ones[i + 1][0] if i + 1 < len(ones) else full_lists_from
        end = min(nxt - timedelta(days=1), parse.week_end(week))
        out.entries("los40-number-ones", week, end, [row])
    for path in sorted(raw("los40").glob("weeks/*/*.html")):
        rows = parse.los40_week(path.read_bytes())
        week = date.fromisoformat(path.stem)
        if not rows:
            continue  # a Saturday with no list: the page answers with an empty list
        if len(rows) == 1 and week >= full_lists_from:
            out.note(f"{path.stem}: one row only")
        out.entries("los40", week, parse.week_end(week), rows)


def build_kworb(out: Out) -> None:
    out.chart("spotify-spain", "Spotify Spain weekly chart, totals (kworb.net)", "spain", "totals", "kworb.net")
    page = raw("kworb") / "es_weekly_totals.html"
    for row in parse.kworb_totals(page.read_bytes()):
        e = row.extra
        out.db.execute(
            "INSERT OR IGNORE INTO totals VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)",
            (out.song(row), "spotify-spain", e["weeks"], e["top10_weeks"], e["peak"], e["peak_times"],
             e["peak_streams"], e["streams"]),
        )


def _apecat_period(path: Path, month_list: parse.MonthList) -> tuple[date, date] | None:
    if month_list.start:
        return month_list.start, month_list.end
    if not month_list.month:
        return None
    # The first lists of 2018 give only their month; the folder is the month it was put online.
    folder_year, folder_month = int(path.parent.parent.name), int(path.parent.name)
    year = folder_year if month_list.month <= folder_month else folder_year - 1
    end = date(year, month_list.month, 11)
    start = (end.replace(day=1) - timedelta(days=1)).replace(day=12)
    return start, end


def build_apecat(out: Out) -> None:
    out.chart("apecat-llengua", "APECAT / BMAT TOP 30, songs in Catalan", "catalan", "month", "apecat.com")
    out.chart("apecat-produccio", "APECAT / BMAT TOP 30, Catalan labels", "catalan", "month", "apecat.com")
    seen = set()
    for path in sorted(raw("apecat").glob("pdf/*/*/*.pdf")):
        xml = subprocess.run(["pdftohtml", "-xml", "-i", "-stdout", str(path)],
                             capture_output=True, text=True).stdout
        month_list = parse.apecat_list(xml, path.name)
        rel = path.relative_to(raw("apecat"))
        if month_list is None:
            out.note(f"{rel}: no text (an image)")
            continue
        if month_list.yearly:
            continue  # the year-end lists: kept as files, not used
        period = _apecat_period(path, month_list)
        if period is None or len(month_list.rows) != 30:
            out.note(f"{rel}: {len(month_list.rows)} rows, period {period}")
            continue
        chart = f"apecat-{month_list.series}"
        if (chart, period[0]) in seen:
            out.note(f"{rel}: the same list as an earlier file ({period[0]})")
            continue
        seen.add((chart, period[0]))
        out.entries(chart, period[0], period[1], month_list.rows)


def build_wikipedia(out: Out) -> None:
    out.chart("wikipedia-spain-number-ones", "Number ones in Spain (English Wikipedia)", "spain",
              "number_one", "en.wikipedia.org")
    out.chart("wikipedia-spain-top10", "Weekly top 10 in Spain, 1982 to 1996 (Spanish Wikipedia)", "spain",
              "week", "es.wikipedia.org")
    out.chart("viquipedia-spotify-catalan", "Songs in Catalan most played on Spotify (Viquipèdia)", "catalan",
              "totals", "ca.wikipedia.org")
    ones = []
    for path in sorted(raw("wikipedia").glob("en/*.wikitext")):
        year = int(next(part for part in path.stem.split("_") if part.isdigit() and len(part) == 4))
        found = parse.wikipedia_number_ones(path.read_text(encoding="utf-8"), year)
        if not found:
            out.note(f"{path.name}: no table read")
        ones.extend(found)
    ones.sort(key=lambda pair: pair[0])
    for i, (start, row) in enumerate(ones):
        nxt = ones[i + 1][0] if i + 1 < len(ones) else start + timedelta(days=7)
        out.entries("wikipedia-spain-number-ones", start, nxt - timedelta(days=1), [row])
    weeks: dict[date, list[parse.Row]] = {}
    for path in sorted(raw("wikipedia").glob("es/*.wikitext")):
        found = parse.wikipedia_top10(path.read_text(encoding="utf-8"))
        if not found:
            out.note(f"{path.name}: no table read")
        for week, row in found:
            weeks.setdefault(week, []).append(row)
    for week, rows in sorted(weeks.items()):
        out.entries("wikipedia-spain-top10", week, parse.week_end(week), rows)
    for path in raw("wikipedia").glob("ca/*.wikitext"):
        for row in parse.viquipedia_spotify(path.read_text(encoding="utf-8")):
            out.db.execute(
                "INSERT OR IGNORE INTO totals VALUES (?, ?, NULL, NULL, ?, NULL, NULL, ?, ?)",
                (out.song(row), "viquipedia-spotify-catalan", row.rank, row.extra["streams"], row.extra["year"]),
            )


BUILDERS = {
    "spanishcharts": build_spanishcharts,
    "los40": build_los40,
    "kworb": build_kworb,
    "apecat": build_apecat,
    "wikipedia": build_wikipedia,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sources", nargs="+", choices=sorted(BUILDERS) + ["all"])
    args = parser.parse_args()
    for source in sorted(BUILDERS) if "all" in args.sources else args.sources:
        out = Out(source)
        BUILDERS[source](out)
        print(f"{source}: {out.close()}")


if __name__ == "__main__":
    main()
