"""The genres and tags of the public songs, from Wikidata (implementation 02, Phase 18;
``context/music-library/genres.md``).

Wikidata (open data, CC0) gives a song's genres (P136) and its performers' genres. They are
hundreds ("electropop", "synthwave"), and the app has 13 with no sub-genres (plan section 15.3), so
each Wikidata genre is mapped onto one or two of them, or none ("Christmas music" is not a genre of
the list). The proposed map walks "subclass of" (P279) from a genre up to the nearest of
:data:`ROOTS`; the user reviews it (Q-11).

What is read, every answer kept with its date in ``answers.sqlite`` of :func:`default_folder`
(``data/music-library-genres`` beside the repository), through Phase 17's :class:`Answers` and
:class:`Client`. The queries go to QLever's copy of Wikidata (:data:`signals.QLEVER`): the largest
answers 230,000 items in 2 s, and the Wikidata query service limited every client to 1 query a
minute when this was built.

* every item that is a song, a single or a musical work (:data:`SONG_CLASSES`) with a performer
  (P175), its genres, its labels (and other names) in English, Spanish, Catalan or of any language;
* each performer's labels and genres;
* each genre's label and its "subclass of" links, up to the roots;
* **the tags**: the links that tie a song to a film, a TV programme, a video game or an advert, in
  either direction (:data:`SONG_LINKS`, :data:`WORK_LINKS`, and a soundtrack release that lists the
  song), and the labels of those works.

An item is matched to a public song by the identity rule of Phases 12 and 16 (its title and one
credited artist, :class:`regional_import.Index`); a performer of a matched item that is one of the
song's credited artists stands for that artist, so the artist's other songs can take its genres.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from aitu_backend.db.models import ArtistName, Region, Song, SongArtist, SongRegion
from aitu_backend.library import signals
from aitu_backend.library.public_import import plain
from aitu_backend.library.regional_import import Index, SourceSong

__all__ = [
    "CATEGORIES",
    "ROOTS",
    "SONG_CLASSES",
    "Measure",
    "Wikidata",
    "default_folder",
    "map_genres",
    "match",
    "measure",
    "read",
]

_REPOSITORY = Path(__file__).resolve().parents[4]

#: The classes of an item that is a song: song, single, musical work/composition, music track with
#: vocals, music track without lyrics, audio track, single release, 7" single, translated song,
#: promotional single. Albums, films and characters also have performers, and are left out.
SONG_CLASSES = (
    "Q7366",
    "Q134556",
    "Q105543609",
    "Q55850593",
    "Q55850643",
    "Q7302866",
    "Q108352496",
    "Q6128115",
    "Q63141557",
    "Q2188189",
)
#: The Wikidata genre each genre of the app starts from; any genre below one of them ("subclass of",
#: P279) is proposed as that genre.
ROOTS: dict[str, str] = {
    "Q37073": "pop",  # pop music
    "Q11399": "rock",  # rock music
    "Q11401": "hip hop",  # hip-hop
    "Q6010": "hip hop",  # rapping
    "Q45981": "r&b and soul",  # rhythm and blues
    "Q850412": "r&b and soul",  # contemporary R&B
    "Q131272": "r&b and soul",  # soul music
    "Q164444": "r&b and soul",  # funk
    "Q9778": "electronic and dance",  # electronic music
    "Q316930": "electronic and dance",  # dance music
    "Q851213": "electronic and dance",  # electronic dance music
    "Q58339": "electronic and dance",  # disco
    "Q18345375": "latin",  # Latin music
    "Q202930": "latin",  # reggaeton
    "Q42201": "indie",  # independent music
    "Q842324": "indie",  # indie pop
    "Q183504": "indie",  # indie rock
    "Q43343": "folk and singer-songwriter",  # folk music
    "Q83440": "country",  # country music
    "Q8341": "jazz and blues",  # jazz
    "Q9759": "jazz and blues",  # blues
    "Q9730": "classical",  # classical music
    "Q1583807": "classical",  # art music
    "Q492264": "soundtrack",  # film score
    "Q217199": "soundtrack",  # soundtrack
    "Q38848": "metal",  # heavy metal
}
#: The order a tie between two genres of a song is broken in: the narrow genres first, pop last.
_ORDER = (
    "metal",
    "country",
    "latin",
    "hip hop",
    "jazz and blues",
    "classical",
    "soundtrack",
    "r&b and soul",
    "electronic and dance",
    "folk and singer-songwriter",
    "indie",
    "rock",
    "pop",
)
#: The deepest "subclass of" walk from a genre to a root.
_DEPTH = 8
#: The tag categories of the app and the Wikidata class each stands for (with its subclasses).
CATEGORIES: dict[str, str] = {
    "films": "Q11424",  # film
    "tv_shows": "Q15416",  # television program
    "video_games": "Q7889",  # video game
    "adverts": "Q37038",  # advertising
}
#: Properties from a song to a work: present in work, part of, based on, derivative work, modified
#: version of, recording or performance of, has use, main subject.
SONG_LINKS = ("P1441", "P361", "P144", "P4969", "P5059", "P2550", "P366", "P921")
#: Properties from a work to a song: theme music, soundtrack release, tracklist, featured tracks,
#: recording or performance of, based on, derivative work, present in work.
WORK_LINKS = ("P942", "P406", "P658", "P10664", "P2550", "P144", "P4969", "P1441")
LANGUAGES = ("en", "es", "ca", "mul")
_BLOCK = 2000

_PREFIXES = (
    "PREFIX wd: <http://www.wikidata.org/entity/> "
    "PREFIX wdt: <http://www.wikidata.org/prop/direct/> "
    "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> "
    "PREFIX skos: <http://www.w3.org/2004/02/skos/core#> "
)
_SONGS = (
    "VALUES ?c { " + " ".join("wd:" + one for one in SONG_CLASSES) + " } "
    "?item wdt:P31 ?c; wdt:P175 ?performer. "
)
_LANGS = ", ".join(f'"{one}"' for one in LANGUAGES)


def default_folder() -> Path:
    """``MUSIC_LIBRARY_GENRES_DIR``, else ``data/music-library-genres`` beside the repository."""
    folder = os.environ.get("MUSIC_LIBRARY_GENRES_DIR")
    return Path(folder) if folder else _REPOSITORY.parent / "data" / "music-library-genres"


# ------------------------------------------------------------------------- what is read


@dataclass
class Item:
    """A Wikidata song."""

    qid: str
    performers: list[str] = field(default_factory=list)
    genres: list[str] = field(default_factory=list)
    titles: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Link:
    """A song tied to a work: ``via`` is the property, ``song>`` or ``<work`` for the direction
    it is written in, or ``P406+album`` for a soundtrack release that lists the song."""

    song: str
    work: str
    category: str
    via: str


@dataclass
class Wikidata:
    items: dict[str, Item] = field(default_factory=dict)
    #: performer -> its labels and other names
    names: dict[str, list[str]] = field(default_factory=dict)
    performer_genres: dict[str, list[str]] = field(default_factory=dict)
    #: genre -> its English label (or any)
    labels: dict[str, str] = field(default_factory=dict)
    #: genre -> its "subclass of" parents
    parents: dict[str, set[str]] = field(default_factory=dict)
    links: list[Link] = field(default_factory=list)
    #: work -> its label
    works: dict[str, str] = field(default_factory=dict)


def _query(client: signals.Client, body: str) -> list[list[str]]:
    return client.qlever(_PREFIXES + body)


def _blocks(ids: Iterable[str]) -> Iterable[str]:
    ordered = sorted(set(ids))
    for start in range(0, len(ordered), _BLOCK):
        yield " ".join("wd:" + one for one in ordered[start : start + _BLOCK])


def _labels(client: signals.Client, ids: Iterable[str], other_names: bool) -> dict[str, list[str]]:
    """Each item's labels in :data:`LANGUAGES`, English first (and its other names)."""
    found: dict[str, list[tuple[int, str]]] = defaultdict(list)
    # One query per kind of name: a UNION of the two timed out on QLever (its limit is 30 s).
    predicates = ("rdfs:label", "skos:altLabel") if other_names else ("rdfs:label",)
    rows = (
        row
        for predicate in predicates
        for values in _blocks(ids)
        for row in _query(
            client,
            f"SELECT DISTINCT ?x ?l (LANG(?l) AS ?lang) WHERE {{ VALUES ?x {{ {values} }}"
            f" ?x {predicate} ?l. FILTER(LANG(?l) IN ({_LANGS})) }}",
        )
    )
    for qid, text, lang in rows:
        rank = LANGUAGES.index(lang) if lang in LANGUAGES else len(LANGUAGES)
        if text and all(text != one for _, one in found[qid]):
            found[qid].append((rank, text))
    return {
        qid: [text for _, text in sorted(pairs, key=lambda p: p[0])] for qid, pairs in found.items()
    }


def read(client: signals.Client) -> Wikidata:
    """Everything the measure and the import need, from :data:`signals.QLEVER`."""
    data = Wikidata()
    for qid, performer, genre in _query(
        client,
        f"SELECT DISTINCT ?item ?performer ?genre WHERE {{ {_SONGS}"
        " OPTIONAL { ?item wdt:P136 ?genre } }",
    ):
        item = data.items.setdefault(qid, Item(qid))
        if performer not in item.performers:
            item.performers.append(performer)
        if genre and genre not in item.genres:
            item.genres.append(genre)
    for predicate in ("rdfs:label", "skos:altLabel"):
        for qid, title in _query(
            client,
            f"SELECT DISTINCT ?item ?l WHERE {{ {_SONGS}"
            f" ?item {predicate} ?l. FILTER(LANG(?l) IN ({_LANGS})) }}",
        ):
            if qid in data.items and title not in data.items[qid].titles:
                data.items[qid].titles.append(title)
    performers = {one for item in data.items.values() for one in item.performers}
    data.names = _labels(client, performers, other_names=True)
    for performer, genre in _query(
        client, f"SELECT DISTINCT ?performer ?genre WHERE {{ {_SONGS} ?performer wdt:P136 ?genre }}"
    ):
        data.performer_genres.setdefault(performer, [])
        if genre not in data.performer_genres[performer]:
            data.performer_genres[performer].append(genre)
    genres = {g for item in data.items.values() for g in item.genres}
    genres |= {g for found in data.performer_genres.values() for g in found}
    # The "subclass of" links of every genre, and of their parents, up to the roots.
    seen: set[str] = set()
    wanted = set(genres)
    for _ in range(_DEPTH):
        wanted -= seen
        if not wanted:
            break
        seen |= wanted
        added: set[str] = set()
        for values in _blocks(wanted):
            for child, parent in _query(
                client, f"SELECT ?g ?p WHERE {{ VALUES ?g {{ {values} }} ?g wdt:P279 ?p }}"
            ):
                data.parents.setdefault(child, set()).add(parent)
                added.add(parent)
        wanted = added
    data.labels = {qid: names[0] for qid, names in _labels(client, seen, False).items()}
    _read_links(client, data)
    return data


def _read_links(client: signals.Client, data: Wikidata) -> None:
    works: dict[str, set[str]] = {}
    for category, root in CATEGORIES.items():
        works[category] = {
            row[0]
            for row in _query(client, f"SELECT ?w WHERE {{ ?w wdt:P31/wdt:P279* wd:{root} }}")
        }
    category_of: dict[str, str] = {}
    for category, found in works.items():
        for one in found:
            category_of.setdefault(one, category)
    songs = set(data.items)
    links: set[Link] = set()
    song_props = " ".join("wdt:" + one for one in SONG_LINKS)
    for song, prop, work in _query(
        client,
        f"SELECT DISTINCT ?item ?prop ?w WHERE {{ {_SONGS} VALUES ?prop {{ {song_props} }}"
        " ?item ?prop ?w }",
    ):
        if work in category_of:
            links.add(Link(song, work, category_of[work], f"{prop}>"))
    work_props = " ".join("wdt:" + one for one in WORK_LINKS)
    for work, prop, song in _query(
        client,
        f"SELECT DISTINCT ?w ?prop ?item WHERE {{ {_SONGS} VALUES ?prop {{ {work_props} }}"
        " ?w ?prop ?item }",
    ):
        if work in category_of:
            links.add(Link(song, work, category_of[work], f"<{prop}"))
    # A soundtrack release (P406) of a work that lists the song (P658), or that the song is part of.
    releases = _query(client, "SELECT DISTINCT ?w ?album WHERE { ?w wdt:P406 ?album }")
    albums: dict[str, set[str]] = defaultdict(set)
    for work, album in releases:
        if work in category_of and album not in songs:
            albums[album].add(work)
    pairs = (
        row
        for pattern in ("?a wdt:P658 ?item", "?item wdt:P361 ?a")
        for values in _blocks(albums)
        for row in _query(
            client, f"SELECT DISTINCT ?a ?item WHERE {{ VALUES ?a {{ {values} }} {pattern} }}"
        )
    )
    for album, song in pairs:
        if song in songs:
            for work in albums[album]:
                links.add(Link(song, work, category_of[work], "P406+album"))
    data.links = sorted(links, key=lambda one: (one.song, one.work, one.via))
    data.works = {
        qid: names[0] for qid, names in _labels(client, {one.work for one in links}, False).items()
    }


# ------------------------------------------------------------------------- the map


def map_genres(data: Wikidata, roots: dict[str, str] | None = None) -> dict[str, list[str]]:
    """Each Wikidata genre -> the genres of the app at the nearest roots above it (none when no root
    is within :data:`_DEPTH` steps of "subclass of")."""
    roots = ROOTS if roots is None else roots
    found: dict[str, list[str]] = {}
    every = set(data.labels) | set(data.parents)
    every |= {one for item in data.items.values() for one in item.genres}
    every |= {one for found in data.performer_genres.values() for one in found}
    for genre in every:
        depth: dict[str, int] = {genre: 0}
        queue = deque([genre])
        best: int | None = None
        targets: set[str] = set()
        while queue:
            one = queue.popleft()
            if best is not None and depth[one] > best:
                break
            if one in roots:
                best = depth[one]
                targets.add(roots[one])
                continue
            if depth[one] >= _DEPTH:
                continue
            for parent in sorted(data.parents.get(one, ())):
                if parent not in depth:
                    depth[parent] = depth[one] + 1
                    queue.append(parent)
        found[genre] = [one for one in _ORDER if one in targets]
    return found


def chosen(
    wikidata_genres: Iterable[str], mapped: dict[str, list[str]], most: int = 2
) -> list[str]:
    """At most ``most`` genres of the app: the most frequent after the map, a tie broken by
    :data:`_ORDER` (the narrow genres first)."""
    counts: Counter[str] = Counter()
    for genre in dict.fromkeys(wikidata_genres):
        counts.update(mapped.get(genre, []))
    return sorted(counts, key=lambda one: (-counts[one], _ORDER.index(one)))[:most]


# ------------------------------------------------------------------------- the match


@dataclass
class Matched:
    #: public song -> the Wikidata items matched to it
    items: dict[int, list[str]] = field(default_factory=dict)
    #: public artist -> the Wikidata performers that stand for it (a performer of a matched item
    #: credited on the song)
    performers: dict[int, set[str]] = field(default_factory=dict)
    #: public artist -> a performer of the same name, when only one performer has that name
    by_name: dict[int, str] = field(default_factory=dict)


def match(db: DbSession, data: Wikidata, index: Index | None = None) -> Matched:
    index = index or Index(db)
    out = Matched()
    names = {qid: [plain(one) for one in found] for qid, found in data.names.items()}
    for item in data.items.values():
        artist = ";".join(name for one in item.performers for name in data.names.get(one, [])[:1])
        if not artist or not item.titles:
            continue
        for title in item.titles:
            song_id = index.find(SourceSong(f"wikidata.org:{item.qid}", title, artist))
            if song_id is not None:
                out.items.setdefault(song_id, []).append(item.qid)
                credited = index.credited.get(song_id, set())
                for performer in item.performers:
                    for name in names.get(performer, []):
                        if name in credited and name in index.names:
                            out.performers.setdefault(index.names[name][0], set()).add(performer)
                            break
                break
    # The weaker way: a public artist whose name only one performer has.
    holders: dict[str, set[str]] = defaultdict(set)
    for performer, found in names.items():
        for name in found:
            holders[name].add(performer)
    for name, (artist_id, _) in index.names.items():
        if artist_id not in out.performers and len(holders.get(name, ())) == 1:
            out.by_name[artist_id] = next(iter(holders[name]))
    return out


# ------------------------------------------------------------------------- the measure


@dataclass
class Measure:
    #: (region, decade) -> {"own", "performer", "by name", "none"} -> songs
    coverage: dict[tuple[str, str], Counter[str]] = field(default_factory=dict)
    #: Wikidata genre -> (public songs with it as their own, public songs with it only through
    #: their performer)
    genres: dict[str, list[int]] = field(default_factory=dict)
    #: genre of the app -> songs it would be given (own; with the performer's)
    app: dict[str, list[int]] = field(default_factory=dict)
    #: category -> via -> (public songs, works)
    tags: dict[str, dict[str, tuple[int, int]]] = field(default_factory=dict)
    #: category -> (public songs, works) for every way at once
    tag_totals: dict[str, tuple[int, int]] = field(default_factory=dict)
    #: category -> the works with the most public songs: (label, songs)
    top_works: dict[str, list[tuple[str, int]]] = field(default_factory=dict)
    items: int = 0
    items_with_genres: int = 0
    matched_songs: int = 0
    matched_items: int = 0
    public_songs: int = 0
    artists_by_item: int = 0
    artists_by_name: int = 0


def _song_rows(
    db: DbSession,
) -> tuple[dict[int, tuple[str, ...]], dict[int, int | None], dict[int, list[int]]]:
    regions: dict[int, list[str]] = defaultdict(list)
    for song_id, code in db.execute(
        select(SongRegion.song_id, Region.code).join(Region, Region.id == SongRegion.region_id)
    ):
        regions[int(song_id)].append(str(code))
    years: dict[int, int | None] = {}
    for song_id, year in db.execute(select(Song.id, Song.year).where(Song.scope == "public")):
        years[int(song_id)] = year
    artists: dict[int, list[int]] = defaultdict(list)
    for song_id, artist_id in db.execute(
        select(SongArtist.song_id, ArtistName.artist_id)
        .join(ArtistName, ArtistName.id == SongArtist.artist_name_id)
        .join(Song, Song.id == SongArtist.song_id)
        .where(Song.scope == "public")
        .order_by(SongArtist.song_id, SongArtist.position)
    ):
        artists[int(song_id)].append(int(artist_id))
    return {one: tuple(sorted(regions.get(one, []))) for one in years}, years, artists


def _decade(year: int | None) -> str:
    return f"{year // 10 * 10}s" if year else "no year"


def measure(db: DbSession, data: Wikidata) -> Measure:
    found = match(db, data)
    mapped = map_genres(data)
    regions, years, artists = _song_rows(db)
    out = Measure(
        items=len(data.items),
        items_with_genres=sum(1 for one in data.items.values() if one.genres),
        matched_songs=len(found.items),
        matched_items=sum(len(one) for one in found.items.values()),
        public_songs=len(years),
        artists_by_item=len(found.performers),
        artists_by_name=len(found.by_name),
    )
    genres_own: dict[str, set[int]] = defaultdict(set)
    genres_performer: dict[str, set[int]] = defaultdict(set)
    app_own: Counter[str] = Counter()
    app_any: Counter[str] = Counter()
    total: Counter[str] = Counter()
    for song_id in years:
        own = [g for qid in found.items.get(song_id, []) for g in data.items[qid].genres]
        through = [
            g
            for artist in artists.get(song_id, [])
            for performer in sorted(found.performers.get(artist, ()))
            for g in data.performer_genres.get(performer, [])
        ]
        named = [
            g
            for artist in artists.get(song_id, [])
            if artist in found.by_name
            for g in data.performer_genres.get(found.by_name[artist], [])
        ]
        if chosen(own, mapped):
            kind = "own"
        elif chosen(through, mapped):
            kind = "performer"
        elif chosen(named, mapped):
            kind = "by name"
        else:
            kind = "none"
        for g in own:
            genres_own[g].add(song_id)
        if not own:
            for g in through:
                genres_performer[g].add(song_id)
        app_own.update(chosen(own, mapped))
        app_any.update(chosen(own, mapped) or chosen(through, mapped))
        total[kind] += 1
        for region in regions[song_id] or ("no region",):
            for key in ((region, _decade(years[song_id])), (region, "all")):
                out.coverage.setdefault(key, Counter())[kind] += 1
    out.coverage[("all", "all")] = total
    for g in set(genres_own) | set(genres_performer):
        out.genres[g] = [len(genres_own.get(g, ())), len(genres_performer.get(g, ()))]
    out.app = {one: [app_own[one], app_any[one]] for one in _ORDER}
    song_of: dict[str, list[int]] = defaultdict(list)
    for song_id, qids in found.items.items():
        for qid in qids:
            song_of[qid].append(song_id)
    for category in CATEGORIES:
        per_via: dict[str, tuple[set[int], set[str]]] = defaultdict(lambda: (set(), set()))
        every: tuple[set[int], set[str]] = (set(), set())
        per_work: dict[str, set[int]] = defaultdict(set)
        for link in data.links:
            if link.category != category or link.song not in song_of:
                continue
            per_via[link.via][0].update(song_of[link.song])
            per_via[link.via][1].add(link.work)
            every[0].update(song_of[link.song])
            every[1].add(link.work)
            per_work[link.work].update(song_of[link.song])
        out.tags[category] = {via: (len(s), len(w)) for via, (s, w) in sorted(per_via.items())}
        out.tag_totals[category] = (len(every[0]), len(every[1]))
        out.top_works[category] = [
            (data.works.get(work, work), len(songs))
            for work, songs in sorted(per_work.items(), key=lambda kv: -len(kv[1]))[:15]
        ]
    return out


def _lines(result: Measure, data: Wikidata, mapped: dict[str, list[str]], top: int) -> list[str]:
    out = [
        f"Wikidata songs with a performer: {result.items} ({result.items_with_genres} with genres)",
        f"public songs: {result.public_songs}; matched to an item: {result.matched_songs}"
        f" ({result.matched_items} items)",
        f"public artists: {result.artists_by_item} by a matched item, {result.artists_by_name} more"
        " by a unique name",
        "",
        "coverage (region, decade): own / performer / by name / none",
    ]
    for (region, decade), counts in sorted(result.coverage.items()):
        out.append(
            f"  {region:10} {decade:8} {counts['own']:6} {counts['performer']:6}"
            f" {counts['by name']:6} {counts['none']:6}"
        )
    out += ["", "genres of the app: songs (own genres only; with the performer's)"]
    out += [f"  {name:28} {own:6} {any_:6}" for name, (own, any_) in result.app.items()]
    out += ["", f"the {top} most frequent Wikidata genres: own / performer only -> proposed"]
    for genre, (own, through) in sorted(result.genres.items(), key=lambda kv: -sum(kv[1]))[:top]:
        out.append(
            f"  {genre:11} {data.labels.get(genre, '?')[:38]:38} {own:6} {through:6}"
            f" -> {', '.join(mapped.get(genre, [])) or 'none'}"
        )
    out += ["", "tags: category, via: public songs, works"]
    for category, vias in result.tags.items():
        songs, works = result.tag_totals[category]
        out.append(f"  {category}: {songs} songs, {works} works")
        out += [f"    {via:12} {s:6} {w:6}" for via, (s, w) in vias.items()]
        out += [f"      {label[:50]:50} {n}" for label, n in result.top_works[category][:8]]
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--database", type=Path, default=None, help="another .database/ folder")
    commands = parser.add_subparsers(dest="command", required=True)
    measure_ = commands.add_parser("measure", help="read Wikidata and count; write nothing")
    measure_.add_argument("--top", type=int, default=80)
    measure_.add_argument("--out", type=Path, default=None, help="a JSON file of every genre")
    args = parser.parse_args(argv)
    if args.database is not None:
        os.environ["AITU_DATABASE_DIR"] = str(args.database.resolve())

    from aitu_backend.db.database import session  # noqa: PLC0415 - after AITU_DATABASE_DIR

    answers = signals.Answers(default_folder() / "answers.sqlite")
    client = signals.Client(answers)
    data = read(client)
    mapped = map_genres(data)
    with session() as db:
        result = measure(db, data)
    print("\n".join(_lines(result, data, mapped, args.top)))
    print("roots: " + ", ".join(f"{qid} {data.labels.get(qid, '?')}" for qid in ROOTS))
    print(f"asked {dict(client.asked)}")
    if args.out is not None:
        args.out.write_text(
            json.dumps(
                {
                    genre: {
                        "label": data.labels.get(genre, ""),
                        "own": own,
                        "performer": through,
                        "proposed": mapped.get(genre, []),
                    }
                    for genre, (own, through) in sorted(
                        result.genres.items(), key=lambda kv: -sum(kv[1])
                    )
                },
                ensure_ascii=False,
                indent=1,
            )
        )
    answers.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
