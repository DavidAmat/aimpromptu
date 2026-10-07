/**
 * The Source step of a project that has its audio (implementation 02, Phase 5): the audio files of
 * the project in the order they play, and the ways to add another one.
 *
 * Each row is one file: its name (the file's own name or the video's title at first; **Rename**
 * changes it), where it came from, its length and how much of it is cut. A row is dragged by its
 * handle to a new place, or moved with **Move up** and **Move down** in its `⋯` menu; **Remove**
 * takes it out (not the last one). Below the list, **Add audio**: a file (dropped or chosen, several
 * at once) or a YouTube link, each added at the end.
 *
 * Any change of the files changes the audio, so notes made before it are out of date; the step then
 * says so once, with the way to the Audio step where the audio is transcribed again.
 *
 * A version of the library (read only, Phase 6) shows the list only: no handle, no menu, no Add audio.
 */

import { useCallback, useEffect, useRef, useState, type DragEvent } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import InputAdornment from "@mui/material/InputAdornment";
import LinearProgress from "@mui/material/LinearProgress";
import Link from "@mui/material/Link";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import DeleteIcon from "@mui/icons-material/DeleteOutlined";
import DragIndicatorIcon from "@mui/icons-material/DragIndicator";
import DriveFileRenameIcon from "@mui/icons-material/DriveFileRenameOutline";
import UploadFileIcon from "@mui/icons-material/UploadFileOutlined";
import { useNavigate } from "react-router-dom";
import { audioApi, matrixApi, SUPPORTED_AUDIO_SUFFIXES, youtubeApi, type AudioFiles, type AxisFile } from "../../api";
import { formatTimeShort } from "../../audio/time";
import { useProgress } from "../../hooks/useProgress";
import { ROUTES } from "../../layout/routes";
import { ConfirmDialog, IconAction, PillButton, RowMenu, Section, ui, useScheme } from "../../ui";
import { stepStatus, usePiece } from "./pieceContext";

const isAudioFile = (file: File) => SUPPORTED_AUDIO_SUFFIXES.some((suffix) => file.name.toLowerCase().endsWith(suffix));
const seconds = (frames: number) => frames / 100;
const message = (caught: unknown, fallback: string) => (caught instanceof Error ? caught.message : fallback);

/** "YouTube · 4:10 · 0:05 cut": where a file came from, its length and its cuts. */
function facts(file: AxisFile): string {
  const kind = { upload: "Audio file", youtube: "YouTube", recording: "Recording", segment: "Part of another project", composed: "Composed" }[
    file.kind
  ] ?? "Audio";
  const cut = file.cutFrames > 0 ? ` · ${formatTimeShort(seconds(file.cutFrames))} cut` : "";
  return `${kind} · ${formatTimeShort(seconds(file.frames))}${cut}`;
}

/** The order after moving the file at `from` to the place `to`. */
function moved(count: number, from: number, to: number): number[] {
  const order = Array.from({ length: count }, (_, index) => index);
  const [item] = order.splice(from, 1);
  order.splice(to, 0, item);
  return order;
}

export function SourceFiles() {
  useScheme();
  const { uuid, status, refresh, readOnly } = usePiece();
  const navigate = useNavigate();
  const [state, setState] = useState<AudioFiles | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [renaming, setRenaming] = useState<number | null>(null);
  const [removing, setRemoving] = useState<AxisFile | null>(null);
  const [dragging, setDragging] = useState<number | null>(null);
  const [over, setOver] = useState<number | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      if (!uuid) return;
      try {
        setState(await audioApi.files(uuid, signal));
      } catch (caught) {
        if (!signal?.aborted) setError(message(caught, "The audio files could not be loaded."));
      }
    },
    [uuid],
  );

  useEffect(() => {
    if (!uuid) return;
    const controller = new AbortController();
    audioApi
      .files(uuid, controller.signal)
      .then(setState)
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(message(caught, "The audio files could not be loaded."));
      });
    return () => controller.abort();
  }, [uuid]);

  /** Run a change of the files, then show the new list and the new state of the steps. */
  const change = async (work: () => Promise<AudioFiles | unknown>, fallback: string) => {
    setBusy(true);
    setError(null);
    try {
      const answer = await work();
      if (answer && typeof answer === "object" && "files" in answer) setState(answer as AudioFiles);
      else await load();
      await refresh();
      return true;
    } catch (caught) {
      setError(message(caught, fallback));
      return false;
    } finally {
      setBusy(false);
    }
  };

  const reorder = (order: number[]) => {
    if (!uuid || !state || order.every((at, index) => at === index)) return;
    void change(() => audioApi.reorderFiles(uuid, order, state.audioRevision), "The files could not be moved.");
  };

  const rename = (index: number, name: string) => {
    if (!uuid) return;
    setRenaming(null);
    if (!name.trim() || name.trim() === state?.files[index]?.name) return;
    void change(() => audioApi.renameFile(uuid, index, name.trim()), "The file could not be renamed.");
  };

  const remove = async (file: AxisFile) => {
    if (!uuid || !state) return;
    const done = await change(() => audioApi.removeFile(uuid, file.index, state.audioRevision), "The file could not be removed.");
    if (done) setRemoving(null);
  };

  // ------------------------------------------------------------------ adding

  const fileInput = useRef<HTMLInputElement | null>(null);
  const [adding, setAdding] = useState<string | null>(null);
  const [droppingOver, setDroppingOver] = useState(false);
  const [url, setUrl] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const progress = useProgress(jobId ? matrixApi.progressUrl(jobId) : null);
  const downloading = jobId !== null && progress.status !== "done" && progress.status !== "error";

  const addFiles = async (files: File[]) => {
    if (!uuid || files.length === 0) return;
    const wrong = files.find((file) => !isAudioFile(file));
    if (wrong) {
      setError(`“${wrong.name}” is not an audio file this app reads (${SUPPORTED_AUDIO_SUFFIXES.join(", ")}).`);
      return;
    }
    for (const file of files) {
      setAdding(file.name);
      const done = await change(() => audioApi.addAudio(uuid, file), `“${file.name}” could not be added.`);
      if (!done) break;
    }
    setAdding(null);
  };

  const download = async () => {
    const link = url.trim();
    if (!uuid || !link || downloading) return;
    setError(null);
    try {
      const handle = await youtubeApi.startDownload({ url: link, appendTo: uuid });
      setJobId(handle.jobId);
    } catch (caught) {
      setError(message(caught, "The download could not start."));
    }
  };

  // The YouTube audio is in: show it in the list.
  useEffect(() => {
    if (progress.status !== "done") return;
    const controller = new AbortController();
    audioApi
      .files(uuid ?? "", controller.signal)
      .then(setState)
      .then(() => refresh())
      .catch(() => undefined);
    return () => controller.abort();
  }, [progress.status, uuid, refresh]);

  const notes = stepStatus(status, "notes");
  const percent = progress.event?.total ? progress.event.fraction * 100 : null;
  const failed = progress.status === "error" ? progress.error : null;

  // ------------------------------------------------------------------ dragging

  const onRowDrop = (event: DragEvent, to: number) => {
    event.preventDefault();
    if (dragging !== null && state) reorder(moved(state.files.length, dragging, to));
    setDragging(null);
    setOver(null);
  };

  const onZoneDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDroppingOver(false);
    void addFiles(Array.from(event.dataTransfer.files ?? []));
  };

  const total = state?.files.reduce((sum, file) => sum + file.frames - file.cutFrames, 0) ?? 0;

  return (
    <Stack spacing={3} sx={{ maxWidth: 720, mx: "auto", pt: { xs: 2, md: 4 }, pb: 6 }} data-source-files={state?.files.length ?? ""}>
      {error || failed ? (
        <Alert severity="error" onClose={() => setError(null)}>
          {error ?? failed}
        </Alert>
      ) : null}
      {notes?.state === "stale" && !readOnly ? (
        <Alert
          severity="warning"
          action={
            <PillButton size="small" onClick={() => uuid && navigate(ROUTES.project(uuid, "audio"))}>
              Open Audio
            </PillButton>
          }
        >
          The audio changed after the notes were made. Transcribe it again.
        </Alert>
      ) : null}

      <Section
        title="Audio"
        actions={
          state ? (
            <Typography variant="body2" color="text.secondary" sx={{ fontVariantNumeric: "tabular-nums" }}>
              {formatTimeShort(seconds(total))}
            </Typography>
          ) : null
        }
      >
        {state === null ? (
          <Stack spacing={1}>
            <Skeleton variant="rounded" height={56} />
          </Stack>
        ) : (
          <Box role="list" aria-label="The audio files, in the order they play" aria-busy={busy}>
            {state.files.map((file) => (
              <Box
                role="listitem"
                key={`${file.index}:${file.name}:${file.startFrame}`}
                data-file-row={file.index}
                onDragOver={(event) => {
                  if (dragging === null) return;
                  event.preventDefault();
                  setOver(file.index);
                }}
                onDrop={(event) => onRowDrop(event, file.index)}
                sx={(theme) => ({
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                  px: 1,
                  py: 1,
                  borderRadius: "12px",
                  opacity: dragging === file.index ? 0.4 : 1,
                  boxShadow:
                    over === file.index && dragging !== null && dragging !== file.index
                      ? `inset 0 ${dragging < file.index ? -2 : 2}px 0 ${ui.text}`
                      : "none",
                  "&:hover": { backgroundColor: (theme.vars ?? theme).palette.action.hover },
                })}
              >
                {readOnly ? null : (
                  <Box
                    draggable={state.files.length > 1 && !busy}
                    onDragStart={(event) => {
                      event.dataTransfer.effectAllowed = "move";
                      event.dataTransfer.setData("text/plain", String(file.index));
                      setDragging(file.index);
                    }}
                    onDragEnd={() => {
                      setDragging(null);
                      setOver(null);
                    }}
                    title={state.files.length > 1 ? "Drag to put it in another place" : undefined}
                    aria-hidden
                    sx={{
                      display: "flex",
                      color: state.files.length > 1 ? "text.secondary" : "text.disabled",
                      cursor: state.files.length > 1 ? "grab" : "default",
                    }}
                  >
                    <DragIndicatorIcon fontSize="small" />
                  </Box>
                )}
                <Typography variant="body2" color="text.secondary" sx={{ width: 20, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                  {file.index + 1}
                </Typography>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  {renaming === file.index ? (
                    <RenameField file={file} onDone={(name) => rename(file.index, name)} onCancel={() => setRenaming(null)} />
                  ) : (
                    <Typography noWrap title={file.name} sx={{ fontWeight: 500 }}>
                      {file.name}
                    </Typography>
                  )}
                  <Typography variant="body2" color="text.secondary" noWrap>
                    {facts(file)}
                    {file.url ? (
                      <>
                        {" · "}
                        <Link href={file.url} target="_blank" rel="noreferrer" underline="hover" color="inherit">
                          {file.url.replace(/^https?:\/\/(www\.)?/, "")}
                        </Link>
                      </>
                    ) : file.originalFilename && file.originalFilename !== file.name ? (
                      ` · ${file.originalFilename}`
                    ) : null}
                  </Typography>
                </Box>
                {readOnly ? null : (
                  <RowMenu
                    title="File actions"
                    restoreFocus={false}
                    items={[
                      { label: "Rename", icon: <DriveFileRenameIcon fontSize="small" />, onClick: () => setRenaming(file.index) },
                      {
                        label: "Move up",
                        icon: <ArrowUpwardIcon fontSize="small" />,
                        onClick: () => reorder(moved(state.files.length, file.index, file.index - 1)),
                        disabled: file.index === 0 || busy,
                      },
                      {
                        label: "Move down",
                        icon: <ArrowDownwardIcon fontSize="small" />,
                        onClick: () => reorder(moved(state.files.length, file.index, file.index + 1)),
                        disabled: file.index === state.files.length - 1 || busy,
                      },
                      {
                        label: "Remove",
                        icon: <DeleteIcon fontSize="small" />,
                        onClick: () => setRemoving(file),
                        danger: true,
                        disabled: state.files.length === 1 || busy,
                      },
                    ]}
                  />
                )}
              </Box>
            ))}
          </Box>
        )}
      </Section>

      {readOnly ? null : (
        <Section title="Add audio">
          <Stack spacing={1.5}>
            <Box
              onDragOver={(event) => {
                if (dragging !== null) return;
                event.preventDefault();
                setDroppingOver(true);
              }}
              onDragLeave={() => setDroppingOver(false)}
              onDrop={onZoneDrop}
              data-testid="add-drop-zone"
              sx={(theme) => ({
                border: `1.5px dashed ${droppingOver ? ui.text : ui.lineStrong}`,
                borderRadius: "16px",
                backgroundColor: droppingOver ? (theme.vars ?? theme).palette.action.hover : "transparent",
                display: "flex",
                alignItems: "center",
                gap: 2,
                px: 2.5,
                py: 2,
                flexWrap: "wrap",
              })}
            >
              <UploadFileIcon sx={{ color: "text.secondary" }} />
              <Typography color="text.secondary" sx={{ flex: 1, minWidth: 160 }} role={adding ? "status" : undefined}>
                {adding ? `Adding ${adding}` : "Drop audio files"}
              </Typography>
              {adding ? (
                <LinearProgress sx={{ width: 120 }} />
              ) : (
                <PillButton onClick={() => fileInput.current?.click()} disabled={busy || downloading}>
                  Choose files
                </PillButton>
              )}
              <input
                ref={fileInput}
                type="file"
                hidden
                multiple
                accept={SUPPORTED_AUDIO_SUFFIXES.join(",")}
                aria-label="Choose audio files to add"
                onChange={(event) => {
                  void addFiles(Array.from(event.target.files ?? []));
                  event.target.value = "";
                }}
              />
            </Box>
            <TextField
              fullWidth
              label="Paste a YouTube link"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") void download();
              }}
              disabled={downloading || busy}
              slotProps={{
                input: {
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconAction
                        title="Download the audio and add it at the end"
                        icon={<ArrowForwardIcon fontSize="small" />}
                        onClick={() => void download()}
                        disabled={!url.trim() || downloading || busy}
                      />
                    </InputAdornment>
                  ),
                },
              }}
            />
            {downloading ? (
              <Box role="status" aria-live="polite">
                <LinearProgress variant={percent === null ? "indeterminate" : "determinate"} value={percent ?? 0} />
                <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.75 }}>
                  {percent === null ? "Downloading" : `Downloading · ${Math.round(percent)}%`}
                </Typography>
              </Box>
            ) : null}
          </Stack>
        </Section>
      )}

      <ConfirmDialog
        open={removing !== null}
        title={`Remove “${removing?.name ?? ""}”?`}
        message="Its part of the audio and its cuts go. The notes must be transcribed again."
        confirmLabel="Remove the file"
        danger
        busy={busy}
        onConfirm={() => removing && void remove(removing)}
        onCancel={() => setRemoving(null)}
      />
    </Stack>
  );
}

function RenameField({ file, onDone, onCancel }: { file: AxisFile; onDone: (name: string) => void; onCancel: () => void }) {
  const [name, setName] = useState(file.name);
  return (
    <TextField
      autoFocus
      size="small"
      fullWidth
      label="Name"
      value={name}
      onChange={(event) => setName(event.target.value)}
      onKeyDown={(event) => {
        if (event.key === "Enter") onDone(name);
        if (event.key === "Escape") onCancel();
      }}
      onBlur={() => onDone(name)}
      onFocus={(event) => event.target.select()}
    />
  );
}

export default SourceFiles;
