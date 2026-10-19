"""The genres and tags of the public songs from Wikidata (implementation 02, Phase 18;
``context/music-library/genres.md``): the answers of QLever read and kept, the proposed map from a
Wikidata genre to the genres of the app, the two genres a song keeps, the match of Wikidata songs and
performers to the public rows, and the counts of the measure, with no network (the Wikidata answer
is written in the test)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aitu_backend.db.database import session
from aitu_backend.library import genres, signals
from aitu_backend.library.genres import Item, Link, Wikidata
from tests.test_regional_import import folder, run, song_titled  # noqa: F401 - the fixture


class Offline(signals.Client):
    """A client whose network answers every query with ``answer``, and counts the queries."""

    def __init__(self, answers: signals.Answers, answer: tuple[int, str]):
        super().__init__(answers, say=False)
        self.answer = answer
        self.queries = 0

    def _fetch(self, url, data=None, headers=None):  # type: ignore[no-untyped-def]
        self.queries += 1
        return self.answer


def test_a_qlever_answer_is_read_and_kept_and_a_refusal_is_not(tmp_path: Path) -> None:
    answers = signals.Answers(tmp_path / "answers.sqlite")
    tsv = (
        "?item\t?l\t?lang\n"
        '<http://www.wikidata.org/entity/Q1>\t"Stayin\' Alive"@en\ten\n'
        '<http://www.wikidata.org/entity/Q2>\t"A \\"quoted\\" title"@es\tes\n'
        "<http://www.wikidata.org/entity/Q3>\t\t\n"
    )
    client = Offline(answers, (200, tsv))
    rows = client.qlever("SELECT ...")
    assert rows == [["Q1", "Stayin' Alive", "en"], ["Q2", 'A "quoted" title', "es"], ["Q3", "", ""]]
    assert client.qlever("SELECT ...") == rows and client.queries == 1
    timed_out = Offline(answers, (200, '{"exception": "Operation timed out"}'))
    with pytest.raises(RuntimeError):
        timed_out.qlever("SELECT other")
    with pytest.raises(RuntimeError):
        Offline(answers, (400, "bad query")).qlever("SELECT other")
    assert answers.get("qlever:x") is None and timed_out.queries == 1


def _graph() -> Wikidata:
    data = Wikidata()
    data.parents = {
        "Qelectropop": {"Q37073", "Q9778"},  # pop music, electronic music
        "Qindie-rock": {"Q11399", "Q42201"},  # indie rock is itself a root
        "Q183504": {"Q11399", "Q42201"},
        "Qdeep": {"Qa"},
        "Qa": {"Qb"},
        "Qb": {"Q11399"},
        "Qchristmas": {"Qseasonal"},
        "Qloop1": {"Qloop2"},
        "Qloop2": {"Qloop1"},
    }
    data.labels = {one: one for one in [*data.parents, "Q37073", "Q9778", "Q11399"]}
    return data


def test_a_wikidata_genre_is_proposed_as_the_genres_of_its_nearest_roots() -> None:
    mapped = genres.map_genres(_graph())
    assert mapped["Qelectropop"] == ["electronic and dance", "pop"]
    assert mapped["Q183504"] == ["indie"]  # a root itself: nearer than rock music above it
    assert mapped["Qdeep"] == ["rock"]
    assert mapped["Qchristmas"] == [] and mapped["Qloop1"] == []
    assert mapped["Q37073"] == ["pop"]


def test_a_song_keeps_its_two_most_frequent_genres_the_narrow_one_first_on_a_tie() -> None:
    mapped = {"Qpop": ["pop"], "Qelectropop": ["electronic and dance", "pop"], "Qrock": ["rock"]}
    assert genres.chosen(["Qpop", "Qelectropop", "Qrock"], mapped) == [
        "pop",
        "electronic and dance",
    ]
    assert genres.chosen(["Qrock", "Qpop"], mapped) == ["rock", "pop"]
    assert genres.chosen(["Qpop", "Qpop"], mapped) == ["pop"]  # a genre counts once
    assert genres.chosen(["Qchristmas"], mapped) == []


def _wikidata() -> Wikidata:
    data = Wikidata()
    data.items = {
        # Matched by its title and one performer, like a regional source
        "Qgive": Item("Qgive", ["Qpitbull", "Qneyo"], ["Q850412"], ["Give Me Everything"]),
        # A second item of the same song: its genres join
        "Qgive-single": Item("Qgive-single", ["Qpitbull"], ["Q11401"], ["Give Me Everything"]),
        # Another performer: not this public song
        "Qsuper-cover": Item("Qsuper-cover", ["Qsomeone"], ["Q11399"], ["Superestrella"]),
        "Qstayin": Item("Qstayin", ["Qbeegees"], [], ["Stayin' Alive"]),
    }
    data.names = {
        "Qpitbull": ["Pitbull"],
        "Qneyo": ["Ne-Yo"],
        "Qsomeone": ["Someone Else"],
        "Qbeegees": ["Bee Gees"],
        # Two performers share the name "Los Bravos": the weaker match takes neither
        "Qbravos1": ["Los Bravos"],
        "Qbravos2": ["Los Bravos"],
        "Qaitana": ["Aitana"],
    }
    data.performer_genres = {
        "Qbeegees": ["Q58339"],  # disco
        "Qaitana": ["Q37073"],
        "Qbravos1": ["Q11399"],
    }
    data.labels = {"Q850412": "contemporary R&B", "Q11401": "hip-hop", "Q58339": "disco"}
    data.links = [
        Link("Qstayin", "Qfever", "films", "<P406"),
        Link("Qstayin", "Qfever", "films", "P406+album"),
        Link("Qgive", "Qshow", "tv_shows", "<P942"),
        Link("Qnot-public", "Qother", "films", "<P406"),
    ]
    data.works = {"Qfever": "Saturday Night Fever", "Qshow": "A show"}
    return data


def test_wikidata_songs_and_performers_are_matched_to_the_public_rows(
    folder: Path,  # noqa: F811
) -> None:
    run(folder)
    data = _wikidata()
    with session() as db:
        found = genres.match(db, data)
        give = song_titled(db, "Give Me Everything").id
        superestrella = song_titled(db, "Superestrella").id
        stayin = song_titled(db, "Stayin' Alive").id
        assert sorted(found.items[give]) == ["Qgive", "Qgive-single"]
        assert superestrella not in found.items
        assert found.items[stayin] == ["Qstayin"]
        artist_of = {name: artist for name, (artist, _) in genres.Index(db).names.items()}
    # A performer of a matched item that the song credits stands for that artist.
    assert found.performers[artist_of["pitbull"]] == {"Qpitbull"}
    assert found.performers[artist_of["bee gees"]] == {"Qbeegees"}
    # A name only one performer has; not one two performers share.
    assert found.by_name[artist_of["aitana"]] == "Qaitana"
    assert artist_of["los bravos"] not in found.by_name


def test_the_measure_counts_own_genres_a_performers_and_the_tags(
    folder: Path,  # noqa: F811
) -> None:
    run(folder)
    data = _wikidata()
    with session() as db:
        result = genres.measure(db, data)
        public = result.public_songs
    total = result.coverage[("all", "all")]
    # Give Me Everything has its own genres; Stayin' Alive takes the Bee Gees' disco;
    # Superestrella takes Aitana's pop by her name; the others none.
    assert (total["own"], total["performer"], total["by name"]) == (1, 1, 1)
    assert sum(total.values()) == public
    assert result.genres["Q850412"] == [1, 0] and result.genres["Q58339"] == [0, 1]
    assert result.app["r&b and soul"] == [1, 1] and result.app["hip hop"] == [1, 1]
    assert result.app["electronic and dance"] == [0, 1]
    assert result.tag_totals["films"] == (1, 1)
    assert result.tags["films"] == {"<P406": (1, 1), "P406+album": (1, 1)}
    assert result.top_works["films"] == [("Saturday Night Fever", 1)]
    assert result.tag_totals["tv_shows"] == (1, 1) and result.tag_totals["adverts"] == (0, 0)
