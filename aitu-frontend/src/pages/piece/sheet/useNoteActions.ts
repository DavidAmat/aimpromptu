/**
 * What the note toolbox knows about the picked notes, and every action it offers on them.
 *
 * Split out of `RhythmPage.tsx` (implementation 02, Phase 2): the derived values
 * and the actions are the page's own, now read from the edits they act on.
 */

import { useCallback, useMemo } from "react";
import type { Dispatch, SetStateAction } from "react";
import type { GraceNote, FigureName, TimeScorePayload } from "../../../api";
import {
  keySignatureAtFrame,
  MAX_EVEN_SPACING_SCALE,
  MIN_EVEN_SPACING_SCALE,
  pitchToStaffPosition,
  type FingerNumber,
  type KeySignature,
} from "@aimpromptu/grid-notation";
import { spanishNoteName } from "../../../music/noteNames";
import {
  frameOf,
  groupKeyOf,
  handOf,
  noteRefOf,
  rowOf,
} from "../../../music/renderOverrides";
import type { EditHistory } from "../../../hooks/useEditHistory";
import { BEAMABLE_FIGURES } from "./sheetConstants";
import type { SheetEdits } from "./sheetEdits";

export interface FingerDraft {
  forSelection: string;
  picked: FingerNumber[];
}

export function useNoteActions({
  score,
  selectedNotes,
  chords,
  state,
  set,
  fingerDraft,
  setFingerDraft,
  closeNotes,
}: {
  score: TimeScorePayload | null;
  selectedNotes: readonly string[];
  chords: ReadonlyMap<string, number[]>;
  state: SheetEdits;
  set: EditHistory<SheetEdits>["set"];
  fingerDraft: FingerDraft | null;
  setFingerDraft: Dispatch<SetStateAction<FingerDraft | null>>;
  closeNotes: () => void;
}) {
  const {
    keySignature,
    keyChanges,
    evenSpacings,
    cueRanges,
    overrides,
    beamBreaks,
    beamJoins,
    graceNotes,
  } = state;
  const {
    trills: setTrills,
    cueRanges: setCueRanges,
    evenSpacings: setEvenSpacings,
    fingers: setFingers,
    overrides: setOverrides,
    beamBreaks: setBeamBreaks,
    beamJoins: setBeamJoins,
    hiddenNotes: setHiddenNotes,
    graceNotes: setGraceNotes,
  } = set;

  /** The selection, gathered the same way, so the two can be compared chord by chord. */
  const selectedChords = useMemo(() => {
    const byGroup = new Map<string, Set<number>>();
    for (const noteKey of selectedNotes) {
      const key = groupKeyOf(noteKey);
      const rows = byGroup.get(key);
      if (rows) rows.add(rowOf(noteKey));
      else byGroup.set(key, new Set([rowOf(noteKey)]));
    }
    const whole: string[] = [];
    const partial: string[] = [];
    for (const [key, rows] of byGroup) {
      const all = chords.get(key) ?? [];
      if (all.length > 0 && all.every((row) => rows.has(row))) whole.push(key);
      else partial.push(key);
    }
    return { whole, partial };
  }, [selectedNotes, chords]);

  /** The whole selection is one chord, which is when several finger numbers make sense at once. */
  const oneChord = useMemo(() => {
    if (selectedNotes.length < 2) return null;
    const groups = new Set(selectedNotes.map(groupKeyOf));
    if (groups.size !== 1) return null;
    return [...selectedNotes].sort((left, right) => rowOf(left) - rowOf(right));
  }, [selectedNotes]);

  /**
   * The chords the selection touches, what they are all drawn as, and how to say otherwise.
   *
   * A figure belongs to a chord and never to one notehead — notes struck together are written as
   * one thing — so picking any note of a chord names the whole of it, which is what the single-note
   * panel always did. What a band adds is doing it to every chord at once: a passage written as a
   * mix of corcheas, semicorcheas and tresillos becomes one figure without a column moving. That is
   * safe here in a way it would not be on a bar-counted page, because a column is a slice of wall
   * clock and a figure is a label on a note rather than its length (D-18).
   *
   * `selectedPrintedFigure` below is empty when the chords picked disagree, so the row of pills
   * offers a name instead of claiming one of them is already the answer.
   */
  const selectedGroups = useMemo(
    () => [...new Set(selectedNotes.map(groupKeyOf))],
    [selectedNotes],
  );

  /**
   * What each chord on the page is actually drawn as: the reader's name where there is one, and the
   * score's otherwise.
   *
   * `namedGroups` below answers a narrower question — which chords the reader has renamed — and
   * that is the right question for the undo. It is the wrong one for a row of figure pills, which
   * has to show what is on the page whether anybody named it or not.
   */
  const printedFigures = useMemo(() => {
    const byGroup = new Map<string, FigureName>();
    for (const note of score?.notes ?? []) {
      const groupKey = `${note.hand}:${note.startFrame}`;
      if (!byGroup.has(groupKey)) byGroup.set(groupKey, note.figure);
    }
    for (const [groupKey, name] of Object.entries(overrides)) {
      byGroup.set(groupKey, name);
    }
    return byGroup;
  }, [score, overrides]);

  /** The one figure every picked chord prints as, or empty when they disagree. */
  const selectedPrintedFigure = useMemo<FigureName | "">(() => {
    const drawn = selectedGroups.map((groupKey) => printedFigures.get(groupKey));
    const first = drawn[0];
    if (!first) return "";
    return drawn.every((one) => one === first) ? first : "";
  }, [selectedGroups, printedFigures]);

  /**
   * Whether these notes could share one beam at all.
   *
   * Three conditions, and every one of them is a thing that cannot be drawn rather than a rule of
   * taste: a beam holds whole chords, it needs at least two of them, and every one has to print a
   * figure that carries flags — a negra has no beam to share. The button is disabled rather than
   * hidden so the tooltip can say which of the three is missing.
   */
  const beamable = useMemo(() => {
    if (selectedChords.partial.length > 0 || selectedChords.whole.length < 2) return false;
    return selectedChords.whole.every((groupKey) => {
      const name = printedFigures.get(groupKey);
      return name !== undefined && BEAMABLE_FIGURES.has(name);
    });
  }, [selectedChords, printedFigures]);

  const joinedHere =
    selectedChords.whole.length > 0 &&
    selectedChords.whole.every((groupKey) => beamJoins.has(groupKey));
  const brokenHere =
    selectedChords.whole.length > 0 &&
    selectedChords.whole.every((groupKey) => beamBreaks.has(groupKey));

  /**
   * The run of columns the picked notes cover, on the one hand they are all on.
   *
   * `null` when the selection spans both hands or holds fewer than two onsets — neither of which is
   * a run that can be set evenly. A run needs two notes to have a distance between them.
   */
  const selectedRun = useMemo(() => {
    if (selectedNotes.length === 0) return null;
    const sides = new Set(selectedNotes.map(handOf));
    if (sides.size !== 1) return null;
    const columns = [...new Set(selectedNotes.map(frameOf))].sort((a, z) => a - z);
    if (columns.length < 2) return null;
    return {
      hand: [...sides][0]!,
      fromColumn: columns[0]!,
      toColumn: columns[columns.length - 1]! + 1,
    };
  }, [selectedNotes]);

  /** The even spacing already on this run, if the reader has asked for one. */
  const evenHere = useMemo(() => {
    if (!selectedRun) return null;
    return (
      evenSpacings.find(
        (run) =>
          run.hand === selectedRun.hand &&
          run.fromColumn === selectedRun.fromColumn &&
          run.toColumn === selectedRun.toColumn,
      ) ?? null
    );
  }, [selectedRun, evenSpacings]);

  /**
   * Set the picked run an equal distance apart, or put it back the way the page measured it.
   *
   * The scale starts at one, which is the **tightest even spacing the run allows** — every gap
   * opened out to the widest gap it already had. Nothing is ever closed up, because a gap is the
   * sum of its columns' own widths and a column cannot be narrower than the ink in it.
   */
  const toggleEvenSpacing = useCallback(() => {
    if (!selectedRun) return;
    setEvenSpacings((current) => {
      const kept = current.filter(
        (run) =>
          !(
            run.hand === selectedRun.hand &&
            run.fromColumn === selectedRun.fromColumn &&
            run.toColumn === selectedRun.toColumn
          ),
      );
      return kept.length < current.length ? kept : [...kept, { ...selectedRun, scale: 1 }];
    });
  }, [selectedRun, setEvenSpacings]);

  /**
   * Open the picked run further, or close it up.
   *
   * Only reachable once the run has been made even, which is why the two buttons are disabled until
   * then: there is nothing for them to be a multiple of until a run has one distance rather than
   * several.
   *
   * **It closes below one.** One is the widest gap the run already had, and that gap is usually
   * wide because of the *other* hand — a four-note chord with accidentals under one of these
   * notes — so evening a run to it makes the whole run as wide as its worst moment. A reader
   * looking at their own hand's notes with room to spare is right about that, and a control that
   * refuses them over a collision they can see has not happened is second-guessing what is in front
   * of them. Below one the glyphs may touch. That is visible, it is reversible, and it is theirs.
   */
  const nudgeEvenSpacing = useCallback(
    (by: number) => {
      if (!selectedRun) return;
      setEvenSpacings((current) =>
        current.map((run) =>
          run.hand === selectedRun.hand &&
          run.fromColumn === selectedRun.fromColumn &&
          run.toColumn === selectedRun.toColumn
            ? {
                ...run,
                scale:
                  Math.round(
                    Math.min(
                      MAX_EVEN_SPACING_SCALE,
                      Math.max(MIN_EVEN_SPACING_SCALE, run.scale + by),
                    ) * 100,
                  ) / 100,
              }
            : run,
        ),
      );
    },
    [selectedRun, setEvenSpacings],
  );

  /** Whether the picked notes are already inside a stretch printed small. */
  const cueHere = useMemo(() => {
    if (selectedNotes.length === 0) return false;
    const sides = new Set(selectedNotes.map(handOf));
    const side = sides.size === 1 ? [...sides][0]! : "single";
    const columns = selectedNotes.map(frameOf);
    const fromColumn = Math.min(...columns);
    const toColumn = Math.max(...columns) + 1;
    return cueRanges.some(
      (cue) => cue.hand === side && cue.fromColumn <= fromColumn && cue.toColumn >= toColumn,
    );
  }, [selectedNotes, cueRanges]);

  /**
   * Whether these notes could be one shake.
   *
   * One hand, and three onsets or more. That is the whole test, and it is deliberately looser than
   * the rule behind **Find trills**: an ornament the automatic rule was too strict for is exactly
   * the case a reader has to be able to overrule, and they are looking at the notes.
   */
  const trillable = useMemo(() => {
    if (selectedNotes.length < 3) return false;
    if (new Set(selectedNotes.map(handOf)).size !== 1) return false;
    return new Set(selectedNotes.map(frameOf)).size >= 3;
  }, [selectedNotes]);

  /** The chords in the selection that carry a name already, which is what the undo is about. */
  const namedGroups = useMemo(
    () => selectedGroups.filter((groupKey) => overrides[groupKey] !== undefined),
    [selectedGroups, overrides],
  );

  const drawSelectionAs = useCallback(
    (name: FigureName) => {
      setOverrides((current) => {
        const next = { ...current };
        for (const groupKey of selectedGroups) next[groupKey] = name;
        return next;
      });
    },
    [selectedGroups, setOverrides],
  );

  /** Back to whatever the score called them. */
  const unnameSelection = useCallback(() => {
    setOverrides((current) => {
      const next = { ...current };
      for (const groupKey of selectedGroups) delete next[groupKey];
      return next;
    });
  }, [selectedGroups, setOverrides]);

  const selectionKey = selectedNotes.join("|");
  // Numbers only belong to the selection they were pressed for. Carried with that selection rather
  // than cleared by an effect, so picking a different chord offers a clean row of chips without a
  // render in between showing the last chord's answer.
  const pickedFingers = useMemo<FingerNumber[]>(
    () =>
      fingerDraft?.forSelection === selectionKey ? fingerDraft.picked : [],
    [fingerDraft, selectionKey],
  );

  /**
   * The one note picked, or `null` when none or several are.
   *
   * A grace note leans on exactly one note. Offering it for a chord would have to answer which
   * notehead it hangs off, and the honest answer is that the reader has to say.
   */
  const onlyNote = selectedNotes.length === 1 ? selectedNotes[0]! : null;
  const graceHere = onlyNote
    ? (graceNotes.find(
        (one) =>
          one.hand === handOf(onlyNote) &&
          one.startFrame === frameOf(onlyNote) &&
          one.targetRow === rowOf(onlyNote),
      ) ?? null)
    : null;

  /**
   * Put a decoration note of a given pitch in front of the note it leans on, replacing any already
   * there.
   *
   * The pitch is picked on a keyboard rather than off a list of intervals. The list was six
   * buttons — a tone below, a third above — which covers most decorations and refuses the rest, and
   * it asked a reader to do arithmetic on a page where they can already see the note they want. The
   * keyboard shows the note being decorated in one colour and the decoration in another, so the
   * question is answered by pointing at it.
   *
   * Every one of them leans on its note. Crushed and leaned-on is a distinction a reader can make
   * in their playing and rarely wants to argue about in print, and offering the choice cost two
   * buttons and a paragraph explaining them.
   */
  const putGrace = useCallback(
    (noteKey: string, row: number) => {
      if (row < 0 || row > 87 || row === rowOf(noteKey)) return;
      const grace: GraceNote = {
        hand: handOf(noteKey),
        startFrame: frameOf(noteKey),
        targetRow: rowOf(noteKey),
        row,
        kind: "appoggiatura",
      };
      setGraceNotes((current) => [
        ...current.filter(
          (one) =>
            !(
              one.hand === grace.hand &&
              one.startFrame === grace.startFrame &&
              one.targetRow === grace.targetRow
            ),
        ),
        grace,
      ]);
    },
    [setGraceNotes],
  );

  /** Take the decoration off the note it leans on. */
  const clearGrace = useCallback(() => {
    if (!graceHere) return;
    setGraceNotes((current) => current.filter((one) => one !== graceHere));
  }, [graceHere, setGraceNotes]);

  /**
   * Which note is picked, said in solfège: `Do 4`, `Do-# 3`, `Re-b 5`.
   *
   * Only when exactly one is picked. A chord is three notes at one moment and naming all of them in
   * a panel title would be a list rather than an answer; the keyboard under **Show piano** is where
   * a chord is read.
   *
   * **Spelled the way the sheet spells it**, through the same `pitchToStaffPosition` the noteheads
   * come from, against the signature sounding at that column — so a black key printed as `Re-b`
   * under five flats is called `Re-b` here and not `Do-#`. Working the name out from the row on its
   * own would have been a second opinion about the same note.
   *
   * The hand is the staff the note is drawn on and has nothing to do with the name; it is passed
   * because the spelling takes it, and it only moves the staff step, which this throws away. An
   * octave bracket does not move it either: `letter` and `octave` are the note as it **sounds**.
   */
  const pickedNoteName =
    selectedNotes.length === 1 && selectedNotes[0]
      ? spanishNoteName(
          pitchToStaffPosition(
            rowOf(selectedNotes[0]),
            handOf(selectedNotes[0]),
            keySignatureAtFrame(
              frameOf(selectedNotes[0]),
              keySignature as KeySignature,
              keyChanges,
            ),
          ),
        )
      : null;

  /**
   * Put the numbers that are pressed onto the notes that are picked.
   *
   * One number goes on every note in the selection, which is what a run of the same finger is. Two
   * or more only mean anything on a single chord: there the numbers are read low to high against the
   * noteheads low to high, which is the order a hand takes them in and the order they print in. A
   * selection spanning several onsets keeps to one number, because pairing across chords would be
   * guessing which note in one chord answers which in the next.
   */
  const applyFingers = useCallback(
    (
      picked: FingerNumber[],
      notes: readonly string[],
      chord: readonly string[] | null,
    ) => {
      setFingers((current) => {
        const next = { ...current };
        for (const noteKey of notes) delete next[noteKey];
        if (picked.length === 0) return next;
        if (chord && picked.length > 1) {
          const ordered = [...picked].sort((left, right) => left - right);
          chord.forEach((noteKey, index) => {
            const finger = ordered[index];
            if (finger !== undefined) next[noteKey] = finger;
          });
          return next;
        }
        const one = picked[picked.length - 1]!;
        for (const noteKey of notes) next[noteKey] = one;
        return next;
      });
    },
    [setFingers],
  );

  const pressFinger = useCallback(
    (finger: FingerNumber) => {
      const single = oneChord === null;
      const already = pickedFingers.includes(finger);
      const picked: FingerNumber[] = single
        ? already
          ? []
          : [finger]
        : already
          ? pickedFingers.filter((one) => one !== finger)
          : [...pickedFingers, finger];
      setFingerDraft({ forSelection: selectionKey, picked });
      applyFingers(picked, selectedNotes, oneChord);
    },
    [applyFingers, oneChord, pickedFingers, selectedNotes, selectionKey, setFingerDraft],
  );

  /**
   * Take the picked notes off the page.
   *
   * Marked here and nothing more. **Save** is what takes them out of the piano matrix the piece is
   * drawn from, which is also what makes the roll and the falling view agree with this page; until
   * then it is only the drawing that has stopped asking for them. `wipe` puts them back.
   */
  const hideSelected = useCallback(() => {
    const refs = selectedNotes.map(noteRefOf);
    setHiddenNotes((current) => new Set([...current, ...refs]));
    setFingers((current) => {
      const next = { ...current };
      for (const noteKey of selectedNotes) delete next[noteKey];
      return next;
    });
    closeNotes();
  }, [selectedNotes, closeNotes, setFingers, setHiddenNotes]);

  /**
   * Cut the beam in front of the picked chords, or join it again.
   *
   * A beam holds a whole chord, so it can only be cut in front of all of it — half a chord starting
   * a new group is not a thing that can be drawn. Cutting also drops any *join* on the same chords:
   * the two are opposite answers to one question, and holding both would mean the reader had said
   * two contradictory things about the same note.
   */
  const toggleBeamBreak = useCallback(() => {
    const targets = selectedChords.whole;
    if (targets.length === 0 || selectedChords.partial.length > 0) return;
    const breaking = !targets.every((key) => beamBreaks.has(key));
    setBeamBreaks((current) => {
      const next = new Set(current);
      for (const key of targets) {
        if (breaking) next.add(key);
        else next.delete(key);
      }
      return next;
    });
    if (breaking) {
      setBeamJoins((current) => {
        const next = new Set(current);
        for (const key of targets) next.delete(key);
        return next;
      });
    }
  }, [selectedChords, beamBreaks, setBeamBreaks, setBeamJoins]);

  /**
   * Beam the picked notes as one group, whatever the page's own rule makes of them.
   *
   * The rule cuts a run where it turns over at its lowest note, which is right for an arpeggio and
   * wrong for a scale that happens to dip a step. Only the reader can tell those apart, and this is
   * where they say so: every chord in the selection is marked as not starting a group, and any
   * break the reader had put inside the selection is taken off, because it says the opposite.
   *
   * It only reaches a run the page could beam at all — everything in it has to be a corchea or
   * shorter, since a negra has no beam to share. `beamable` below is what decides that.
   */
  const joinBeams = useCallback(() => {
    const targets = selectedChords.whole;
    if (targets.length === 0) return;
    setBeamJoins((current) => new Set([...current, ...targets]));
    setBeamBreaks((current) => {
      const next = new Set(current);
      for (const key of targets) next.delete(key);
      return next;
    });
  }, [selectedChords, setBeamBreaks, setBeamJoins]);

  /**
   * Write the picked notes as one held note with `tr` over it.
   *
   * It used to be a pill on the frames toolbox, which had to ask which hand and then guess which
   * note of that hand the shake stood on. A selection answers both: the hand is the hand the notes
   * are on, the run is from the first column to the last, and the note that stays is the lowest —
   * because `tr` means "alternate with the note above".
   */
  const markTrillOnSelection = useCallback(() => {
    if (selectedNotes.length === 0) return;
    const side = handOf(selectedNotes[0]!);
    if (!selectedNotes.every((noteKey) => handOf(noteKey) === side)) return;
    const columns = selectedNotes.map(frameOf);
    const rows = selectedNotes.map(rowOf);
    setTrills((current) => [
      ...current,
      {
        hand: side,
        startFrame: Math.min(...columns),
        endFrame: Math.max(...columns) + 1,
        row: Math.min(...rows),
      },
    ]);
    closeNotes();
  }, [selectedNotes, setTrills, closeNotes]);

  /**
   * Print the picked notes smaller than the rest of the page, or full size again.
   *
   * Also moved off the frames toolbox, and for the same reason: "these notes are decoration" is a
   * statement about notes. The stretch it writes is the columns the selection covers, on the staff
   * the selection is on — which is what the panel used to make the reader say twice.
   */
  const toggleCueOnSelection = useCallback(() => {
    if (selectedNotes.length === 0) return;
    const sides = new Set(selectedNotes.map(handOf));
    const side = sides.size === 1 ? [...sides][0]! : "single";
    const columns = selectedNotes.map(frameOf);
    const fromColumn = Math.min(...columns);
    const toColumn = Math.max(...columns) + 1;
    setCueRanges((current) => {
      const covering = current.filter(
        (cue) =>
          cue.hand === side && cue.fromColumn <= fromColumn && cue.toColumn >= toColumn,
      );
      if (covering.length > 0) {
        return current.filter((cue) => !covering.includes(cue));
      }
      return [
        ...current.filter(
          (cue) =>
            !(cue.hand === side && cue.fromColumn < toColumn && cue.toColumn > fromColumn),
        ),
        { hand: side, fromColumn, toColumn },
      ];
    });
  }, [selectedNotes, setCueRanges]);

  return {
    selectedChords,
    oneChord,
    selectedGroups,
    printedFigures,
    selectedPrintedFigure,
    beamable,
    joinedHere,
    brokenHere,
    selectedRun,
    evenHere,
    toggleEvenSpacing,
    nudgeEvenSpacing,
    cueHere,
    trillable,
    namedGroups,
    drawSelectionAs,
    unnameSelection,
    selectionKey,
    pickedFingers,
    onlyNote,
    graceHere,
    putGrace,
    clearGrace,
    pickedNoteName,
    applyFingers,
    pressFinger,
    hideSelected,
    toggleBeamBreak,
    joinBeams,
    markTrillOnSelection,
    toggleCueOnSelection,
  };
}

export type NoteActions = ReturnType<typeof useNoteActions>;
