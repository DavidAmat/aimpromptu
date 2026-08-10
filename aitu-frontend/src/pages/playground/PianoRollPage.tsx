/**
 * `/playground/piano-roll` — the recording laid out left to right against a
 * vertical keyboard.
 *
 * Restored from Epic 8 and put back on the wall clock. The layout is the one
 * that worked: keyboard down the left edge, time running right, the waveform of
 * the take watermarked behind the notes, one cursor line, click anywhere to
 * seek. Three things changed underneath it.
 *
 * **A rectangle is as long as the note was held.** It used to be a run of matrix
 * cells, so its length was a multiple of one beat subdivision and two notes
 * played 30 ms apart were drawn on top of each other. Here the x axis is
 * seconds, and what you see is what the engine heard.
 *
 * **The guides are seconds, not frame numbers.** A frame is a column length
 * chosen for drawing the sheet; it has nothing to say about where you are in a
 * recording. The dashed lines are one second apart and carry a clock time.
 *
 * **Nothing is dragged.** Epic 8 let you drag a rectangle to another key and
 * save it as a matrix cell edit. That endpoint went with the tempo model. The
 * successor is correcting the *hand* on the Rhythm step, which is written onto
 * the recording instead of onto a grid.
 */

import { useEffect, useMemo, useRef, useState } from "react";
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
import { usePlayedNotes } from "../../hooks/usePlayedNotes";
import { ROUTES } from "../../layout/routes";
import { formatTime } from "../../audio/time";
import { laneTop, PIANO_WIDTH, pianoKeyByRow } from "../../piano/keyPositions";
import Piano from "../../piano/Piano";
import { describeEvents } from "../../playback/playedNotes";
import { PlayerToolbar } from "../../playback/PlayerToolbar";
import { usePlayback, type PlaybackSource } from "../../playback/usePlayback";
import { useWorkingArtifact } from "../../state/useWorkingArtifact";
import { grays, handColors, PageContainer, SectionCard, semantic } from "../../ui";

/** Zoom, in pixels of timeline per second of recording. */
const ZOOM_LEVELS = [40, 60, 90, 120, 180, 260, 400];
const DEFAULT_ZOOM = 120;
const VIEW_HEIGHT = "min(68vh, 760px)";
/** Keep the cursor this far into the viewport while it scrolls itself. */
const CURSOR_LEAD = 0.28;

export function PianoRollPage() {
  const { artifact, hasArtifact } = useWorkingArtifact();
  const data = usePlayedNotes(artifact);
  const [source, setSource] = useState<PlaybackSource>("piano");
  const [speed, setSpeed] = useState(1);
  const [zoom, setZoom] = useState(DEFAULT_ZOOM);
  const [showArtifacts, setShowArtifacts] = useState(false);
  const [rangeStart, setRangeStart] = useState(0);
  const [rangeEndOverride, setRangeEndOverride] = useState<number | null>(null);
  const scrollerRef = useRef<HTMLDivElement | null>(null);

  const rangeEnd = Math.max(
    rangeStart,
    Math.min(data.durationSeconds, rangeEndOverride ?? data.durationSeconds),
  );

  // Filtered notes are hidden by default but never dropped from the response, so
  // turning them on costs a re-filter and not a re-fetch.
  const visibleNotes = useMemo(
    () => (showArtifacts ? data.notes : data.notes.filter((note) => !note.artifact)),
    [data.notes, showArtifacts],
  );
  // What is *heard* never includes an artifact: they are what the pipeline
  // decided was not played, and playing them back would argue with the sheet.
  const audibleNotes = useMemo(() => data.notes.filter((note) => !note.artifact), [data.notes]);

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

  const timelineWidth = Math.max(900, data.durationSeconds * zoom + 160);
  const secondMarks = Math.ceil(data.durationSeconds) + 1;
  // A label every second is unreadable when zoomed out, so they thin out with
  // the zoom rather than overlapping into a smear.
  const labelEvery = zoom >= 120 ? 1 : zoom >= 60 ? 5 : 10;

  // Follow the cursor. While playing it is kept a fixed way into the viewport so
  // the notes flow past at a steady place on screen. While paused — after a seek,
  // a zoom change or a click on the far edge — the timeline only moves when the
  // cursor has actually left the visible stretch, so nudging the transport does
  // not yank the page out from under someone reading it.
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
    const visible = target >= scroller.scrollLeft + margin
      && target <= scroller.scrollLeft + scroller.clientWidth - margin;
    if (visible) return;
    scroller.scrollTo({
      left: Math.max(0, target - scroller.clientWidth * CURSOR_LEAD),
      behavior: "smooth",
    });
  }, [playback.currentSeconds, playback.playing, zoom]);

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

  return (
    <PageContainer
      title="Piano Roll"
      subtitle="Time runs left to right in seconds; each rectangle is as long as the note was held."
      wide
    >
      <SectionCard>
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
          showArtifacts={showArtifacts}
          onShowArtifactsChange={setShowArtifacts}
          artifactCount={data.artifactCount}
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
              ref={scrollerRef}
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
                width={timelineWidth}
                height="100%"
                viewBox={`0 0 ${timelineWidth} ${PIANO_WIDTH}`}
                preserveAspectRatio="none"
                style={{ display: "block", position: "relative" }}
                onClick={(event) => {
                  const bounds = event.currentTarget.getBoundingClientRect();
                  const seconds =
                    ((event.clientX - bounds.left) / bounds.width) * (timelineWidth / zoom);
                  playback.seek(seconds);
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
                        y2={PIANO_WIDTH}
                        stroke={grays.slate}
                        strokeDasharray="5 7"
                        opacity={second % labelEvery === 0 ? 0.45 : 0.18}
                      />
                      {second % labelEvery === 0 ? (
                        <text x={x + 3} y={18} fontSize={11} fill={grays.slate}>
                          {formatTime(second)}
                        </text>
                      ) : null}
                    </g>
                  );
                })}

                {visibleNotes.map((note) => {
                  const key = pianoKeyByRow.get(note.row);
                  if (!key) return null;
                  const x = note.startSeconds * zoom;
                  const y = laneTop(key);
                  const width = Math.max(3, (note.endSeconds - note.startSeconds) * zoom);
                  const active =
                    note.startSeconds <= playback.currentSeconds &&
                    playback.currentSeconds < note.endSeconds;
                  return (
                    <g key={note.id}>
                      <rect
                        x={x}
                        y={y + 1}
                        width={width}
                        height={Math.max(5, key.width - 2)}
                        rx={3}
                        fill={
                          note.artifact
                            ? "none"
                            : active
                              ? semantic.rightHand.sustain
                              : handColors(note.hand).onset
                        }
                        stroke={note.artifact ? semantic.status.warning : grays.ink}
                        strokeWidth={note.artifact ? 1.5 : 0.5}
                        strokeDasharray={note.artifact ? "4 3" : undefined}
                        opacity={note.artifact ? 0.8 : 1}
                      >
                        <title>
                          {`${key.es} · ${formatTime(note.startSeconds)} → ${formatTime(
                            note.endSeconds,
                          )} · ${((note.endSeconds - note.startSeconds) * 1000).toFixed(0)} ms${
                            note.artifact
                              ? ` · filtered${
                                  note.octaveBelow
                                    ? `, ${note.octaveBelow} semitones under a struck note`
                                    : ""
                                }`
                              : ""
                          }`}
                        </title>
                      </rect>
                      {width >= 38 ? (
                        <text x={x + 5} y={y + key.width / 2 + 4} fontSize={10} fill={grays.ink}>
                          {key.es}
                        </text>
                      ) : null}
                    </g>
                  );
                })}

                <line
                  x1={playback.currentSeconds * zoom}
                  x2={playback.currentSeconds * zoom}
                  y1={0}
                  y2={PIANO_WIDTH}
                  stroke={semantic.waveform.cursor}
                  strokeWidth={2}
                />
              </svg>
            </Box>
          </Box>
          <Stack direction="row" spacing={2} sx={{ mt: 1, alignItems: "center", flexWrap: "wrap" }}>
            <Typography variant="caption" color="text.secondary">
              {formatTime(playback.currentSeconds)} of {formatTime(data.durationSeconds)}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ ml: "auto" }}>
              {describeEvents(data.events)}
            </Typography>
          </Stack>
        </SectionCard>
      ) : null}
    </PageContainer>
  );
}

export default PianoRollPage;
