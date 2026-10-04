/**
 * The flow page: one piece, five tabs in the order of the work (implementation 08, plan section 7).
 *
 * **Source** brings the audio in, **Audio** chooses the selected region, **Notes** transcribes and
 * edits the notes, **Hands** splits them between the two hands, and **Sheet** is the piano sheet.
 * The page asks the backend which steps are ready (`GET /pieces/{uuid}/status`) and enables its
 * tabs from that answer only, so a tab never opens on a result made from an older version of an
 * earlier step. The reader can always go back to an earlier tab.
 *
 * The piece is in the address (`/piece/<uuid>/<step>`), so a reload or a shared link opens the same
 * piece at the same step. `/piece/<uuid>` opens it on the furthest step that is ready.
 *
 * **Unsaved edits.** A tab with unsaved edits tells the page through `useUnsavedChanges`. Leaving
 * it by any link then asks the reader to save or discard first, and closing the browser tab shows
 * the browser's own warning (plan section 7.3).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Container from "@mui/material/Container";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import LibraryMusicIcon from "@mui/icons-material/LibraryMusicOutlined";
import {
  Navigate,
  Outlet,
  useBlocker,
  useLocation,
  useNavigate,
  useParams,
  type BlockerFunction,
} from "react-router-dom";
import {
  audioApi,
  piecesApi,
  PIECE_STEPS,
  type AudioItem,
  type PieceStatus,
  type PieceStep,
  type StepStatus,
} from "../../api";
import { formatTimeShort } from "../../audio/time";
import StepTabs from "../../components/piece/StepTabs";
import { STEP_LABELS } from "../../components/piece/stepLabels";
import { ROUTES } from "../../layout/routes";
import { useWorkingArtifact } from "../../state/useWorkingArtifact";
import {
  PieceContext,
  SAVED_NAVIGATION,
  stepStatus,
  type PieceContextValue,
  type UnsavedHandlers,
} from "./pieceContext";

/** The tabs of `/piece/new`: only Source can be opened. */
const NO_PIECE: StepStatus[] = PIECE_STEPS.map((step) => ({
  step,
  state: step === "source" ? "ready" : "missing",
  enabled: step === "source",
  reason: step === "source" ? null : "Choose an audio first.",
  details: {},
}));

/** Which tab the address names, or `null` for `/piece/<uuid>` itself. */
function stepOf(pathname: string, uuid: string | undefined): PieceStep | null {
  if (!uuid) return "source";
  const last = pathname.replace(/\/$/, "").split("/").pop();
  return (PIECE_STEPS as readonly string[]).includes(last ?? "") ? (last as PieceStep) : null;
}

/** The piece, tagged with the uuid it belongs to, so nothing of the previous piece leaks through. */
interface Loaded {
  uuid: string | null;
  audio: AudioItem | null;
  status: PieceStatus | null;
  error: string | null;
}

const EMPTY: Loaded = { uuid: null, audio: null, status: null, error: null };

export function PiecePage() {
  const { uuid } = useParams();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { update } = useWorkingArtifact();
  const step = stepOf(pathname, uuid);

  const [loaded, setLoaded] = useState<Loaded>(EMPTY);
  const current = loaded.uuid === (uuid ?? null) ? loaded : { ...EMPTY, uuid: uuid ?? null };

  useEffect(() => {
    if (!uuid) return;
    const controller = new AbortController();
    Promise.all([piecesApi.status(uuid, controller.signal), audioApi.get(uuid, controller.signal)])
      .then(([status, audio]) => {
        setLoaded({ uuid, audio, status, error: null });
        // The Playground tabs read the working piece; opening a piece here makes it theirs too.
        update({ audioUuid: uuid, artifactId: undefined, label: audio.alias });
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return;
        setLoaded({
          uuid,
          audio: null,
          status: null,
          error: caught instanceof Error ? caught.message : "Could not load this piece.",
        });
      });
    return () => controller.abort();
  }, [uuid, update]);

  const refresh = useCallback(async (): Promise<PieceStatus | null> => {
    if (!uuid) return null;
    try {
      // The audio too: saved cuts change the length of the piece the header shows.
      const [status, audio] = await Promise.all([piecesApi.status(uuid), audioApi.get(uuid)]);
      setLoaded((previous) => (previous.uuid === uuid ? { ...previous, audio, status, error: null } : previous));
      return status;
    } catch {
      return null;
    }
  }, [uuid]);

  // ------------------------------------------------------------------ unsaved edits

  const handlersRef = useRef<UnsavedHandlers | null>(null);
  const [unsaved, setUnsaved] = useState<string | null>(null);
  const [leaving, setLeaving] = useState(false);

  const registerUnsaved = useCallback((handlers: UnsavedHandlers | null) => {
    handlersRef.current = handlers;
  }, []);

  const shouldBlock = useCallback<BlockerFunction>(
    ({ currentLocation, nextLocation }) =>
      unsaved !== null &&
      currentLocation.pathname !== nextLocation.pathname &&
      !(nextLocation.state as typeof SAVED_NAVIGATION | null)?.savedBeforeLeaving,
    [unsaved],
  );
  const blocker = useBlocker(shouldBlock);

  useEffect(() => {
    if (unsaved === null) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      // Older browsers show the dialog only when this is set.
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [unsaved]);

  const leaveWith = async (choice: "save" | "discard" | "stay") => {
    if (blocker.state !== "blocked") return;
    if (choice === "stay") {
      blocker.reset();
      return;
    }
    if (choice === "discard") {
      handlersRef.current?.discard();
      blocker.proceed();
      return;
    }
    setLeaving(true);
    const saved = (await handlersRef.current?.save()) ?? true;
    setLeaving(false);
    if (saved) blocker.proceed();
    else blocker.reset();
  };

  const context = useMemo<PieceContextValue>(
    () => ({
      uuid: uuid ?? null,
      audio: current.audio,
      status: current.status,
      refresh,
      registerUnsaved,
      setUnsavedSummary: setUnsaved,
    }),
    [uuid, current.audio, current.status, refresh, registerUnsaved],
  );

  // ------------------------------------------------------------------ render

  const status = current.status;
  // Unsaved edits of the notes or of the hands: the Hands step is not done until they are saved.
  const unsavedStep = unsaved !== null && (step === "notes" || step === "hands") ? "hands" : null;
  const steps = uuid ? status?.steps ?? null : NO_PIECE;
  const here = step ? stepStatus(status, step) : null;

  // A tab that cannot be opened yet (typed in the address, or an old bookmark) goes to the step
  // the piece has reached instead.
  if (uuid && status && step && here && !here.enabled) {
    return <Navigate to={ROUTES.piece(uuid, status.resume)} replace />;
  }

  const audio = current.audio;
  const notes = stepStatus(status, "notes");
  const engine = typeof notes?.details.engine === "string" ? notes.details.engine : null;
  const blockedTab = step ? STEP_LABELS[step] : "This";

  return (
    <PieceContext value={context}>
      <Container maxWidth={false} sx={{ pt: 1.5, pb: 4 }}>
        <Stack
          direction="row"
          spacing={1.5}
          sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1, mb: 0.5 }}
        >
          <Typography variant="h2" sx={{ mr: 1 }}>
            {uuid ? (audio?.alias ?? " ") : "New piece"}
          </Typography>
          {audio?.durationSeconds ? (
            <Chip size="small" variant="outlined" label={formatTimeShort(audio.durationSeconds)} />
          ) : null}
          {audio ? <Chip size="small" variant="outlined" label={audio.source} /> : null}
          {engine ? <Chip size="small" variant="outlined" label={`Notes: ${engine}`} /> : null}
          <Box sx={{ flexGrow: 1 }} />
          {uuid ? (
            <Button
              size="small"
              startIcon={<LibraryMusicIcon />}
              onClick={() => navigate(ROUTES.pieceNew)}
            >
              Open another piece
            </Button>
          ) : null}
        </Stack>

        {current.error ? (
          <Alert severity="error" sx={{ my: 2 }}>
            {current.error}
          </Alert>
        ) : null}

        {steps ? (
          <StepTabs
            steps={steps}
            current={step}
            unsaved={unsavedStep}
            onSelect={(next) => navigate(uuid ? ROUTES.piece(uuid, next) : ROUTES.pieceNew)}
          />
        ) : current.error ? null : (
          <Stack direction="row" spacing={1} sx={{ alignItems: "center", py: 2 }}>
            <CircularProgress size={18} />
            <Typography variant="body2" color="text.secondary">
              Loading the piece…
            </Typography>
          </Stack>
        )}

        <Box sx={{ pt: 2 }}>{!uuid || status ? <Outlet /> : null}</Box>
      </Container>

      <Dialog open={blocker.state === "blocked"} onClose={() => void leaveWith("stay")}>
        <DialogTitle>Unsaved changes</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {`${blockedTab} tab: ${unsaved ?? "some changes are not saved"}. Save them before you leave?`}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => void leaveWith("stay")} disabled={leaving}>
            Stay
          </Button>
          <Button color="error" onClick={() => void leaveWith("discard")} disabled={leaving}>
            Discard
          </Button>
          <Button
            variant="contained"
            onClick={() => void leaveWith("save")}
            disabled={leaving}
            startIcon={leaving ? <CircularProgress size={14} color="inherit" /> : undefined}
          >
            Save and continue
          </Button>
        </DialogActions>
      </Dialog>
    </PieceContext>
  );
}

export default PiecePage;
