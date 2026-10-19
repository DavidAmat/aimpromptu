"""Read the saved pages of each regional source (implementation 02, Phase 16).

Each function takes the bytes of one saved page (or the XML of one PDF) and returns plain rows;
``build.py`` writes them into the source's database. Kept apart from the download so a parser fix
needs no new download, and so the tests can run on small fixtures with no network.
"""

from __future__ import annotations

import html
import re
import unicodedata
import urllib.parse
from dataclasses import dataclass, field
from datetime import date, timedelta


@dataclass
class Row:
    """One song at one place of one list."""

    title: str
    artist: str
    rank: int
    key: str = ""  # the source's own identity of the song, when it has one
    youtube_id: str | None = None
    apple_id: str | None = None
    spotify_id: str | None = None
    extra: dict = field(default_factory=dict)


def clean(text: str) -> str:
    """HTML entities and tags out, spaces collapsed."""
    text = html.unescape(html.unescape(re.sub(r"<[^>]+>", " ", text)))  # some names are escaped twice
    return re.sub(r"\s+", " ", text).strip()


def compared(text: str) -> str:
    """The form two titles or names are compared in: no case, accents or punctuation."""
    text = unicodedata.normalize("NFKD", text.replace("·", "")).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def youtube_id(url: str | None) -> str | None:
    if not url:
        return None
    match = re.search(r"(?:v=|youtu\.be/|/embed/)([A-Za-z0-9_-]{11})", html.unescape(url))
    return match.group(1) if match else None


# --------------------------------------------------------------------------------- spanishcharts


def spanishcharts_week(page: bytes) -> list[Row]:
    """The rows of one weekly chart page of spanishcharts.com (ISO-8859-1)."""
    text = page.decode("latin-1")
    rows = []
    for part in text.split("<tr onclick=\"location.href='showitem.asp")[1:]:
        ident = re.match(r"\?interpret=([^&]*)&titel=([^&]*)&cat=s'", part)
        rank = re.search(r"<td[^>]*><b>(\d+)</b></td>", part)
        names = re.search(r'class="navb"><b>(.*?)</b><br>(.*?)</a>', part, re.S)
        if not (ident and rank and names):
            continue
        interpret = urllib.parse.unquote_plus(ident.group(1), encoding="latin-1")
        titel = urllib.parse.unquote_plus(ident.group(2), encoding="latin-1")
        rows.append(Row(
            title=clean(names.group(2)), artist=clean(names.group(1)), rank=int(rank.group(1)),
            key=f"{interpret}|{titel}",
        ))
    return rows


# --------------------------------------------------------------------------------------- los40


def _apple_id(chunk: str) -> str | None:
    match = re.search(r"music\.apple\.com/[^\"]*?[?&](?:amp;)?i=(\d+)", chunk)
    return match.group(1) if match else None


def los40_week(page: bytes) -> list[Row]:
    """The rows of one weekly list of los40.com (40 rows from 2004, the number one before)."""
    text = page.decode("utf-8", "replace")
    start = text.find('<ul class="lst-can">')
    if start < 0:
        return []
    text = text[start:]
    rows = []
    for chunk in re.split(r'(?=<li id="[0-9a-f]{16,}")', text)[1:]:
        rank = re.search(r'<div class="pos"><p>(\d+)</p>', chunk)
        title = re.search(r"<h2>(.*?)</h2>\s*<span>(.*?)</span>", chunk, re.S)
        if not (rank and title):
            continue
        video = re.search(r'data-youtube-url="([^"]*)"', chunk[:400])
        rows.append(Row(
            title=clean(title.group(1)), artist=clean(title.group(2)), rank=int(rank.group(1)),
            youtube_id=youtube_id(video.group(1) if video else None), apple_id=_apple_id(chunk),
        ))
    return rows


def los40_number_ones(page: bytes) -> list[tuple[date, Row]]:
    """The number one of each week of a year page of los40.com, with the list's date."""
    text = page.decode("utf-8", "replace")
    start = text.find('<ul class="lst-num-1">')
    if start < 0:
        return []
    out = []
    for chunk in re.split(r'(?=<li class="[^"]*" data-youtube-url=)', text[start:])[1:]:
        title = re.search(r"<h2>(.*?)</h2>\s*<span>(.*?)</span>", chunk, re.S)
        day = re.search(r'href="/lista40/listas-anteriores/(\d{4})-(\d{2})-(\d{2})"', chunk)
        if not (title and day):
            continue
        video = re.search(r'data-youtube-url="([^"]*)"', chunk[:300])
        out.append((date(*map(int, day.groups())), Row(
            title=clean(title.group(1)), artist=clean(title.group(2)), rank=1,
            youtube_id=youtube_id(video.group(1) if video else None), apple_id=_apple_id(chunk),
        )))
    return out


# --------------------------------------------------------------------------------------- kworb


def _number(text: str) -> int | None:
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def kworb_totals(page: bytes) -> list[Row]:
    """Every song of Spotify Spain's weekly chart, with its weeks, top 10 weeks, peak, streams."""
    text = page.decode("utf-8", "replace")
    body = text[text.find("<tbody>"):]
    rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", body, re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if len(cells) < 7:
            continue
        name = cells[0]
        track = re.search(r'<a href="\.\./track/([A-Za-z0-9]+)\.html">(.*?)</a>', name, re.S)
        if not track:
            continue
        artist = clean(name[: track.start()]).rstrip(" -")
        rows.append(Row(
            title=clean(track.group(2)), artist=artist, rank=0, key=track.group(1),
            spotify_id=track.group(1),
            extra={
                "weeks": _number(cells[1]), "top10_weeks": _number(cells[2]),
                "peak": _number(cells[3]), "peak_times": _number(cells[4]) or 1,
                "peak_streams": _number(cells[5]), "streams": _number(cells[6]),
            },
        ))
    return rows


# -------------------------------------------------------------------------------------- APECAT

CATALAN_MONTHS = {
    "gener": 1, "febrer": 2, "marc": 3, "abril": 4, "maig": 5, "juny": 6, "juliol": 7,
    "agost": 8, "setembre": 9, "octubre": 10, "novembre": 11, "desembre": 12,
}


HEADER_WORDS = re.compile(r"TOP ?30|MES ANTERIOR|TOCADES|CANÇONS|PRODUCCIÓ|PRODUÏDES|CATALUNYA")


@dataclass
class TextBox:
    page: int
    top: int
    left: int
    font: str
    text: str
    width: int = 0


def pdf_boxes(xml: str) -> list[TextBox]:
    """The text lines of ``pdftohtml -xml`` output, each with its page, place and font.

    The PDFs of 2018 and 2019 give one piece per one to three letters ("I", "n", "the", "N"...):
    pieces of one font on one line are joined, with a space where the gap is wider than a letter's
    spacing."""
    fonts = {m.group(1): m.group(2) for m in re.finditer(r'<fontspec id="(\d+)"[^>]*family="([^"]*)"', xml)}
    lines: list[TextBox] = []
    for number, body in re.findall(r'<page number="(\d+)"(.*?)</page>', xml, re.S):
        pieces = []
        for m in re.finditer(
            r'<text top="(-?\d+)" left="(-?\d+)" width="(-?\d+)"[^>]*font="(\d+)"[^>]*>(.*?)</text>', body, re.S
        ):
            text = clean(m.group(5))
            if text:
                pieces.append(TextBox(int(number), int(m.group(1)), int(m.group(2)),
                                      fonts.get(m.group(4), ""), text, int(m.group(3))))
        pieces.sort(key=lambda b: (b.font, b.left))
        page_lines: list[TextBox] = []
        for piece in pieces:
            for line in page_lines:
                gap = piece.left - (line.left + line.width)
                if line.font == piece.font and abs(line.top - piece.top) <= 4 and -3 <= gap < 25:
                    line.text += (" " if gap > 3 else "") + piece.text
                    line.width = piece.left + piece.width - line.left
                    line.top = min(line.top, piece.top)
                    break
            else:
                page_lines.append(piece)
        lines.extend(sorted(page_lines, key=lambda b: (b.top, b.left)))
    return lines


@dataclass
class MonthList:
    series: str  # "llengua" (songs in Catalan) or "produccio" (Catalan labels, any language)
    start: date | None
    end: date | None
    month: int | None  # the month the header names, when there is no date range
    yearly: bool
    rows: list[Row]


def apecat_series(name: str, header: str = "") -> str | None:
    """``llengua`` or ``produccio``, from the file name (it always says), else the header."""
    for text in (name, header):
        flat = compared(text).replace(" ", "")
        if "catprod" in flat or "produ" in flat:
            return "produccio"
        if "catlang" in flat or "llengua" in flat or "catala" in flat:
            return "llengua"
    return None


def apecat_list(xml: str, name: str = "") -> MonthList | None:
    """One APECAT / BMAT TOP 30: its series, its period, and its 30 rows.

    ``name`` is the PDF's file name, which says the series; ``None`` when the PDF has no text
    (three files of 2020 are images)."""
    boxes = pdf_boxes(xml)
    if not boxes:
        return None
    header = " ".join(b.text for b in boxes if b.page == 1 and b.top < 200)
    flat = compared(header).replace(" ", "")
    series = apecat_series(name, header)
    if series is None:
        return None
    joined = re.sub(r"\s+", "", header)
    span = re.search(r"(\d\d)\.(\d\d)\.(\d{4})-(\d\d)\.(\d\d)\.(\d{4})", joined)
    start = end = None
    if span:
        d1, m1, y1, d2, m2, y2 = map(int, span.groups())
        start, end = date(y1, m1, d1), date(y2, m2, d2)
    month = next((n for name, n in CATALAN_MONTHS.items() if name in flat), None)
    yearly = bool(start and (end - start).days > 200)

    rows: list[Row] = []
    for page in sorted({b.page for b in boxes}):
        on_page = [b for b in boxes if b.page == page]
        ranks = [b for b in on_page if b.left < 170 and re.fullmatch(r"\d{1,2}", b.text) and b.top > 150]
        titles = sorted(
            (b for b in on_page if "ExtraBold" in b.font and 250 <= b.left <= 620 and b.top > 150
             and not HEADER_WORDS.search(b.text)),
            key=lambda b: b.top,
        )
        artists = [b for b in on_page if "Medium" in b.font and 250 <= b.left <= 620]
        used = set()
        merged: list[TextBox] = []
        for box in titles:  # a long title wraps onto a second ExtraBold line
            if merged and box.top - merged[-1].top < 26 and abs(box.left - merged[-1].left) < 8 and not any(
                merged[-1].top < a.top < box.top for a in artists
            ):
                merged[-1] = TextBox(page, merged[-1].top, merged[-1].left, box.font,
                                     merged[-1].text + " " + box.text)
            else:
                merged.append(box)
        for box in merged:
            below = [a for a in artists if 0 < a.top - box.top < 60 and abs(a.left - box.left) < 40
                     and id(a) not in used]
            if not below or not ranks:
                continue
            artist = min(below, key=lambda a: a.top)
            used.add(id(artist))
            middle = (box.top + artist.top) / 2  # the place is printed level with title and artist
            rank = min(ranks, key=lambda r: abs(r.top - middle))
            rows.append(Row(title=box.text, artist=artist.text, rank=int(rank.text)))
    rows.sort(key=lambda r: r.rank)
    return MonthList(series, start, end, month, yearly, rows)


# ----------------------------------------------------------------------------------- Wikipedia

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september",
     "october", "november", "december"], 1)}


def wiki_plain(cell: str) -> str:
    """A wikitext cell as plain text: links by their label, templates and references out."""
    cell = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", cell, flags=re.S)
    cell = re.sub(r"\{\{[^{}]*\}\}", "", cell)
    cell = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", cell)
    cell = re.sub(r"'{2,}", "", cell)
    cell = re.sub(r"<br\s*/?>", " ", cell)
    cell = clean(cell)
    return cell.strip(' "“”«»')


def _cell(raw: str) -> tuple[int, str]:
    """``rowspan=3 | text`` -> (3, text); attributes before a single ``|`` are dropped."""
    span = 1
    match = re.match(r'\s*((?:[a-z-]+\s*=\s*"?[^|"]*"?\s*)+)\|(?!\|)(.*)$', raw, re.S | re.I)
    if match:
        attrs, raw = match.groups()
        found = re.search(r'rowspan\s*=\s*"?(\d+)', attrs, re.I)
        span = int(found.group(1)) if found else 1
    return span, raw.strip()


def wiki_tables(text: str) -> list[list[list[str]]]:
    """Every wikitable as rows of plain cells, with rowspans filled down."""
    tables = []
    for body in re.findall(r"\{\|(.*?)\n\|\}", text, re.S):
        rows: list[list[str]] = []
        pending: dict[int, list] = {}  # column -> [rows left, text]
        # the header row may come before the first ``|-``, so the first chunk is read too; its
        # first line (the table's attributes) starts with neither ``|`` nor ``!`` and is skipped
        for chunk in re.split(r"\n\|-[^\n]*", "\n" + body.split("\n", 1)[-1]):
            cells: list[tuple[int, str]] = []
            for line in chunk.strip("\n").split("\n"):
                line = line.strip()
                if not line or line[0] not in "|!":
                    if cells and line:  # a cell that runs onto the next line
                        span, last = cells[-1]
                        cells[-1] = (span, last + " " + line)
                    continue
                sep = "!!" if line[0] == "!" and "!!" in line else "||"
                parts = line[1:].lstrip("|").split(sep) if line.startswith(("||", "!|")) else line[1:].split(sep)
                cells.extend(_cell(p) for p in parts)
            if not cells:
                continue
            row: list[str] = []
            col = 0
            source = iter(cells)
            while True:
                if col in pending:
                    left, value = pending[col]
                    row.append(value)
                    pending[col][0] -= 1
                    if pending[col][0] == 0:
                        del pending[col]
                    col += 1
                    continue
                try:
                    span, raw = next(source)
                except StopIteration:
                    break
                value = wiki_plain(raw)
                row.append(value)
                if span > 1:
                    pending[col] = [span - 1, value]
                col += 1
            while col in pending:  # spans to the right of the last cell given
                left, value = pending[col]
                row.append(value)
                pending[col][0] -= 1
                if pending[col][0] == 0:
                    del pending[col]
                col += 1
            rows.append(row)
        tables.append(rows)
    return tables


def _column(header: list[str], *names: str) -> int | None:
    low = [compared(h) for h in header]
    for name in names:
        for i, h in enumerate(low):
            if h.startswith(name):
                return i
    return None


def _english_date(text: str, year: int) -> date | None:
    text = compared(text)
    match = re.search(r"(\d{1,2}) ([a-z]+)", text) or None
    if match and match.group(2) in MONTHS:
        return date(year, MONTHS[match.group(2)], int(match.group(1)))
    match = re.search(r"([a-z]+) (\d{1,2})", text)
    if match and match.group(1) in MONTHS:
        return date(year, MONTHS[match.group(1)], int(match.group(2)))
    return None


def wikipedia_number_ones(text: str, year: int) -> list[tuple[date, Row]]:
    """The weekly (or fortnightly) number ones of one English page, with their dates."""
    out = []
    for table in wiki_tables(text):
        if not table:
            continue
        header = table[0]
        when = _column(header, "issue date", "week", "date", "chart date")
        song = _column(header, "song", "single", "title")
        artist = _column(header, "artist", "performer")
        if None in (when, song, artist):
            continue
        for row in table[1:]:
            if len(row) <= max(when, song, artist):
                continue
            day = _english_date(row[when], year)
            if day and row[song]:
                out.append((day, Row(title=row[song], artist=row[artist], rank=1)))
    out.sort(key=lambda pair: pair[0])
    return out


def wikipedia_top10(text: str) -> list[tuple[date, Row]]:
    """The weekly top 10 of one Spanish page, ``Fecha | Posición | Artista | Sencillo``."""
    out = []
    for table in wiki_tables(text):
        if not table:
            continue
        header = table[0]
        when, rank = _column(header, "fecha"), _column(header, "posicion")
        artist, song = _column(header, "artista"), _column(header, "sencillo", "cancion")
        if None in (when, rank, artist, song):
            continue
        for row in table[1:]:
            if len(row) <= max(when, rank, artist, song):
                continue
            day = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", row[when])
            place = re.search(r"\d+", row[rank])
            if not day:  # the 1982 page has the place and the date the other way round
                day = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", row[rank])
                place = re.search(r"\d+", row[when])
            if day and place and row[song]:
                d, m, y = map(int, day.groups())
                out.append((date(y, m, d), Row(title=row[song], artist=row[artist], rank=int(place.group()))))
    return out


def viquipedia_spotify(text: str) -> list[Row]:
    """The Catalan songs most played on Spotify: place, title, plays, artist, year."""
    rows = []
    for table in wiki_tables(text):
        if not table:
            continue
        header = table[0]
        song, plays = _column(header, "canco"), _column(header, "reproduccions")
        artist, year = _column(header, "artista"), _column(header, "any")
        if None in (song, plays, artist):
            continue
        for place, row in enumerate(table[1:], 1):
            if len(row) <= max(song, plays, artist):
                continue
            first = re.match(r"\d+", row[0])
            published = re.search(r"\d{4}", row[year]) if year is not None and len(row) > year else None
            rows.append(Row(
                title=row[song], artist=row[artist], rank=int(first.group()) if first else place,
                extra={"streams": _number(row[plays]), "year": int(published.group()) if published else None},
            ))
    return rows


def week_end(start: date) -> date:
    return start + timedelta(days=6)
