/** `/playground/piano-roll` — horizontal time view with shared playback. */

import { useEffect, useMemo, useRef, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import SaveIcon from "@mui/icons-material/Save";
import { Link, useNavigate } from "react-router-dom";
import { audioApi, matrixApi, type Granularity, type MatrixCellEdit } from "../../api";
import WaveformView from "../../components/audio/WaveformView";
import { usePianoViewData } from "../../hooks/usePianoViewData";
import { ROUTES } from "../../layout/routes";
import { formatFrameLabel } from "../../audio/time";
import { nearestPianoKey, PIANO_WIDTH, pianoKeyByRow, pianoKeyPositions } from "../../piano/keyPositions";
import Piano from "../../piano/Piano";
import type { MatrixPlaybackNote } from "../../playback/matrixNotes";
import { PlayerToolbar } from "../../playback/PlayerToolbar";
import {
  useMatrixPlayback,
  type PlaybackSource,
} from "../../playback/useMatrixPlayback";
import { useWorkingArtifact } from "../../state/useWorkingArtifact";
import { grays, handColors, PageContainer, SectionCard, semantic } from "../../ui";

const PIXELS_PER_SECOND = 120;
const VIEW_HEIGHT = "min(68vh, 760px)";

interface StagedMove {
  key: number;
  startFrame: number;
}

function movedNote(note: MatrixPlaybackNote, move: StagedMove | undefined, step: number) {
  if (!move) return note;
  const durationFrames = note.endFrame - note.startFrame;
  return {
    ...note,
    key: move.key,
    startFrame: move.startFrame,
    endFrame: move.startFrame + durationFrames,
    startSeconds: move.startFrame * step,
    endSeconds: (move.startFrame + durationFrames) * step,
  };
}

export function PianoRollPage() {
  const { artifact, update, hasArtifact } = useWorkingArtifact();
  const navigate = useNavigate();
  const [revision, setRevision] = useState(0);
  const data = usePianoViewData(artifact, revision);
  const [source, setSource] = useState<PlaybackSource>("piano");
  const [speed, setSpeed] = useState(1);
  const [rangeStart, setRangeStart] = useState(0);
  const [rangeEndOverride, setRangeEndOverride] = useState<number | null>(null);
  const [moves, setMoves] = useState<Record<string, StagedMove>>({});
  const [dragging, setDragging] = useState<string | null>(null);
  const [editBusy, setEditBusy] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const scrollerRef = useRef<HTMLDivElement | null>(null);

  const rangeEnd = Math.max(
    rangeStart,
    Math.min(data.durationSeconds, rangeEndOverride ?? data.durationSeconds),
  );
  const displayNotes = useMemo(
    () => data.notes.map((note) => movedNote(note, moves[note.id], data.timeStepSeconds)),
    [data.notes, data.timeStepSeconds, moves],
  );
  const originalAvailable = Boolean(data.peaks);
  const alignedPeaks = data.peaks;
  const playback = useMatrixPlayback({
    notes: displayNotes,
    timeStepSeconds: data.timeStepSeconds,
    durationSeconds: data.durationSeconds,
    selectionStart: rangeStart,
    selectionEnd: rangeEnd,
    speed,
    source: originalAvailable ? source : "piano",
    originalAudioUrl:
      originalAvailable && data.audioUuid ? audioApi.fileUrl(data.audioUuid, true) : null,
    originalAudioOffset: 0,
  });

  const timelineWidth = Math.max(900, data.durationSeconds * PIXELS_PER_SECOND + 160);
  const frameCount = data.right.length;
  const hasMoves = Object.keys(moves).length > 0;

  useEffect(() => {
    if (!playback.playing || !scrollerRef.current) return;
    const target = playback.currentSeconds * PIXELS_PER_SECOND;
    scrollerRef.current.scrollTo({
      left: Math.max(0, target - scrollerRef.current.clientWidth * 0.28),
      behavior: "auto",
    });
  }, [playback.currentSeconds, playback.playing]);

  const saveMoves = async () => {
    if (!data.audioUuid) return;
    const edits: MatrixCellEdit[] = [];
    for (const note of data.notes) {
      const move = moves[note.id];
      if (!move) continue;
      edits.push({ frame: note.startFrame, key: note.key, value: 0 });
      edits.push({ frame: move.startFrame, key: move.key, value: 1 });
      for (let offset = 1; offset < note.endFrame - note.startFrame; offset += 1) {
        edits.push({ frame: move.startFrame + offset, key: move.key, value: -1 });
      }
    }
    setEditBusy(true);
    setEditError(null);
    try {
      await matrixApi.edit(data.audioUuid, {
        tempoBpm: artifact.tempoBpm,
        granularity: artifact.granularity,
        edits,
        persist: true,
      });
      setMoves({});
      setRevision((current) => current + 1);
    } catch (caught) {
      setEditError(caught instanceof Error ? caught.message : "The staged moves could not be saved.");
    } finally {
      setEditBusy(false);
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

  return (
    <PageContainer
      title="Piano Roll"
      subtitle="Time moves left to right; drag a rectangle to correct its key or frame."
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
          tempoBpm={artifact.tempoBpm}
          onTempoChange={(tempoBpm) => update({ tempoBpm })}
          granularity={artifact.granularity}
          onGranularityChange={(granularity: Granularity) => update({ granularity })}
          rangeStart={rangeStart}
          rangeEnd={rangeEnd}
          durationSeconds={data.durationSeconds}
          onRangeChange={(start, end) => {
            setRangeStart(start);
            setRangeEndOverride(end);
          }}
        />
      </SectionCard>

      {data.error ? <Alert severity="error">{data.error}</Alert> : null}
      {editError ? <Alert severity="error">{editError}</Alert> : null}
      {data.loading ? (
        <Stack direction="row" spacing={1} sx={{ alignItems: "center", py: 4 }}>
          <CircularProgress size={18} />
          <Typography variant="body2">Loading piano roll…</Typography>
        </Stack>
      ) : null}

      {data.envelope ? (
        <SectionCard
          title="Roll view"
          actions={
            <>
              <Button
                size="small"
                disabled={!hasMoves || editBusy}
                onClick={() => setMoves({})}
              >
                Cancel moves
              </Button>
              <Button
                size="small"
                variant="contained"
                startIcon={<SaveIcon />}
                disabled={!hasMoves || editBusy}
                onClick={() => void saveMoves()}
              >
                Save {hasMoves ? `(${Object.keys(moves).length})` : ""}
              </Button>
            </>
          }
        >
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
              {alignedPeaks ? (
                <Box
                  sx={{
                    position: "absolute",
                    inset: 0,
                    width: timelineWidth,
                    height: "100%",
                    pointerEvents: "none",
                  }}
                >
                  <WaveformView peaks={alignedPeaks} height={500} watermark />
                </Box>
              ) : null}
              <svg
                width={timelineWidth}
                height="100%"
                viewBox={`0 0 ${timelineWidth} ${PIANO_WIDTH}`}
                preserveAspectRatio="none"
                style={{ display: "block", position: "relative" }}
                onClick={(event) => {
                  if (dragging) return;
                  const bounds = event.currentTarget.getBoundingClientRect();
                  const seconds =
                    ((event.clientX - bounds.left) / bounds.width) *
                    (timelineWidth / PIXELS_PER_SECOND);
                  playback.seek(seconds);
                }}
                onPointerUp={(event) => {
                  if (!dragging) return;
                  const bounds = event.currentTarget.getBoundingClientRect();
                  const x = ((event.clientX - bounds.left) / bounds.width) * timelineWidth;
                  const y = ((event.clientY - bounds.top) / bounds.height) * PIANO_WIDTH;
                  const key = nearestPianoKey(y);
                  const original = data.notes.find((note) => note.id === dragging);
                  const durationFrames = original
                    ? original.endFrame - original.startFrame
                    : 1;
                  const latestStart = Math.max(0, frameCount - durationFrames);
                  const startFrame = Math.max(
                    0,
                    Math.min(
                      latestStart,
                      Math.round(x / PIXELS_PER_SECOND / data.timeStepSeconds),
                    ),
                  );
                  setMoves((current) => ({ ...current, [dragging]: { key: key.row, startFrame } }));
                  setDragging(null);
                }}
              >
                {Array.from({ length: frameCount }, (_, frame) => {
                  const x = frame * data.timeStepSeconds * PIXELS_PER_SECOND;
                  return (
                    <g key={frame}>
                      <line
                        x1={x}
                        x2={x}
                        y1={0}
                        y2={PIANO_WIDTH}
                        stroke={grays.slate}
                        strokeDasharray="5 7"
                        opacity={0.45}
                      />
                      <text x={x + 3} y={18} fontSize={11} fill={grays.slate}>
                        {frame}
                      </text>
                    </g>
                  );
                })}

                {dragging
                  ? pianoKeyPositions.map((key) => (
                      <g key={`guide-${key.row}`}>
                        <line
                          x1={0}
                          x2={timelineWidth}
                          y1={key.x + key.width / 2}
                          y2={key.x + key.width / 2}
                          stroke={semantic.status.warning}
                          strokeDasharray="7 8"
                          opacity={0.24}
                        />
                        <text
                          x={6}
                          y={key.x + key.width / 2}
                          fontSize={9}
                          fill={semantic.status.warning}
                        >
                          {key.es}
                        </text>
                      </g>
                    ))
                  : null}

                {displayNotes.map((note) => {
                  const key = pianoKeyByRow.get(note.key);
                  if (!key) return null;
                  const x = note.startSeconds * PIXELS_PER_SECOND;
                  const width = Math.max(
                    5,
                    (note.endSeconds - note.startSeconds) * PIXELS_PER_SECOND,
                  );
                  const active =
                    note.startSeconds <= playback.currentSeconds &&
                    playback.currentSeconds < note.endSeconds;
                  const staged = Boolean(moves[note.id]);
                  return (
                    <g
                      key={note.id}
                      onPointerDown={(event) => {
                        event.stopPropagation();
                        setDragging(note.id);
                      }}
                      style={{ cursor: "grab" }}
                    >
                      <rect
                        x={x}
                        y={key.x + 1}
                        width={width}
                        height={Math.max(5, key.width - 2)}
                        rx={3}
                        fill={
                          active
                            ? semantic.rightHand.sustain
                            : handColors(note.hand).onset
                        }
                        stroke={staged ? semantic.status.warning : grays.ink}
                        strokeWidth={staged ? 3 : 0.5}
                      />
                      {width >= 38 ? (
                        <text
                          x={x + 5}
                          y={key.x + key.width / 2 + 4}
                          fontSize={10}
                          fill={grays.ink}
                        >
                          {key.es}
                        </text>
                      ) : null}
                    </g>
                  );
                })}

                <line
                  x1={playback.currentSeconds * PIXELS_PER_SECOND}
                  x2={playback.currentSeconds * PIXELS_PER_SECOND}
                  y1={0}
                  y2={PIANO_WIDTH}
                  stroke={semantic.waveform.cursor}
                  strokeWidth={2}
                />
              </svg>
            </Box>
          </Box>
          <Stack direction="row" spacing={2} sx={{ mt: 1, alignItems: "center" }}>
            <Typography variant="caption" color="text.secondary">
              {formatFrameLabel(playback.currentFrame, playback.currentSeconds)}
            </Typography>
            <Button
              size="small"
              onClick={() => navigate(`${ROUTES.playgroundMatrix}?frame=${playback.currentFrame}`)}
            >
              Open this frame in Matrix
            </Button>
            <Typography variant="caption" color="text.secondary" sx={{ ml: "auto" }}>
              {displayNotes.length} notes · {frameCount} frames
            </Typography>
          </Stack>
        </SectionCard>
      ) : null}
    </PageContainer>
  );
}

export default PianoRollPage;
