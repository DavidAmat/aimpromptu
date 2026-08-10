/**
 * `/playground/notes-falling` — the Synthesia view: notes drop onto the keyboard
 * and are swallowed at the moment they sound.
 *
 * The window is a **lead time in seconds** that the reader sets. It used to be
 * eight beats converted through the piece's BPM, so how far ahead you could see
 * depended on a tempo the app no longer has — and seconds are the honest unit
 * anyway: what a player wants is "show me the next two seconds".
 *
 * Notes can be picked here exactly as on the roll, and for the same reason: a
 * note the transcriber invented is often easiest to spot as it falls. The
 * geometry is the other way round — pitch across, time down — so the band maths
 * differs, but the rules and the panel are shared.
 *
 * Like the roll, the SVG is measured rather than stretched, so the note names
 * inside the rectangles are drawn undistorted and read horizontally instead of
 * being turned on their side.
 */

import { useCallback, useMemo, useRef, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { Link } from "react-router-dom";
import { audioApi } from "../../api";
import NoteSelectionToolbox from "../../components/notes/NoteSelectionToolbox";
import PendingRemovalsBar from "../../components/notes/PendingRemovalsBar";
import { useElementSize } from "../../hooks/useElementSize";
import { useStagedRemovals } from "../../hooks/useStagedRemovals";
import { useNoteSelection } from "../../hooks/useNoteSelection";
import { usePlayedNotes } from "../../hooks/usePlayedNotes";
import { ROUTES } from "../../layout/routes";
import { formatTime } from "../../audio/time";
import { fittingNoteLabel } from "../../music/noteNames";
import { PIANO_WIDTH, pianoKeyByRow } from "../../piano/keyPositions";
import Piano from "../../piano/Piano";
import { describeEvents, type PlayedNote } from "../../playback/playedNotes";
import {
  labelFontSize,
  NOTE_LABEL_FAMILY,
  NOTE_LABEL_FILL,
  noteVisuals,
  STRIKE_COLOR,
} from "../../playback/noteVisuals";
import { PlayerToolbar } from "../../playback/PlayerToolbar";
import ProgressBar from "../../playback/ProgressBar";
import { usePlayback, type PlaybackSource } from "../../playback/usePlayback";
import { useSpacebarPlay } from "../../playback/useSpacebarPlay";
import { useWorkingArtifact } from "../../state/useWorkingArtifact";
import { grays, PageContainer, SectionCard, semantic } from "../../ui";

const PLOT_HEIGHT = "min(58vh, 620px)";
/** How far ahead the window shows, in seconds. */
const LEAD_OPTIONS = [1, 1.5, 2, 3, 4, 6, 8];
const DEFAULT_LEAD = 3;
/** Below this a rectangle is a sliver, so it is floored to stay visible. */
const MIN_NOTE_HEIGHT = 6;
const BAND_THRESHOLD = 4;

interface Band {
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  additive: boolean;
}

export function NotesFallingPage() {
  const { artifact, hasArtifact } = useWorkingArtifact();
  const removal = useStagedRemovals(artifact.audioUuid ?? null);
  const data = usePlayedNotes(artifact, removal.revision);
  const selection = useNoteSelection(data.notes);

  const [source, setSource] = useState<PlaybackSource>("piano");
  const [speed, setSpeed] = useState(1);
  const [leadSeconds, setLeadSeconds] = useState(DEFAULT_LEAD);
  const [showHidden, setShowHidden] = useState(false);
  const [rangeStart, setRangeStart] = useState(0);
  const [rangeEndOverride, setRangeEndOverride] = useState<number | null>(null);
  const [band, setBand] = useState<Band | null>(null);
  /** Flashes `Saved` on the floating bar for a moment, as the sheet's does. */
  const [justSaved, setJustSaved] = useState(false);
  const [sizeRef, size] = useElementSize<HTMLDivElement>();
  const svgRef = useRef<SVGSVGElement | null>(null);

  const rangeEnd = Math.max(
    rangeStart,
    Math.min(data.durationSeconds, rangeEndOverride ?? data.durationSeconds),
  );

  // `removal.isRemoved` and not `note.removed`: a staged decision has to read as
  // if it had already happened, or the reader cannot see what they are about to
  // save. Staged notes stay drawn regardless of the toggle, struck through, so a
  // delete never makes a note vanish before it has been kept.
  const isRemoved = removal.isRemoved;
  const hiddenCount = data.notes.filter((note) => note.artifact || isRemoved(note)).length;
  const visibleNotes = useMemo(
    () =>
      data.notes.filter(
        (note) =>
          showHidden || removal.isStaged(note) || (!note.artifact && !isRemoved(note)),
      ),
    [data.notes, isRemoved, removal, showHidden],
  );
  const audibleNotes = useMemo(
    () => data.notes.filter((note) => !note.artifact && !isRemoved(note)),
    [data.notes, isRemoved],
  );

  const originalAvailable = Boolean(data.peaks);
  const playback = usePlayback({
    notes: audibleNotes,
    durationSeconds: data.durationSeconds,
    selectionStart: rangeStart,
    selectionEnd: rangeEnd,
    speed,
    source: originalAvailable ? source : "piano",
    originalAudioUrl:
      originalAvailable && data.audioUuid ? audioApi.fileUrl(data.audioUuid, true) : null,
  });

  const togglePlay = useCallback(() => {
    if (playback.playing) playback.pause();
    else void playback.play();
  }, [playback]);
  useSpacebarPlay(togglePlay, Boolean(data.events));

  const width = size.width || 1;
  const height = size.height || 1;
  // Pixels per second of travel. The window is the whole plot, so a 3 s lead over
  // a 600 px drop is 200 px/s and a 6 s lead is half that.
  const velocity = height / leadSeconds;

  /** A key's lane, as a fraction of the measured box. */
  const lane = useCallback(
    (row: number) => {
      const key = pianoKeyByRow.get(row);
      if (!key) return null;
      return {
        key,
        x: (key.x / PIANO_WIDTH) * width,
        w: (key.width / PIANO_WIDTH) * width,
      };
    },
    [width],
  );

  /** Where a note's rectangle sits right now, or `null` if it is off the window. */
  const placement = useCallback(
    (note: PlayedNote) => {
      const bottom = height - (note.startSeconds - playback.currentSeconds) * velocity;
      const noteHeight = Math.max(
        MIN_NOTE_HEIGHT,
        (note.endSeconds - note.startSeconds) * velocity,
      );
      const top = bottom - noteHeight;
      if (bottom < 0 || top > height) return null;
      return { top, height: noteHeight };
    },
    [height, playback.currentSeconds, velocity],
  );

  const windowedNotes = useMemo(
    () => visibleNotes.filter((note) => placement(note) !== null),
    [placement, visibleNotes],
  );

  const pointIn = useCallback((event: { clientX: number; clientY: number }) => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };
    const bounds = svg.getBoundingClientRect();
    return { x: event.clientX - bounds.left, y: event.clientY - bounds.top };
  }, []);

  const finishBand = useCallback(
    (current: Band) => {
      const dx = Math.abs(current.toX - current.fromX);
      const dy = Math.abs(current.toY - current.fromY);
      if (dx < BAND_THRESHOLD && dy < BAND_THRESHOLD) {
        if (!current.additive) selection.clear();
        return;
      }
      const left = Math.min(current.fromX, current.toX);
      const right = Math.max(current.fromX, current.toX);
      const top = Math.min(current.fromY, current.toY);
      const bottom = Math.max(current.fromY, current.toY);
      const covered = windowedNotes.filter((note) => {
        const geometry = lane(note.row);
        const place = placement(note);
        if (!geometry || !place) return false;
        return (
          geometry.x + geometry.w > left &&
          geometry.x < right &&
          place.top + place.height > top &&
          place.top < bottom
        );
      });
      selection.pickMany(
        covered.map((note) => note.id),
        current.additive,
      );
    },
    [lane, placement, selection, windowedNotes],
  );

  // Marking, not writing. The floating bar commits the lot; see `useStagedRemovals`.
  const stageRemove = () => {
    removal.stage(
      selection.selected.filter((note) => !removal.isRemoved(note)),
      true,
    );
    selection.clear();
  };
  const stageRestore = () => {
    removal.stage(
      selection.selected.filter((note) => removal.isRemoved(note)),
      false,
    );
    selection.clear();
  };
  const saveStaged = async () => {
    if (await removal.save(data.notes)) {
      setJustSaved(true);
      window.setTimeout(() => setJustSaved(false), 2600);
    }
  };

  if (!hasArtifact || !artifact.audioUuid) {
    return (
      <PageContainer title="Notes Falling" wide>
        <Alert
          severity="info"
          action={
            <Button component={Link} to={ROUTES.playgroundInput} size="small">
              Go to Input
            </Button>
          }
        >
          Load and transcribe a piece before opening Notes Falling.
        </Alert>
      </PageContainer>
    );
  }

  return (
    <PageContainer
      title="Notes Falling"
      subtitle="Only the seconds ahead are drawn. Click a note to pick it, ⌘-click to add, or drag a band over several."
      wide
    >
      <SectionCard>
        <Stack spacing={1.5}>
          <ProgressBar
            currentSeconds={playback.currentSeconds}
            durationSeconds={data.durationSeconds}
            onSeek={playback.seek}
            rangeStart={rangeStart}
            rangeEnd={rangeEnd}
          />
          <PlayerToolbar
            playback={playback}
            source={source}
            onSourceChange={setSource}
            originalAvailable={originalAvailable}
            speed={speed}
            onSpeedChange={setSpeed}
            rangeStart={rangeStart}
            rangeEnd={rangeEnd}
            durationSeconds={data.durationSeconds}
            onRangeChange={(start, end) => {
              setRangeStart(start);
              setRangeEndOverride(end);
            }}
            showArtifacts={showHidden}
            onShowArtifactsChange={setShowHidden}
            artifactCount={hiddenCount}
          >
            <TextField
              label="Look ahead"
              select
              size="small"
              value={leadSeconds}
              onChange={(event) => setLeadSeconds(Number(event.target.value))}
              sx={{ width: 128 }}
            >
              {LEAD_OPTIONS.map((option) => (
                <MenuItem key={option} value={option}>
                  {option} s
                </MenuItem>
              ))}
            </TextField>
          </PlayerToolbar>
        </Stack>
      </SectionCard>

      {data.error ? <Alert severity="error">{data.error}</Alert> : null}
      {data.loading ? (
        <Stack direction="row" spacing={1} sx={{ alignItems: "center", py: 4 }}>
          <CircularProgress size={18} />
          <Typography variant="body2">Loading the recorded notes…</Typography>
        </Stack>
      ) : null}

      {data.events ? (
        <SectionCard title="Falling view">
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            The next {leadSeconds} s of playing travel through the window, at{" "}
            {velocity.toFixed(0)} px per second.
          </Typography>
          <Box
            sx={{
              maxWidth: 1200,
              mx: "auto",
              border: 1,
              borderColor: "divider",
              backgroundColor: grays.ink,
              overflow: "hidden",
            }}
          >
            <Box ref={sizeRef} sx={{ height: PLOT_HEIGHT, position: "relative" }}>
              <svg
                ref={svgRef}
                width={width}
                height={height}
                viewBox={`0 0 ${width} ${height}`}
                style={{
                  display: "block",
                  touchAction: "none",
                  userSelect: "none",
                  WebkitUserSelect: "none",
                }}
                onPointerDown={(event) => {
                  if (event.button !== 0) return;
                  const point = pointIn(event);
                  event.currentTarget.setPointerCapture(event.pointerId);
                  setBand({
                    fromX: point.x,
                    fromY: point.y,
                    toX: point.x,
                    toY: point.y,
                    additive: event.metaKey || event.ctrlKey,
                  });
                }}
                onPointerMove={(event) => {
                  if (!band) return;
                  const point = pointIn(event);
                  setBand({ ...band, toX: point.x, toY: point.y });
                }}
                onPointerUp={(event) => {
                  if (event.currentTarget.hasPointerCapture(event.pointerId)) {
                    event.currentTarget.releasePointerCapture(event.pointerId);
                  }
                  if (band) finishBand(band);
                  setBand(null);
                }}
              >
                {windowedNotes.map((note) => {
                  const geometry = lane(note.row);
                  const place = placement(note);
                  if (!geometry || !place) return null;
                  const selected = selection.ids.has(note.id);
                  const active =
                    note.startSeconds <= playback.currentSeconds &&
                    playback.currentSeconds < note.endSeconds;
                  const boxWidth = Math.max(4, geometry.w - 2);
                  const staged = removal.isStaged(note);
                  const visuals = noteVisuals(
                    {
                      hand: note.hand,
                      active,
                      selected,
                      ghost: note.artifact || isRemoved(note),
                      staged: staged && isRemoved(note),
                    },
                    place.height,
                    boxWidth,
                  );
                  const fontSize = labelFontSize(boxWidth);
                  const label = fittingNoteLabel(
                    note.midiNote,
                    boxWidth,
                    place.height,
                    fontSize,
                  );
                  return (
                    <g
                      key={note.id}
                      // Addressable from the outside: the render check and any
                      // browser automation need a handle on a specific note.
                      data-note-id={note.id}
                      data-note-selected={selected || undefined}
                      style={{ cursor: "pointer" }}
                      onPointerDown={(event) => {
                        event.stopPropagation();
                        selection.pick(note.id, event.metaKey || event.ctrlKey);
                      }}
                    >
                      <rect
                        x={geometry.x + 1}
                        y={place.top}
                        width={boxWidth}
                        height={place.height}
                        rx={visuals.rx}
                        fill={visuals.fill}
                        stroke={visuals.stroke}
                        strokeWidth={visuals.strokeWidth}
                        strokeDasharray={visuals.strokeDasharray}
                      />
                      {staged && isRemoved(note) ? (
                        <line
                          x1={geometry.x + 2}
                          x2={geometry.x + boxWidth}
                          y1={place.top + place.height / 2}
                          y2={place.top + place.height / 2}
                          stroke={STRIKE_COLOR}
                          strokeWidth={1.5}
                          pointerEvents="none"
                        />
                      ) : null}
                      {label ? (
                        <text
                          x={geometry.x + 1 + boxWidth / 2}
                          y={place.top + place.height / 2}
                          textAnchor="middle"
                          dominantBaseline="central"
                          fontSize={fontSize}
                          fontFamily={NOTE_LABEL_FAMILY}
                          fontWeight={600}
                          fill={NOTE_LABEL_FILL}
                          style={{ pointerEvents: "none", userSelect: "none" }}
                        >
                          {label}
                        </text>
                      ) : null}
                    </g>
                  );
                })}

                {band ? (
                  <rect
                    x={Math.min(band.fromX, band.toX)}
                    y={Math.min(band.fromY, band.toY)}
                    width={Math.abs(band.toX - band.fromX)}
                    height={Math.abs(band.toY - band.fromY)}
                    fill={`${semantic.status.info}22`}
                    stroke={semantic.status.info}
                    strokeDasharray="4 3"
                  />
                ) : null}

                <line
                  x1={0}
                  x2={width}
                  y1={height - 1.5}
                  y2={height - 1.5}
                  stroke={semantic.pressedKey}
                  strokeWidth={3}
                />
              </svg>
            </Box>
            <Piano
              width="100%"
              height="auto"
              pressedKeys={playback.pressedKeys}
              ariaLabel="Piano receiving the falling notes"
            />
          </Box>
          <Stack direction="row" spacing={2} sx={{ mt: 1, alignItems: "center", flexWrap: "wrap" }}>
            <Typography variant="caption" color="text.secondary">
              {formatTime(playback.currentSeconds)} · {windowedNotes.length} in the window
              {selection.selected.length > 0 ? ` · ${selection.selected.length} selected` : ""}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ ml: "auto" }}>
              {describeEvents(data.events)}
            </Typography>
          </Stack>
        </SectionCard>
      ) : null}

      <NoteSelectionToolbox
        selected={selection.selected as PlayedNote[]}
        isRemoved={removal.isRemoved}
        onStageRemove={stageRemove}
        onStageRestore={stageRestore}
        onClose={selection.clear}
      />

      <PendingRemovalsBar
        removing={removal.counts.removing}
        restoring={removal.counts.restoring}
        saving={removal.saving}
        saved={justSaved}
        onSave={() => void saveStaged()}
        onDiscard={removal.discard}
      />
    </PageContainer>
  );
}

export default NotesFallingPage;
