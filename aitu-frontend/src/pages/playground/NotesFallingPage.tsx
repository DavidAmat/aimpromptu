/**
 * `/playground/notes-falling` — the Synthesia view: notes drop onto the keyboard
 * and are swallowed at the moment they sound.
 *
 * Restored from Epic 8, with one substantive change. The window used to be
 * measured in **beats** — eight of them, converted to seconds through the piece's
 * BPM — so how far ahead you could see depended on a tempo the app no longer
 * has. It is now a plain lead time in seconds that you set yourself, which is
 * also the honest unit: what a player wants is "show me the next two seconds",
 * not "show me the next eight beats of a tempo somebody typed in".
 *
 * Everything else is as it was: only the notes inside the window are drawn, the
 * keyboard lights up as each rectangle crosses the line, and drop speed follows
 * the window so a longer lead means slower travel over the same distance.
 */

import { useMemo, useState } from "react";
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
import { usePlayedNotes } from "../../hooks/usePlayedNotes";
import { ROUTES } from "../../layout/routes";
import { formatTime } from "../../audio/time";
import { PIANO_WIDTH, pianoKeyByRow } from "../../piano/keyPositions";
import Piano from "../../piano/Piano";
import { describeEvents } from "../../playback/playedNotes";
import { PlayerToolbar } from "../../playback/PlayerToolbar";
import { usePlayback, type PlaybackSource } from "../../playback/usePlayback";
import { useWorkingArtifact } from "../../state/useWorkingArtifact";
import { grays, handColors, PageContainer, SectionCard, semantic } from "../../ui";

const PLOT_HEIGHT = 520;
/** How far ahead the window shows, in seconds. */
const LEAD_OPTIONS = [1, 1.5, 2, 3, 4, 6, 8];
const DEFAULT_LEAD = 3;
/** Below this height a rectangle is a sliver, so it is floored to stay visible. */
const MIN_NOTE_HEIGHT = 8;

export function NotesFallingPage() {
  const { artifact, hasArtifact } = useWorkingArtifact();
  const data = usePlayedNotes(artifact);
  const [source, setSource] = useState<PlaybackSource>("piano");
  const [speed, setSpeed] = useState(1);
  const [leadSeconds, setLeadSeconds] = useState(DEFAULT_LEAD);
  const [showArtifacts, setShowArtifacts] = useState(false);
  const [rangeStart, setRangeStart] = useState(0);
  const [rangeEndOverride, setRangeEndOverride] = useState<number | null>(null);

  const rangeEnd = Math.max(
    rangeStart,
    Math.min(data.durationSeconds, rangeEndOverride ?? data.durationSeconds),
  );

  const visibleNotes = useMemo(
    () => (showArtifacts ? data.notes : data.notes.filter((note) => !note.artifact)),
    [data.notes, showArtifacts],
  );
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

  // Pixels per second of travel. The window is the whole plot, so a 3 s lead
  // over a 520 px drop is ~173 px/s and a 6 s lead is half that.
  const velocity = PLOT_HEIGHT / leadSeconds;
  const windowedNotes = visibleNotes.filter((note) => {
    const bottom = PLOT_HEIGHT - (note.startSeconds - playback.currentSeconds) * velocity;
    const top = bottom - (note.endSeconds - note.startSeconds) * velocity;
    return bottom >= 0 && top <= PLOT_HEIGHT;
  });

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
      subtitle="Only the seconds ahead are drawn; the keyboard swallows each note as it sounds."
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
            <svg
              viewBox={`0 0 ${PIANO_WIDTH} ${PLOT_HEIGHT}`}
              width="100%"
              height="min(58vh, 620px)"
              preserveAspectRatio="none"
              style={{ display: "block" }}
            >
              <defs>
                <clipPath id="falling-window">
                  <rect x={0} y={0} width={PIANO_WIDTH} height={PLOT_HEIGHT} />
                </clipPath>
              </defs>

              <g clipPath="url(#falling-window)">
                {windowedNotes.map((note) => {
                  const key = pianoKeyByRow.get(note.row);
                  if (!key) return null;
                  const bottom =
                    PLOT_HEIGHT - (note.startSeconds - playback.currentSeconds) * velocity;
                  const height = Math.max(
                    MIN_NOTE_HEIGHT,
                    (note.endSeconds - note.startSeconds) * velocity,
                  );
                  const top = bottom - height;
                  const active =
                    note.startSeconds <= playback.currentSeconds &&
                    playback.currentSeconds < note.endSeconds;
                  return (
                    <g key={note.id}>
                      <rect
                        x={key.x + 1}
                        y={top}
                        width={Math.max(6, key.width - 2)}
                        height={height}
                        rx={3}
                        fill={
                          note.artifact
                            ? "none"
                            : active
                              ? semantic.rightHand.sustain
                              : handColors(note.hand).sustain
                        }
                        stroke={note.artifact ? semantic.status.warning : grays.slate}
                        strokeWidth={note.artifact ? 1.5 : 1}
                        strokeDasharray={note.artifact ? "4 3" : undefined}
                      />
                      {height >= 26 ? (
                        <text
                          x={key.x + key.width / 2}
                          y={top + 8}
                          fontSize={10}
                          fill={note.artifact ? semantic.status.warning : grays.ink}
                          transform={`rotate(90 ${key.x + key.width / 2} ${top + 8})`}
                        >
                          {key.es}
                        </text>
                      ) : null}
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
          <Stack direction="row" spacing={2} sx={{ mt: 1, alignItems: "center", flexWrap: "wrap" }}>
            <Typography variant="caption" color="text.secondary">
              {formatTime(playback.currentSeconds)} · {windowedNotes.length} in the window of{" "}
              {visibleNotes.length}
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

export default NotesFallingPage;
