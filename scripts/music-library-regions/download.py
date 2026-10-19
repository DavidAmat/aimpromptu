"""Download the sources of the `spain` and `catalan` regions (implementation 02, Phase 16, Q-9).

    python3 scripts/music-library-regions/download.py <source>          # download, or continue
    python3 scripts/music-library-regions/download.py <source> --status # what is saved

Sources (``context/music-library/regional-sources.md`` section 6):

    spanishcharts  the weekly Spanish chart, every Sunday from 2001-12-30 (5 s between requests)
    los40          the number ones of each year from 1966, and every weekly list from 2004 (10 s)
    kworb          the Spotify Spain weekly totals, one page
    apecat         the archive page and its monthly TOP 30 PDFs (3 s)
    wikipedia      the weekly number ones of Spain 1959-2001 (en), the weekly top 10 1982-1996 (es),
                   the Catalan songs most played on Spotify (ca) (3 s)

Each page is saved once; running the command again asks only for what is missing. A refusal or a
challenge page stops the run after waits of 60, 120 and 240 s, and nothing saved is lost.
"""

from __future__ import annotations

import argparse
import re
import urllib.parse
from datetime import date, timedelta

from common import Fetcher, Refused, data_dir, fail, logger

TODAY = date.today()


def weekdays(first: date, weekday: int) -> list[date]:
    """Every date of ``weekday`` (Monday 0) from ``first`` to today."""
    day = first + timedelta(days=(weekday - first.weekday()) % 7)
    out = []
    while day <= TODAY:
        out.append(day)
        day += timedelta(days=7)
    return out


def spanishcharts(fetch: Fetcher) -> None:
    weeks = weekdays(date(2001, 12, 30), 6)
    for n, week in enumerate(weeks, 1):
        stamp = week.strftime("%Y%m%d")
        url = f"https://spanishcharts.com/weekchart.asp?cat=s&year={week.year}&date={stamp}"
        page = fetch.get(url, f"{week.year}/{stamp}.html")
        if n % 25 == 0 or n == len(weeks):
            fetch.log(f"spanishcharts {n}/{len(weeks)} {week} HTTP {page.status}")


def los40(fetch: Fetcher) -> None:
    for year in range(1966, TODAY.year + 1):
        page = fetch.get(f"https://los40.com/lista40/numeros-1/{year}/", f"years/{year}.html")
        fetch.log(f"los40 year {year} HTTP {page.status}")
    weeks = weekdays(date(2004, 1, 3), 5)
    for n, week in enumerate(weeks, 1):
        url = f"https://los40.com/lista40/listas-anteriores/{week.isoformat()}/"
        page = fetch.get(url, f"weeks/{week.year}/{week.isoformat()}.html")
        if n % 25 == 0 or n == len(weeks):
            fetch.log(f"los40 week {n}/{len(weeks)} {week} HTTP {page.status}")


def kworb(fetch: Fetcher) -> None:
    page = fetch.get("https://kworb.net/spotify/country/es_weekly_totals.html", "es_weekly_totals.html")
    fetch.log(f"kworb HTTP {page.status}")


def apecat(fetch: Fetcher) -> None:
    archive = fetch.get("https://apecat.com/ca/llistes-musica-catalunya/", "archive.html")
    if archive.status != 200:
        fail(f"apecat archive: HTTP {archive.status}")
    links = sorted(set(re.findall(rb"https://apecat\.com/wp-content/uploads/[^\"'\s<>]+\.pdf", archive.read())))
    for n, link in enumerate(links, 1):
        url = link.decode()
        rel = "pdf/" + url.split("/wp-content/uploads/", 1)[1]
        page = fetch.get(url, rel)
        if n % 20 == 0 or n == len(links):
            fetch.log(f"apecat {n}/{len(links)} HTTP {page.status}")


WIKI_PAGES = (
    [("en", y, [f"List of number-one singles of {y} (Spain)", f"List of Spanish number-one hits of {y}"])
     for y in range(1959, 2002)]
    + [("es", y, [f"Anexo:Sencillos más vendidos en España en {y}"]) for y in range(1982, 1997)]
    + [("ca", None, ["Cançons en català amb més reproduccions a Spotify"])]
)


def wikipedia(fetch: Fetcher) -> None:
    for lang, year, titles in WIKI_PAGES:
        found = None
        for title in titles:
            for _ in range(3):  # a redirect page names its target
                url = (f"https://{lang}.wikipedia.org/w/index.php?title="
                       f"{urllib.parse.quote(title.replace(' ', '_'))}&action=raw")
                rel = f"{lang}/{re.sub(r'[^0-9A-Za-zÀ-ÿ]+', '_', title).strip('_')}.wikitext"
                page = fetch.get(url, rel)
                if page.status != 200:
                    break
                target = re.match(rb"#(?:REDIRECT|REDIRECCI\xc3\x93N)\s*\[\[([^\]#|]+)", page.read(), re.I)
                if not target:
                    found = title
                    break
                title = target.group(1).decode().strip()
            if found:
                break
        fetch.log(f"wikipedia {lang} {year or ''} {'-> ' + found if found else 'not found'}")


SOURCES = {
    "spanishcharts": (spanishcharts, 5.0),
    "los40": (los40, 10.0),
    "kworb": (kworb, 3.0),
    "apecat": (apecat, 3.0),
    "wikipedia": (wikipedia, 3.0),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", choices=sorted(SOURCES))
    parser.add_argument("--status", action="store_true", help="print what is saved and stop")
    args = parser.parse_args()
    run, gap = SOURCES[args.source]
    log = logger(data_dir() / args.source / "download.log")
    fetch = Fetcher(args.source, gap, log)
    if args.status:
        print(fetch.status())
        return
    log(f"{args.source}: start, {gap:g} s between requests")
    try:
        run(fetch)
    except Refused as refused:
        log(f"{args.source}: stopped, {refused}. Run the same command later to continue.")
        raise SystemExit(2)
    log(f"{args.source}: done, {fetch.requests} requests. {fetch.status()}")


if __name__ == "__main__":
    main()
