/**
 * `/playground/piano-roll` — the recording laid out left to right against a
 * vertical keyboard.
 *
 * **Where the position comes from.** Not from clicking the notes. The canvas is
 * for picking notes, so the playhead is moved by the scrub bar above the view or
 * by dragging the playhead itself, and nowhere else. One surface, one meaning:
 * that is what lets a click on a rectangle select it without also jumping the
 * recording somewhere the reader did not ask for.
 *
 * **Why the SVG is measured rather than stretched.** It used to declare a viewBox
 * in keyboard units and stretch it with `preserveAspectRatio="none"`, so the two
 * axes scaled by different amounts and every note name came out squashed. The
 * viewBox is the element's real pixel box now: one unit is one pixel, text is
 * undistorted and a 2 px border is 2 px. Lanes are fractions of that box, which
 * is also how the keyboard beside it scales, so they still line up exactly.
 *
 * **A rectangle is as long as the note was held**, because the x axis is seconds
 * from the recording rather than a run of matrix cells rounded to a subdivision.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import WaveformView from "../../components/audio/WaveformView";
import NoteSelectionToolbox from "../../components/notes/NoteSelectionToolbox";
import PendingRemovalsBar from "../../components/notes/PendingRemovalsBar";
import { useElementSize } from "../../hooks/useElementSize";
import { useStagedRemovals } from "../../hooks/useStagedRemovals";
import { useNoteSelection } from "../../hooks/useNoteSelection";
import { usePlayedNotes } from "../../hooks/usePlayedNotes";
import { ROUTES } from "../../layout/routes";
import { formatTime } from "../../audio/time";
import { fittingNoteLabel } from "../../music/noteNames";
import { laneTop, PIANO_WIDTH, pianoKeyByRow } from "../../piano/keyPositions";
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
import { grays, PageContainer, SectionCard, semantic, surface } from "../../ui";

/** Zoom, in pixels of timeline per second of recording. */
const ZOOM_LEVELS = [40, 60, 90, 120, 180, 260, 400];
const DEFAULT_ZOOM = 120;
const VIEW_HEIGHT = "min(68vh, 760px)";
/** Keep the playhead this far into the viewport while it scrolls itself. */
const CURSOR_LEAD = 0.28;
/** Half-width of the invisible strip that makes the playhead grabbable. */
const CURSOR_GRIP = 7;
/** A drag shorter than this is a click, not a band. */
const BAND_THRESHOLD = 4;

interface Band {
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  additive: boolean;
}

export function PianoRollPage() {
  const { artifact, hasArtifact } = useWorkingArtifact();
  const removal = useStagedRemovals(artifact.audioUuid ?? null);
  const data = usePlayedNotes(artifact, removal.revision);
  const selection = useNoteSelection(data.notes);

  const [source, setSource] = useState<PlaybackSource>("piano");
  const [speed, setSpeed] = useState(1);
  const [zoom, setZoom] = useState(DEFAULT_ZOOM);
  const [showHidden, setShowHidden] = useState(false);
  const [rangeStart, setRangeStart] = useState(0);
  const [rangeEndOverride, setRangeEndOverride] = useState<number | null>(null);
  const [band, setBand] = useState<Band | null>(null);
  /** Flashes `Saved` on the floating bar for a moment, as the sheet's does. */
  const [justSaved, setJustSaved] = useState(false);
  const [draggingCursor, setDraggingCursor] = useState(false);
  const scrollerRef = useRef<HTMLDivElement | null>(null);
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
  // What is *heard* never includes a note the pipeline filtered or the reader
  // took off: playing them back would argue with the sheet.
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

  const timelineWidth = Math.max(900, data.durationSeconds * zoom + 160);
  const height = size.height || 1;
  const secondMarks = Math.ceil(data.durationSeconds) + 1;
  // A label every second is unreadable when zoomed out, so they thin out with the
  // zoom rather than overlapping into a smear.
  const labelEvery = zoom >= 120 ? 1 : zoom >= 60 ? 5 : 10;

  /** A key's lane, as a fraction of the measured box rather than of the keyboard. */
  const lane = useCallback(
    (row: number) => {
      const key = pianoKeyByRow.get(row);
      if (!key) return null;
      return {
        key,
        y: (laneTop(key) / PIANO_WIDTH) * height,
        h: (key.width / PIANO_WIDTH) * height,
      };
    },
    [height],
  );

  const pointIn = useCallback((event: { clientX: number; clientY: number }) => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };
    const bounds = svg.getBoundingClientRect();
    return { x: event.clientX - bounds.left, y: event.clientY - bounds.top };
  }, []);

  // Dragging the playhead listens on the window rather than on the SVG. A move can
  // arrive before React has re-rendered with `draggingCursor` set, and the SVG's
  // own handler would still be the one from the render before the drag began — so
  // the first few pixels of every drag were being dropped. The window listener is
  // installed by the state change itself, so it cannot be out of date, and a drag
  // that leaves the timeline still ends properly.
  useEffect(() => {
    if (!draggingCursor) return;
    const move = (event: PointerEvent) => playback.seek(pointIn(event).x / zoom);
    const up = () => setDraggingCursor(false);
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", up);
    return () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", up);
    };
  }, [draggingCursor, playback, pointIn, zoom]);

  // Follow the playhead. While playing it is held a fixed way into the viewport so
  // notes flow past at a steady place on screen; while paused the timeline only
  // moves when the playhead has actually left the visible stretch, so nudging the
  // scrub bar does not yank the page out from under someone reading it.
  useEffect(() => {
    const scroller = scrollerRef.current;
    if (!scroller) return;
    const target = playback.currentSeconds * zoom;
    if (playback.playing) {
      scroller.scrollTo({
        left: Math.max(0, target - scroller.clientWidth * CURSOR_LEAD),
        behavior: "auto",
      });
      return;
    }
    const margin = scroller.clientWidth * 0.1;
    const inView =
      target >= scroller.scrollLeft + margin &&
      target <= scroller.scrollLeft + scroller.clientWidth - margin;
    if (inView) return;
    scroller.scrollTo({
      left: Math.max(0, target - scroller.clientWidth * CURSOR_LEAD),
      behavior: draggingCursor ? "auto" : "smooth",
    });
  }, [draggingCursor, playback.currentSeconds, playback.playing, zoom]);

  const finishBand = useCallback(
    (current: Band) => {
      const dx = Math.abs(current.toX - current.fromX);
      const dy = Math.abs(current.toY - current.fromY);
      if (dx < BAND_THRESHOLD && dy < BAND_THRESHOLD) {
        // A click on empty canvas, not a band. Nothing is selected any more.
        if (!current.additive) selection.clear();
        return;
      }
      const left = Math.min(current.fromX, current.toX) / zoom;
      const right = Math.max(current.fromX, current.toX) / zoom;
      const top = Math.min(current.fromY, current.toY);
      const bottom = Math.max(current.fromY, current.toY);
      const covered = visibleNotes.filter((note) => {
        const geometry = lane(note.row);
        if (!geometry) return false;
        // Any overlap counts, in both axes — a band drawn over the middle of a
        // long note is a band over that note.
        return (
          note.endSeconds > left &&
          note.startSeconds < right &&
          geometry.y + geometry.h > top &&
          geometry.y < bottom
        );
      });
      selection.pickMany(
        covered.map((note) => note.id),
        current.additive,
      );
    },
    [lane, selection, visibleNotes, zoom],
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
      <PageContainer title="Piano Roll" wide>
        <Alert
          severity="info"
          action={
            <Button component={Link} to={ROUTES.playgroundInput} size="small">
              Go to Input
            </Button>
          }
        >
          Load and transcribe a piece before opening the Piano Roll.
        </Alert>
      </PageContainer>
    );
  }

  const cursorX = playback.currentSeconds * zoom;

  return (
    <PageContainer
      title="Piano Roll"
      subtitle="Time runs left to right in seconds. Click a note to pick it, ⌘-click to add, or drag a band over several."
      wide
    >
      <SectionCard>
        <Stack spacing={1.5}>
          <ProgressBar
            playback={playback}
            durationSeconds={data.durationSeconds}
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
              label="Zoom"
              select
              size="small"
              value={zoom}
              onChange={(event) => setZoom(Number(event.target.value))}
              sx={{ width: 128 }}
            >
              {ZOOM_LEVELS.map((option) => (
                <MenuItem key={option} value={option}>
                  {option} px/s
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
        <SectionCard title="Roll view">
          <Box sx={{ display: "flex", height: VIEW_HEIGHT, minHeight: 430 }}>
            <Box
              sx={{
                width: 112,
                flexShrink: 0,
                border: 1,
                borderColor: "divider",
                borderRight: 0,
                backgroundColor: grays.paper,
              }}
            >
              <Piano
                orientation="vertical"
                width="100%"
                height="100%"
                pressedKeys={playback.pressedKeys}
              />
            </Box>
            <Box
              ref={(node: HTMLDivElement | null) => {
                scrollerRef.current = node;
                sizeRef(node);
              }}
              sx={{
                flexGrow: 1,
                overflowX: playback.playing ? "hidden" : "auto",
                overflowY: "hidden",
                border: 1,
                borderColor: "divider",
                position: "relative",
                backgroundColor: "background.paper",
              }}
            >
              {data.peaks ? (
                <Box
                  sx={{
                    position: "absolute",
                    inset: 0,
                    width: timelineWidth,
                    height: "100%",
                    pointerEvents: "none",
                  }}
                >
                  <WaveformView peaks={data.peaks} height={500} watermark />
                </Box>
              ) : null}
              <svg
                ref={svgRef}
                width={timelineWidth}
                height={height}
                viewBox={`0 0 ${timelineWidth} ${height}`}
                style={{
                  display: "block",
                  position: "relative",
                  cursor: draggingCursor ? "ew-resize" : band ? "crosshair" : "default",
                  touchAction: "none",
                  // A band drag would otherwise highlight the second labels as if
                  // they were prose, which leaves blue blocks across the ruler.
                  userSelect: "none",
                  WebkitUserSelect: "none",
                }}
                onPointerMoveCapture={(event) => {
                  // Only to show the reader that the playhead can be grabbed.
                  if (band || draggingCursor) return;
                  const near = Math.abs(pointIn(event).x - cursorX) <= CURSOR_GRIP;
                  event.currentTarget.style.cursor = near ? "ew-resize" : "default";
                }}
                onPointerDown={(event) => {
                  // One handler decides between the two gestures the background
                  // supports, by where the pointer is. Near the playhead it is a
                  // drag of the playhead; anywhere else it is a selection band. A
                  // note stops the event before it reaches here and handles its
                  // own click.
                  if (event.button !== 0) return;
                  const point = pointIn(event);
                  if (Math.abs(point.x - cursorX) <= CURSOR_GRIP) {
                    setDraggingCursor(true);
                    return;
                  }
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
                {Array.from({ length: secondMarks }, (_, second) => {
                  const x = second * zoom;
                  return (
                    <g key={second}>
                      <line
                        x1={x}
                        x2={x}
                        y1={0}
                        y2={height}
                        stroke={grays.slate}
                        strokeDasharray="5 7"
                        opacity={second % labelEvery === 0 ? 0.4 : 0.16}
                      />
                      {second % labelEvery === 0 ? (
                        <text
                          x={x + 4}
                          y={14}
                          fontSize={10}
                          fontFamily={NOTE_LABEL_FAMILY}
                          fill={surface.mutedText}
                        >
                          {formatTime(second)}
                        </text>
                      ) : null}
                    </g>
                  );
                })}

                {visibleNotes.map((note) => {
                  const geometry = lane(note.row);
                  if (!geometry) return null;
                  const x = note.startSeconds * zoom;
                  const width = Math.max(3, (note.endSeconds - note.startSeconds) * zoom);
                  const selected = selection.ids.has(note.id);
                  const active =
                    note.startSeconds <= playback.currentSeconds &&
                    playback.currentSeconds < note.endSeconds;
                  const staged = removal.isStaged(note);
                  const visuals = noteVisuals(
                    {
                      hand: note.hand,
                      active,
                      selected,
                      ghost: note.artifact || isRemoved(note),
                      staged: staged && isRemoved(note),
                    },
                    width,
                    geometry.h,
                  );
                  const fontSize = labelFontSize(geometry.h);
                  const label = fittingNoteLabel(note.midiNote, width, geometry.h, fontSize);
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
                        x={x}
                        y={geometry.y + 0.5}
                        width={width}
                        height={Math.max(3, geometry.h - 1)}
                        rx={visuals.rx}
                        fill={visuals.fill}
                        stroke={visuals.stroke}
                        strokeWidth={visuals.strokeWidth}
                        strokeDasharray={visuals.strokeDasharray}
                      >
                        <title>
                          {`${formatTime(note.startSeconds)} → ${formatTime(note.endSeconds)} · ${(
                            (note.endSeconds - note.startSeconds) *
                            1000
                          ).toFixed(0)} ms${
                            isRemoved(note)
                              ? removal.isStaged(note)
                                ? " · marked to come off, not saved yet"
                                : " · taken off the recording"
                              : ""
                          }${
                            note.artifact ? " · filtered as an artifact" : ""
                          }`}
                        </title>
                      </rect>
                      {staged && isRemoved(note) ? (
                        <line
                          x1={x + 1}
                          x2={x + width - 1}
                          y1={geometry.y + geometry.h / 2}
                          y2={geometry.y + geometry.h / 2}
                          stroke={STRIKE_COLOR}
                          strokeWidth={1.5}
                          pointerEvents="none"
                        />
                      ) : null}
                      {label ? (
                        <text
                          x={x + width / 2}
                          y={geometry.y + geometry.h / 2}
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

                {/*
                  The playhead. Purely a picture: the pointer passes straight
                  through it and the SVG above decides what a press near it means,
                  which keeps one gesture from being split across two handlers.
                */}
                <g data-playhead style={{ pointerEvents: "none" }}>
                  <line
                    x1={cursorX}
                    x2={cursorX}
                    y1={0}
                    y2={height}
                    stroke={semantic.waveform.cursor}
                    strokeWidth={draggingCursor ? 3 : 2}
                  />
                  <circle
                    cx={cursorX}
                    cy={7}
                    r={draggingCursor ? 7 : 5}
                    fill={semantic.waveform.cursor}
                    stroke={surface.panel}
                    strokeWidth={1.5}
                  />
                </g>
              </svg>
            </Box>
          </Box>
          <Stack direction="row" spacing={2} sx={{ mt: 1, alignItems: "center", flexWrap: "wrap" }}>
            <Typography variant="caption" color="text.secondary">
              {selection.selected.length > 0
                ? `${selection.selected.length} selected`
                : "Nothing selected"}
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

export default PianoRollPage;
