# Transcription quality: what goes wrong between audio and a printed figure

How a note travels from a recording to a symbol on the page, and the four distinct
places that journey can produce something the player never played. Written 2026-08-02
after a session that measured all four on the same file.

Detail and exact parameters: [documentation/services/backend/transcription-pipeline.md](../../documentation/services/backend/transcription-pipeline.md).
Diagnosing a specific bad passage: [documentation/issues/rhythm-figures-and-tempo.md](../../documentation/issues/rhythm-figures-and-tempo.md).

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
| 4 | The grid | Printing an evenly played run as ragged figures |

The **Notes Falling (raw)** tab exists to separate layer 1 from the rest: it draws
`events.json` directly, in seconds, with no grid anywhere. If a passage looks even there
and ragged on the score, the engine is not the problem.

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

## 4. The grid, and the arithmetic that has no way out

This is the subtlest of the four and the one that looks most like a bug when it is not.

A run of notes 106.7 ms apart, on a grid whose columns are 84.27 ms, is **1.27 columns per
note**. An onset can only land on a whole column. Twelve such gaps are 15.2 columns of real
time, so twelve gaps have to be written as nine 1s and three 2s — nine semicorcheas and
three corcheas — and there is no other way to do it. Nobody decided the corcheas; they are
the change left over.

Two things follow, and both are implemented:

- **Runs are quantised as runs, per hand** — one integer span for the whole stretch instead
  of rounding each onset alone. Within a hand, because a left hand holding a redonda has two
  onsets while the right plays twenty-five, and mixed together they are not a run at all.
- **A run that does not fit is refused, not forced.** Forcing 1.27 into 1 ends the passage a
  quarter short and dumps the difference as a rest in the middle of the phrase, which is
  worse notation than the ragged figures it replaced. So it is left as played and the tempo
  it is *asking for* is reported instead.

That report is the useful part. A run of 21 notes all 1.27 columns long is not ambiguous
data — it is a measurement saying the tempo is 27 % out.

---

## The tempo is not one number

The refusals on the reference file cluster at ~139 BPM against a stated 178, and a grid fit
to the attacks either side of 218 s gives 133.5 before and 127.9 after. The piece genuinely
changes tempo.

Worse, one half mixes **sixteenths (107 ms) and eighth-note triplets (143 ms)** — at 140 BPM
those are 107.2 ms and 142.9 ms, which fits. A binary grid can print the first and cannot
print the second at any tempo. So there are two separate outstanding problems:

| Problem | Fix | Status |
|---|---|---|
| The piece changes tempo | Per-region tempo, re-quantised from `events.json` | Clock built and tested; not yet wired |
| Some passages are tuplets | Triplet subdivision in `Granularity` | Not started |

Do not conflate them. Per-region tempo will fix the sixteenths completely and will not touch
the triplets.

---

## Where to look deeper

- [documentation/services/backend/transcription-pipeline.md](../../documentation/services/backend/transcription-pipeline.md) — modules, order, parameters, endpoints
- [documentation/issues/rhythm-figures-and-tempo.md](../../documentation/issues/rhythm-figures-and-tempo.md) — the diagnostic recipe for a bad passage
- [notation-logic/01-matrix-notation-logic.md](notation-logic/01-matrix-notation-logic.md) — Appendices B (sustains) and C (duration approximation)
- [../research/piano-transcription/piano-transcription-python-solutions.md](../research/piano-transcription/piano-transcription-python-solutions.md) — the engine survey
