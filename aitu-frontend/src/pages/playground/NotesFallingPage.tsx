/** `/playground/notes-falling` — windowed Synthesia-style matrix view. */

import { useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import SaveIcon from "@mui/icons-material/Save";
import { Link, useNavigate } from "react-router-dom";
import { audioApi, matrixApi, type Granularity, type MatrixCellEdit } from "../../api";
import { usePianoViewData } from "../../hooks/usePianoViewData";
import { ROUTES } from "../../layout/routes";
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

const PLOT_HEIGHT = 520;
const WINDOW_BEATS = 8;

interface StagedMove {
  key: number;
  startFrame: number;
}

function movedNote(note: MatrixPlaybackNote, move: StagedMove | undefined, step: number) {
  if (!move) return note;
  const duration = note.endFrame - note.startFrame;
  return {
    ...note,
    key: move.key,
    startFrame: move.startFrame,
    endFrame: move.startFrame + duration,
    startSeconds: move.startFrame * step,
    endSeconds: (move.startFrame + duration) * step,
  };
}

export function NotesFallingPage() {
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

  const rangeEnd = Math.max(
    rangeStart,
    Math.min(data.durationSeconds, rangeEndOverride ?? data.durationSeconds),
  );
  const displayNotes = useMemo(
    () => data.notes.map((note) => movedNote(note, moves[note.id], data.timeStepSeconds)),
    [data.notes, data.timeStepSeconds, moves],
  );
  const originalAvailable = Boolean(data.peaks);
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

  const leadSeconds = Math.max(
    data.timeStepSeconds,
    WINDOW_BEATS * (60 / artifact.tempoBpm),
  );
  const visibleFrames = Math.max(1, Math.ceil(leadSeconds / data.timeStepSeconds));
  const velocity = PLOT_HEIGHT / (visibleFrames * data.timeStepSeconds);
  const windowedNotes = displayNotes.filter((note) => {
    const bottom = PLOT_HEIGHT - (note.startSeconds - playback.currentSeconds) * velocity;
    const top = bottom - (note.endSeconds - note.startSeconds) * velocity;
    return bottom >= 0 && top <= PLOT_HEIGHT;
  });
  const hasMoves = Object.keys(moves).length > 0;

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
      subtitle="Only the upcoming window is drawn; the keyboard swallows each note as it sounds."
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
          <Typography variant="body2">Loading falling notes…</Typography>
        </Stack>
      ) : null}

      {data.envelope ? (
        <SectionCard
          title="Falling view"
          actions={
            <>
              <Button size="small" disabled={!hasMoves || editBusy} onClick={() => setMoves({})}>
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
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            {visibleFrames} frames ({leadSeconds.toFixed(2)} s) travel through the visible
            window.
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
            <svg
              viewBox={`0 0 ${PIANO_WIDTH} ${PLOT_HEIGHT}`}
              width="100%"
              height="min(58vh, 620px)"
              preserveAspectRatio="none"
              style={{ display: "block" }}
              onPointerUp={(event) => {
                if (!dragging) return;
                const bounds = event.currentTarget.getBoundingClientRect();
                const x = ((event.clientX - bounds.left) / bounds.width) * PIANO_WIDTH;
                const y = ((event.clientY - bounds.top) / bounds.height) * PLOT_HEIGHT;
                const key = nearestPianoKey(x);
                const original = data.notes.find((note) => note.id === dragging);
                const durationFrames = original ? original.endFrame - original.startFrame : 1;
                const latestStart = Math.max(0, data.right.length - durationFrames);
                const dueSeconds =
                  playback.currentSeconds + Math.max(0, (PLOT_HEIGHT - y) / velocity);
                const startFrame = Math.max(
                  0,
                  Math.min(
                    latestStart,
                    Math.round(dueSeconds / data.timeStepSeconds),
                  ),
                );
                setMoves((current) => ({ ...current, [dragging]: { key: key.row, startFrame } }));
                setDragging(null);
              }}
            >
              <defs>
                <clipPath id="falling-window">
                  <rect x={0} y={0} width={PIANO_WIDTH} height={PLOT_HEIGHT} />
                </clipPath>
              </defs>

              {dragging
                ? pianoKeyPositions.map((key) => (
                    <g key={`landing-${key.row}`}>
                      <line
                        x1={key.x + key.width / 2}
                        x2={key.x + key.width / 2}
                        y1={0}
                        y2={PLOT_HEIGHT}
                        stroke={semantic.status.warning}
                        strokeDasharray="7 8"
                        opacity={0.35}
                      />
                      <text
                        x={key.x + key.width / 2}
                        y={16}
                        fontSize={9}
                        fill={semantic.status.warning}
                        transform={`rotate(90 ${key.x + key.width / 2} 16)`}
                      >
                        {key.es}
                      </text>
                    </g>
                  ))
                : null}

              <g clipPath="url(#falling-window)">
                {windowedNotes.map((note) => {
                  const key = pianoKeyByRow.get(note.key);
                  if (!key) return null;
                  const bottom =
                    PLOT_HEIGHT - (note.startSeconds - playback.currentSeconds) * velocity;
                  const height = Math.max(
                    8,
                    (note.endSeconds - note.startSeconds) * velocity,
                  );
                  const top = bottom - height;
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
                        x={key.x + 1}
                        y={top}
                        width={Math.max(6, key.width - 2)}
                        height={height}
                        rx={3}
                        fill={
                          active ? semantic.rightHand.sustain : handColors(note.hand).sustain
                        }
                        stroke={staged ? semantic.status.warning : grays.slate}
                        strokeWidth={staged ? 4 : 1}
                      />
                      <text
                        x={key.x + key.width / 2}
                        y={top + 8}
                        fontSize={10}
                        fill={grays.ink}
                        transform={`rotate(90 ${key.x + key.width / 2} ${top + 8})`}
                      >
                        {key.es}
                      </text>
                    </g>
                  );
                })}
              </g>
              <line
                x1={0}
                x2={PIANO_WIDTH}
                y1={PLOT_HEIGHT - 1}
                y2={PLOT_HEIGHT - 1}
                stroke={semantic.pressedKey}
                strokeWidth={3}
              />
            </svg>
            <Piano
              width="100%"
              height="auto"
              pressedKeys={playback.pressedKeys}
              ariaLabel="Piano receiving the falling notes"
            />
          </Box>
          <Stack direction="row" spacing={2} sx={{ mt: 1, alignItems: "center" }}>
            <Typography variant="caption" color="text.secondary">
              {windowedNotes.length} rectangles currently rendered of {displayNotes.length}
            </Typography>
            <Button
              size="small"
              onClick={() => navigate(`${ROUTES.playgroundMatrix}?frame=${playback.currentFrame}`)}
            >
              Open landing frame in Matrix
            </Button>
          </Stack>
        </SectionCard>
      ) : null}
    </PageContainer>
  );
}

export default NotesFallingPage;
