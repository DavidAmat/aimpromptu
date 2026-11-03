"""Copy this style, implementation 06, Phase 2: the run in the backend with stand-ins for the AI (no request leaves
the machine): the check of the passages, each passage written the reference's way, the marks the code copies, the
first passage first, Go on, Write this batch again, Stop, Revert, undo, and the routes.

The part of ``test_part_sheet`` is a song of 40 s that repeats every 9 s (four bars of 2 s and a pause of 1 s): its
first 9 s are the reference, and the matcher finds the next repeats.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from aitu_backend.part_sheet import build, edits, job, runs
from aitu_backend.sheet.llm import style as S
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet.data import Note, Sheet
from aitu_backend.transcription import pipeline
import test_part_sheet
from test_part_sheet import finish, messages, sheet
from test_sheet_edits import walk
from test_sheet_reading import edit, notes_of, stored_sheet

client = test_part_sheet.client
part = test_part_sheet.part

HEAD = "F1 frames frameMs=40 quarterMs=500\nkey=0 clefs: R=treble L=bass\n"
REF = (0, 225)  # the first 9 s


def target_of(prompt: str) -> Sheet:
    return f1.read(re.search(r"## Target.*?```\n(.*?)```", prompt, re.S).group(1))


def stand_in(prompts: list[str], *, drop: tuple[str, ...] = (), refuse: bool = False, edges: str = "", hook=None):
    """The AI: the check keeps every passage (but ``drop``); each passage is written as the target with its first
    column of each hand rewritten held as a half note (the reference's way, for the test), the lowest note of its last
    chord left out and declared. ``refuse``: every passage answer is not F1. ``hook``: called before each passage answer."""

    def complete(system: str, messages_: list[dict]) -> str:
        first = messages_[0]["content"]
        prompts.append(messages_[-1]["content"])
        if "the check of" in first.splitlines()[0]:
            names = re.findall(r"^### (P\d+) ", first, re.M)
            lines = [
                f"{n} {edges if n == 'P1' else ''}{'drop' if n in drop else 'keep'} | the same melody".replace("  ", " ")
                for n in names
            ]
            return "```\n" + "\n".join(lines) + "\n```"
        if hook is not None:
            hook()
        if refuse:
            return "I would rather not."
        target = target_of(first)
        firsts = {st: min(n.frame for n in target.notes if n.staff == st) for st in {n.staff for n in target.notes}}
        notes = [replace(n, figure=2, beam=None) if n.frame == firsts[n.staff] else n for n in target.notes]
        # the lowest note of the last column of two notes or more (never the top of the melody)
        cols: dict[tuple[int, int], list[Note]] = {}
        for n in notes:
            cols.setdefault((n.frame, n.staff), []).append(n)
        last = min(cols[max(k for k, v in cols.items() if len(v) > 1)], key=lambda n: n.midi)
        notes = [n for n in notes if n is not last]
        text = f1.write(replace(target, notes=notes).sort(), mode="frames").strip()
        name = f"{last.step}{'#' if last.alter > 0 else 'b' if last.alter < 0 else ''}{last.octave}"
        return f"```\n{text}\n# leave out f{last.frame} {name}\n# explain: the first notes held, as the reference.\n```"

    return complete


def listed(client: TestClient, part: str, hand: str = "both") -> dict:
    r = client.get(f"/sheet/{part}/llm/style", params={"start": REF[0], "end": REF[1], "hand": hand})
    assert r.status_code == 200, r.text
    return r.json()


# ------------------------------------------------------------------ the pure parts


def _passages() -> list[S.Passage]:
    return [S.Passage(0, 300, 500, 0.9, 0, []), S.Passage(1, 600, 800, 0.7, 2, [])]


def test_the_check_keeps_drops_and_moves_an_edge_by_two_negras_at_most() -> None:
    reply = "```\nP1 f290-f510 keep | the chorus again\nP2 drop | the bridge: another melody\n```"
    errs, out = S.read_check(reply, _passages(), reference=(0, 200), quarter_ms=500)
    assert errs == []
    assert (out[0].start, out[0].end, out[0].keep, out[0].why) == (290, 510, True, "the chorus again")
    assert out[1].keep is False and out[1].why.startswith("the bridge")
    errs, _ = S.read_check("```\nP1 f250-f500 keep | x\nP2 keep | y\n```", _passages(), reference=(0, 200), quarter_ms=500)
    assert any("more than 2 negras" in e for e in errs)
    errs, _ = S.read_check("```\nP1 keep | x\n```", _passages(), reference=(0, 200), quarter_ms=500)
    assert any(e.startswith("P2 has no answer") for e in errs)
    errs, _ = S.read_check("P1 keep\nP1 drop\nP2 keep\nP3 keep", _passages(), reference=(0, 200), quarter_ms=500)
    assert any("twice" in e for e in errs) and any("P3 is not a passage" in e for e in errs)
    errs, _ = S.read_check("P1 f290-f500 keep\nP2 keep", _passages(), reference=(0, 295), quarter_ms=500)
    assert any("overlaps the reference" in e for e in errs)


def _target() -> Sheet:
    return f1.read(HEAD + "f300 L: C3:4  R: E5:8 b1\nf306 R: D5:8 b1\nf312 L: E3,G3:4  R: C5:4\n")


def _ref() -> Sheet:
    return f1.read(HEAD + "f100 L: C3:2  R: E5:8 b1\nf106 R: D5:8 b1\nf112 R: C5:4\n")


PASSAGE = S.Passage(0, 300, 320, 0.9, 0, [(1, 100, 300), (1, 106, 306), (1, 112, 312), (2, 100, 300)])


def check(reply: str, staffs=(1, 2)) -> S.Checked:
    t = _target()
    return S.check_style(reply, S._slice(t, 300, 320, staffs), reference=_ref(), passage=PASSAGE, staffs=staffs, around=t)


def test_a_passage_answer_is_checked() -> None:
    # the reference holds the left hand (one note at f100, no column at f112): the chord at f312 may go
    ok = "```\n" + HEAD + "f300 L: C3:2  R: E5:8 b1\nf306 R: D5:8 b1\nf312 R: C5:4\n# leave out f312 E3\n# leave out f312 G3\n# explain: held.\n```"
    got = check(ok)
    assert got.errors == [] and sum(got.left.values()) == 2 and got.explain == ["held."]
    assert got.declared() == ["leave out f312 E3", "leave out f312 G3"]
    # an undeclared note missing, a note outside the passage, the melody lost
    bad = check("```\n" + HEAD + "f300 L: C3:2  R: E5:8 b1\nf306 R: D5:8 b1\nf312 L: E3,G3:4  R: A4:4\nf330 R: C5:4\n```")
    text = " ".join(bad.errors)
    assert "missing" in text and "outside the passage" in text and "of the melody" in text
    # one hand: a note of the fixed hand is refused
    one = check("```\n" + HEAD + "f300 L: C3:2  R: E5:8 b1\nf306 R: D5:8 b1\nf312 R: C5:4\n```", staffs=(1,))
    assert any("fixed" in e for e in one.errors)
    assert check("no block").errors[0].startswith("the answer must be F1 frames")


def test_the_changes_are_limited_to_what_the_reference_asks_for() -> None:
    t = _target()
    # the map pairs every column, and the reference has as many notes: only the base limit (4)
    same = S.Passage(0, 300, 320, 0.9, 0, [(1, 100, 300), (1, 106, 306), (1, 112, 312), (2, 100, 300), (2, 112, 312)])
    ref = f1.read(HEAD + "f100 L: C3:4  R: E5:8 b1\nf106 R: D5:8 b1\nf112 L: E3,G3:4  R: C5:4\n")
    assert S.change_budget(S._slice(t, 300, 320, (1, 2)), ref, same, (1, 2)) == 4
    # the reference plays no left hand at f112: the target's two notes there come on top
    assert S.change_budget(S._slice(t, 300, 320, (1, 2)), _ref(), PASSAGE, (1, 2)) == 4 + 2
    added = "```\n" + HEAD + "f300 L: C3:4  R: E5:8 b1\nf306 R: D5,F#5:8 b1\nf312 L: E3,G3:4  R: C5:4\n# add f306 F#5\n```"
    assert any("harmony" in e for e in check(added).errors)  # F# is not a name the passage plays there


def test_the_marks_are_copied_to_the_same_note_and_the_passage_keeps_its_own() -> None:
    ref = f1.read(HEAD + "f100 R: Bb4:4 fg2\nf106 R: D5:8 fg3\nf112 R: C5:4 fg1\n")
    for n in ref.notes:
        n.spelled = n.midi == 70
    ref.user_clefs = [(100, 113, 1, "F4")]
    passage = S.Passage(0, 300, 320, 0.9, 2, [(1, 100, 300), (1, 106, 306), (1, 112, 312)])
    # a tone higher: Bb4 -> C5 (spelled C, its finger copied: the same note after the shift), D5 -> E5 (finger), and
    # at f312 a D5 (the reference's C5 a tone higher) that the passage already fingered
    now = f1.read(HEAD + "f300 R: C5:4\nf306 R: E5:8\nf312 R: D5:4\n")
    own = [replace(n, finger=5) if n.frame == 312 else n for n in now.notes]
    sheet_ = replace(now, notes=list(own))
    counts = S.copy_marks(sheet_, reference=ref, before=own, passage=passage, staffs=(1,))
    by = {n.frame: n for n in sheet_.notes}
    assert by[300].spelled and (by[300].step, by[300].alter) == ("C", 0) and by[300].finger == 2
    assert by[306].finger == 3 and by[312].finger == 5  # the passage's own finger stays
    assert sheet_.user_clefs == [(300, 313, 1, "F4")]
    assert counts == Counter({"fingers": 2, "spellings": 1, "clefs": 1})
    assert S.copied_text(counts) == "1 spelling, 2 fingers and 1 clef copied"
    # a note that is not the same note gets no finger
    other = replace(now, notes=[replace(n, octave=n.octave + 1) if n.frame == 306 else n for n in now.notes])
    S.copy_marks(other, reference=ref, before=[], passage=passage, staffs=(1,))
    assert next(n for n in other.notes if n.frame == 306).finger is None
    assert S.moved_name("B", 2, 72) == ("C", 0, 5) and S.moved_name("F", 1, 66) == ("G", -1, 4)  # a minor second moves the letter


# ------------------------------------------------------------------ the run


def test_the_dialog_lists_the_passages_like_the_reference_for_free(client: TestClient, part: str) -> None:
    body = listed(client, part)
    starts = [p["start"] for p in body["passages"]]
    assert len(starts) >= 3 and all(s >= REF[1] for s in starts)
    assert body["requests"] == len(starts) + 1 and body["usd"] > 0 and body["minutes"] >= 1
    assert body["tooLong"] is False and body["tooShort"] is False and body["threshold"] == 0.6
    short = client.get(f"/sheet/{part}/llm/style", params={"start": 0, "end": 3}).json()
    assert short["tooShort"] is True and short["passages"] == []
    long = client.get(f"/sheet/{part}/llm/style", params={"start": 0, "end": 2400}).json()
    assert long["tooLong"] is True


def test_a_run_checks_writes_the_first_passage_waits_and_goes_on(client: TestClient, part: str) -> None:
    before = sheet(client, part)
    ticked = [[p["start"], p["end"]] for p in listed(client, part)["passages"][:3]]
    prompts: list[str] = []
    started = job.start_style(part, start=REF[0], end=REF[1], hand="both", passages=ticked, complete=lambda: stand_in(prompts))
    finish(started)
    first = started.summary
    assert first["style"] == "ok" and first["waiting"] is True and first["batches"] == 1 and first["total"] == 3
    assert first["dropped"] == 0 and first["before"] >= 1
    phases = [m.get("phase") for m in messages(started)]
    assert phases[:2] == ["style", "check"] and phases.count("batch") == 1 and phases[-1] == "saved"
    assert "the check of 3 passages" in prompts[0] and "## The reference (f0-f225" in prompts[0]
    assert "## The column map" in prompts[1] and "## Target (both hands" in prompts[1]
    assert sheet(client, part)["history"]["undo"] == "Copy this style with AI, both hands, passage 1"
    # the AI's figures are printed as set by hand; the note left out is marked removed
    a, b = ticked[0]
    drawn = f1.read(build.current(part).text)
    held = [n for n in drawn.notes if n.frame == min(m.frame for m in drawn.notes if a <= m.frame < b)]
    assert held and all(n.figure == 2 and n.fixed for n in held)
    stored = pipeline.load_note_events(part)
    assert sum(e.removed for e in stored.events) == 1
    run = client.get(f"/sheet/{part}/llm/runs/{first['run']}").json()
    assert run["kind"] == "style" and run["state"] == "waiting" and run["plan"]["status"] == "ok"
    assert [p["keep"] for p in run["passages"]] == [True, True, True]
    assert run["batches"][0]["explain"] == ["the first notes held, as the reference."]
    listing = client.get(f"/sheet/{part}/llm/runs").json()
    assert listing[0]["kind"] == "style" and listing[0]["reference"] == [0, 225] and len(listing[0]["passages"]) == 3
    entry = stored_sheet(part).record.styles[0]
    assert entry["reference"] == [0, 225] and entry["passages"][0][2] == "ok" and entry["passages"][1][2] == "waiting"

    went = job.continue_level(part, first["run"], complete=lambda: stand_in(prompts))
    finish(went)
    done = went.summary
    assert done["style"] == "ok" and "waiting" not in done and done["batches"] == 3 and done["before"] == first["before"]
    assert not any("the check of" in p.splitlines()[0] for p in prompts[3:])  # the check is the run's
    assert "## The passages written before in this run" in prompts[2]
    assert sheet(client, part)["history"]["undo"] == "Copy this style with AI, both hands, the other passages"
    run = client.get(f"/sheet/{part}/llm/runs/{first['run']}").json()
    assert run["state"] == "done" and [b["status"] for b in run["batches"]] == ["ok", "ok", "ok"]
    assert sum(e.removed for e in pipeline.load_note_events(part).events) == 3

    # Revert puts back the part as it was before the run; its undo puts the run back
    r = client.post(f"/sheet/{part}/llm/revert", json={"version": done["before"]})
    assert r.status_code == 200, r.text
    assert set(notes_of(r.json())) == set(notes_of(before))
    walk(client, part, "undo")
    assert sum(e.removed for e in pipeline.load_note_events(part).events) == 3


def test_the_check_drops_a_passage_and_one_hand_keeps_the_other(client: TestClient, part: str) -> None:
    ticked = [[p["start"], p["end"]] for p in listed(client, part, "right")["passages"][:2]]
    before = f1.read(build.current(part).text)
    prompts: list[str] = []
    started = job.start_style(
        part, start=REF[0], end=REF[1], hand="right", passages=ticked, first=False,
        complete=lambda: stand_in(prompts, drop=("P2",)),
    )
    finish(started)
    s = started.summary
    assert s["style"] == "ok" and s["dropped"] == 1 and s["batches"] == s["total"] == 1
    assert "## The left hand (fixed" in prompts[1] and len(prompts) == 2
    after = f1.read(build.current(part).text)
    left = lambda sh: sorted((n.frame, n.midi) for n in sh.notes if n.staff == 2)  # noqa: E731
    assert left(after) == left(before)
    run = runs.load(part, s["run"])
    assert run["passages"][1]["keep"] is False and run["passages"][1]["why"] == "the same melody"
    assert sheet(client, part)["history"]["undo"] == "Copy this style with AI, the right hand"


def test_every_passage_dropped_writes_nothing(client: TestClient, part: str) -> None:
    ticked = [[p["start"], p["end"]] for p in listed(client, part)["passages"][:2]]
    started = job.start_style(part, start=REF[0], end=REF[1], hand="both", passages=ticked,
                              complete=lambda: stand_in([], drop=("P1", "P2")))
    finish(started)
    assert started.summary["style"] == "dropped" and started.summary["dropped"] == 2
    assert sheet(client, part)["history"]["undo"] is None
    assert runs.load(part, started.summary["run"])["state"] == "done"


def test_a_passage_refused_three_times_keeps_its_notes(client: TestClient, part: str) -> None:
    before = build.current(part).text
    ticked = [[p["start"], p["end"]] for p in listed(client, part)["passages"][:1]]
    prompts: list[str] = []
    started = job.start_style(part, start=REF[0], end=REF[1], hand="both", passages=ticked,
                              complete=lambda: stand_in(prompts, refuse=True))
    finish(started)
    assert started.summary["style"] == "failed" and started.summary["batches"] == 0
    assert len(prompts) == 1 + S.MAX_CHECKS and prompts[-1].startswith("The checker did not accept")
    assert build.current(part).text == before
    run = runs.load(part, started.summary["run"])
    assert run["state"] == "failed" and run["batches"][0]["status"] == "failed" and len(run["batches"][0]["errors"]) == 3


def test_a_finger_of_the_reference_is_copied_to_the_same_note(client: TestClient, part: str) -> None:
    body = sheet(client, part)
    ticked = [[p["start"], p["end"]] for p in listed(client, part, "right")["passages"][:1]]
    a, b = ticked[0]
    # the first right-hand note of the reference, and the same note in the passage
    ref_note = min((n for n in body["notes"] if n["hand"] == "right" and int(n["ref"].split(":")[0]) < REF[1]),
                   key=lambda n: int(n["ref"].split(":")[0]))
    edit(client, part, action="finger", notes=[ref_note["ref"]], value=[4])
    started = job.start_style(part, start=REF[0], end=REF[1], hand="right", passages=ticked, first=False,
                              complete=lambda: stand_in([]))
    finish(started)
    assert started.summary["style"] == "ok", started.summary
    run = runs.load(part, started.summary["run"])
    assert run["batches"][0]["copied"].get("fingers", 0) >= 1 and "finger" in run["batches"][0]["copiedText"]
    drawn = f1.read(build.current(part).text)
    midi = int(ref_note["ref"].split(":")[1])
    assert any(n.finger == 4 and n.midi == midi and a <= n.frame < b for n in drawn.notes)


def test_stop_keeps_the_passages_accepted_and_stale_notes_store_nothing(client: TestClient, part: str) -> None:
    ticked = [[p["start"], p["end"]] for p in listed(client, part)["passages"][:3]]
    calls = {"n": 0}

    def stop_on_second() -> None:
        calls["n"] += 1
        if calls["n"] == 2:
            job.stop(part)

    started = job.start_style(part, start=REF[0], end=REF[1], hand="both", passages=ticked, first=False,
                              complete=lambda: stand_in([], hook=stop_on_second))
    finish(started)
    s = started.summary
    # the request Stop found going ends first (its passage is kept); the third is never asked
    assert s["style"] == "ok" and s["stopped"] is True and s["batches"] == 2 and calls["n"] == 2
    assert runs.load(part, s["run"])["state"] == "stopped"

    # the notes change while the AI writes: nothing is stored
    late = max(sheet(client, part)["notes"], key=lambda n: int(n["ref"].split(":")[0]))["ref"]

    def change_notes() -> None:
        edits.remove_notes(part, [late])  # the Notes step changes the notes meanwhile

    started = job.start_style(part, start=REF[0], end=REF[1], hand="both", passages=ticked[1:2], first=False,
                              complete=lambda: stand_in([], hook=change_notes))
    finish(started)
    assert started.summary["style"] == "stale"


def test_write_this_passage_again_with_the_users_answer(client: TestClient, part: str) -> None:
    ticked = [[p["start"], p["end"]] for p in listed(client, part)["passages"][:2]]
    prompts: list[str] = []
    started = job.start_style(part, start=REF[0], end=REF[1], hand="both", passages=ticked, complete=lambda: stand_in(prompts))
    finish(started)
    run_id = started.summary["run"]
    again = job.again_batch(part, run_id, 0, "Hold the first notes longer.", complete=lambda: stand_in(prompts))
    finish(again)
    assert again.summary["style"] == "ok" and again.summary["again"] == 1 and again.summary["waiting"] is True
    assert prompts[-1].startswith("The user read your passage")
    assert sheet(client, part)["history"]["undo"] == "Passage 1 written again with AI"
    run = runs.load(part, run_id)
    assert run["batches"][0]["answers"][0]["words"] == "Hold the first notes longer." and run["state"] == "waiting"


def test_the_routes_of_the_run(client: TestClient, part: str, monkeypatch: pytest.MonkeyPatch) -> None:
    url = f"/sheet/{part}/llm/style"
    ticked = [[p["start"], p["end"]] for p in listed(client, part)["passages"][:1]]
    assert client.post(url, json={"start": 0, "end": 225, "passages": []}).status_code == 400
    assert client.post(url, json={"start": 0, "end": 225, "passages": [[100, 300]]}).status_code == 400  # overlaps
    assert client.post(url, json={"start": 0, "end": 3, "passages": ticked}).status_code == 400  # too short
    from aitu_backend.api import sheet as api_sheet

    monkeypatch.setattr(api_sheet, "_writes", lambda uuid: False)
    assert client.post(url, json={"start": 0, "end": 225, "passages": ticked}).status_code == 403
    monkeypatch.setattr(api_sheet, "_writes", lambda uuid: True)
    monkeypatch.setattr(job, "job_of", lambda part_id: object())
    assert client.post(url, json={"start": 0, "end": 225, "passages": ticked}).status_code == 409


def test_a_style_run_left_running_is_closed_with_its_saved_passages(part: str) -> None:
    log = runs.create(part, {"hand": "both", "start": 0, "end": 225, "windows": [[300, 500]]}, "system", kind="style")
    log["passages"] = [S.Passage(0, 300, 500).to_json()]
    log["batches"] = [{"k": 0, "start": 300, "end": 500, "status": "ok"}]
    runs.save(part, log)
    assert runs.close_unfinished() >= 1
    closed = runs.load(part, log["id"])
    assert closed["state"] == "stopped" and closed["batches"][0]["status"] == "error"  # its notes never reached the sheet


def test_a_batch_prompt_of_a_long_reference_fits_one_request(part: str) -> None:
    # Plan section 7: a reference of 30 s and a passage of 30 s make a request of a reasonable size.
    current = f1.read(build.current(part).text)
    p = S.Passage(0, 750, 1000, 0.8, 0, [(1, f, f + 750) for f in sorted({n.frame for n in current.notes if n.frame < 250})])
    prompt = S.batch_prompt(
        sid="test", index=0, count=1, sheet=current, reference=(0, 750), passage=p, staffs=(1, 2),
        target=S._slice(current, 750, 1000, (1, 2)), fixed=None,
    )
    assert len(prompt) < 40_000, len(prompt)
    assert len(S.system_prompt()) < 40_000
