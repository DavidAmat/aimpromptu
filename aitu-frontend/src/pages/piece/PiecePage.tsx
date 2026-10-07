/**
 * A project, step by step: five steps in the order of the work (implementation 08, plan section 7;
 * restyled by implementation 02, plan section 10.2). Until Phase 3 a project is one piece, and its
 * id is the piece's audio uuid.
 *
 * **Source** brings the audio in, **Audio** chooses the selected region, **Notes** transcribes and
 * edits the notes, **Hands** splits them between the two hands, and **Sheet** is the piano sheet.
 * The page asks the backend which steps are ready (`GET /pieces/{uuid}/status`) and enables its
 * tabs from that answer only, so a tab never opens on a result made from an older version of an
 * earlier step. The reader can always go back to an earlier tab.
 *
 * The project is in the address (`/projects/<id>/<step>`), so a reload or a shared link opens the
 * same project at the same step. `/projects/<id>` opens it on the furthest step that is ready. The
 * header is the back arrow to Projects, the title, the step tabs, and the `⋯` menu of the project.
 *
 * **Unsaved edits.** A tab with unsaved edits tells the page through `useUnsavedChanges`. Leaving
 * it by any link then asks the reader to save or discard first, and closing the browser tab shows
 * the browser's own warning (plan section 7.3).
 *
 * **The library** (Phase 6, plan sections 10.2 and 10.6). A project of the Personal Vault shows
 * **Save to library** once its Sheet step is ready. A version of the Private Library opens **read
 * only**: every step shows what it holds and nothing changes it (`readOnly` in the context), the
 * back arrow goes to its song, and the one action is **Edit**, which opens the copy that changes it.
 * That copy is an ordinary project with **Save to library** (replace the version, or a new one)
 * and, in its `⋯`, **Discard changes**.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Skeleton from "@mui/material/Skeleton";
import DeleteIcon from "@mui/icons-material/DeleteOutlined";
import DownloadIcon from "@mui/icons-material/FileDownloadOutlined";
import EditIcon from "@mui/icons-material/EditOutlined";
import LibraryAddIcon from "@mui/icons-material/LibraryAddOutlined";
import Tooltip from "@mui/material/Tooltip";
import WaterfallIcon from "@mui/icons-material/WaterfallChartOutlined";
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
  ApiError,
  audioApi,
  piecesApi,
  PIECE_STEPS,
  projectsApi,
  type AudioItem,
  type PieceStatus,
  type ProjectRow,
  type PieceStep,
  type StepStatus,
} from "../../api";
import { STEP_LABELS } from "../../components/piece/stepLabels";
import { ROUTES } from "../../layout/routes";
import { useWorkingArtifact } from "../../state/useWorkingArtifact";
import { ConfirmDialog, EmptyState, PageHeader, PillButton, RowMenu, StepTabs } from "../../ui";

const NOT_FOUND = "There is no project of yours at this address.";
import SaveToLibraryDialog from "./SaveToLibraryDialog";
import { said } from "../library/shared";
import {
  PieceContext,
  SAVED_NAVIGATION,
  stepStatus,
  type PieceContextValue,
  type UnsavedHandlers,
} from "./pieceContext";

/** The steps of `/projects/new`: only Source can be opened. */
const NO_PIECE: StepStatus[] = PIECE_STEPS.map((step) => ({
  step,
  state: step === "source" ? "ready" : "missing",
  enabled: step === "source",
  reason: step === "source" ? null : "Choose an audio first",
  details: {},
}));

/** Which step the address names, or `null` for `/projects/<id>` itself and for Notes Falling. */
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
  /** The project's row: its layer, and the song and version it is or edits. */
  project: ProjectRow | null;
  error: string | null;
}

const EMPTY: Loaded = { uuid: null, audio: null, status: null, project: null, error: null };

export function PiecePage() {
  const { id: uuid } = useParams();
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
      .then(async ([status, audio]) => {
        const project = await projectsApi.get(audio.projectId ?? uuid, controller.signal).catch(() => null);
        if (controller.signal.aborted) return;
        setLoaded({ uuid, audio, status, project, error: null });
        // The Playground tabs read the working piece; opening a piece here makes it theirs too.
        update({ audioUuid: uuid, artifactId: undefined, label: audio.alias });
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return;
        setLoaded({
          uuid,
          audio: null,
          status: null,
          project: null,
          // 404: no project here, or one of another user, which the backend does not tell apart.
          error:
            caught instanceof ApiError && caught.status === 404
              ? NOT_FOUND
              : caught instanceof Error
                ? caught.message
                : "Could not load this piece.",
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

  // A version of a library (or of the Public Library) is read only: it changes through Edit.
  const layer = current.audio?.layer ?? null;
  const readOnly = layer === "private" || layer === "public";

  const context = useMemo<PieceContextValue>(
    () => ({
      uuid: uuid ?? null,
      audio: current.audio,
      status: current.status,
      readOnly,
      refresh,
      registerUnsaved,
      setUnsavedSummary: setUnsaved,
    }),
    [uuid, current.audio, current.status, readOnly, refresh, registerUnsaved],
  );

  // ------------------------------------------------------------------ the library

  const project = current.project;
  const library = project?.library ?? null;
  const editing = project?.editing ?? null;
  const [saving, setSaving] = useState(false);
  const [discarding, setDiscarding] = useState(false);
  const [libraryBusy, setLibraryBusy] = useState(false);
  const [libraryError, setLibraryError] = useState<string | null>(null);

  const openEdit = async () => {
    if (!project) return;
    setLibraryBusy(true);
    setLibraryError(null);
    try {
      const copy = await projectsApi.edit(project.id);
      navigate(ROUTES.project(copy.parts[0] ?? copy.id, step ?? undefined));
    } catch (caught) {
      setLibraryError(said(caught, "The version could not be opened for editing."));
    } finally {
      setLibraryBusy(false);
    }
  };

  const discard = async () => {
    if (!project) return;
    setLibraryBusy(true);
    setLibraryError(null);
    try {
      await projectsApi.remove(project.id);
      handlersRef.current?.discard();
      navigate(editing ? ROUTES.librarySong(editing.songId) : ROUTES.projects, {
        replace: true,
        state: SAVED_NAVIGATION,
      });
    } catch (caught) {
      setLibraryError(said(caught, "The changes could not be discarded."));
      setDiscarding(false);
    } finally {
      setLibraryBusy(false);
    }
  };

  // ------------------------------------------------------------------ render

  const status = current.status;
  // Unsaved edits of the notes or of the hands: the Hands step is not done until they are saved.
  const unsavedStep = unsaved !== null && (step === "notes" || step === "hands") ? "hands" : null;
  const steps = uuid ? status?.steps ?? null : NO_PIECE;
  const here = step ? stepStatus(status, step) : null;

  // A step that cannot be opened yet (typed in the address, or an old bookmark) goes to the step
  // the project has reached instead.
  if (uuid && status && step && here && !here.enabled) {
    return <Navigate to={ROUTES.project(uuid, status.resume)} replace />;
  }

  const audio = current.audio;
  const blockedTab = step ? STEP_LABELS[step] : "This step";
  const title = !uuid
    ? "New project"
    : library
      ? `${library.songTitle} (${library.versionName})`
      : (audio?.alias ?? "");
  const hasNotes = stepStatus(status, "notes")?.state === "ready";
  const sheetReady = stepStatus(status, "sheet")?.state === "ready";
  const back = library
    ? { to: ROUTES.librarySong(library.songId), label: `Back to ${library.songTitle}` }
    : { to: ROUTES.projects, label: "Back to Projects" };

  const menu = uuid
    ? [
        {
          label: "Notes Falling",
          icon: <WaterfallIcon fontSize="small" />,
          onClick: () => navigate(ROUTES.projectNotesFalling(uuid)),
          disabled: !hasNotes,
        },
        {
          label: "Export",
          icon: <DownloadIcon fontSize="small" />,
          onClick: () => {
            const link = document.createElement("a");
            link.href = projectsApi.exportUrl(project?.id ?? uuid);
            link.download = "";
            link.click();
          },
        },
        ...(editing
          ? [
              {
                label: "Discard changes",
                icon: <DeleteIcon fontSize="small" />,
                onClick: () => setDiscarding(true),
                danger: true,
              },
            ]
          : []),
      ]
    : [];

  let primary = null;
  if (uuid && readOnly && layer === "private") {
    primary = (
      <PillButton kind="primary" startIcon={<EditIcon />} busy={libraryBusy} onClick={() => void openEdit()}>
        Edit
      </PillButton>
    );
  } else if (uuid && layer === "vault" && project && sheetReady) {
    primary = (
      <Tooltip title={unsaved !== null ? "Save your changes first" : ""}>
        <span>
          <PillButton
            kind="primary"
            startIcon={<LibraryAddIcon />}
            disabled={unsaved !== null}
            onClick={() => setSaving(true)}
          >
            Save to library
          </PillButton>
        </span>
      </Tooltip>
    );
  }

  return (
    <PieceContext value={context}>
      <Box sx={{ px: { xs: 2, md: 3 }, pt: 1, pb: 4 }}>
        <PageHeader
          title={title}
          back={back}
          actions={
            uuid ? (
              <>
                {primary}
                <RowMenu title="Project actions" items={menu} />
              </>
            ) : undefined
          }
        >
          {steps ? (
            <StepTabs
              steps={steps.map((item) => ({
                key: item.step,
                // A video project's second step is its video (plan section 10.2).
                label: item.step === "audio" && audio?.hasVideo && !readOnly ? "Video" : STEP_LABELS[item.step],
                state: item.state,
                enabled: item.enabled,
                reason: item.reason,
              }))}
              current={step}
              unsaved={unsavedStep}
              onSelect={(next) => navigate(uuid ? ROUTES.project(uuid, next) : ROUTES.projectNew)}
            />
          ) : current.error ? null : (
            <Skeleton variant="rounded" width={320} height={28} />
          )}
        </PageHeader>

        {current.error === NOT_FOUND ? (
          <EmptyState
            message={NOT_FOUND}
            action={
              <PillButton kind="primary" onClick={() => navigate(ROUTES.projects)}>
                Open Projects
              </PillButton>
            }
          />
        ) : current.error ? (
          <Alert severity="error" sx={{ my: 2 }}>
            {current.error}
          </Alert>
        ) : null}

        {libraryError ? (
          <Alert severity="error" onClose={() => setLibraryError(null)} sx={{ my: 2 }}>
            {libraryError}
          </Alert>
        ) : null}

        <Box sx={{ pt: 2 }}>{!uuid || status ? <Outlet /> : null}</Box>
      </Box>

      {saving && project ? (
        <SaveToLibraryDialog
          projectId={project.id}
          title={project.title}
          editing={editing}
          onClose={() => setSaving(false)}
          onSaved={(saved) => {
            setSaving(false);
            navigate(ROUTES.librarySong(saved.songId), { state: SAVED_NAVIGATION });
          }}
        />
      ) : null}

      <ConfirmDialog
        open={discarding}
        title={editing ? `Discard your changes to “${editing.versionName}”?` : "Discard this project?"}
        message="This copy is deleted. The version in your library stays as it is."
        confirmLabel="Discard changes"
        danger
        busy={libraryBusy}
        onCancel={() => setDiscarding(false)}
        onConfirm={() => void discard()}
      />

      <ConfirmDialog
        open={blocker.state === "blocked"}
        title="Save your changes?"
        message={`${blockedTab}: ${unsaved ?? "some changes are not saved"}.`}
        cancelLabel="Stay"
        confirmLabel="Save and continue"
        busy={leaving}
        onCancel={() => void leaveWith("stay")}
        onConfirm={() => void leaveWith("save")}
        extra={
          <PillButton kind="quiet" onClick={() => void leaveWith("discard")} disabled={leaving} sx={{ color: "error.main" }}>
            Discard
          </PillButton>
        }
      />
    </PieceContext>
  );
}

export default PiecePage;
