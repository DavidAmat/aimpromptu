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
import {
  FIGURE_LABELS,
  timeScoreApi,
  type FigureName,
  type HandChoice,
  type LadderPreview,
  type Peak,
  type PeaksResponse,
  type TimeScorePayload,
} from "../../api";
import { ApiError } from "../../api";
import { useWorkingArtifact } from "../../state/useWorkingArtifact";

const NAMEABLE_FIGURES: FigureName[] = ["blanca", "negra", "corchea", "semicorchea"];

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
  const [newAnchorMs, setNewAnchorMs] = useState(320);

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
            />
            <TimeScoreView
              score={score}
              overrides={overrides}
              beamBreaks={beamBreaks}
              onSelectNote={setSelectedNote}
              onSelectRange={setRange}
            />
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
    </PageContainer>
  );
}

export default RhythmPage;
