"""The signals a song has outside the charts (implementation 02, Phase 17;
``context/music-library/popularity.md`` section 6): the views of its official video on YouTube, and
its all-time streams on Spotify as kworb.net lists them (Q-10).

Where a song's official video comes from, cheapest first:

* **Los 40**: each row of its lists from 2004 (and many number ones before) links a YouTube video;
  ``data/music-library-regions/los40/los40.sqlite``, found through ``song_keys``;
* **Wikidata**: every item with a YouTube video id (P1651) and a performer (P175), about 40,000,
  matched to the public songs by the identity rule of Phase 16 (title and one credited artist);
* **Enderrock**: the magazine's yearly "Top 100 de videoclips en català a YouTube" (2017 to 2025)
  embeds each video; its title ("Artist - Song") is matched to a public song by the same rule. Most
  `catalan` songs have no other free video;
* **a YouTube search** (``search.list``, its own bucket of 100 calls a day since 2026-06-01), only
  for the songs the others leave without one.

``videos.list`` (1 unit of the 10,000 a day for up to 50 videos) then gives each video's channel,
upload date and views. **Only an official upload counts**: the artist's own channel, its "Topic"
channel (the uploads YouTube makes for a label), its Vevo channel, or a record label's channel
when the video's title names the artist and the song (:func:`channel_kind`); a fan's upload is left
out. A song with several official videos keeps the one with the most views.

The streams (Q-10, answered 2026-10-19): the Spotify Web API gives no play count and, since 2026,
no ``popularity``; it is used only to find an artist's Spotify id, a cross-reference key. kworb.net's
page of that artist (``/spotify/artist/<id>_songs.html``) lists each of its tracks with its streams;
a song keeps the most streamed track of the same title. Small artists have no page.

**Every answer is kept** in ``answers.sqlite`` in :func:`default_folder` (``data/music-library-views``
next to the repository) with the date it was read, so nothing is asked twice; a YouTube statistic is
deleted after :data:`STATS_DAYS` days, as the YouTube API Developer Policies ask, and read again when
needed. The keys come from ``.env``: ``YOUTUBE_API_KEY``, ``SPOTIFY_CLIENT_ID``,
``SPOTIFY_CLIENT_SECRET``; none is ever written into an answer.
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from aitu_backend.db.models import Artist, ArtistName, Song, SongArtist
from aitu_backend.library.public_import import plain
from aitu_backend.library.regional_import import (
    Index,
    SourceSong,
    default_folder as regions_folder,
    title_forms,
)

__all__ = [
    "Answers",
    "Client",
    "OutOfQuota",
    "STATS_DAYS",
    "SEARCHES_A_DAY",
    "Signal",
    "Video",
    "channel_kind",
    "collect",
    "default_folder",
    "kworb_rows",
]

_REPOSITORY = Path(__file__).resolve().parents[4]
USER_AGENT = "AImpromptuMusicLibrary/1.0 (personal local archive)"
#: Days a YouTube statistic may be kept before it is read again or deleted.
STATS_DAYS = 30
#: ``search.list`` calls a day: its own bucket, which resets at midnight in California.
SEARCHES_A_DAY = 100
_QUOTA_DAY = ZoneInfo("America/Los_Angeles")
#: The least time between two requests to one host, in seconds.
PACE = {
    "query.wikidata.org": 1.0,
    "www.googleapis.com": 0.2,
    "accounts.spotify.com": 1.0,
    "api.spotify.com": 1.0,
    "kworb.net": 4.0,
    "www.enderrock.cat": 3.0,
}
#: Enderrock's yearly top 100 of Catalan videos on YouTube, by year (article number and address).
ENDERROCK = {
    2017: "16158/clips-mes-vistos-2017",
    2018: "18525/videoclips/mes/vistos/2018",
    2019: "20385/top-100-2019-videoclips-catala-youtube",
    2020: "22136/top-100-2020-videoclips-catala-youtube",
    2021: "23772/top-100-2021-videoclips-catala-youtube",
    2022: "25455/top-100-videoclips-catala-youtube-2022",
    2023: "27298/top-100-videoclips-catala-youtube-2023",
    2024: "29008/top-100-videoclips-catala-youtube-2024",
    2025: "30609/top-100-videoclips-catala-youtube-2025",
}
#: The longest wait a refusal is waited out, in seconds; a longer one closes the host for the run.
MAX_WAIT = 300
#: The labels and the items asked for in one Wikidata query.
_WIKIDATA_BLOCK = 2000


def default_folder() -> Path:
    """``MUSIC_LIBRARY_VIEWS_DIR``, else ``data/music-library-views`` beside the repository."""
    folder = os.environ.get("MUSIC_LIBRARY_VIEWS_DIR")
    return Path(folder) if folder else _REPOSITORY.parent / "data" / "music-library-views"


class OutOfQuota(RuntimeError):
    """The day's searches are spent, or a service refused for its quota."""


# ------------------------------------------------------------------------- the answers


class Answers:
    """Every answer once, by a key that never holds a secret: ``youtube:video:<id>``,
    ``youtube:search:<query>``, ``wikidata:<hash>``, ``spotify:artist:<name>``,
    ``kworb:artist:<id>``. ``status`` is the HTTP status (404 is kept: a page that does not exist).
    """

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS answers (key TEXT PRIMARY KEY, status INTEGER,"
            " body TEXT, read_at TEXT)"
        )
        self.forget("youtube:video:", STATS_DAYS)

    def get(self, key: str, days: int | None = None) -> tuple[int, str] | None:
        row = self.connection.execute(
            "SELECT status, body, read_at FROM answers WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return None
        if days is not None and _read_at(row[2]) < _now() - timedelta(days=days):
            return None
        return int(row[0]), str(row[1])

    def read_at(self, key: str) -> datetime | None:
        row = self.connection.execute(
            "SELECT read_at FROM answers WHERE key = ?", (key,)
        ).fetchone()
        return _read_at(row[0]) if row else None

    def put(self, key: str, status: int, body: str) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO answers VALUES (?, ?, ?, ?)",
            (key, status, body, _now().isoformat(timespec="seconds")),
        )
        self.connection.commit()

    def forget(self, prefix: str, days: int) -> int:
        """Delete the answers of ``prefix`` read more than ``days`` days ago."""
        before = (_now() - timedelta(days=days)).isoformat(timespec="seconds")
        found = self.connection.execute(
            "DELETE FROM answers WHERE key >= ? AND key < ? AND read_at < ?",
            (prefix, prefix + "￿", before),
        ).rowcount
        self.connection.commit()
        return int(found)

    def searches_today(self) -> int:
        """The searches asked since midnight in California, when the bucket was last refilled."""
        midnight = datetime.now(_QUOTA_DAY).replace(hour=0, minute=0, second=0, microsecond=0)
        return int(
            self.connection.execute(
                "SELECT count(*) FROM answers WHERE key >= 'youtube:search:'"
                " AND key < 'youtube:search:￿' AND read_at >= ?",
                (midnight.astimezone(timezone.utc).isoformat(timespec="seconds"),),
            ).fetchone()[0]
        )

    def close(self) -> None:
        self.connection.close()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _read_at(text: str) -> datetime:
    found = datetime.fromisoformat(text)
    return found if found.tzinfo else found.replace(tzinfo=timezone.utc)


# ------------------------------------------------------------------------- the client


class Client:
    """The services, paced per host; every answer read from :class:`Answers` first."""

    def __init__(
        self,
        answers: Answers,
        youtube_key: str | None = None,
        spotify: tuple[str, str] | None = None,
        say: bool = True,
    ):
        self.answers = answers
        self.youtube_key = youtube_key or os.environ.get("YOUTUBE_API_KEY") or None
        found = (os.environ.get("SPOTIFY_CLIENT_ID"), os.environ.get("SPOTIFY_CLIENT_SECRET"))
        self.spotify = spotify or (found if all(found) else None)
        self.say = say
        self._last: dict[str, float] = {}
        self._token: tuple[str, float] | None = None
        self.asked: dict[str, int] = defaultdict(int)
        #: Hosts that asked for a wait longer than :data:`MAX_WAIT`: not asked again in this run.
        self.closed: set[str] = set()

    def _fetch(
        self, url: str, data: bytes | None = None, headers: dict[str, str] | None = None
    ) -> tuple[int, str]:
        host = urllib.parse.urlsplit(url).netloc
        if host in self.closed:
            raise OutOfQuota(f"{host} asked to wait; not asked again in this run")
        for wait in (60, 120, 240, None):
            gap = PACE.get(host, 1.0) - (time.monotonic() - self._last.get(host, 0.0))
            if gap > 0:
                time.sleep(gap)
            self._last[host] = time.monotonic()
            self.asked[host] += 1
            request = urllib.request.Request(
                url, data=data, headers={"User-Agent": USER_AGENT, **(headers or {})}
            )
            try:
                with urllib.request.urlopen(request, timeout=120) as answer:
                    return answer.status, answer.read().decode("utf-8", "replace")
            except urllib.error.HTTPError as error:
                body = error.read().decode("utf-8", "replace")
                if error.code == 403 and "quota" in body.casefold():
                    raise OutOfQuota(f"{host}: {body[:200]}") from error
                if error.code in (404, 400):
                    return error.code, body
                if error.code not in (429, 500, 502, 503, 504) or wait is None:
                    raise
                retry = error.headers.get("Retry-After")
                pause = int(retry) if retry and retry.isdigit() else wait
                if pause > MAX_WAIT:
                    # Spotify answered 429 with a wait of 23 hours after about 700 searches.
                    self.closed.add(host)
                    raise OutOfQuota(f"{host} asks to wait {pause} s") from error
            except (urllib.error.URLError, TimeoutError):
                if wait is None:
                    raise
                pause = wait
            if self.say:
                print(f"  {host} refused or timed out, waiting {pause} s")
            time.sleep(pause)
        raise RuntimeError("unreachable")

    def _ask(
        self,
        key: str,
        url: str,
        days: int | None = None,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, str]:
        found = self.answers.get(key, days)
        if found is not None:
            return found
        status, body = self._fetch(url, data, headers)
        self.answers.put(key, status, body)
        return status, body

    # --- Wikidata

    def _sparql(self, query: str) -> list[dict[str, dict[str, str]]]:
        key = "wikidata:" + hashlib.sha256(query.encode()).hexdigest()[:32]
        _, body = self._ask(
            key,
            "https://query.wikidata.org/sparql",
            data=urllib.parse.urlencode({"query": query, "format": "json"}).encode(),
            headers={
                "Accept": "application/sparql-results+json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        return list(json.loads(body)["results"]["bindings"])

    def wikidata_songs(self) -> list[WikidataSong]:
        """Every item with a YouTube video and a performer, with its labels in English, Spanish,
        Catalan or of any language, and its performers' labels."""
        rows = self._sparql(
            "SELECT ?item ?yt ?performer ?date WHERE { ?item wdt:P1651 ?yt; wdt:P175 ?performer."
            " OPTIONAL { ?item wdt:P577 ?date } }"
        )
        songs: dict[str, WikidataSong] = {}
        performers: set[str] = set()
        for row in rows:
            qid = row["item"]["value"].rsplit("/", 1)[1]
            song = songs.setdefault(qid, WikidataSong(qid))
            if row["yt"]["value"] not in song.videos:
                song.videos.append(row["yt"]["value"])
            performer = row["performer"]["value"].rsplit("/", 1)[1]
            if performer not in song.performer_ids:
                song.performer_ids.append(performer)
            performers.add(performer)
            if "date" in row and row["date"]["value"][:4].isdigit():
                year = int(row["date"]["value"][:4])
                song.year = min(song.year or year, year)
        labels = self._labels(sorted(songs) + sorted(performers))
        for song in songs.values():
            song.titles = labels.get(song.qid, [])
            song.performers = [name for one in song.performer_ids for name in labels.get(one, [])]
        return [song for song in songs.values() if song.titles and song.performers]

    def _labels(self, ids: list[str]) -> dict[str, list[str]]:
        found: dict[str, list[str]] = defaultdict(list)
        for start in range(0, len(ids), _WIKIDATA_BLOCK):
            values = " ".join("wd:" + one for one in ids[start : start + _WIKIDATA_BLOCK])
            for row in self._sparql(
                f"SELECT ?item ?l WHERE {{ VALUES ?item {{ {values} }} ?item rdfs:label ?l."
                ' FILTER(LANG(?l) IN ("en", "es", "ca", "mul")) }'
            ):
                qid = row["item"]["value"].rsplit("/", 1)[1]
                if row["l"]["value"] not in found[qid]:
                    found[qid].append(row["l"]["value"])
        return found

    # --- YouTube

    def videos(self, ids: Iterable[str], days: int = STATS_DAYS) -> dict[str, Video]:
        """Each video's channel, upload date and views; a deleted or private video is absent. An
        answer older than ``days`` is asked again (0: always)."""
        wanted = list(dict.fromkeys(ids))
        missing = [one for one in wanted if self.answers.get(f"youtube:video:{one}", days) is None]
        if missing and not self.youtube_key:
            raise OutOfQuota("YOUTUBE_API_KEY is not set")
        for start in range(0, len(missing), 50):
            block = missing[start : start + 50]
            query = urllib.parse.urlencode(
                {"part": "snippet,statistics", "id": ",".join(block), "key": self.youtube_key}
            )
            status, body = self._fetch(f"https://www.googleapis.com/youtube/v3/videos?{query}")
            items = (
                {item["id"]: item for item in json.loads(body).get("items", [])}
                if status == 200
                else {}
            )
            for one in block:
                self.answers.put(
                    f"youtube:video:{one}", 200 if one in items else 404, json.dumps(items.get(one))
                )
        found: dict[str, Video] = {}
        for one in wanted:
            answer = self.answers.get(f"youtube:video:{one}")
            if answer is None or answer[0] != 200:
                continue
            item = json.loads(answer[1])
            snippet, stats = item.get("snippet", {}), item.get("statistics", {})
            if "viewCount" not in stats:
                continue
            found[one] = Video(
                id=one,
                title=snippet.get("title", ""),
                channel=snippet.get("channelTitle", ""),
                published=date.fromisoformat(snippet.get("publishedAt", "1970-01-01")[:10]),
                views=int(stats["viewCount"]),
                read_at=self.answers.read_at(f"youtube:video:{one}") or _now(),
            )
        return found

    def search(self, query: str) -> list[str]:
        """The video ids of a search, the five most relevant music videos; :class:`OutOfQuota`
        when the day's searches are spent."""
        key = f"youtube:search:{query}"
        found = self.answers.get(key)
        if found is None:
            if not self.youtube_key:
                raise OutOfQuota("YOUTUBE_API_KEY is not set")
            if self.answers.searches_today() >= SEARCHES_A_DAY:
                raise OutOfQuota(f"the {SEARCHES_A_DAY} searches of the day are spent")
            params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "videoCategoryId": "10",
                "maxResults": "5",
                "key": self.youtube_key,
            }
            found = self._fetch(
                "https://www.googleapis.com/youtube/v3/search?" + urllib.parse.urlencode(params)
            )
            self.answers.put(key, *found)
        if found[0] != 200:
            return []
        return [item["id"]["videoId"] for item in json.loads(found[1]).get("items", [])]

    # --- Spotify and kworb

    def _spotify_token(self) -> str:
        if self._token and self._token[1] > time.monotonic():
            return self._token[0]
        if not self.spotify:
            raise OutOfQuota("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are not set")
        secret = base64.b64encode(f"{self.spotify[0]}:{self.spotify[1]}".encode()).decode()
        _, body = self._fetch(
            "https://accounts.spotify.com/api/token",
            data=b"grant_type=client_credentials",
            headers={
                "Authorization": f"Basic {secret}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        answer = json.loads(body)
        self._token = (answer["access_token"], time.monotonic() + answer["expires_in"] - 60)
        return self._token[0]

    def spotify_artist(self, name: str) -> str | None:
        """The Spotify id of the artist of this name (the same compared form), or None."""
        key = f"spotify:artist:{plain(name)}"
        found = self.answers.get(key)
        if found is None:
            query = urllib.parse.urlencode({"q": f"artist:{name}", "type": "artist", "limit": "5"})
            found = self._fetch(
                f"https://api.spotify.com/v1/search?{query}",
                headers={"Authorization": f"Bearer {self._spotify_token()}"},
            )
            self.answers.put(key, *found)
        if found[0] != 200:
            return None
        for item in json.loads(found[1]).get("artists", {}).get("items", []):
            if plain(item.get("name", "")) == plain(name):
                return str(item["id"])
        return None

    def kworb_songs(self, artist_id: str) -> list[tuple[str, int]]:
        """``(title, streams)`` of each track of kworb's page of the artist; none when it has no
        page."""
        status, body = self._ask(
            f"kworb:artist:{artist_id}", f"https://kworb.net/spotify/artist/{artist_id}_songs.html"
        )
        return kworb_rows(body) if status == 200 else []

    def enderrock_videos(self) -> list[str]:
        """The YouTube videos embedded in Enderrock's yearly lists, in their order."""
        found: list[str] = []
        for article in ENDERROCK.values():
            status, body = self._ask(
                f"enderrock:{article}", f"https://www.enderrock.cat/noticia/{article}"
            )
            if status == 200:
                found += [one for one in _EMBED.findall(body) if one not in found]
        return found


_EMBED = re.compile(r"youtube(?:-nocookie)?\.com/embed/([A-Za-z0-9_-]{11})")
_KWORB_ROW = re.compile(
    r'<tr><td class="text"><div>(?:\*\s*)?<a href="https://open\.spotify\.com/track/[^"]+"[^>]*>'
    r"(.*?)</a>.*?</td><td>([\d,]+)</td>",
    re.S,
)


def kworb_rows(page: str) -> list[tuple[str, int]]:
    """The tracks of a kworb artist page: ``(title, all-time streams)``."""
    return [
        (html.unescape(title).strip(), int(streams.replace(",", "")))
        for title, streams in _KWORB_ROW.findall(page)
    ]


# ------------------------------------------------------------------------- what is found


@dataclass
class WikidataSong:
    qid: str
    videos: list[str] = field(default_factory=list)
    performer_ids: list[str] = field(default_factory=list)
    titles: list[str] = field(default_factory=list)
    performers: list[str] = field(default_factory=list)
    year: int | None = None


@dataclass(frozen=True)
class Video:
    id: str
    title: str
    channel: str
    published: date
    views: int
    read_at: datetime


@dataclass
class Signal:
    """What was found for one public song."""

    song_id: int
    #: The official video with the most views, and where its id came from: ``los40``,
    #: ``wikidata`` or ``search``.
    video: Video | None = None
    found_by: str | None = None
    #: ``artist``, ``topic``, ``vevo`` or ``label`` (:func:`channel_kind`).
    channel_kind: str | None = None
    #: The most streamed track of the same title on kworb's page of one of its artists.
    streams: int | None = None
    streams_read_at: datetime | None = None
    #: The videos found but left out (not official), for the report.
    unofficial: list[Video] = field(default_factory=list)


_CHANNEL_WORDS = re.compile(
    r"(?:the|official|oficial|officiel|music|musica|musique|tv|channel|band|vevo|records|topic"
    r"|videos?|vids|hq)*"
)
#: Words of a record label's channel: the label runs it, so its uploads are the official ones.
_LABEL = re.compile(
    r"\b(?:warner|rhino|atlantic|records|recordings|parlophone|sony|universal|emi|columbia|rca"
    r"|island|def jam|interscope|capitol|republic|epic|elektra|motown|virgin|polydor|mercury"
    r"|geffen|arista|kontor|spinnin|hybe labels|ultra|fueled by ramen|bad boy|tommy boy|pwl"
    r"|unidisc|blanco y negro|roster music|catalogo|vault)\b"
)


def _squeezed(name: str) -> set[str]:
    """A name as a channel writes it: no spaces, with and without "and" ("Simon & Garfunkel" is
    ``simonandgarfunkel`` and ``simongarfunkel``)."""
    text = plain(name)
    return {text.replace(" ", ""), re.sub(r"\band\b", "", text).replace(" ", "")} - {""}


def channel_kind(
    channel: str, names: Iterable[str], video_title: str = "", song_title: str = ""
) -> str | None:
    """Whether a video is the official upload, by its channel:

    * ``artist``, ``topic`` or ``vevo``: one of these names' own channel, with nothing but words
      like "official", "music" or "VEVO" around the name ("Luis Fonsi", "LuisFonsiVEVO", "The
      Mamas & The Papas - Topic"); a VEVO channel whose name starts a credited name or is part of
      one ("SouljaBoyTellemVEVO" for "Soulja Boy");
    * ``label``: any other VEVO channel, or a record label's ("Warner Music Spain", "Rhino"), when
      the video's title names one of the artists and the song, so a cover is left out;
    * None: a fan, a TV show, anyone else.
    """
    squeezed = plain(channel).replace(" ", "")
    if not squeezed:
        return None
    names = list(names)
    vevo = squeezed.endswith("vevo")
    for name in names:
        for wanted in _squeezed(name):
            if len(wanted) < 2:
                continue
            if wanted in squeezed and _CHANNEL_WORDS.fullmatch(squeezed.replace(wanted, "", 1)):
                if channel.rstrip().endswith("- Topic"):
                    return "topic"
                return "vevo" if vevo else "artist"
            if vevo and len(squeezed) > 6 and squeezed[:-4] in wanted:
                return "vevo"
            if vevo and squeezed[:-4].startswith(wanted):
                return "vevo"
    if vevo or _LABEL.search(plain(channel)):
        said = plain(video_title)
        if any(form in said for form in title_forms(song_title)) and any(
            plain(name) in said for name in names if plain(name)
        ):
            return "label"
    return None


# ------------------------------------------------------------------------- the collection


def _credits(db: DbSession, song_ids: Iterable[int]) -> dict[int, list[tuple[int, list[str]]]]:
    """song id -> its credited artists in order, each with every name of the artist."""
    wanted = set(song_ids)
    names: dict[int, list[str]] = defaultdict(list)
    for artist_id, name in db.execute(
        select(ArtistName.artist_id, ArtistName.name)
        .join(Artist, Artist.id == ArtistName.artist_id)
        .where(Artist.scope == "public")
        .order_by(ArtistName.is_default.desc(), ArtistName.id)
    ):
        names[int(artist_id)].append(str(name))
    found: dict[int, list[tuple[int, list[str]]]] = defaultdict(list)
    for song_id, artist_id in db.execute(
        select(SongArtist.song_id, ArtistName.artist_id)
        .join(ArtistName, ArtistName.id == SongArtist.artist_name_id)
        .order_by(SongArtist.song_id, SongArtist.position)
    ):
        if song_id in wanted and all(a != artist_id for a, _ in found[song_id]):
            found[int(song_id)].append((int(artist_id), names[int(artist_id)]))
    return found


def free_videos(
    db: DbSession, client: Client, index: Index | None = None
) -> dict[int, dict[str, str]]:
    """song id -> {video id: where it came from}, from Los 40, Wikidata and Enderrock, which cost no
    quota (only ``videos.list`` to read Enderrock's titles)."""
    index = index or Index(db)
    found: dict[int, dict[str, str]] = defaultdict(dict)
    los40 = regions_folder() / "los40" / "los40.sqlite"
    if los40.is_file():
        connection = sqlite3.connect(f"file:{los40}?mode=ro&immutable=1", uri=True)
        try:
            for key, video in connection.execute(
                "SELECT key, youtube_id FROM songs WHERE youtube_id IS NOT NULL AND youtube_id != ''"
            ):
                song_id = index.by_key.get(f"los40.com:{key}")
                if song_id is not None:
                    found[song_id].setdefault(str(video), "los40")
        finally:
            connection.close()
    for item in client.wikidata_songs():
        artist = ";".join(item.performers)
        for title in item.titles:
            song_id = index.find(SourceSong(f"wikidata.org:{item.qid}", title, artist))
            if song_id is not None:
                for video in item.videos:
                    found[song_id].setdefault(video, "wikidata")
                break
    embedded = client.enderrock_videos()
    for video in client.videos(embedded).values():
        parts = [one.strip() for one in _TITLE_PARTS.split(video.title) if one.strip()]
        for artist, title in zip(parts, parts[1:]):
            song_id = index.find(SourceSong(f"youtube:{video.id}", title, artist))
            if song_id is not None:
                found[song_id].setdefault(video.id, "enderrock")
                break
    return found


#: The separators of a video title "Artist - Song | Videoclip".
_TITLE_PARTS = re.compile(r"\s+[-–—|]\s+|\s*\|\s*")


def collect(
    db: DbSession,
    client: Client,
    song_ids: list[int],
    search: bool = True,
    streams: bool = True,
    free: dict[int, dict[str, str]] | None = None,
) -> dict[int, Signal]:
    """The signals of these public songs: their official video (free ids first, then a search
    while the day's searches last) and their streams. A song whose search is spent is left
    without a video; asked again another day, it is searched then."""
    free = free if free is not None else free_videos(db, client)
    credits = _credits(db, song_ids)
    titles = dict(db.execute(select(Song.id, Song.title).where(Song.id.in_(song_ids))).all())
    signals = {song_id: Signal(song_id) for song_id in song_ids}

    def names_of(song_id: int) -> list[str]:
        return [name for _, names in credits.get(song_id, []) for name in names]

    def choose(song_id: int, candidates: dict[str, str], videos: dict[str, Video]) -> None:
        signal = signals[song_id]
        for video_id, source in candidates.items():
            video = videos.get(video_id)
            if video is None:
                continue
            kind = channel_kind(video.channel, names_of(song_id), video.title, titles[song_id])
            if kind is None:
                signal.unofficial.append(video)
            elif signal.video is None or video.views > signal.video.views:
                signal.video, signal.found_by, signal.channel_kind = video, source, kind

    wanted = {song_id: free.get(song_id, {}) for song_id in song_ids}
    videos = client.videos(v for candidates in wanted.values() for v in candidates)
    for song_id, candidates in wanted.items():
        choose(song_id, candidates, videos)
    if search:
        try:
            for song_id in song_ids:
                if signals[song_id].video is not None or not credits.get(song_id):
                    continue
                first = credits[song_id][0][1][0]
                ids = client.search(f"{first} {titles[song_id]}")
                found = client.videos(ids)
                choose(song_id, {one: "search" for one in ids}, found)
        except OutOfQuota as error:
            if client.say:
                print(f"  search stopped: {error}")
    if streams and client.spotify:
        _streams(client, signals, credits, titles)
    return signals


def _streams(
    client: Client,
    signals: dict[int, Signal],
    credits: dict[int, list[tuple[int, list[str]]]],
    titles: dict[int, str],
) -> None:
    pages: dict[int, list[tuple[str, int]] | None] = {}
    for song_id, signal in signals.items():
        wanted = title_forms(titles[song_id])
        best: int | None = None
        for artist_id, names in credits.get(song_id, []):
            if artist_id not in pages:
                try:
                    spotify_id = client.spotify_artist(names[0]) if names else None
                    pages[artist_id] = client.kworb_songs(spotify_id) if spotify_id else None
                except OutOfQuota:
                    pages[artist_id] = None  # the answers already kept still count
            for title, streams in pages[artist_id] or []:
                if title_forms(title) & wanted and (best is None or streams > best):
                    best = streams
        if best is not None:
            signal.streams = best
            signal.streams_read_at = _now()
