# Transcription quality: what goes wrong between audio and a printed figure

How a note travels from a recording to a symbol on the page, and the four distinct places that
journey can produce something the player never played. Written 2026-08-02 after a session that
measured all four on the same file; **layers 1 to 3 are unchanged and layer 4 was removed by the
wall-clock model** — §4 below says what took its place.

Detail and exact parameters: [documentation/services/backend/transcription-pipeline.md](../../documentation/services/backend/transcription-pipeline.md).
Diagnosing a specific bad passage:
[documentation/issues/piano-matrix-sustains-and-phantom-onsets.md](../../documentation/issues/piano-matrix-sustains-and-phantom-onsets.md).

---

## The one idea to hold on to

**`events.json` is the transcription. The matrix is an opinion about it.**

The engine emits notes in seconds. Everything after that — which column a note lands in,
which hand plays it, whether it prints as a corchea or a semicorchea — is a decision this
codebase makes, and every one of those decisions can be wrong independently of the model
being right. When a passage looks wrong, the first question is always *which of the four
layers produced it*, because they need completely different fixes.

The four layers, in the order they run:

| # | Layer | Gets it wrong by |
|---|-------|------------------|
| 1 | The engine | Missing a note, or inventing one |
| 2 | The artifact filter | Keeping something that is not a note |
| 3 | The hand split | Giving a note to the wrong hand |
| 4 | ~~The grid~~ | **Removed.** It printed an evenly played run as ragged figures; see §4 |

**Piano Roll** and **Notes Falling** exist to separate layer 1 from the rest: both draw
`events.json` directly, in seconds, with no grid anywhere, and both can show the notes the artifact
filter discarded, dashed. If a passage looks even there and ragged on the score, the engine is not
the problem.

---

## 1. The engine, and the octave it cannot hear

Transcribing an octave is the hardest thing a piano model does. Every partial of the upper
note lands on an even partial of the lower one, so the upper note adds almost no new
spectral evidence and the model has to infer it from the attack transient alone. It fails
in **both** directions: sometimes it misses the upper note, sometimes it invents one an
octave *below* the real bass.

Both were observed on the same file. ByteDance emitted `D#2` alone where the recording has
a `D#2`/`D#3` octave; Transkun, on the same audio, got both. Elsewhere ByteDance invented
46 phantom `F1` notes under a played `F2`/`F3`.

No threshold fixes this — there is no extra evidence to threshold. It is a property of the
model, which is why more than one engine is registered
([transkun-engine notes](../../documentation/services/backend/transcription-pipeline.md#engines)).

## 2. The artifact filter, and why 20 ms

The invented notes give themselves away by their length. Durations on the reference file
are cleanly **bimodal with an empty band**: 78 events between 4 and 16 ms, *nothing at all*
between 16 and 32 ms, then 2673 real notes from 32 ms up. A hammer needs tens of
milliseconds to produce a tone anyone can place.

So notes under **20 ms** that coincide with another attack are dropped before anything else
runs. The coincidence condition names the mechanism: the artifact is created *by* a struck
chord, so a short note alone in silence is something else and is kept.

**The floor must stay low.** ByteDance offsets follow the pedal, so its notes are long and a
40 ms floor looks free. Transkun reports true key release and returns 34–85 ms notes for
the same music — a 40 ms floor would delete a third of a Transkun transcription.

## 3. The hand split, and why one phantom wrecks it

A played `F2`/`F3` octave with a phantom `F1` under it spans two octaves. No hand holds
that, so the beam is *forced* to give `F3` to the right hand, and from there the whole
assignment unravels. Measured over one passage:

```
before the artifact filter:  LEFT F1: 19   LEFT F2: 24   RIGHT F3: 20   LEFT F3: 3
after:                                     LEFT F2: 24   LEFT F3: 23
```

This is the reason the artifact filter runs **first**. It is not tidying; it is removing an
impossible constraint before the optimiser is asked to satisfy it.

The split then runs on the **raw semifusa grid**, not the collapsed one, because two attacks
closer together than one display column merge into a single column when collapsed and the
splitter sees a chord where the player struck twice.

### ...and why the page has a vote (2026-08-08)

The split also decides which *staff* a note is drawn on — right on the treble, left on the
bass — so it is a typesetting decision as much as an ergonomic one. Seventeen of the
eighteen cost terms ask only what the hands can do, and two assignments that were equally
comfortable were indistinguishable even when one printed four more ledger lines than the
other. On *Mr Blue Sky* at f1041 that produced the left hand six ledger lines above the bass
staff and the right hand six below the treble, for three onsets, before the two swapped back.

`C_ledger` charges those lines, **by direction**: running outward is register and is free to
six lines (the bottom octave of the piano lives six lines under the bass staff), while
running *across* — the left above the bass staff, the right below the treble — is free only
to two. La-0 and Fa-5 are both six lines off the bass staff and only one of them is a
mistake, which is why a single distance threshold cannot express this.

It is a cost, not a veto: a crossing the hands are genuinely committed to still happens, and
prints with its ledger lines. On the reference file the term agrees with 6 of the 14 hand
corrections the reader had made by hand; the other 8 are a pedalled chord the model reads as
seven keys physically held down, which is the pedal limitation, not a tuning problem.

Runbook, including the search bug found alongside it:
[documentation/issues/hand-split-ledger-lines.md](../../documentation/issues/hand-split-ledger-lines.md).

## 4. The grid — the layer that was removed

This was the subtlest of the four and the one that looked most like a bug when it was not. It is
recorded here because the reasoning is what produced the wall-clock model, and because a reader who
finds an old note about "ragged figures" should be able to find out what happened to it.

**The arithmetic had no way out.** A run of notes 106.7 ms apart, on a grid whose columns were
84.27 ms, is **1.27 columns per note**. An onset can only land on a whole column. Twelve such gaps
are 15.2 columns of real time, so twelve gaps had to be written as nine 1s and three 2s — nine
semicorcheas and three corcheas — and there was no other way to do it. Nobody decided the corcheas;
they were the change left over.

Two mitigations were built and both are gone with the layer: quantising runs as runs per hand, and
refusing a run that did not fit rather than forcing it.

**The measurement that ended the layer.** The refusals on the reference file clustered at about
139 BPM against a stated 178, and a grid fitted to the attacks either side of 218 s gave 133.5
before and 127.9 after. The piece genuinely changed tempo. Worse, one half mixed sixteenths (107 ms)
and eighth-note triplets (143 ms): at 140 BPM those are 107.2 ms and 142.9 ms, which fits, and **a
binary grid can print the first and cannot print the second at any tempo**.

At that point the conclusion was not "fit a better grid". It was that a grid built from a typed
tempo cannot express playing, and the position of a note should not be derived from its rhythmic
value at all.

### What replaced it

Position is measured wall-clock time — a column is a fixed 40 ms — and the figure is a name the
reader chooses from the distribution of gaps in their own playing. The whole class of "played
evenly, printed ragged" error is retired, and the two problems this section left open were answered
rather than fixed:

| The old problem | What answers it now |
|---|---|
| The piece changes tempo | Passages: mark a stretch, say what a gap is worth from there on. Nothing outside it moves |
| Some passages are tuplets | Tresillos are detected on the raw gaps and marked with a bracket, not rounded |

Full reasoning in [`../backend/time-model.md`](../backend/time-model.md); the derivation path in
[`documentation/services/backend/events-to-sheet.md`](../../documentation/services/backend/events-to-sheet.md).

---

## Where to look deeper

- [documentation/services/backend/transcription-pipeline.md](../../documentation/services/backend/transcription-pipeline.md) — modules, order, parameters, endpoints
- [documentation/issues/rhythm-figures-and-tempo.md](../../documentation/issues/rhythm-figures-and-tempo.md) — **retired.** The bug class layer 4 produced, kept as the record of it
- [`../backend/time-model.md`](../backend/time-model.md) — the model that replaced layer 4
- [archive/superseded/01-matrix-notation-logic.md](../archive/superseded/01-matrix-notation-logic.md) — Appendix B (sustains), still in force; the rest is history
- [../research/piano-transcription/piano-transcription-python-solutions.md](../research/piano-transcription/piano-transcription-python-solutions.md) — the engine survey
