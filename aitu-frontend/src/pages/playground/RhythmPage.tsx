/**
 * Rhythm — read the playing, name one pile, see the sheet.
 *
 * Everything the wall-clock model asks of a person happens on this one screen, in the order it
 * makes sense: look at where the notes keep landing, say what one of those piles is, and read the
 * result. Naming a different pile changes the names on the page and nothing else, so trying two is
 * cheap and nothing is lost by getting it wrong the first time.
 */

import { useCallback, useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { PageContainer, SectionCard } from "../../ui";
import PeakPlot from "../../components/time/PeakPlot";
import ScorePlayer from "../../components/time/ScorePlayer";
import TimeScoreView from "../../components/time/TimeScoreView";
import ToolboxDialog from "../../components/common/ToolboxDialog";
import {
  FIGURE_LABELS,
  timeScoreApi,
  type FigureName,
  type HandChoice,
  type LadderPreview,
  type Peak,
  type PeaksResponse,
  KEY_LABELS,
  KEY_SIGNATURES,
  type KeySignatureName,
  type SavedRhythm,
  type TimeScorePayload,
} from "../../api";
import { ApiError } from "../../api";
import {
  applyKeySignatureRange,
  clearKeySignatureRange,
  keySignatureAtFrame,
  type KeyChangeAnnotation,
  type KeySignature,
} from "@aimpromptu/grid-notation";
import { useWorkingArtifact } from "../../state/useWorkingArtifact";

const NAMEABLE_FIGURES: FigureName[] = ["blanca", "negra", "corchea", "semicorchea"];

/** `mm:ss.cc`, so a column range can be read as a moment in the recording. */
function formatSeconds(seconds: number): string {
  const total = Math.max(0, Math.round(seconds * 100));
  const minutes = Math.floor(total / 6000);
  const rest = Math.floor((total % 6000) / 100);
  return `${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}.${String(
    total % 100,
  ).padStart(2, "0")}`;
}

/**
 * The rungs a figure shift walks: the plain figures, each twice the one below it (D-18).
 *
 * The dotted pair is not here. A dot is an exception the vocabulary allows on two figures so a held
 * note can be written; it is not a rung, and stepping onto it would re-scale the ladder by 1.5
 * rather than doubling it. This mirrors `SHIFT_LADDER` in `matrix/ladder.py`, which is the same
 * list on the other side.
 */
const SHIFT_LADDER: FigureName[] = [
  "semifusa",
  "fusa",
  "semicorchea",
  "corchea",
  "negra",
  "blanca",
  "redonda",
];

/** The figure `steps` rungs away, or `null` when that runs off the end of the vocabulary. */
function shifted(figure: FigureName, steps: number): FigureName | null {
  const at = SHIFT_LADDER.indexOf(figure);
  if (at < 0) return null;
  return SHIFT_LADDER[at + steps] ?? null;
}

/** Everything a single note may be drawn as. Wider than the list used to name a gap. */
const ALL_FIGURES: FigureName[] = [
  "redonda",
  "blanca",
  "dottedBlanca",
  "negra",
  "dottedNegra",
  "corchea",
  "semicorchea",
];

interface Stretch {
  /** The frame the stretch starts at. Everything before it keeps the previous name. */
  startFrame: number;
  /** What a gap is called from here on, in milliseconds. */
  anchorMs: number;
}

/** A clicked note arrives as `hand:frame:row`; an override belongs to the whole chord at that frame. */
function figureKeyOf(noteKey: string): string {
  const [hand, frame] = noteKey.split(":");
  return `${hand}:${frame}`;
}

interface View {
  key: string;
  peaks: PeaksResponse | null;
  selected: Peak | null;
  preview: LadderPreview | null;
  score: TimeScorePayload | null;
  error: string | null;
}

function emptyView(key: string): View {
  return { key, peaks: null, selected: null, preview: null, score: null, error: null };
}

/**
 * The backend's own sentence, without the status code in front of it.
 *
 * `ApiError.message` reads "409 — This piece was transcribed before…", which is
 * a number a reader has no use for. The `detail` behind it is written to be shown
 * as it stands, so that is what appears.
 */
function readable(caught: unknown, fallback: string): string {
  if (caught instanceof ApiError) return caught.detail;
  return caught instanceof Error ? caught.message : fallback;
}

/** A piece with no recorded notes yet: not a failure, just nothing to read. */
function notTranscribed(caught: unknown): boolean {
  return caught instanceof ApiError && caught.status === 409;
}

export function RhythmPage() {
  const { artifact } = useWorkingArtifact();
  const audioUuid = artifact.audioUuid;
  const frameMs = artifact.frameMs;

  const [hand, setHand] = useState<HandChoice>("right");
  const [figure, setFigure] = useState<FigureName>("negra");
  const [busy, setBusy] = useState(false);
  /**
   * Figures set by hand on one note, keyed `hand:startFrame`.
   *
   * Kept here and drawn on top rather than saved, because an override is only a glyph: nothing
   * moves and no other note changes. Writing the sheet again keeps them.
   */
  const [overrides, setOverrides] = useState<Record<string, FigureName>>({});
  const [selectedNote, setSelectedNote] = useState<string | null>(null);
  /**
   * The signature the whole piece is written in, and what the notes themselves suggest.
   *
   * A transcription has no key. The recording says which keys were pressed and nothing about how
   * they should be spelled, so until someone chooses, everything is written in C and every black
   * key prints its own accidental. Choosing moves those accidentals into the clef.
   */
  const [keySignature, setKeySignature] = useState<KeySignatureName>("C");
  const [keyHint, setKeyHint] = useState<{ best: KeySignatureName; saved: number } | null>(null);
  /**
   * Where the piece leaves the main signature, and what it changes to.
   *
   * Kept as transitions rather than as ranges, which is how the drawing package stores them: at any
   * column exactly one signature is sounding, so two edits cannot disagree. Giving a passage its own
   * key writes two, one at each end.
   */
  const [keyChanges, setKeyChanges] = useState<KeyChangeAnnotation[]>([]);
  /** Notes picked on the sheet: click one, then hold Command and click more. */
  const [selectedNotes, setSelectedNotes] = useState<readonly string[]>([]);
  const [framesToolbox, setFramesToolbox] = useState(false);
  const [notesToolbox, setNotesToolbox] = useState(false);
  /** Raised to drop every selection on the sheet: Escape, or closing a toolbox. */
  const [clearedAt, setClearedAt] = useState(0);
  /**
   * What the frames toolbox will write when Apply is pressed, and which selection it was chosen for.
   *
   * Carried with the range it belongs to rather than reset by an effect: picking a different stretch
   * of columns should offer whatever is sounding there, not whatever was chosen for the last one.
   */
  const [passageDraft, setPassageDraft] = useState<{
    forRange: string;
    value: KeySignatureName;
  } | null>(null);
  /**
   * Notes the reader has asked to start a new beam.
   *
   * Kept beside the overrides and for the same reason: it changes how the page is grouped and
   * nothing about the music. A long arpeggio beams as one slope because no rule can see where the
   * phrase restarts — only the person reading can, so they say.
   */
  const [beamBreaks, setBeamBreaks] = useState<ReadonlySet<string>>(new Set());
  /**
   * Where the piece changes speed, as frames, and what a gap is called after each of them.
   *
   * A boundary is drawn by hand. Nothing detects them: a wrong hand-drawn one spoils one stretch,
   * while a wrong automatic one scatters speed changes through the piece and makes the sheet
   * unreadable. Frames are absolute wall clock, so a boundary never moves a note.
   */
  const [stretches, setStretches] = useState<Stretch[]>([]);
  const [range, setRange] = useState<{ fromColumn: number; toColumn: number } | null>(null);
  // Where the recording is, in seconds, while it plays. `null` when nothing is playing, which is
  // what hides the line on the staves.
  const [playheadSeconds, setPlayheadSeconds] = useState<number | null>(null);
  const [newAnchorMs, setNewAnchorMs] = useState(320);
  /**
   * The reading saved with the piece, and whether this screen still matches it.
   *
   * `null` means nobody has read this piece yet, which is the blank state the plot is for.
   */
  const [saved, setSaved] = useState<SavedRhythm | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedNote, setSavedNote] = useState<string | null>(null);

  /**
   * Everything read for one (piece, hand, resolution), kept together under the key it belongs to.
   *
   * One object rather than five, because they always change together: asking about the other hand
   * invalidates the piles, the chosen pile, the preview and the sheet at once. Comparing the key
   * during render is how the reset happens, which keeps it out of the effect.
   */
  const key = `${audioUuid ?? ""}|${hand}|${frameMs}`;
  const [view, setView] = useState<View>(() => emptyView(key));
  const [untranscribed, setUntranscribed] = useState(false);
  if (view.key !== key) setView(emptyView(key));

  const { peaks, selected, preview, score, error } = view;

  // Which stretch the toolbox is about, and what it will write. The signature offered is whatever
  // is already sounding at the start of the stretch, until the reader picks another.
  const rangeKey = range ? `${range.fromColumn}:${range.toColumn}` : "";
  const passageKey: KeySignatureName =
    passageDraft?.forRange === rangeKey
      ? passageDraft.value
      : (keySignatureAtFrame(
          range?.fromColumn ?? 0,
          keySignature as KeySignature,
          keyChanges,
        ) as KeySignatureName);

  useEffect(() => {
    if (!audioUuid) return;
    const controller = new AbortController();
    timeScoreApi
      .peaks(audioUuid, { hand, frameMs }, controller.signal)
      .then((found) => {
        setUntranscribed(false);
        // The pile holding most of the playing is the one a reader looks at first, so it starts
        // chosen. Nothing is committed by that: the sheet only appears once a name is given.
        const biggest = [...found.peaks].sort((a, b) => b.share - a.share)[0] ?? null;
        setView((current) =>
          current.key === key ? { ...current, peaks: found, selected: biggest } : current,
        );
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return;
        // Stop waiting. Leaving the spinner turning says "nearly there" to a
        // reader whose piece is never going to load.
        setUntranscribed(notTranscribed(caught));
        setView((current) =>
          current.key === key
            ? { ...current, error: readable(caught, "Could not read the rhythm.") }
            : current,
        );
      });
    return () => controller.abort();
  }, [audioUuid, hand, frameMs, key]);

  // Read back what this piece was last read as, once per piece.
  //
  // Restoring the anchor is not enough on its own: the pile it names has to be the one the plot
  // shows, or the number under the name would say one thing and the highlighted bar another. So the
  // nearest pile is selected too, and if none is near, the saved reading is kept and the plot simply
  // has nothing highlighted, which is honest about the two disagreeing.
  useEffect(() => {
    if (!audioUuid) return;
    const controller = new AbortController();
    timeScoreApi
      .rhythm(audioUuid, controller.signal)
      .then((found) => {
        if (!found) return;
        setSaved(found);
        setHand(found.hand);
        setFigure(found.anchorFigure);
        setStretches(
          found.speedChanges.map((change) => ({
            startFrame: change.startFrame,
            anchorMs: change.anchorMs,
          })),
        );
        setOverrides(
          Object.fromEntries(
            found.overrides.map((one) => [`${one.hand}:${one.startFrame}`, one.figure]),
          ),
        );
        setBeamBreaks(new Set(found.beamBreaks.map((one) => `${one.hand}:${one.startFrame}`)));
        if (found.keySignature) setKeySignature(found.keySignature);
        setKeyChanges(
          (found.keyChanges ?? []).map((change) => ({
            fromColumn: change.fromColumn,
            keySignature: change.keySignature as KeySignature,
          })),
        );
      })
      .catch(() => {
        // A reading that cannot be read is not worth stopping the screen for: the plot still works
        // and the reader can name the gap again.
      });
    return () => controller.abort();
  }, [audioUuid]);

  /**
   * Both of these have to keep the same identity between renders.
   *
   * The sheet is rebuilt whenever anything it draws from changes, and a handler written inline is a
   * different function every time, so the sheet would be rebuilt on every click and would lose the
   * selection it had just made.
   */
  const pickRange = useCallback((picked: { fromColumn: number; toColumn: number }) => {
    setRange(picked);
    setFramesToolbox(true);
  }, []);

  const pickNotes = useCallback((keys: readonly string[]) => {
    setSelectedNotes(keys);
    setNotesToolbox(keys.length > 0);
  }, []);

  /**
   * Closing a toolbox lets the selection go with it.
   *
   * A dashed outline left on the page after its panel has gone says something is still picked when
   * nothing is, and the next click would then extend that invisible selection instead of starting a
   * new one.
   */
  const closeFrames = useCallback(() => {
    setFramesToolbox(false);
    setRange(null);
    setPassageDraft(null);
    setClearedAt((at) => at + 1);
  }, []);

  const closeNotes = useCallback(() => {
    setNotesToolbox(false);
    setSelectedNotes([]);
    setSelectedNote(null);
    setClearedAt((at) => at + 1);
  }, []);

  // Escape drops whatever is picked, which is what it does everywhere else.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      closeFrames();
      closeNotes();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [closeFrames, closeNotes]);

  const save = useCallback(async () => {
    if (!audioUuid || !selected) return;
    setSaving(true);
    setSavedNote(null);
    const body: SavedRhythm = {
      hand,
      frameMs,
      keySignature,
      keyChanges: keyChanges.map((change) => ({
        fromColumn: change.fromColumn,
        keySignature: change.keySignature,
      })),
      anchorFigure: figure,
      anchorMs: selected.medianMs,
      speedChanges: stretches.map((stretch) => ({
        startFrame: stretch.startFrame,
        anchorMs: stretch.anchorMs,
      })),
      overrides: Object.entries(overrides).map(([key, name]) => {
        const [side, frame] = key.split(":");
        // The row is not part of the key: an override belongs to a chord, not to one notehead, so
        // every note struck together takes it. Row 0 stands for "the group at this column".
        return { hand: side ?? "right", row: 0, startFrame: Number(frame), figure: name };
      }),
      beamBreaks: [...beamBreaks].map((key) => {
        const [side, frame] = key.split(":");
        return { hand: side ?? "right", startFrame: Number(frame) };
      }),
    };
    try {
      const stored = await timeScoreApi.saveRhythm(audioUuid, body);
      setSaved(stored);
      setSavedNote("Saved with the piece. It will be here next time.");
    } catch (caught) {
      setSavedNote(readable(caught, "Could not save this rhythm."));
    } finally {
      setSaving(false);
    }
  }, [
    audioUuid,
    selected,
    hand,
    frameMs,
    figure,
    keySignature,
    keyChanges,
    stretches,
    overrides,
    beamBreaks,
  ]);

  const apply = useCallback(async () => {
    if (!audioUuid || !selected) return;
    setBusy(true);
    try {
      const [nextPreview, nextScore] = await Promise.all([
        timeScoreApi.ladderPreview(audioUuid, {
          anchorFigure: figure,
          anchorMs: selected.medianMs,
          hand,
          frameMs,
        }),
        timeScoreApi.score(audioUuid, {
          anchorFigure: figure,
          anchorMs: selected.medianMs,
          frameMs,
          boundaries: stretches.map((stretch) => stretch.startFrame),
          boundaryMs: [selected.medianMs, ...stretches.map((stretch) => stretch.anchorMs)],
        }),
      ]);
      setView((current) =>
        current.key === key
          ? { ...current, preview: nextPreview, score: nextScore, error: null }
          : current,
      );
    } catch (caught) {
      const message = readable(caught, "Could not build the sheet.");
      setView((current) => (current.key === key ? { ...current, error: message } : current));
    } finally {
      setBusy(false);
    }
  }, [audioUuid, selected, figure, hand, frameMs, key, stretches]);

  if (!audioUuid) {
    return (
      <PageContainer
        title="Rhythm"
        subtitle="Read how the piece was played, name one gap, and the sheet follows."
        wide
      >
        <Alert severity="info">
          Load and transcribe an audio on the <strong>Upload / Input</strong> tab first. The rhythm
          is read from the notes that transcription records.
        </Alert>
      </PageContainer>
    );
  }

  return (
    <PageContainer
      title="Rhythm"
      subtitle="Every bar below is a gap that keeps repeating between one note and the next. Click the one you recognise, say what it is, and the sheet is written from it. Choosing a different one renames the notes and moves nothing."
      wide
    >
      {error ? (
        <Alert severity={untranscribed ? "warning" : "error"} sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : null}

      <SectionCard
        title="How this piece was played"
        description="Measured from the recording itself, one hand at a time, before anything was rounded."
      >
        <Stack spacing={2}>
          <Stack direction="row" spacing={2} sx={{ alignItems: "center", flexWrap: "wrap" }}>
            <TextField
              label="Hand"
              select
              size="small"
              value={hand}
              onChange={(event) => setHand(event.target.value as HandChoice)}
              sx={{ minWidth: 160 }}
            >
              <MenuItem value="right">Right hand</MenuItem>
              <MenuItem value="left">Left hand</MenuItem>
              <MenuItem value="both">Both hands</MenuItem>
            </TextField>
            {peaks ? (
              <Typography variant="body2" color="text.secondary">
                {peaks.gapCount} gaps between {peaks.attackCount} notes, over{" "}
                {peaks.endSeconds.toFixed(1)} seconds.
              </Typography>
            ) : error ? null : (
              <CircularProgress size={18} />
            )}
          </Stack>

          {peaks?.warning ? (
            <Alert severity="info" sx={{ mb: 1 }}>
              {peaks.warning}
            </Alert>
          ) : null}

          {peaks ? (
            <PeakPlot
              peaks={peaks.peaks}
              labelled={preview?.labelled}
              selectedMs={selected?.centreMs ?? null}
              onSelect={(peak) => setView((current) => ({ ...current, selected: peak }))}
            />
          ) : null}
        </Stack>
      </SectionCard>

      <SectionCard
        title="Name it"
        description="One name fixes every other figure, because they are all proportions of each other."
      >
        <Stack direction="row" spacing={2} sx={{ alignItems: "center", flexWrap: "wrap" }}>
          <Typography variant="body1">
            The <strong>{selected ? Math.round(selected.centreMs) : "—"} ms</strong> gap is one
          </Typography>
          <TextField
            select
            size="small"
            value={figure}
            onChange={(event) => setFigure(event.target.value as FigureName)}
            sx={{ minWidth: 240 }}
            disabled={!selected}
          >
            {NAMEABLE_FIGURES.map((name) => (
              <MenuItem key={name} value={name}>
                {FIGURE_LABELS[name]}
              </MenuItem>
            ))}
          </TextField>
          <Button
            variant="contained"
            onClick={() => void apply()}
            disabled={!selected || busy}
            startIcon={busy ? <CircularProgress size={16} /> : undefined}
          >
            Write the sheet
          </Button>
          {preview ? (
            <Typography variant="body1" sx={{ fontWeight: 600 }}>
              {preview.headerLabel}
            </Typography>
          ) : null}
        </Stack>

        {/*
          A figure shift. The same playing, written in longer or shorter figures: `negra = 337`
          becomes `blanca = 337`, and every note is renamed with it. Nothing moves, because a column
          is wall clock and the name of a note has no say in where it sits (D-18).

          It is the answer to a page of semicorcheas that should read as corcheas. The names were
          never wrong in any measurable way, they are just harder to read than they need to be, and
          this is one button rather than a re-transcription.
        */}
        {score ? (
          <Stack
            direction="row"
            spacing={1.5}
            sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1, mt: 2 }}
          >
            <Typography variant="body2">Too many short notes, or too few?</Typography>
            <Button
              size="small"
              variant="outlined"
              disabled={busy || shifted(figure, 1) === null}
              onClick={() => {
                const next = shifted(figure, 1);
                if (next) setFigure(next);
              }}
            >
              Write it one step longer
            </Button>
            <Button
              size="small"
              variant="outlined"
              disabled={busy || shifted(figure, -1) === null}
              onClick={() => {
                const next = shifted(figure, -1);
                if (next) setFigure(next);
              }}
            >
              Write it one step shorter
            </Button>
            <Typography variant="caption" color="text.secondary">
              Renames every note. Nothing moves, and the recording is untouched. Press{" "}
              <strong>Write the sheet</strong> to see it.
            </Typography>
          </Stack>
        ) : null}
      </SectionCard>

      {score ? (
        <SectionCard
          title="Does the piece change speed?"
          description="Drag across the numbers above the staves to mark where it changes, then say what a gap is worth after that point. Everything before keeps the name it had."
        >
          <Stack spacing={1.5}>
            <Stack direction="row" spacing={2} sx={{ alignItems: "center", flexWrap: "wrap" }}>
              {range ? (
                <>
                  <Typography variant="body2">
                    From column <strong>{range.fromColumn}</strong>, a gap is
                  </Typography>
                  <TextField
                    size="small"
                    type="number"
                    value={newAnchorMs}
                    onChange={(event) => setNewAnchorMs(Number(event.target.value))}
                    sx={{ width: 120 }}
                    slotProps={{ htmlInput: { min: 20, step: 5 } }}
                  />
                  <Typography variant="body2">ms</Typography>
                  <Button
                    variant="outlined"
                    onClick={() => {
                      setStretches((current) =>
                        [
                          ...current.filter((one) => one.startFrame !== range.fromColumn),
                          { startFrame: range.fromColumn, anchorMs: newAnchorMs },
                        ].sort((a, b) => a.startFrame - b.startFrame),
                      );
                      setRange(null);
                    }}
                  >
                    Add the change
                  </Button>
                </>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Nothing selected. Drag over the column numbers above the staves to choose where a
                  change starts.
                </Typography>
              )}
            </Stack>

            {stretches.length ? (
              <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", rowGap: 1 }}>
                {score.passages.map((passage, index) => (
                  <Typography key={passage.id} variant="caption" color="text.secondary">
                    <strong>
                      {index === 0 ? "From the start" : `From column ${passage.startFrame}`}
                    </strong>
                    : {passage.headerLabel}
                  </Typography>
                ))}
                <Button size="small" onClick={() => setStretches([])}>
                  Remove all changes
                </Button>
              </Stack>
            ) : null}

            <Typography variant="caption" color="text.secondary">
              After adding or removing a change, press <strong>Write the sheet</strong> again.
            </Typography>
          </Stack>
        </SectionCard>
      ) : null}

      <SectionCard
        title="The sheet"
        description={
          score
            ? `${score.notes.length} notes, ${score.envelope.frameMs} ms per column.`
            : "Name a gap above and it appears here."
        }
      >
        {score ? (
          <Stack spacing={1.5}>
            <ScorePlayer
              audioUuid={audioUuid}
              scoreSeconds={(score.envelope.frameCount * score.envelope.frameMs) / 1000}
              onTime={setPlayheadSeconds}
            />
            {/*
              The key signature belongs beside the sheet rather than beside the plot, because it is
              read off the sheet: you change it and look at how many sharps and flats disappear.
            */}
            <Stack direction="row" spacing={2} sx={{ alignItems: "center", flexWrap: "wrap" }}>
              <TextField
                select
                size="small"
                label="Key signature"
                value={keySignature}
                onChange={(event) => setKeySignature(event.target.value as KeySignatureName)}
                sx={{ minWidth: 200 }}
                helperText="Written on both clefs. It changes spelling only: no note moves."
              >
                {KEY_SIGNATURES.map((name) => (
                  <MenuItem key={name} value={name}>
                    {KEY_LABELS[name]}
                  </MenuItem>
                ))}
              </TextField>
              {keyHint ? (
                <Button size="small" onClick={() => setKeySignature(keyHint.best)}>
                  Try {KEY_LABELS[keyHint.best]}
                  {keyHint.saved > 0 ? ` (${keyHint.saved} fewer accidentals)` : ""}
                </Button>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No other signature would print fewer accidentals than this one.
                </Typography>
              )}
            </Stack>
            <TimeScoreView
              score={score}
              overrides={overrides}
              beamBreaks={beamBreaks}
              keySignature={keySignature}
              keyChanges={keyChanges}
              onKeySuggestion={setKeyHint}
              onSelectNote={setSelectedNote}
              onSelectNotes={pickNotes}
              onSelectRange={pickRange}
              selectedRange={range}
              clearSelectionsAt={clearedAt}
              playheadSeconds={playheadSeconds}
            />
            {/*
              Everything above is a decision, and until now every one of them went when the tab did.
              The columns, the figures and the beams are all worked out again from the recording on
              each visit, so they cost nothing to lose; which pile is the beat, where the piece
              changes speed, which note you renamed and where you broke a beam are not in the
              recording at all, and re-deciding them is the actual work.
            */}
            <Stack direction="row" spacing={2} sx={{ alignItems: "center", flexWrap: "wrap" }}>
              <Button
                variant="outlined"
                onClick={() => void save()}
                disabled={!selected || saving}
                startIcon={saving ? <CircularProgress size={16} /> : undefined}
              >
                Save this rhythm with the piece
              </Button>
              {savedNote ? (
                <Typography variant="body2" color="text.secondary">
                  {savedNote}
                </Typography>
              ) : saved ? (
                <Typography variant="body2" color="text.secondary">
                  Last saved as {FIGURE_LABELS[saved.anchorFigure]} = {saved.anchorMs.toFixed(0)}{" "}
                  ms{saved.keySignature ? `, in ${KEY_LABELS[saved.keySignature]}` : ""}.
                </Typography>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Nothing saved yet, so this reading goes when you leave the tab.
                </Typography>
              )}
            </Stack>

            <Stack direction="row" spacing={2} sx={{ alignItems: "center", flexWrap: "wrap" }}>
              {selectedNote ? (
                <>
                  <Typography variant="body2">Draw this one note as</Typography>
                  <TextField
                    select
                    size="small"
                    value={overrides[figureKeyOf(selectedNote)] ?? ""}
                    onChange={(event) =>
                      setOverrides((current) => ({
                        ...current,
                        [figureKeyOf(selectedNote)]: event.target.value as FigureName,
                      }))
                    }
                    sx={{ minWidth: 220 }}
                  >
                    {ALL_FIGURES.map((name) => (
                      <MenuItem key={name} value={name}>
                        {FIGURE_LABELS[name]}
                      </MenuItem>
                    ))}
                  </TextField>
                  {overrides[figureKeyOf(selectedNote)] ? (
                    <Button
                      size="small"
                      onClick={() =>
                        setOverrides((current) => {
                          const next = { ...current };
                          delete next[figureKeyOf(selectedNote)];
                          return next;
                        })
                      }
                    >
                      Undo this one
                    </Button>
                  ) : null}
                  <Button
                    size="small"
                    variant="outlined"
                    onClick={() =>
                      setBeamBreaks((current) => {
                        const next = new Set(current);
                        const key = figureKeyOf(selectedNote);
                        if (!next.delete(key)) next.add(key);
                        return next;
                      })
                    }
                  >
                    {beamBreaks.has(figureKeyOf(selectedNote))
                      ? "Join the beam again"
                      : "Break the beam here"}
                  </Button>
                </>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Click a notehead to draw that one note as a different figure, or to start a new
                  beam group on it. Both change how the page reads and nothing about the music.
                </Typography>
              )}
            </Stack>
          </Stack>
        ) : (
          <Typography variant="body2" color="text.secondary">
            Nothing written yet.
          </Typography>
        )}
      </SectionCard>

      {/*
        Two toolboxes, because a column and a notehead answer different questions. A column belongs
        to the piece and both hands are in it; a notehead is one note in one hand. Keeping them
        apart is what stopped `8vb` being offered to the right hand only pointing upward.
      */}
      <ToolboxDialog
        open={framesToolbox && range !== null}
        title="Frames"
        subtitle={
          range
            ? `f${range.fromColumn} – f${range.toColumn - 1} · ${formatSeconds(
                (range.fromColumn * frameMs) / 1000,
              )} → ${formatSeconds((range.toColumn * frameMs) / 1000)}`
            : undefined
        }
        initialPosition={{ x: 24, y: 140 }}
        onClose={closeFrames}
      >
        <Stack spacing={1.5}>
          <Typography variant="body2" color="text.secondary">
            Click a group of columns above the staves to pick it, then hold Shift and click another
            to take everything between them.
          </Typography>
          <TextField
            select
            size="small"
            label="Key signature for this passage"
            value={passageKey}
            onChange={(event) =>
              setPassageDraft({ forRange: rangeKey, value: event.target.value as KeySignatureName })
            }
            fullWidth
          >
            {KEY_SIGNATURES.map((name) => (
              <MenuItem key={name} value={name}>
                {KEY_LABELS[name]}
              </MenuItem>
            ))}
          </TextField>
          <Typography variant="caption" color="text.secondary">
            The passage starts with naturals cancelling what was sounding, both clefs again, and the
            new signature. Where it ends, the same happens in reverse and the piece returns to{" "}
            {KEY_LABELS[keySignature].split(" —")[0]}.
          </Typography>
          <Stack direction="row" spacing={1}>
            <Button
              variant="contained"
              size="small"
              disabled={!range}
              onClick={() => {
                if (!range || !score) return;
                setKeyChanges(
                  applyKeySignatureRange(
                    keyChanges,
                    {
                      fromFrame: range.fromColumn,
                      toFrame: range.toColumn,
                      keySignature: passageKey as KeySignature,
                    },
                    keySignature as KeySignature,
                    score.envelope.frameCount,
                  ),
                );
              }}
            >
              Write this passage in {passageKey}
            </Button>
            <Button
              size="small"
              disabled={!range || keyChanges.length === 0}
              onClick={() => {
                if (!range || !score) return;
                setKeyChanges(
                  clearKeySignatureRange(
                    keyChanges,
                    { fromFrame: range.fromColumn, toFrame: range.toColumn },
                    keySignature as KeySignature,
                    score.envelope.frameCount,
                  ),
                );
              }}
            >
              Back to the piece&rsquo;s key
            </Button>
          </Stack>
          {keyChanges.length > 0 ? (
            <Typography variant="caption" color="text.secondary">
              {keyChanges.length} key change
              {keyChanges.length === 1 ? "" : "s"} in this piece, at{" "}
              {keyChanges.map((change) => `f${change.fromColumn}`).join(", ")}.
            </Typography>
          ) : null}
        </Stack>
      </ToolboxDialog>

      <ToolboxDialog
        open={notesToolbox && selectedNotes.length > 0}
        title={selectedNotes.length === 1 ? "Note" : `${selectedNotes.length} notes`}
        subtitle={
          selectedNotes.length > 0
            ? selectedNotes
                .slice(0, 4)
                .map((noteKey) => `f${noteKey.split(":")[1]}`)
                .join(", ") + (selectedNotes.length > 4 ? ", …" : "")
            : undefined
        }
        initialPosition={{ x: 420, y: 140 }}
        onClose={closeNotes}
      >
        <Stack spacing={1.5}>
          <Typography variant="body2" color="text.secondary">
            Click a notehead to pick it, then hold Command and click more to build a set. Everything
            this toolbox will offer applies to the whole set at once.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Nothing to set here yet. The controls come next; this is the panel they will live in.
          </Typography>
        </Stack>
      </ToolboxDialog>
    </PageContainer>
  );
}

export default RhythmPage;
