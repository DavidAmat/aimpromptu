"""The example set, the score board, and the `/frame-examples` router.

The two examples with a hand read ground truth are the exit criteria of Phase 2
in miniature: on them the detector must find every onset and invent none. They
are the only two examples where a human can read the picture without guessing —
the others have a halo over the band where the answer is, which is what the
annotation page of Task 2.2.2 is for.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from aitu_backend.main import create_app
from aitu_backend.schemas.video import Annotation
from aitu_backend.video import examples, images, scoring

client = TestClient(create_app())

#: The two Phase 1 read by hand off a label sheet, applying V-18 word for word.
HAND_READ = ["derulo", "shut-up-and-dance"]


def _seeded(slug: str) -> bool:
    return examples.exists(slug) and examples.load(slug).calibration is not None


@pytest.mark.skipif(not examples.slugs(), reason="the example screenshots are not checked out")
def test_every_screenshot_is_listed_once() -> None:
    response = client.get("/frame-examples")
    assert response.status_code == 200
    payload = response.json()
    assert [row["slug"] for row in payload] == examples.slugs()
    assert all("hasCalibration" in row and "annotationCount" in row for row in payload)


@pytest.mark.skipif(not examples.slugs(), reason="the example screenshots are not checked out")
def test_the_picture_is_served_at_the_working_resolution() -> None:
    """One width for the UI and the detector, so a coordinate means one thing."""
    slug = examples.slugs()[0]
    response = client.get(f"/frame-examples/{slug}/image")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    width, height = examples.image_size(slug)
    assert width == images.WORK_WIDTH and height > 0

    record = client.get(f"/frame-examples/{slug}").json()
    assert record["imageWidth"] == images.WORK_WIDTH


def test_an_unknown_slug_is_a_404() -> None:
    assert client.get("/frame-examples/not-a-screenshot").status_code == 404
    assert client.get("/frame-examples/not-a-screenshot/image").status_code == 404


@pytest.mark.skipif(not _seeded("derulo"), reason="run scripts/seed_frame_examples.py first")
def test_the_two_services_build_the_same_overlay() -> None:
    """The endpoint that proves the frontend's own geometry has not drifted."""
    record = client.get("/frame-examples/derulo").json()
    response = client.post("/frame-examples/derulo/geometry", json=record["calibration"])
    assert response.status_code == 200
    built = response.json()
    whites = [key for key in built["keys"] if key["kind"] == "white"]
    assert len(whites) == len(record["calibration"]["whiteBorders"]) - 1
    # `derulo` is a whole piano with its top Do cropped off by the screenshot,
    # which is what 19 of the 21 examples look like.
    assert built["keys"][0]["nameEn"] == "A0"
    assert [key["midi"] for key in built["keys"]] == list(range(21, 21 + len(built["keys"])))
    assert len(built["lanes"]) == len(built["keys"])


@pytest.mark.skipif(not _seeded("derulo"), reason="run scripts/seed_frame_examples.py first")
def test_the_detector_draws_its_runs_on_the_pixels_they_came_from() -> None:
    """Task 2.3.2: a disagreement has to be something you can look at."""
    record = client.get("/frame-examples/derulo").json()
    offset = record["annotations"][0]["offsetPx"]
    response = client.post(f"/frame-examples/derulo/detect?offsetPx={offset}")
    assert response.status_code == 200
    detection = response.json()
    assert detection["runs"], "derulo has rectangles on it"
    run = detection["runs"][0]
    for field in ("midi", "yTop", "yBottom", "x0", "x1", "widthKeys", "clipped", "verdict"):
        assert field in run
    assert run["yTop"] < run["yBottom"], "y grows downward; the tip is the lowest row"


@pytest.mark.skipif(
    not all(_seeded(slug) for slug in HAND_READ), reason="run scripts/seed_frame_examples.py first"
)
def test_on_the_hand_read_examples_every_onset_is_found_and_none_invented() -> None:
    """Phase 2's exit criteria, on the ground truth that exists.

    The criterion is stated rather than a count frozen: every onset in the hand
    reading is found and no onset is invented, and the same for sustains. A count
    would have to be edited every time a reading is added, which is the opposite
    of what a score board is for.
    """
    board = scoring.board(only=HAND_READ)
    assert board.lines, "both hand read examples have at least one reading"
    assert board.total.onsets_invented == 0
    assert board.total.onsets_missed == 0
    assert board.total.sustains_invented == 0
    assert board.total.sustains_missed == 0
    assert all(not line.disagreements for line in board.lines)

    # And it found something: a detector that reports nothing at all would pass
    # every line above.
    expected = sum(len(a.onsets) for slug in HAND_READ for a in examples.load(slug).annotations)
    assert board.total.onsets_found == expected


@pytest.mark.skipif(not _seeded("derulo"), reason="run scripts/seed_frame_examples.py first")
def test_the_detector_follows_the_offset_line_and_not_the_nearest_rectangle() -> None:
    """V-25, as the example set tests it.

    `derulo` is read at three windows. Every rectangle tip on it sits at row 151
    or 152 and the upper line is at 162, so a window of 147 to 161 holds all three
    and a window of 156 to 161 holds none — and the strike light lives in exactly
    those last rows. A detector that reported the nearest rectangle rather than
    the one inside the window would answer the same thing at both.
    """
    board = scoring.board(only=["derulo"])
    by_offset = {round(line.offset_px): line for line in board.lines}
    assert 6 in by_offset and 15 in by_offset, "the two narrow readings are saved"
    assert by_offset[6].onsets_found + by_offset[6].onsets_invented == 0
    assert by_offset[15].onsets_found == 3 and by_offset[15].onsets_invented == 0


@pytest.mark.skipif(not examples.slugs(), reason="the example screenshots are not checked out")
def test_an_example_with_no_annotation_is_named_rather_than_counted() -> None:
    """An honest failure list is a result; a rounded up number is not."""
    board = scoring.board()
    assert board.skipped, "most examples have no hand reading yet"
    assert all(reason for reason in board.skipped.values())
    assert set(board.skipped) & set(examples.slugs()) == set(board.skipped)


def test_a_key_the_picture_cannot_answer_for_leaves_the_score_on_both_sides() -> None:
    annotation = Annotation(offset_px=50.0, onsets=[60], sustains=[], skip=[65])
    line = scoring.score_one("made-up", annotation, detected_onsets=[60, 65], detected_sustains=[])
    assert line.onsets_found == 1
    assert line.onsets_invented == 0, "65 was skipped, so it is not an invention"
    assert line.disagreements == []


def test_an_annotation_never_lists_a_key_as_both_onset_and_sustain() -> None:
    annotation = Annotation(offset_px=50.0, onsets=[60, 60, 64], sustains=[60, 48])
    assert annotation.onsets == [60, 64]
    assert annotation.sustains == [48]


@pytest.mark.skipif(not examples.slugs(), reason="the example screenshots are not checked out")
def test_saving_a_reading_twice_at_one_offset_replaces_it() -> None:
    """The entry is the triple (example, offset line position, keys marked)."""
    slug = examples.slugs()[0]
    before = examples.load(slug)
    try:
        examples.put_annotation(slug, Annotation(offset_px=999.0, onsets=[60]))
        examples.put_annotation(slug, Annotation(offset_px=999.0, onsets=[62]))
        saved = [a for a in examples.load(slug).annotations if a.offset_px == 999.0]
        assert len(saved) == 1 and saved[0].onsets == [62]

        examples.delete_annotation(slug, 999.0)
        assert not [a for a in examples.load(slug).annotations if a.offset_px == 999.0]
    finally:
        examples.save(before)
