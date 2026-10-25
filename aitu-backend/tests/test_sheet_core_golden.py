"""The golden files of the product core ``aitu_backend.sheet`` (``golden/sheet/README.md``): every port must
reproduce them. Copied from the research core (implementation 03, Phase 1) with the backend names.
"""

from __future__ import annotations

import gzip
import json
import re
from pathlib import Path

import numpy as np
import pytest

from aitu_backend.sheet.engrave.cursor import render_song
from aitu_backend.sheet.llm.chain import write_song
from aitu_backend.sheet.llm.guards import guard_errors
from aitu_backend.sheet.llm.windows import answer_text, check
from aitu_backend.sheet.proposal.pipeline import propose
from aitu_backend.sheet.sheet import f1
from aitu_backend.matrix.keys import LOWEST_MIDI
from aitu_backend.pmn.notes import Notes

GOLD = Path(__file__).with_name("golden") / "sheet"
ENGRAVE = sorted((GOLD / "engrave").rglob("*.f1"))


def notes_of_frames(sheet) -> Notes:
    """One 40 ms note per onset of a frames sheet (the matrix the frames text stands for)."""
    ns = sorted(sheet.notes, key=lambda n: (n.frame, n.midi))
    return Notes.build(
        key=np.array([n.midi - LOWEST_MIDI for n in ns]),
        on_ms=np.array([n.frame * 40.0 for n in ns]),
        len_ms=np.full(len(ns), 40.0),
        hand=np.zeros(len(ns), np.int8),
    )


def test_golden_files_exist():
    assert len(ENGRAVE) == 120  # 41 rulebook passages, 10 viewer songs, 69 clef passage versions


@pytest.mark.parametrize("path", ENGRAVE, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_engrave(path: Path):
    r = render_song(path.read_text())
    assert r.svg == gzip.decompress(path.with_suffix(".svg.gz").read_bytes()).decode()
    want = json.loads(path.with_suffix(".cursor.json").read_text())
    assert {
        "bars": r.bars,
        "width": r.width,
        "height": r.height,
        "systems": r.systems,
        "columns": r.columns,
    } == want


@pytest.mark.parametrize(
    "path", sorted((GOLD / "proposal").glob("*.hands.f1")), ids=lambda p: p.name[:8]
)
def test_proposal(path: Path):
    want = path.with_name(path.name.replace(".hands.", ".proposal.")).read_text()
    meta = json.loads(want.splitlines()[0][2:])
    hs = f1.read(path.read_text())
    prop = propose(notes_of_frames(hs), key=meta["key"], hand_sheet=hs, track=True)
    assert (prop.quarter_ms, prop.meter, prop.phase_ms) == (
        meta["quarter_ms"],
        meta["meter"],
        meta["phase_ms"],
    )
    assert f1.write(prop.sheet, mode="bars", anchors=True) == want.split("\n", 1)[1]


@pytest.mark.parametrize(
    "case", json.loads((GOLD / "checker" / "cases.json").read_text()), ids=lambda c: c["name"]
)
def test_checker(case: dict):
    errs, sheet = check(answer_text(case["reply"]), f1.read(case["target"]))
    assert errs == case["errors"]
    assert (guard_errors(sheet) if not errs else []) == case["guard_errors"]


def test_chain_replay():
    d = GOLD / "chain" / "43faf78e"
    replies = {
        int(p.stem.split("-")[1]): p.read_text() for p in (d / "answers").glob("window-*.md")
    }
    asked = []

    def complete(system: str, messages: list[dict]) -> str:
        assert system.startswith("# Task") and messages[0]["role"] == "user"
        k = int(re.match(r"# Window (\d+) of song ", messages[0]["content"]).group(1))
        asked.append(k)
        return replies[k]

    frames = f1.read((d / "frames.f1").read_text())
    res = write_song(
        notes_of_frames(frames),
        complete,
        key=frames.key,
        sid="43faf78e",
        hand_sheet=f1.read((d / "hands.f1").read_text()),
        guards=False,
    )
    assert asked == sorted(replies)
    assert res.text == (d / "song.f1").read_text()
    assert [vars(w) for w in res.windows] == json.loads((d / "windows.json").read_text())
