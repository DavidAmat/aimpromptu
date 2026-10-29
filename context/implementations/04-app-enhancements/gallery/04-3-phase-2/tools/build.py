"""Implementation 04-3, Phase 2: the gallery of patterns (index.html) and its list (patterns.json), from one list.

    python3 build.py        # writes ../index.html and ../patterns.json

Phase 3 reads patterns.json, so a pattern has one stable ``id`` (its name in the prompts) and one ``level``.
Each example is a snapshot of the user's Chopin PDFs (``images/chopin_passages/``, cut by ``crop.py``) or a drawing
of the app's engine (``drawn/``, made by ``easy.py`` from the brief's own examples). ``kern`` gives the notes of the
same bars in the research's kern files (first editions), for the prompts of Phase 3; its bar numbers count a pickup
bar as bar 1 in some Waltzes, so they can differ by one from the edition's bars.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
LEVELS = ["easy", "medium", "hard", "super hard"]
LABEL = {"easy": "Easy", "medium": "Medium", "hard": "Hard", "super hard": "Super hard"}
PDF = "/home/david/Documents/projects/music/chopin/"


def ex(image, piece, pdf, page, bars, kern=None, kbars=None, note=None):
    return {
        "image": image, "piece": piece, "pdf": pdf, "page": page, "bars": bars,
        "kern": kern, "kernBars": kbars, "note": note,
    }


def drawn(name, piece="From the brief, drawn by the app"):
    return {"image": f"drawn/{name}.svg", "piece": piece, "pdf": None, "page": None,
            "bars": None, "kern": None, "kernBars": None, "f1": f"drawn/{name}.f1", "note": None}


VARIATION = "A variation asked in the review of 2026-10-29, drawn by the app"


def var(level, pid, name, line):
    """A left-hand pattern drawn by the app (tools/drawn.py), on the melody shared by all the drawings."""
    return dict(hand="left", level=level, id=pid, name=name, line=line,
                examples=[drawn(f"drawn-left-{pid}", VARIATION)])


B1, B4 = "Ballade No. 1 in G minor, Op. 23", "Ballade No. 4 in F minor, Op. 52"
W = "Waltz Op. {}"
P = "Prelude Op. 28 No. {}"

PATTERNS = [
    # ---------------------------------------------------------------- left hand
    dict(hand="left", level="easy", id="held-triad", name="Held triad",
         line="The chord of the harmony (Fa-La-Do) held under the melody; the hand changes position only when the "
              "harmony changes. Easy because the hand holds one shape and does not move inside the chord.",
         examples=[drawn("drawn-left-held-triad")]),
    dict(hand="left", level="easy", id="low-note-then-chord", name="Low note, then the chord",
         line="Fa2, then Fa3-La3-Do4: one note and one chord, the same shape every time. Easy because the hand makes "
              "one jump of an octave to a triad that does not change.",
         examples=[drawn("drawn-left-low-note-then-chord")]),
    dict(hand="left", level="easy", id="triads-in-steps", name="Triads in steps",
         line="The triad slides one step up or down with the melody (Fa-La-Do, Sol-Sib-Re, La-Do-Mi). Easy because "
              "the three fingers keep one shape and the hand moves one key at a time.",
         examples=[drawn("drawn-left-triads-in-steps")]),
    dict(hand="left", level="easy", id="held-chord-repeated", name="Held chord, repeated",
         line="A small chord held as a blanca and played again with the same notes, bar after bar. Easy because the "
              "hand does not move at all.",
         examples=[ex("ballade1-left-1.png", B1, "ballades.pdf", 10, "65-67", "023-1-BH.krn", "65-67")]),
    dict(hand="left", level="medium", id="low-note-then-octave", name="Low note, then the octave",
         line="Mi2, then the octave Mi3-Mi4 on the two next beats, in a slow tempo. Medium because of the octava; "
              "the jump and the shape are the same in every bar.",
         examples=[ex("prelude-7-left-1.png", P.format(7), "preludes.pdf", 16, "1-4 (with the notes before bar 1)",
                      "028-1-BH-007.krn", "1-4")]),
    dict(hand="left", level="medium", id="low-note-then-two-chords", name="Low note, then two chords",
         line="The waltz left hand: a low note on the first beat, then the same chord on the second and third beats. "
              "Medium because the hand jumps every bar, but the chord shape stays and only the bass note changes.",
         examples=[
             ex("waltz-69-2-left-1.png", W.format("69 No. 2"), "waltzes.pdf", 79, "1-3 (with the notes before bar 1)",
                "069-1-MEIf-002.krn", "2-4", "Si2, then Fa#3-Si3-Re4 twice: the plain pattern."),
             ex("waltz-64-3-left-1.png", W.format("64 No. 3"), "waltzes.pdf", 65, "1-3", "064_3-1a-BR-003.krn",
                "1-3", "Lab2, Mib2, Lab2 under the same chord Mib3-Lab3-Do4: only the fifth finger moves."),
             ex("waltz-64-2-left-1.png", W.format("64 No. 2"), "waltzes.pdf", 59, "1-4 (with the notes before bar 1)",
                "064_2-1-BR-002.krn", "1-4", "Do#2, then Sol#3-Do#4-Mi4: the same pattern with a jump of more "
                "than an octave, the hardest form of it."),
         ]),
    dict(hand="left", level="medium", id="held-bass-under-two-chords", name="Held bass under two chords",
         line="The low note is held for the whole bar (blanca with puntillo) while two chords sound on the second "
              "and third beats. Medium because there is no jump: the hand stays over the bass and the chord.",
         examples=[ex("waltz-69-1-left-1.png", W.format("69 No. 1"), "waltzes.pdf", 71, "1-4 (with the notes before bar 1)",
                      "069-1-MEIf-001.krn", "2-5")]),
    dict(hand="left", level="medium", id="low-note-then-two-chords-in-corcheas",
         name="Low note, then two chords, in corcheas",
         line="Mib2, then two chords in beamed corcheas (Sol3-Mib4, then Sib3-Mib4-Sol4), three times in a bar. "
              "Medium because the figure repeats at every beat; the second chord only adds a note on top.",
         examples=[ex("nocturne-9-2-left-1.png", "Nocturne Op. 9 No. 2", "nocturnes.pdf", 10,
                      "1-2 (with the notes before bar 1)", "009-1-KI-002.krn", "1-2")]),
    dict(hand="left", level="medium", id="same-chord-one-note-changes", name="Same chord, one note changes",
         line="One chord repeated in corcheas (Sol3-Si3-Mi4); every bar or half bar one or two of its notes move "
              "down (Fa#3-La3-Mi4, then Fa#3-La3-Mib4, then Fa3-La3-Mib4). Medium because of the many notes, but "
              "the hand never leaves its position.",
         examples=[ex("prelude-4-left-1.png", P.format(4), "preludes.pdf", 13, "1-4", "028-1-BH-004.krn", "1-4")]),
    dict(hand="left", level="medium", id="repeated-note", name="Repeated note",
         line="Lab3 repeated in corcheas, with a low note and a small chord on the strong beats. Medium because the "
              "thumb stays on one key and the other fingers add the harmony.",
         examples=[ex("prelude-15-left-1.png", P.format(15), "preludes.pdf", 29, "1-4", "028-1-BH-015.krn",
                      "1-4")]),
    dict(hand="left", level="medium", id="octave-bass-in-negras", name="Octave bass in negras",
         line="Octavas in negras that walk down by semitones (Do, Si, Sib, La, Lab, Sol). Medium because the hand "
              "keeps the octave shape and slides; it gives a strong bass without more notes.",
         examples=[ex("prelude-20-left-1.png", P.format(20), "preludes.pdf", 45, "5-7", "028-1-BH-020.krn",
                      "5-7")]),
    dict(hand="left", level="medium", id="low-note-then-small-wave", name="Low note, then a small wave",
         line="Fa#2, then Mi#3-Sol#3-Fa#3-La#3 and back to Do#3: a low note and a short figure up and down inside "
              "one hand position, the same at every half bar. Medium because the figure never changes.",
         examples=[ex("prelude-13-left-1.png", P.format(13), "preludes.pdf", 26, "1-3", "028-1-BH-013.krn",
                      "1-3")]),
    dict(hand="left", level="medium", id="simple-line-in-negras", name="Simple line in negras",
         line="Single notes in negras: a low note, then a broken chord that climbs, with a step or two between its "
              "notes (Sib1, Sib2, Lab3, Fa3, Do4, Sib3). Medium because there are few notes and they are easy to "
              "read, although they belong to no fixed shape (the user's example of page 10).",
         examples=[ex("ballade1-left-2.png", B1, "ballades.pdf", 10, "68-71", "023-1-BH.krn", "68-71")]),
    dict(hand="left", level="hard", id="octave-then-chord-up-and-down", name="Octave, then the chord up and down",
         line="The octava Mi1-Mi2, then the chord in negras going up and coming down with the same notes. Hard "
              "because the hand jumps and changes fingers, but the way down repeats the way up (the user's example "
              "of page 12).",
         examples=[ex("ballade1-left-3.png", B1, "ballades.pdf", 12, "106-108", "023-1-BH.krn", "106-108")]),
    dict(hand="left", level="hard", id="low-note-then-moving-chord", name="Low note, then a chord that moves",
         line="Fa3, then Reb4-Mi4-Sol4 and the same shape one step lower (Sib3-Reb4-Mi4); then Fa2, Do4-Fa4-Lab4 "
              "and Lab3-Do4-Fa4. Hard because the second chord moves (the brief's hard level) and the hand crosses "
              "from the bass to the treble clef.",
         examples=[ex("ballade4-left-1.png", B4, "ballades.pdf", 41, "9-11", "052-1-BH.krn", "9-11")]),
    dict(hand="left", level="hard", id="octaves-that-draw-the-chord", name="Octaves that draw the chord",
         line="Octavas in corcheas that go through the notes of the chord (Solb, Reb, Solb, Sib, Mib, Sib) under "
              "held chords of the right hand. Hard because the hand moves on every note, but it keeps the octave "
              "shape and a regular figure.",
         examples=[ex("ballade4-left-2.png", B4, "ballades.pdf", 43, "38-40", "052-1-BH.krn", "38-40")]),
    dict(hand="left", level="hard", id="wave-in-one-position", name="Wave in one position",
         line="A low note, then semicorcheas in groups of six that go up and come down over the chord "
              "(Dob2, then Dob3-Reb3-Fa3-Reb4-Fa3-Reb3). Hard because they are fast, but each wave is symmetric and the hand "
              "stays over one place.",
         examples=[ex("ballade4-left-3.png", B4, "ballades.pdf", 52, "181-182", "052-1-BH.krn", "181-182")]),
    dict(hand="left", level="hard", id="line-of-no-chord", name="A line that belongs to no chord",
         line="A low note, then two-note chords in corcheas whose notes move apart, the lower one down by "
              "semitones and the upper one up (Mi3-Sol3, Mib3-La3, Re3-Sib3, Do3-Do4). Hard because the line fits "
              "no known chord (the brief's irregular passages), but the hand stays in one position.",
         examples=[ex("prelude-21-left-1.png", P.format(21), "preludes.pdf", 45, "1-4", "028-1-BH-021.krn",
                      "1-4")]),
    dict(hand="left", level="super hard", id="sweeps-over-two-octaves", name="Sweeps over two octaves",
         line="From Fa2 up to Lab4 in six semicorcheas, twice in each bar, then a jump back down. Super hard "
              "because the hand opens, crosses and jumps without rest while the right hand runs in groups of 7 "
              "and 8.",
         examples=[ex("ballade4-left-4.png", B4, "ballades.pdf", 50, "152-153", "052-1-BH.krn", "152-153")]),
    dict(hand="left", level="super hard", id="fast-octaves-in-stretto", name="Fast octaves in stretto",
         line="A chord, then octavas in corcheas (Dob, Sib, Do, Sib), faster and faster (stretto), under chords of "
              "four notes that jump in the right hand. Super hard because both hands play heavy shapes at speed.",
         examples=[ex("ballade4-left-5.png", B4, "ballades.pdf", 54, "198-200", "052-1-BH.krn", "198-200")]),
    # ---------------------------------------------------------------- right hand
    dict(hand="right", level="easy", id="slow-melody-single-notes", name="Slow melody in single notes",
         line="Si4 held for three beats, then Do5: the melody alone, with long notes and no chords. Easy because "
              "the hand has one note at a time and almost no movement.",
         examples=[ex("prelude-4-right-1.png", P.format(4), "preludes.pdf", 13, "1-4", "028-1-BH-004.krn", "1-4")]),
    dict(hand="right", level="easy", id="melody-single-notes", name="Melody in single notes",
         line="Fa#5-Sol5-Fa#5-Do#5-Re5-Si4 in corcheas, then La#4: one line of single notes inside one hand "
              "position. Easy because there are no chords, also when the notes are corcheas.",
         examples=[ex("waltz-69-2-right-1.png", W.format("69 No. 2"), "waltzes.pdf", 79,
                      "1-3 (with the notes before bar 1)", "069-1-MEIf-002.krn", "2-4")]),
    dict(hand="right", level="medium", id="second-note-on-long-notes", name="A second note on long notes",
         line="Single notes on the short figures, and a second note (a third, a sixth) only on the long ones; three "
              "notes only to land on a long note. Medium because the hand stays fluent and the chords come when "
              "there is time for them.",
         examples=[
             ex("waltz-64-2-right-1.png", W.format("64 No. 2"), "waltzes.pdf", 59, "1-2 (with the notes before bar 1)",
                "064_2-1-BR-002.krn", "1-2", "Sol#4-Mi5 held as a sixth, then Fa##4-Re#5."),
             ex("ballade1-right-1.png", B1, "ballades.pdf", 10, "68-71", "023-1-BH.krn", "68-71",
                "Two notes on the blancas with puntillo, single notes on the negras, three notes to land on bar "
                "70 (the user's example of page 10)."),
         ]),
    dict(hand="right", level="hard", id="melody-in-chords-one-rhythm", name="Melody in chords, one rhythm",
         line="The melody on top of three-note chords on every negra, with the same rhythm (corchea with puntillo, "
              "semicorchea, two negras) every two bars. Hard because every note is a chord, although the rhythm "
              "repeats and the tempo is slow.",
         examples=[ex("prelude-7-right-1.png", P.format(7), "preludes.pdf", 16, "1-4 (with the notes before bar 1)",
                      "028-1-BH-007.krn", "1-4")]),
    dict(hand="right", level="hard", id="melody-with-pieces-of-chords", name="Melody with small pieces of chords",
         line="The melody on top (Sib5, Lab5, Solb5) with a second voice and two-note pieces of chords under it, and "
              "a few decoration notes. Hard because the hand plays the melody and part of the harmony (the brief's "
              "example of Ballade No. 4).",
         examples=[ex("ballade4-right-1.png", B4, "ballades.pdf", 43, "50-52", "052-1-BH.krn", "50-52")]),
    dict(hand="right", level="hard", id="melody-over-inner-line", name="Melody over an inner line",
         line="The melody in negras with puntillo on the fifth finger, and a line of corcheas under it in the same "
              "hand. Hard because one hand plays two voices with different rhythms.",
         examples=[ex("waltz-42-right-1.png", W.format("42"), "waltzes.pdf", 45, "9-11", "042-1-BH.krn", "9-11")]),
    dict(hand="right", level="hard", id="thirds-and-sixths-in-corcheas", name="Thirds and sixths in corcheas",
         line="Two notes on every corchea (Fa5-Reb5, Mib5-Sol4) after a long two-note chord. Hard because the hand "
              "plays double notes fast, although it keeps the same shape.",
         examples=[ex("waltz-70-3-right-1.png", W.format("70 No. 3"), "waltzes.pdf", 99, "17-19",
                      "070-1-MEIf-003.krn", "17-19")]),
    dict(hand="right", level="super hard", id="full-chords-in-octaves", name="Full chords in octaves",
         line="Chords of four and five notes, ff, with the melody doubled at the octava and jumps up of an octave "
              "(La4-Do#5-La5, then La5-Do#6-La6). Super hard because the hand is open to its limit and jumps.",
         examples=[ex("ballade1-right-2.png", B1, "ballades.pdf", 12, "106-108", "023-1-BH.krn", "106-108")]),
    dict(hand="right", level="super hard", id="runs-in-groups", name="Runs in groups of 7 and 8",
         line="Fast runs of semicorcheas in groups of 7 and 8 that cross positions, over the left hand's sweeps. "
              "Super hard because the hand moves without rest and both hands move at once.",
         examples=[ex("ballade4-right-2.png", B4, "ballades.pdf", 50, "152-153", "052-1-BH.krn", "152-153")]),
    # ---------------------------------------------------------------- left hand, drawn variations (review 1)
    var("easy", "low-note-then-two-notes-rocking", "Low note, then two notes rocking",
        "Fa2, then La3-Do4-La3-Do4 in corcheas: one low note, then two notes of the chord one after the other. "
        "Easy because after the low note the hand stays on two keys."),
    var("easy", "alberti", "Alberti bass",
        "Fa3-Do4-La3-Do4 in corcheas, again and again: the lowest, the highest and the middle note of the triad. "
        "Easy because the hand never leaves the position of the triad."),
    var("easy", "triad-up-and-down", "Triad up and down",
        "Fa3-La3-Do4-La3 in corcheas: the three notes of the chord going up and coming down. Easy because the "
        "figure is symmetric and stays in one position."),
    var("easy", "triad-up-and-hold", "Triad up, then held",
        "Fa3 and La3 in corcheas, then Do4 as a negra: the triad goes up and stops on its top note. Easy because "
        "three fingers stay on three keys."),
    var("easy", "triad-down-and-hold", "Triad down, then held",
        "Do4 and La3 in corcheas, then Fa3 as a negra: the same figure going down. Easy for the same reason as "
        "going up."),
    var("easy", "chord-then-two-notes-above", "Chord, then two notes above",
        "Fa3-La3-Do4, then Do4-Fa4: the chord, then two of its notes in a higher position, again and again. Easy "
        "because the hand moves a little and comes back, always with the same two shapes."),
    var("easy", "held-two-note-chord", "Held two-note chord",
        "The fifth Fa3-Do4 held as blancas (Do3-Sol3 and Sib2-Fa3 for the other chords). Easy because two notes "
        "are enough to give the harmony and the hand holds one shape."),
    var("easy", "low-note-then-two-note-chords", "Low note, then two-note chords",
        "Fa2, then La3-Do4 three times in negras. Easy because the chord has only two notes and its shape never "
        "changes."),
    var("easy", "two-note-chord-then-arpeggio", "Two-note chord, then an arpeggio",
        "Fa3-Do4 together, then Fa3-La3-Do4-La3-Fa3-La3 in corcheas. Easy because the arpeggio uses the same "
        "position as the two-note chord."),
    var("easy", "fifth-to-sixth-rocking", "Fifth to sixth, rocking",
        "Fa3-Do4, then Fa3-Re4, in negras: the upper note moves one key and back while the lower note stays. "
        "Easy because only one finger moves."),
    var("medium", "octave-then-arpeggio", "Octava, then an arpeggio",
        "Fa2-Fa3 together, then Fa3-La3-Do4-La3-Fa3-La3 in corcheas. Medium because of the octava and the jump "
        "to the arpeggio; the arpeggio itself stays in one position."),
    var("medium", "low-note-then-off-beat-chords", "Low note, then chords off the beat",
        "Fa2 on the beat, then the triad on the half beats (corcheas), with blank space between them. Medium "
        "because of the rhythm: the chord sounds between the beats."),
    var("medium", "added-sixth-up-and-down", "Added sixth, up and down",
        "Fa3-La3-Do4-Re4 and back in corcheas: the triad with its sixth (Re), a new note of the chord. Medium "
        "because the hand uses four fingers, still in one position."),
    var("medium", "held-bass-under-rocking-notes", "Held bass under rocking notes",
        "Fa3 held for the whole bar while La3-Do4 rock above it in corcheas. Medium because one hand plays two "
        "voices: one finger holds and the others move."),
    var("medium", "triad-in-semicorcheas", "Triad in semicorcheas",
        "Fa3-La3-Do4-La3 in semicorcheas at every beat. Medium because the notes are fast, although the figure "
        "and the position never change."),
    var("medium", "octave-then-two-beamed-chords", "Octava, then two beamed chords",
        "Fa2-Fa3, then the triad twice in beamed corcheas, twice in each bar (the brief's example of an octava "
        "and two corcheas of the chord). Medium because of the jump between the octava and the chord."),
    var("medium", "alternating-bass-and-chord", "Alternating bass and chord",
        "Fa2, the triad, Do3, the triad, in negras: the bass changes between the root and the fifth of the chord. "
        "Medium because the bass note moves every two beats."),
    var("medium", "arpeggio-three-three-two", "Arpeggio in 3 + 3 + 2",
        "The triad in corcheas grouped 3 + 3 + 2 (Fa3-La3-Do4, Fa3-La3-Do4, Fa3-La3), a common rhythm in pop "
        "songs. Medium because the groups do not follow the beat, although the notes stay in one position."),
    var("medium", "octave-rocking", "Octavas rocking",
        "Fa2, Fa3, Fa2, Fa3 in corcheas: the octava played as two notes, one after the other. Medium because the "
        "hand stays open on the octava for the whole bar."),
    var("medium", "chord-then-arpeggio-down", "Chord, then an arpeggio down",
        "The triad, then Fa4-Do4-La3-Fa3-La3-Do4 in corcheas: down from the top and back. Medium because the "
        "arpeggio covers an octava, one note more than the triad."),
    var("hard", "four-note-arpeggio-up-and-down", "Four-note arpeggio up and down",
        "Fa3-La3-Do4-Fa4 and back in corcheas: the triad with its octava as a fourth note. Hard because the hand "
        "is open on the octava and uses all five fingers."),
    var("hard", "low-note-then-four-note-chords", "Low note, then four-note chords",
        "Fa2, then Fa3-La3-Do4-Fa4 three times in negras. Hard because the chord fills the octava and the hand "
        "jumps to it."),
    var("hard", "open-arpeggio-up-and-down", "Open arpeggio up and down",
        "Fa2-Do3-Fa3-La3-Do4 and back in corcheas: the root, the fifth, the octava and the tenth. Hard because "
        "the arpeggio covers more than an octava and the hand must move inside it."),
    var("hard", "alberti-over-an-octave", "Alberti over an octava",
        "Fa3-Fa4-Do4-Fa4, La3-Fa4-Do4-Fa4: the Alberti figure with the octava on top. Hard because the hand stays "
        "open on the octava while the lower fingers change."),
    var("hard", "four-note-wave-in-semicorcheas", "Four-note wave in semicorcheas",
        "Fa2, then Fa3-La3-Do4-Fa4 up and down in semicorcheas. Hard because the wave is fast and covers an "
        "octava; it is symmetric, so the fingers repeat."),
    var("hard", "low-note-then-chord-moving-up", "Octava, then a chord that moves up",
        "Fa2-Fa3, then Fa3-La3-Do4 and La3-Do4-Fa4 in corcheas: the second chord is the same chord one position "
        "higher (the brief's La4-Do5-Mi5, then Do5-Mi5-La5). Hard because the hand moves between the two chords."),
    var("hard", "octave-then-four-note-chords", "Octava, then four-note chords",
        "Fa2-Fa3, then Fa3-La3-Do4-Fa4 six times in corcheas. Hard because the hand jumps and then repeats a full "
        "chord fast."),
    var("hard", "held-bass-under-moving-thirds", "Held bass under moving thirds",
        "Fa3 held, with La3-Do4 and Sib3-Re4 moving above it in corcheas. Hard because one hand plays two voices "
        "and the upper voice moves two fingers at a time."),
    var("hard", "off-beat-four-note-chords", "Four-note chords off the beat",
        "Fa2-Fa3 on the beat, then Fa3-La3-Do4-Fa4 on the half beats. Hard because of the jump, the full chord "
        "and the rhythm between the beats."),
    var("hard", "arpeggio-up-then-chord", "Arpeggio up, then the chord",
        "Fa3-La3-Do4-Fa4 in corcheas, then the four notes together as a blanca. Hard because the hand covers the "
        "octava twice, first note by note and then all at once."),
]

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gallery of patterns</title>
<style>
:root { color-scheme: only light; --ink: #1d1d1f; --soft: #5f6368; --line: #e3e3e6; --chip: #f2f2f4; }
body { margin: 0; background: #fff; color: var(--ink); font: 15px/1.5 system-ui, -apple-system, sans-serif; }
main { max-width: 1200px; margin: 0 auto; padding: 24px 16px 80px; }
h1 { font-size: 22px; margin: 0 0 4px; } .lead { color: var(--soft); margin: 0 0 18px; max-width: 900px; }
.tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--line); margin-bottom: 14px; }
.tabs button { border: 0; background: none; font: inherit; padding: 8px 14px; cursor: pointer; color: var(--soft);
  border-bottom: 2px solid transparent; margin-bottom: -1px; }
.tabs button.on { color: var(--ink); border-bottom-color: var(--ink); font-weight: 600; }
.pills { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 18px; }
.pills button { border: 1px solid var(--line); background: #fff; border-radius: 999px; padding: 4px 12px;
  font: inherit; font-size: 13px; cursor: pointer; color: var(--soft); }
.pills button.on { background: var(--ink); color: #fff; border-color: var(--ink); }
.card { border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; margin-bottom: 16px; }
.card h2 { font-size: 17px; margin: 0; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.level { font-size: 12px; font-weight: 600; border-radius: 999px; padding: 1px 9px; }
.easy { background: #e5f4ea; color: #1e6b3a; } .medium { background: #e6eefc; color: #1f4fa3; }
.hard { background: #fdf0dc; color: #8a5300; } .super-hard { background: #fbe4e4; color: #9b1c1c; }
.id { font: 12px ui-monospace, monospace; color: var(--soft); }
.line { margin: 6px 0 10px; max-width: 980px; }
figure { margin: 10px 0 4px; } figcaption { font-size: 13px; color: var(--soft); margin-bottom: 4px; }
figure img { display: block; max-width: 100%; height: auto; border: 1px solid var(--line); border-radius: 6px; }
.drawn img { max-width: 720px; width: 100%; }
.none { color: var(--soft); }
</style></head><body><main>
<h1>Gallery of patterns</h1>
<p class="lead">Implementation 04-3, Phase 2: the patterns of each hand for the levels of the Whole Song
simplification, found in Chopin (snapshots of your PDFs) or drawn by the app (the easy patterns of the brief, and
the variations of easy, medium and hard asked in your review). The drawn patterns share one melody in Fa major (two bars of Fa, one of Do, then Sib and Do), so that only
the left hand changes from one to the next. In each snapshot the other hand is grey. The names are the ones the level
prompts of Phase 3 will use.</p>
<div class="tabs">__TABS__</div>
<div class="pills">__PILLS__</div>
__CARDS__
<p class="none" id="none" hidden>No pattern at this level in this tab.</p>
</main>
<script>
const state = { hand: 'left', level: 'all' };
function read() {
  const h = new URLSearchParams(location.hash.slice(1));
  state.hand = h.get('hand') || 'left'; state.level = h.get('level') || 'all';
}
function show() {
  document.querySelectorAll('.tabs button').forEach(b => b.classList.toggle('on', b.dataset.hand === state.hand));
  document.querySelectorAll('.pills button').forEach(b => {
    b.classList.toggle('on', b.dataset.level === state.level);
    b.querySelector('span').textContent = document.querySelectorAll(
      `.card[data-hand="${state.hand}"]` + (b.dataset.level === 'all' ? '' : `[data-level="${b.dataset.level}"]`)).length;
  });
  let n = 0;
  document.querySelectorAll('.card').forEach(c => {
    const on = c.dataset.hand === state.hand && (state.level === 'all' || c.dataset.level === state.level);
    c.hidden = !on; if (on) n++;
  });
  document.getElementById('none').hidden = n > 0;
}
function go(k, v) { state[k] = v; location.hash = `hand=${state.hand}&level=${state.level}`; show(); }
document.querySelectorAll('.tabs button').forEach(b => b.onclick = () => go('hand', b.dataset.hand));
document.querySelectorAll('.pills button').forEach(b => b.onclick = () => go('level', b.dataset.level));
window.onhashchange = () => { read(); show(); };
read(); show();
</script></body></html>
"""


def card(p: dict) -> str:
    figs = []
    for e in p["examples"]:
        if e["pdf"]:
            src = f"../../images/chopin_passages/{e['image']}"
            cap = f"{e['piece']}, {e['pdf']} page {e['page']}, bars {e['bars']}"
            cls = ""
        else:
            src, cap, cls = e["image"], e["piece"], ' class="drawn"'
        if e.get("note"):
            cap += f". {e['note']}"
        alt = f"{p['name']}: {e['piece']}"
        figs.append(f'<figure{cls}><figcaption>{html.escape(cap)}</figcaption>'
                    f'<a href="{src}"><img src="{src}" alt="{html.escape(alt)}" loading="lazy"></a></figure>')
    lv = p["level"].replace(" ", "-")
    return (f'<section class="card" data-hand="{p["hand"]}" data-level="{p["level"]}">'
            f'<h2>{html.escape(p["name"])} <span class="level {lv}">{LABEL[p["level"]]}</span>'
            f'<span class="id">{p["id"]}</span></h2><p class="line">{html.escape(p["line"])}</p>'
            + "".join(figs) + "</section>")


def main() -> None:
    ids = [p["id"] for p in PATTERNS]
    assert len(ids) == len(set(ids)), "one pattern, one name"
    for p in PATTERNS:
        for e in p["examples"]:
            path = (HERE / e["image"]) if not e["pdf"] else (HERE.parent.parent / "images/chopin_passages" / e["image"])
            assert path.exists(), path
    order = {lv: i for i, lv in enumerate(LEVELS)}
    pats = sorted(PATTERNS, key=lambda p: (p["hand"] != "right", order[p["level"]]))
    tabs = ('<button data-hand="right">Right hand</button>'
            '<button data-hand="left">Left hand</button>')
    pills = '<button data-level="all">All <span></span></button>' + "".join(
        f'<button data-level="{lv}">{LABEL[lv]} <span></span></button>' for lv in LEVELS)
    page = PAGE.replace("__TABS__", tabs).replace("__PILLS__", pills).replace(
        "__CARDS__", "\n".join(card(p) for p in pats))
    (HERE / "index.html").write_text(page)
    out = {
        "about": "Implementation 04-3, Phase 2: the gallery of patterns. One pattern, one name: Phase 3 uses these "
                 "ids and levels in the level prompts. Images are relative to this folder (drawn/) or to "
                 "context/implementations/04-app-enhancements/images/chopin_passages/. pdf pages are pages of the "
                 f"user's PDFs in {PDF} (outside the repo). kern files are in poc-aitu-research/data/raw/kern/"
                 "humdrum-chopin-first-editions/kern/.",
        "status": "proposed, waiting for the user's review",
        "levels": LEVELS,
        "patterns": pats,
    }
    (HERE / "patterns.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(len(pats), "patterns:", {h: sum(p["hand"] == h for p in pats) for h in ("left", "right")})


if __name__ == "__main__":
    main()
