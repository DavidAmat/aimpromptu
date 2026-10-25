/**
 * The Sheet step with the new sheet (implementation 03, Phase 5): the sheet the backend draws without compases,
 * to see and to hear. It is what `SheetPage` shows first on the Sheet step, a version of My library and in Play
 * mode; the old vexflow-v2 sheet stays one press away for editing until Phase 8 (`onOldSheet`).
 *
 * - **At once**: the sheet as it is now: the AI's (Sonnet 5.5 today), or the algorithm's on a part it has not
 *   enhanced. A sheet the AI enhanced carries the green badge **Enhanced with AI** for good, whatever changes later
 *   (the user's rule of 2026-10-25): a new run is then **Enhance it again with AI**, at the user's own risk of the
 *   same result. The page says "AI", not the model's name: the model may change.
 * - **The AI in the background** (plan section 3.6): a new transcription is sent by itself; any other part offers
 *   **Enhance with AI** (on a version of My library, the button opens the copy that edits it, as **Edit** does,
 *   and starts there). The segment at the AI looks pale, a segment that comes back appears column by column, and
 *   no text says any of it. The old sheet cannot be opened while the AI writes: the segments still waiting cannot
 *   be edited.
 * - **To hear**: the recording plays with a cursor, the notes it reaches lit, and a click on the sheet moves the
 *   recording there.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesomeOutlined";
import EditNoteIcon from "@mui/icons-material/EditNoteOutlined";
import PauseIcon from "@mui/icons-material/Pause";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import { timeScoreApi, type SavedRhythm } from "../../../../api";
import ScorePlayer, { type ScorePlayerControls } from "../../../../components/time/ScorePlayer";
import { useElementSize } from "../../../../hooks/useElementSize";
import { ConfirmDialog, FloatingBar, IconAction, Pill, PillButton, semantic } from "../../../../ui";
import type { SheetStep } from "../SheetPage";
import { FramesSheetView } from "./FramesSheetView";
import { ENHANCE_WITH_AI } from "./navigation";
import { useFramesSheet } from "./useFramesSheet";

/** The size the sheet is drawn at: about the old sheet's (8 px a staff space at the Sheet step's width). */
const PX_PER_SPACE = 8.5;
/** The SVG adds this much margin to the staff width, in staff spaces. */
const MARGINS = 8;
/** The width asked for moves in steps of this many staff spaces, so a small resize draws nothing again. */
const WIDTH_STEP = 4;

export function FramesSheetPage({ step, onOldSheet }: { step: SheetStep; onOldSheet: () => void }) {
  const audioUuid = step.audioUuid;
  const playView = step.play ?? null;
  const playMode = playView !== null;
  const readOnly = (step.readOnly ?? false) || playMode;
  const navigate = useNavigate();
  const location = useLocation();

  const [sizeRef, size] = useElementSize<HTMLDivElement>();
  const width = useMemo(() => {
    if (size.width <= 0) return null;
    const spaces = size.width / PX_PER_SPACE - MARGINS;
    return Math.min(320, Math.max(60, Math.round(spaces / WIDTH_STEP) * WIDTH_STEP));
  }, [size.width]);

  const { sheet, error, run, starting } = useFramesSheet(audioUuid, width, {
    autoStart: !readOnly,
    onChanged: step.onChanged,
  });

  // The title lines the old sheet saved (its Title tab): kept on the page.
  const [titles, setTitles] = useState<SavedRhythm | null>(null);
  useEffect(() => {
    if (playMode) return;
    const controller = new AbortController();
    timeScoreApi
      .rhythm(audioUuid, controller.signal)
      .then((found) => setTitles(found))
      .catch(() => undefined);
    return () => controller.abort();
  }, [audioUuid, playMode]);
  const title = titles?.title ?? step.label ?? "Untitled";
  const underTitle = [titles?.subtitle, titles?.artist].filter(Boolean).join(" · ");

  // ------------------------------------------------------------------ the recording

  const ownPlayer = useRef<ScorePlayerControls | null>(null);
  // Play mode plays this sheet from its own button and keys: the player fills its handle directly.
  const player = playView?.playerRef ?? ownPlayer;
  const [seconds, setSeconds] = useState<number | null>(0);
  const [playing, setPlaying] = useState(false);
  const [openedAtRevision] = useState(step.audioRevision);
  const onPlayTime = playView?.onTime;
  const reportTime = useCallback(
    (now: number | null) => {
      setSeconds(now);
      onPlayTime?.(now);
    },
    [onPlayTime],
  );
  const onPlayPlaying = playView?.onPlaying;
  const reportPlaying = useCallback(
    (now: boolean) => {
      setPlaying(now);
      onPlayPlaying?.(now);
    },
    [onPlayPlaying],
  );
  const onPlaySeek = playView?.onSeek;
  const seek = (to: number) => {
    player.current?.seek(to);
    onPlaySeek?.();
  };
  // A stretch of a playlist starts where it was chosen.
  const fromMs = playView?.fromMs ?? null;
  const [startedAt, setStartedAt] = useState<string | null>(null);
  useEffect(() => {
    if (!sheet || fromMs === null || startedAt === `${audioUuid}:${fromMs}`) return;
    const wait = window.setTimeout(() => {
      player.current?.seek(fromMs / 1000);
      setStartedAt(`${audioUuid}:${fromMs}`);
    }, 120);
    return () => window.clearTimeout(wait);
  }, [sheet, fromMs, startedAt, audioUuid, player]);

  // ------------------------------------------------------------------ the AI

  const running = sheet?.llm.state === "running" || starting;
  const enhanced = sheet?.llm.enhanced === true;
  const runs = sheet?.llm.runs ?? 0;
  const viaEdit = sheet?.llm.viaEdit === true && step.enhanceInCopy !== undefined;
  const offerAi = !playMode && !running && (sheet?.llm.canRun === true || viaEdit);
  const enhanceLabel = enhanced ? "Enhance it again with AI" : "Enhance with AI";
  const [asking, setAsking] = useState(false);
  const enhance = () => {
    setAsking(false);
    if (sheet?.llm.canRun) void run();
    else step.enhanceInCopy?.();
  };
  // The edit copy opened by **Enhance with AI** on a version of My library: the AI starts here.
  const askedInCopy = (location.state as typeof ENHANCE_WITH_AI | null)?.enhanceWithAi === true;
  useEffect(() => {
    if (!askedInCopy || !sheet) return;
    navigate(location.pathname, { replace: true, state: null });
    if (sheet.llm.canRun) void run();
  }, [askedInCopy, sheet, navigate, location.pathname, run]);

  // A blank sheet (From scratch): the old page has its empty state, with Record a passage and Paste.
  const empty = sheet !== null && sheet.columns.length === 0;
  useEffect(() => {
    if (empty && !playMode) onOldSheet();
  }, [empty, playMode, onOldSheet]);

  const scoreSeconds = sheet && sheet.columns.length > 0 ? sheet.columns[sheet.columns.length - 1].ms / 1000 + 1 : 1;

  return (
    <Box data-sheet-page data-sheet-engine="frames">
      {error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : null}
      <Stack spacing={1.5}>
        {playMode ? null : (
          <Box sx={{ px: 1 }}>
            <Stack direction="row" spacing={1.5} sx={{ alignItems: "center", minWidth: 0 }}>
              <Typography component="h2" sx={{ fontSize: 20, fontWeight: 600, lineHeight: 1.3, minWidth: 0 }} noWrap title={title} data-sheet-title>
                {title}
              </Typography>
              {enhanced ? (
                <Box data-enhanced-badge sx={{ flexShrink: 0 }}>
                  <Pill
                    label="Enhanced with AI"
                    selected
                    color={semantic.status.success}
                    title={runs > 1 ? `The AI enhanced this sheet ${runs} times` : "The AI enhanced this sheet"}
                  />
                </Box>
              ) : null}
            </Stack>
            {underTitle ? (
              <Typography variant="body2" color="text.secondary" noWrap title={underTitle}>
                {underTitle}
              </Typography>
            ) : null}
          </Box>
        )}
        {sheet ? (
          <ScorePlayer
            compact
            audioUuid={audioUuid}
            version={`${openedAtRevision ?? 0}`}
            scoreSeconds={scoreSeconds}
            onTime={reportTime}
            controlsRef={player}
            onPlaying={reportPlaying}
            keys={!playMode}
            headless={playMode}
            stopAt={playView?.toMs != null ? playView.toMs / 1000 : null}
            onEnded={playView?.onEnded}
            preload={playView?.preload ?? "auto"}
          />
        ) : null}
        <Box ref={sizeRef}>
          {sheet ? (
            <FramesSheetView sheet={sheet} playheadSeconds={seconds} follow={playing} centre={playMode} onSeek={seek} />
          ) : !error ? (
            <Box sx={{ display: "grid", placeItems: "center", minHeight: 320 }} data-sheet-loading>
              <CircularProgress size={22} />
            </Box>
          ) : null}
        </Box>
      </Stack>

      {playMode || !sheet ? null : (
        <FloatingBar open label="sheet buttons">
          <IconAction
            title={playing ? "Pause" : "Play"}
            shortcut="Space"
            icon={playing ? <PauseIcon /> : <PlayArrowIcon />}
            onClick={() => player.current?.toggle()}
            placement="top"
          />
          {offerAi ? (
            <PillButton
              kind="secondary"
              size="small"
              startIcon={<AutoAwesomeIcon fontSize="small" />}
              onClick={() => setAsking(true)}
              data-testid="enhance-with-ai"
            >
              {enhanceLabel}
            </PillButton>
          ) : null}
          <Divider orientation="vertical" flexItem />
          <IconAction
            title={readOnly ? "Open the old sheet (print, copy a stretch)" : "Edit in the old sheet"}
            icon={<EditNoteIcon />}
            onClick={onOldSheet}
            disabled={running}
            disabledTitle="The AI is enhancing this sheet"
            placement="top"
            data-testid="old-sheet"
          />
        </FloatingBar>
      )}

      <ConfirmDialog
        open={asking}
        title={enhanced ? "Enhance this sheet again with AI?" : "Enhance this sheet with AI?"}
        message={
          !sheet?.llm.canRun
            ? "This opens a copy in Projects, as Edit does, and the AI enhances it there in a few minutes (about $1 of the monthly credits). Save it to your library when it is done."
            : enhanced
              ? "The AI already enhanced this sheet. A new run may give much the same result, and it uses about $1 of the monthly credits. If it does not finish, the sheet you have now stays."
              : "The AI writes the hands and the reading of the sheet, part by part, in a few minutes. It uses about $1 of the monthly credits. The hands you have now are kept in the history."
        }
        confirmLabel={enhanceLabel}
        onConfirm={enhance}
        onCancel={() => setAsking(false)}
      />
    </Box>
  );
}

export default FramesSheetPage;
