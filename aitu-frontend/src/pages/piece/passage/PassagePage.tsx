/**
 * Recording in Sheet: the page of a passage (implementation 02, plan section 13, Phase 9).
 *
 * `/projects/:id/passages/:passageId`. **Current** is the copy of the marked frames, read only;
 * **Proposal** is a take, once it is read, drawn by the whole sheet page with every toolbox and its
 * undo, named with the passage's key and figure so the two read alike. A take is recorded here (or
 * added from a file), the stretch of it to keep is chosen on its waveform, and **Write the
 * proposal** does the rest as one job: the transcription, the hands, the sheet.
 *
 * **Promote** writes the take into the song in one write: fitted into the window (the song keeps
 * its length, with the original audio or the recording), or the whole take in place of the passage
 * (the song gets longer or shorter). The sheet then opens with the promotion as its last step, so
 * Command-Z takes it back.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Slider from "@mui/material/Slider";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import ContentCutIcon from "@mui/icons-material/ContentCutOutlined";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlineOutlined";
import FiberManualRecordIcon from "@mui/icons-material/FiberManualRecordOutlined";
import FileUploadIcon from "@mui/icons-material/FileUploadOutlined";
import PauseIcon from "@mui/icons-material/Pause";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import StopIcon from "@mui/icons-material/Stop";
import SwapHorizIcon from "@mui/icons-material/SwapHorizOutlined";
import {
  audioApi,
  matrixApi,
  passagesApi,
  timeScoreApi,
  type OpenPassage,
  type PlayedNote,
  type PromotionAudio,
  type PromotionFacts,
  type PromotionMode,
  type SavedRhythm,
} from "../../../api";
import { useMidiInput } from "../../../audio/useMidiInput";
import { fileNameFor, useRecorder } from "../../../audio/useRecorder";
import { formatTime } from "../../../audio/time";
import LiveLevelBars from "../../../components/audio/LiveLevelBars";
import WaveformRangeSelector, {
  type AudioRange,
} from "../../../components/audio/WaveformRangeSelector";
import ProgressBanner from "../../../components/ProgressBanner";
import type { ScorePlayerControls } from "../../../components/time/ScorePlayer";
import { useProgress } from "../../../hooks/useProgress";
import { ROUTES } from "../../../layout/routes";
import { useWorkingArtifact } from "../../../state/useWorkingArtifact";
import {
  ConfirmDialog,
  EmptyState,
  IconAction,
  PageHeader,
  PillButton,
  RowMenu,
  Section,
  Segmented,
  Toolbox,
  type RowMenuItem,
} from "../../../ui";
import SheetPage from "../sheet/SheetPage";

/** The speeds a take can be played into the song at, as powers of two (×0.25 to ×4). */
const SPEED_STEPS = { min: -2, max: 2, step: 1 / 12 };

/** What each kind of mark of `sheet.json` is called when a promotion takes it away. */
const MARK_WORDS: Record<string, [string, string]> = {
  fingers: ["fingering", "fingerings"],
  ottavas: ["octave bracket", "octave brackets"],
  lyrics: ["lyrics piece", "lyrics pieces"],
  overrides: ["figure set by hand", "figures set by hand"],
  beam_breaks: ["beam break", "beam breaks"],
  beam_joins: ["beam join", "beam joins"],
  hidden_notes: ["note taken off", "notes taken off"],
  grace_notes: ["grace note", "grace notes"],
  trills: ["trill", "trills"],
  cue_ranges: ["small print stretch", "small print stretches"],
  spacings: ["spacing", "spacings"],
  even_spacings: ["even spacing", "even spacings"],
  staff_gaps: ["staff gap", "staff gaps"],
};

function clock(ms: number): string {
  const seconds = Math.round(ms / 1000);
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

function said(caught: unknown, fallback: string): string {
  return caught instanceof Error && caught.message ? caught.message : fallback;
}

/** "2 fingerings and 1 octave bracket", or `null` for none. */
function marksWords(dropped: Record<string, number>): string | null {
  const parts = Object.entries(dropped)
    .filter(([, count]) => count > 0)
    .map(([field, count]) => {
      const [one, many] = MARK_WORDS[field] ?? ["mark", "marks"];
      return `${count} ${count === 1 ? one : many}`;
    });
  if (parts.length === 0) return null;
  return parts.length === 1 ? parts[0]! : `${parts.slice(0, -1).join(", ")} and ${parts.at(-1)}`;
}

/** The browser lets a page use the microphone only on a secure address (HTTPS or localhost). */
/** Where the chosen microphone is remembered, in this browser only. */
const INPUT_KEY = "aitu.recorder.input";
/** Where the source of a take's notes is remembered: the microphone or a MIDI piano. */
const SOURCE_KEY = "aitu.recorder.source";
/** The microphone list's choice for a take played on a MIDI piano with no sound recorded. */
const NO_SOUND = "none";

type NotesFrom = "microphone" | "midi";

function remembered(key: string, fallback: string): string {
  try {
    return localStorage.getItem(key) ?? fallback;
  } catch {
    return fallback;
  }
}

function remember(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // A private window: the choice lasts this page.
  }
}
const MICROPHONE = typeof navigator !== "undefined" && Boolean(navigator.mediaDevices?.getUserMedia);

export function PassagePage() {
  const { id: projectId = "", passageId = "" } = useParams();
  const navigate = useNavigate();
  const { artifact } = useWorkingArtifact();
  const frameMs = artifact.frameMs;
  const [passage, setPassage] = useState<OpenPassage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refused, setRefused] = useState<string | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        setPassage(await passagesApi.get(passageId, signal));
        setError(null);
      } catch (caught) {
        if (signal?.aborted) return;
        setError(said(caught, "Could not open this passage."));
      }
    },
    [passageId],
  );
  useEffect(() => {
    const controller = new AbortController();
    passagesApi
      .get(passageId, controller.signal)
      .then(setPassage)
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "Could not open this passage."));
      });
    return () => controller.abort();
  }, [passageId]);

  const take = passage?.takes.find((one) => one.id === passage.take) ?? null;
  const lengthMs = passage ? passage.toMs - passage.fromMs : 0;
  const isNew = passage !== null && lengthMs <= 0;
  const speed = passage?.speed ?? 1;

  // ------------------------------------------------------------------ the two players

  const currentPlayer = useRef<ScorePlayerControls | null>(null);
  const proposalPlayer = useRef<ScorePlayerControls | null>(null);
  const [currentPlaying, setCurrentPlaying] = useState(false);
  const [proposalPlaying, setProposalPlaying] = useState(false);
  // One sound at a time: starting one sheet stops the other.
  const reportCurrentPlaying = useCallback((now: boolean) => {
    setCurrentPlaying(now);
  }, []);
  const reportProposalPlaying = useCallback((now: boolean) => {
    setProposalPlaying(now);
  }, []);
  const toggleCurrent = () => {
    if (!currentPlaying && proposalPlaying) proposalPlayer.current?.toggle();
    currentPlayer.current?.toggle();
  };
  useEffect(() => {
    if (proposalPlaying && currentPlaying) currentPlayer.current?.toggle();
    // Only when the Proposal starts: the Current's own start is handled by its button.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [proposalPlaying]);

  // ------------------------------------------------------------------ speed and window

  const [speedDraft, setSpeedDraft] = useState<number | null>(null);
  const shownSpeed = speedDraft ?? speed;
  const update = useCallback(
    async (body: { take?: string; speed?: number; windowMs?: number }) => {
      try {
        setPassage(await passagesApi.update(passageId, body));
      } catch (caught) {
        setRefused(said(caught, "Could not change the passage."));
      }
    },
    [passageId],
  );
  const [windowDraft, setWindowDraft] = useState<number | null>(null);
  const frameWindow = useMemo(() => {
    if (!passage || isNew || take?.state !== "ready") return undefined;
    const from = windowDraft ?? Math.round(passage.windowMs / frameMs);
    return { fromColumn: from, toColumn: from + Math.max(1, Math.round((lengthMs * shownSpeed) / frameMs)) };
  }, [passage, isNew, take, windowDraft, frameMs, lengthMs, shownSpeed]);
  const moveWindow = useCallback(
    (fromColumn: number, done: boolean) => {
      setWindowDraft(fromColumn);
      if (done) void update({ windowMs: fromColumn * frameMs }).then(() => setWindowDraft(null));
    },
    [update, frameMs],
  );
  /** The speed at which the whole take fills the window, and the window at its start. */
  const fitTake = () => {
    if (!passage?.takeMs || lengthMs <= 0) return;
    const fitted = Math.min(4, Math.max(0.25, passage.takeMs / lengthMs));
    void update({ speed: Math.round(fitted * 100) / 100, windowMs: 0 });
  };

  // ------------------------------------------------------------------ recording

  const recorder = useRecorder();
  const playAlong = useRef<HTMLAudioElement | null>(null);
  const [recorderOpen, setRecorderOpen] = useState(false);
  /** The waveform of the take on show, to choose the stretch of it again. */
  const [editingRange, setEditingRange] = useState(false);
  const [withOriginal, setWithOriginal] = useState(false);
  /** The microphones of this computer, and the one chosen (kept in this browser). */
  const [inputs, setInputs] = useState<MediaDeviceInfo[]>([]);
  const [input, setInput] = useState<string>(() => remembered(INPUT_KEY, ""));
  const chooseInput = (deviceId: string) => {
    setInput(deviceId);
    remember(INPUT_KEY, deviceId);
  };
  /** A MIDI piano: its keys are the take's notes; the microphone, if any, records its sound. */
  const midi = useMidiInput();
  const [notesFrom, setNotesFrom] = useState<NotesFrom>(() =>
    midi.supported && remembered(SOURCE_KEY, "microphone") === "midi" ? "midi" : "microphone",
  );
  const chooseNotesFrom = (next: NotesFrom) => {
    setNotesFrom(next);
    remember(SOURCE_KEY, next);
    if (next === "midi") void midi.request();
  };
  const { request: requestMidi } = midi;
  useEffect(() => {
    if (recorderOpen && notesFrom === "midi") void requestMidi();
  }, [recorderOpen, notesFrom, requestMidi]);
  const [piano, setPiano] = useState("");
  const pianoChosen = midi.inputs.some((one) => one.id === piano) ? piano : "";
  /** The keys of the take being recorded, kept until its sound arrives. */
  const playedNow = useRef<PlayedNote[] | null>(null);
  /** A take played on a MIDI piano with no sound: its start, while it is recorded. */
  const [silentSince, setSilentSince] = useState<number | null>(null);
  const [silentSeconds, setSilentSeconds] = useState(0);
  useEffect(() => {
    if (silentSince === null) return;
    const timer = window.setInterval(() => setSilentSeconds((performance.now() - silentSince) / 1000), 250);
    return () => window.clearInterval(timer);
  }, [silentSince]);
  // Their names are known once the page may use the microphone, so they are read again after a
  // take and whenever a device comes or goes.
  useEffect(() => {
    if (!recorderOpen || !MICROPHONE) return;
    const read = () =>
      void navigator.mediaDevices
        .enumerateDevices()
        .then((found) => setInputs(found.filter((one) => one.kind === "audioinput" && one.deviceId)))
        .catch(() => setInputs([]));
    read();
    navigator.mediaDevices.addEventListener("devicechange", read);
    return () => navigator.mediaDevices.removeEventListener("devicechange", read);
  }, [recorderOpen, recorder.status]);
  const inputChosen =
    input === NO_SOUND && notesFrom === "midi"
      ? NO_SOUND
      : inputs.some((one) => one.deviceId === input)
        ? input
        : "";
  const withMidi = notesFrom === "midi";
  const withSound = MICROPHONE && !(withMidi && inputChosen === NO_SOUND);
  const recording = recorder.status === "recording" || silentSince !== null;
  const [sending, setSending] = useState(false);
  const fileInput = useRef<HTMLInputElement | null>(null);

  const stopAlong = () => {
    playAlong.current?.pause();
    playAlong.current = null;
  };
  const beginRecording = async () => {
    setRefused(null);
    playedNow.current = null;
    if (withSound) await recorder.start(inputChosen && inputChosen !== NO_SOUND ? inputChosen : undefined);
    if (withMidi) {
      // The keys are timed from the moment the sound starts recording, so the two line up.
      const zero = performance.now();
      midi.start(pianoChosen, zero);
      if (!withSound) {
        setSilentSeconds(0);
        setSilentSince(zero);
      }
    }
    if (withOriginal && passage && !isNew) {
      // The passage as it sounds, slowed (or hurried) to the speed the take is played at.
      const along = new Audio(audioApi.fileUrl(passage.current));
      along.playbackRate = 1 / speed;
      along.preservesPitch = true;
      playAlong.current = along;
      void along.play();
    }
  };
  const endRecording = () => {
    stopAlong();
    if (withMidi) {
      playedNow.current = midi.stop();
      if (silentSince !== null) {
        setSilentSince(null);
        const notes = playedNow.current;
        playedNow.current = null;
        if (notes.length === 0) {
          setRefused("No key was played on the MIDI piano.");
          return;
        }
        void sendTake(null, notes);
        return;
      }
    }
    recorder.stop();
  };
  useEffect(() => () => stopAlong(), []);

  const sendTake = useCallback(
    async (file: File | null, notes?: readonly PlayedNote[]) => {
      setSending(true);
      setRefused(null);
      try {
        setPassage(await passagesApi.addTake(passageId, file, notes));
        setRecorderOpen(false);
        setEditingRange(true);
      } catch (caught) {
        setRefused(said(caught, "Could not keep that take."));
      } finally {
        setSending(false);
      }
    },
    [passageId],
  );
  // A take that has just been recorded is kept at once, as a new take.
  const { blob, reset } = recorder;
  const keepRecorded = useCallback(
    async (recorded: Blob) => {
      const name = fileNameFor(recorded.type, "take");
      if (!name) {
        setRefused("This browser recorded a format the app does not read.");
        return;
      }
      // With the keys of a MIDI piano when they were played with it.
      const notes = playedNow.current ?? undefined;
      playedNow.current = null;
      await sendTake(new File([recorded], name, { type: recorded.type }), notes);
    },
    [sendTake],
  );
  useEffect(() => {
    if (!blob) return;
    // After this render, like the recorder's own state: the take is sent from a callback.
    const waiting = window.setTimeout(() => {
      reset();
      void keepRecorded(blob);
    }, 0);
    return () => window.clearTimeout(waiting);
  }, [blob, reset, keepRecorded]);

  // ------------------------------------------------------------------ the stretch of the take

  const [range, setRange] = useState<AudioRange | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const followed = jobId ?? take?.jobId ?? null;
  const progress = useProgress(followed ? matrixApi.progressUrl(followed) : null);
  const showRange = take !== null && (take.state !== "ready" || editingRange);
  const writeProposal = async () => {
    if (!take) return;
    const kept = range ?? { startSeconds: take.fromSeconds, endSeconds: take.toSeconds };
    setRefused(null);
    try {
      const job = await passagesApi.readTake(passageId, take.id, kept.startSeconds, kept.endSeconds);
      setJobId(job.jobId);
    } catch (caught) {
      setRefused(said(caught, "Could not read that take."));
    }
  };
  const afterRead = useCallback(
    async (read: boolean) => {
      await load();
      if (read) setEditingRange(false);
      setJobId(null);
    },
    [load],
  );
  useEffect(() => {
    if (progress.status !== "done" && progress.status !== "error") return;
    const read = progress.status === "done";
    const waiting = window.setTimeout(() => void afterRead(read), 0);
    return () => window.clearTimeout(waiting);
  }, [progress.status, afterRead]);
  const loadTakeWaveform = useCallback(
    (points: number, signal: AbortSignal) =>
      take ? audioApi.waveform(take.id, points, signal) : Promise.reject(new Error("No take")),
    [take],
  );

  // ------------------------------------------------------------------ promote

  const proposalSheet = useRef<SavedRhythm | null>(null);
  const keepSheet = useCallback((sheet: SavedRhythm | null) => {
    proposalSheet.current = sheet;
  }, []);
  const [promoteAnchor, setPromoteAnchor] = useState<HTMLElement | null>(null);
  const [promoting, setPromoting] = useState<PromotionMode | null>(null);
  const [audioChoice, setAudioChoice] = useState<PromotionAudio>("recording");
  const [facts, setFacts] = useState<PromotionFacts | null>(null);
  const [writing, setWriting] = useState(false);
  const askedAudio: PromotionAudio = promoting === "window" ? audioChoice : "recording";
  useEffect(() => {
    if (!promoting) return;
    let gone = false;
    passagesApi
      .facts(passageId, {
        mode: promoting,
        audio: askedAudio,
        ...(proposalSheet.current ? { sheet: proposalSheet.current } : {}),
      })
      .then((found) => {
        if (!gone) setFacts(found);
      })
      .catch((caught: unknown) => {
        if (!gone) setRefused(said(caught, "Could not work out the promotion."));
      });
    return () => {
      gone = true;
    };
  }, [promoting, askedAudio, passageId]);
  const promote = async () => {
    if (!promoting || !passage) return;
    setWriting(true);
    setRefused(null);
    try {
      const before = await timeScoreApi.rhythm(passage.part).catch(() => null);
      const done = await passagesApi.promote(passageId, {
        mode: promoting,
        audio: askedAudio,
        ...(proposalSheet.current ? { sheet: proposalSheet.current } : {}),
      });
      navigate(ROUTES.project(done.projectId, "sheet"), {
        state: { promoted: { ...done, before } },
      });
    } catch (caught) {
      setRefused(said(caught, "Could not promote the take."));
      setWriting(false);
    }
  };

  const [discarding, setDiscarding] = useState(false);
  const discard = async () => {
    try {
      await passagesApi.discard(passageId);
    } catch {
      // Gone already: the sheet is where the reader goes either way.
    }
    navigate(ROUTES.project(projectId, "sheet"));
  };

  // ------------------------------------------------------------------ the page

  if (error) {
    return (
      <Box sx={{ px: { xs: 2, md: 3 }, pt: 1 }}>
        <PageHeader title="Passage" back={{ to: ROUTES.project(projectId, "sheet"), label: "Back to the sheet" }} />
        <EmptyState message={error} />
      </Box>
    );
  }
  if (!passage) return null;

  const ready = take?.state === "ready" && !showRange;
  const title = passage.title;
  const menu: RowMenuItem[] = [
    ...(take
      ? [
          {
            label: `Delete ${take.name}`,
            icon: <DeleteOutlineIcon fontSize="small" />,
            onClick: () =>
              void passagesApi
                .deleteTake(passageId, take.id)
                .then(setPassage)
                .catch((caught: unknown) => setRefused(said(caught, "Could not delete that take."))),
          },
        ]
      : []),
    {
      label: "Discard this passage",
      icon: <DeleteOutlineIcon fontSize="small" />,
      danger: true,
      onClick: () => setDiscarding(true),
    },
  ];
  const recordAction = (
    <IconAction
      title="Record a take"
      icon={<FiberManualRecordIcon />}
      onClick={() => setRecorderOpen(true)}
      placement="top"
      data-testid="passage-record"
    />
  );
  const barActions = (
    <>
      {recordAction}
      <IconAction
        title="Choose the stretch of the take"
        icon={<ContentCutIcon />}
        onClick={() => setEditingRange(true)}
        placement="top"
      />
      {isNew ? null : (
        <IconAction
          title="Fit the whole take into the window"
          icon={<SwapHorizIcon />}
          onClick={fitTake}
          placement="top"
          data-testid="passage-fit"
        />
      )}
    </>
  );

  return (
    <Box sx={{ px: { xs: 2, md: 3 }, pt: 1, pb: 12 }} data-passage-page={passage.id}>
      <PageHeader
        title={title}
        back={{ to: ROUTES.project(projectId, "sheet"), label: "Back to the sheet" }}
        actions={
          <>
            {isNew ? (
              <PillButton
                kind="primary"
                disabled={take?.state !== "ready"}
                onClick={() => setPromoting("whole")}
                data-testid="passage-promote"
              >
                Put it in
              </PillButton>
            ) : (
              <PillButton
                kind="primary"
                disabled={take?.state !== "ready"}
                endIcon={<ArrowDropDownIcon />}
                onClick={(event) => setPromoteAnchor(event.currentTarget)}
                data-testid="passage-promote"
              >
                Promote
              </PillButton>
            )}
            <RowMenu title="Passage actions" items={menu} />
          </>
        }
      />
      <Menu anchorEl={promoteAnchor} open={promoteAnchor !== null} onClose={() => setPromoteAnchor(null)}>
        <MenuItem
          onClick={() => {
            setPromoteAnchor(null);
            setPromoting("window");
          }}
          data-testid="promote-window"
        >
          Fit to the window
        </MenuItem>
        <MenuItem
          onClick={() => {
            setPromoteAnchor(null);
            setPromoting("whole");
          }}
          data-testid="promote-whole"
        >
          Replace the whole passage
        </MenuItem>
      </Menu>

      {refused ? (
        <Alert severity="warning" onClose={() => setRefused(null)} sx={{ my: 2 }}>
          {refused}
        </Alert>
      ) : null}

      {isNew ? null : (
        <Section
          title={`Current · ${clock(passage.fromMs)} – ${clock(passage.toMs)}`}
          actions={
            <IconAction
              title={currentPlaying ? "Pause" : "Play the current passage"}
              icon={currentPlaying ? <PauseIcon /> : <PlayArrowIcon />}
              onClick={toggleCurrent}
            />
          }
        >
          <Box data-passage-current>
            <SheetPage
              key={passage.current}
              step={{
                audioUuid: passage.current,
                state: "ready",
                reason: null,
                onChanged: () => undefined,
                passage: {
                  role: "current",
                  ...(passage.anchorMs !== null ? { anchorMs: passage.anchorMs } : {}),
                  playerRef: currentPlayer,
                  onPlaying: reportCurrentPlaying,
                },
              }}
            />
          </Box>
        </Section>
      )}

      <Section
        title={isNew ? `New passage at ${clock(passage.fromMs)}` : "Proposal"}
        actions={
          take ? (
            <Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
              {passage.takes.length > 1 ? (
                <TextField
                  select
                  size="small"
                  value={take.id}
                  onChange={(event) => void update({ take: event.target.value })}
                  sx={{ minWidth: 120 }}
                  slotProps={{ htmlInput: { "aria-label": "Take" } }}
                >
                  {passage.takes.map((one) => (
                    <MenuItem key={one.id} value={one.id}>
                      {one.name}
                    </MenuItem>
                  ))}
                </TextField>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  {take.name}
                </Typography>
              )}
              <Stack direction="row" spacing={1} sx={{ alignItems: "center", width: 200 }} title="How many times as fast the take goes into the song">
                <Typography variant="body2" sx={{ fontVariantNumeric: "tabular-nums", minWidth: 44 }} data-testid="passage-speed">
                  ×{shownSpeed.toFixed(2)}
                </Typography>
                <Slider
                  size="small"
                  aria-label="Speed"
                  min={SPEED_STEPS.min}
                  max={SPEED_STEPS.max}
                  step={SPEED_STEPS.step}
                  value={Math.log2(shownSpeed)}
                  onChange={(_event, value) => setSpeedDraft(2 ** (value as number))}
                  onChangeCommitted={(_event, value) => {
                    const next = Math.round(2 ** (value as number) * 100) / 100;
                    void update({ speed: next }).then(() => setSpeedDraft(null));
                  }}
                />
              </Stack>
            </Stack>
          ) : undefined
        }
      >
        {!take ? (
          <EmptyState
            message={isNew ? "Record the new passage." : "Record the passage again."}
            action={
              <Stack direction="row" spacing={1}>
                <PillButton
                  kind="primary"
                  startIcon={<FiberManualRecordIcon />}
                  onClick={() => setRecorderOpen(true)}
                  data-testid="passage-first-record"
                >
                  Record
                </PillButton>
                <PillButton
                  kind="secondary"
                  startIcon={<FileUploadIcon />}
                  busy={sending}
                  onClick={() => fileInput.current?.click()}
                >
                  Add a take from a file
                </PillButton>
              </Stack>
            }
          />
        ) : showRange ? (
          <Stack spacing={2} sx={{ maxWidth: 960 }} data-passage-range={take.id}>
            <WaveformRangeSelector
              key={take.id}
              audioUrl={audioApi.originalFileUrl(take.id)}
              loadWaveform={loadTakeWaveform}
              durationSeconds={take.seconds}
              initialRange={{ startSeconds: take.fromSeconds, endSeconds: take.toSeconds }}
              onRangeChange={setRange}
            />
            {followed ? <ProgressBanner progress={progress} fallbackLabel="Writing the proposal" /> : null}
            <Stack direction="row" spacing={1}>
              <PillButton
                kind="primary"
                busy={followed !== null}
                onClick={() => void writeProposal()}
                data-testid="passage-write"
              >
                Write the proposal
              </PillButton>
              <PillButton kind="secondary" onClick={() => setRecorderOpen(true)}>
                Record again
              </PillButton>
              {take.state === "ready" ? (
                <PillButton kind="quiet" onClick={() => setEditingRange(false)}>
                  Cancel
                </PillButton>
              ) : null}
            </Stack>
          </Stack>
        ) : ready ? (
          <Box data-passage-proposal={take.id}>
            <SheetPage
              key={`${take.id}:${take.audioRevision}`}
              step={{
                audioUuid: take.id,
                audioRevision: take.audioRevision,
                state: "ready",
                reason: null,
                onChanged: () => undefined,
                passage: {
                  role: "proposal",
                  ...(passage.anchorMs !== null ? { anchorMs: passage.anchorMs * shownSpeed } : {}),
                  ...(frameWindow ? { frameWindow } : {}),
                  onWindowMove: moveWindow,
                  barActions,
                  playerRef: proposalPlayer,
                  onPlaying: reportProposalPlaying,
                  onSheet: keepSheet,
                },
              }}
            />
          </Box>
        ) : null}
      </Section>

      <input
        ref={fileInput}
        type="file"
        accept="audio/*,video/webm"
        hidden
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (file) void sendTake(file);
        }}
      />

      <Toolbox
        open={recorderOpen}
        title="Record a take"
        initialPosition={{ x: 24, y: 140 }}
        onClose={() => {
          if (!recording) setRecorderOpen(false);
        }}
        width={340}
      >
        <Stack spacing={1.5} data-passage-recorder>
          {midi.supported ? (
            <Segmented<NotesFrom>
              label="Notes from"
              value={notesFrom}
              options={[
                { value: "microphone", label: "Microphone" },
                { value: "midi", label: "MIDI piano" },
              ]}
              onChange={chooseNotesFrom}
            />
          ) : null}
          {withMidi && midi.error ? <Alert severity="warning">{midi.error}</Alert> : null}
          {withMidi && !midi.error && midi.inputs.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No MIDI piano is connected.
            </Typography>
          ) : null}
          {withMidi && midi.inputs.length > 1 ? (
            <TextField
              select
              size="small"
              label="MIDI piano"
              value={pianoChosen}
              onChange={(event) => setPiano(event.target.value)}
              disabled={recording}
              slotProps={{ select: { displayEmpty: true }, inputLabel: { shrink: true } }}
            >
              <MenuItem value="">Every one connected</MenuItem>
              {midi.inputs.map((one) => (
                <MenuItem key={one.id} value={one.id}>
                  {one.name}
                </MenuItem>
              ))}
            </TextField>
          ) : null}
          {isNew ? null : (
            <FormControlLabel
              control={<Checkbox size="small" checked={withOriginal} onChange={(event) => setWithOriginal(event.target.checked)} />}
              label={speed === 1 ? "Play the passage along" : `Play the passage along at ×${(1 / speed).toFixed(2)}`}
            />
          )}
          {MICROPHONE && (inputs.length > 1 || withMidi) ? (
            <TextField
              select
              size="small"
              label={withMidi ? "Sound" : "Microphone"}
              value={inputChosen}
              onChange={(event) => chooseInput(event.target.value)}
              disabled={recording}
              slotProps={{ select: { displayEmpty: true }, inputLabel: { shrink: true } }}
            >
              {withMidi ? <MenuItem value={NO_SOUND}>No sound</MenuItem> : null}
              <MenuItem value="">The computer's default</MenuItem>
              {inputs.map((one, index) => (
                <MenuItem key={one.deviceId} value={one.deviceId}>
                  {one.label || `Microphone ${index + 1}`}
                </MenuItem>
              ))}
            </TextField>
          ) : null}
          {recorder.error ? <Alert severity="error">{recorder.error}</Alert> : null}
          {withSound ? (
            <LiveLevelBars levels={recorder.levels} active={recorder.status === "recording"} height={40} />
          ) : null}
          <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
            {recording ? (
              <PillButton kind="danger" startIcon={<StopIcon />} onClick={endRecording} data-testid="passage-stop">
                Stop {formatTime(silentSince !== null ? silentSeconds : recorder.elapsedSeconds)}
              </PillButton>
            ) : (
              <PillButton
                kind="primary"
                startIcon={<FiberManualRecordIcon />}
                busy={sending || recorder.status === "requesting"}
                disabled={withMidi ? midi.inputs.length === 0 : !MICROPHONE}
                title={
                  withMidi || MICROPHONE
                    ? undefined
                    : "This address cannot use the microphone: open the app at localhost, or add a take from a file"
                }
                onClick={() => void beginRecording()}
                data-testid="passage-start"
              >
                Record
              </PillButton>
            )}
            {recording && withMidi ? (
              <Typography variant="body2" color="text.secondary" data-testid="passage-keys">
                {midi.heard} {midi.heard === 1 ? "key" : "keys"}
              </Typography>
            ) : null}
            <IconAction
              title="Add a take from a file"
              icon={<FileUploadIcon />}
              disabled={recording || sending}
              onClick={() => fileInput.current?.click()}
            />
          </Stack>
        </Stack>
      </Toolbox>

      <Dialog open={promoting !== null} onClose={() => (writing ? undefined : setPromoting(null))} maxWidth="xs" fullWidth>
        <DialogTitle>
          {isNew ? "Put the take in" : promoting === "window" ? "Fit to the window" : "Replace the whole passage"}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={1.5} sx={{ pt: 0.5 }} data-promotion={promoting ?? ""}>
            {promoting === "window" ? (
              <Segmented<PromotionAudio>
                label="Which audio"
                value={audioChoice}
                options={[
                  { value: "original", label: "Keep the original audio" },
                  { value: "recording", label: "Use my recording" },
                ]}
                onChange={setAudioChoice}
              />
            ) : null}
            {facts && facts.lengthChangeMs !== 0 ? (
              <Typography variant="body2" data-testid="promotion-length">
                The song gets {(Math.abs(facts.lengthChangeMs) / 1000).toFixed(1)} s{" "}
                {facts.lengthChangeMs > 0 ? "longer" : "shorter"}.
              </Typography>
            ) : null}
            {facts && marksWords(facts.marksDropped) ? (
              <Typography variant="body2" data-testid="promotion-marks">
                Removed with the passage: {marksWords(facts.marksDropped)}.
              </Typography>
            ) : null}
          </Stack>
        </DialogContent>
        <DialogActions>
          <PillButton kind="quiet" onClick={() => setPromoting(null)} disabled={writing}>
            Cancel
          </PillButton>
          <PillButton kind="primary" busy={writing} disabled={facts === null} onClick={() => void promote()} data-testid="promotion-confirm">
            {isNew ? "Put it in" : "Promote"}
          </PillButton>
        </DialogActions>
      </Dialog>

      <ConfirmDialog
        open={discarding}
        title="Discard this passage?"
        message="Its takes are deleted. The song stays as it is."
        confirmLabel="Discard the passage"
        danger
        onConfirm={() => void discard()}
        onCancel={() => setDiscarding(false)}
      />
    </Box>
  );
}

export default PassagePage;
