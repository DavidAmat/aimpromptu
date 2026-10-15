/**
 * **From other projects** (`/projects/compose`, implementation 02, plan section 10.4, Phase 10).
 *
 * The app context's three moves: choose a project; on its piano sheet (read only) mark a stretch,
 * or none for the whole sheet, and add it; from the second passage on, say whether it follows the
 * one before (**Sequential**) or starts under a title of its own (**Subheader**). The passages are
 * listed on the left in the order they will play and can be dragged to another place. **Save as
 * song** or **Save as integrated playlist** asks a title and makes the project
 * (`POST /projects/compose`), which opens on its Sheet step.
 *
 * The list is kept in the browser until it is saved (`state/composeDraft.ts`), so leaving the page
 * loses nothing. The passages are copies when the project is made: what is chosen here is only a
 * reference.
 */

import { useEffect, useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import MenuItem from "@mui/material/MenuItem";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import AddIcon from "@mui/icons-material/Add";
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import DeleteIcon from "@mui/icons-material/DeleteOutlined";
import { useNavigate } from "react-router-dom";
import {
  piecesApi,
  projectsApi,
  type PartRow,
  type ProjectRow,
  type StepStatus,
} from "../../api";
import { ROUTES } from "../../layout/routes";
import {
  EmptyState,
  IconAction,
  ListRow,
  movedOrder,
  PageHeader,
  PillButton,
  RailRow,
  Segmented,
  useRowDrag,
} from "../../ui";
import { newPassageKey, useComposeDraft, type DraftPassage, type Join } from "../../state/composeDraft";
import SheetPage, { type SheetStep } from "../piece/sheet/SheetPage";
import { said, stretchLabel } from "../library/shared";

type Kind = "song" | "integratedPlaylist";

/** What a project is called here: its song and version when it is in My library. */
function nameOf(row: ProjectRow): string {
  if (row.library) return `${row.library.songTitle} (${row.library.versionName})`;
  return row.title || "Untitled project";
}

/** The project whose sheet is open, and which of its parts. */
interface Source {
  row: ProjectRow;
  parts: PartRow[];
  part: string;
  sheet: StepStatus | null;
}

export function ComposePage() {
  const navigate = useNavigate();
  const [passages, setPassages] = useComposeDraft();
  const [projects, setProjects] = useState<ProjectRow[] | null>(null);
  const [filter, setFilter] = useState("");
  const [source, setSource] = useState<Source | null>(null);
  const [picking, setPicking] = useState(passages.length === 0);
  const [shown, setShown] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<Kind | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    projectsApi
      .list(["vault", "private"], controller.signal)
      .then((rows) => setProjects(rows.filter((row) => row.hasNotes)))
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "The projects could not be loaded."));
      });
    return () => controller.abort();
  }, []);

  const open = async (row: ProjectRow, part?: string) => {
    setError(null);
    try {
      const [{ parts }, ...statuses] = await Promise.all([
        projectsApi.parts(row.id),
        piecesApi.status(part ?? row.parts[0] ?? row.id),
      ]);
      const chosen = part ?? parts[0]?.id ?? row.id;
      setSource({
        row,
        parts,
        part: chosen,
        sheet: statuses[0].steps.find((step) => step.step === "sheet") ?? null,
      });
      setPicking(false);
    } catch (caught) {
      setError(said(caught, "That project could not be opened."));
    }
  };

  const add = (fromMs: number | null, toMs: number | null) => {
    if (!source) return;
    const index = source.parts.findIndex((part) => part.id === source.part);
    const partTitle = source.parts.length > 1 ? source.parts[index]?.subheader : null;
    const passage: DraftPassage = {
      key: newPassageKey(),
      part: source.part,
      project: source.row.id,
      title: partTitle || nameOf(source.row),
      fromMs,
      toMs,
      join: "sequential",
      subheader: "",
    };
    setPassages([...passages, passage]);
    setShown(passage.key);
  };

  const change = (key: string, patch: Partial<DraftPassage>) =>
    setPassages(passages.map((one) => (one.key === key ? { ...one, ...patch } : one)));
  const move = (from: number, to: number) => {
    if (to < 0 || to >= passages.length || from === to) return;
    setPassages(movedOrder(passages.length, from, to).map((index) => passages[index]));
  };
  const drag = useRowDrag(passages.length, move);

  const showPassage = (passage: DraftPassage) => {
    setShown(passage.key);
    const row = projects?.find((one) => one.id === passage.project);
    if (row) void open(row, passage.part);
  };

  const wanted = filter.trim().toLocaleLowerCase();
  const listed = useMemo(
    () => (projects ?? []).filter((row) => !wanted || nameOf(row).toLocaleLowerCase().includes(wanted)),
    [projects, wanted],
  );

  const sheetReady = source?.sheet?.enabled ?? false;
  const step = useMemo<SheetStep | null>(
    () =>
      source && source.sheet && sheetReady
        ? {
            audioUuid: source.part,
            label: nameOf(source.row),
            state: source.sheet.state,
            reason: source.sheet.reason,
            readOnly: true,
            onChanged: () => undefined,
            stretchAction: { label: "Add this stretch", onStretch: (fromMs, toMs) => add(fromMs, toMs) },
          }
        : null,
    // `add` reads the source and the list, both in the dependencies.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [source, sheetReady, passages],
  );

  // ------------------------------------------------------------------ the parts of the page

  const picker = (
    <Stack spacing={1.5} data-compose-picker sx={{ maxWidth: 760 }}>
      <TextField
        size="small"
        label="Filter"
        value={filter}
        onChange={(event) => setFilter(event.target.value)}
        sx={{ maxWidth: 320 }}
        autoFocus
      />
      {projects === null ? (
        <Stack spacing={1} aria-busy>
          {Array.from({ length: 5 }, (_, row) => (
            <Skeleton key={row} variant="rounded" height={44} />
          ))}
        </Stack>
      ) : listed.length === 0 ? (
        <EmptyState
          message={projects.length === 0 ? "No project has notes yet." : `Nothing matches “${filter.trim()}”`}
          action={
            projects.length === 0 ? undefined : <PillButton onClick={() => setFilter("")}>Clear the filter</PillButton>
          }
        />
      ) : (
        <Box role="list" aria-label="Projects to take a passage from">
          {listed.map((row) => (
            <Box role="listitem" key={row.id}>
              <ListRow
                data-testid={`compose-source-${row.id}`}
                title={nameOf(row)}
                status={row.layer === "private" ? "My library" : "Projects"}
                meta={row.parts.length > 1 ? `${row.parts.length} parts` : undefined}
                onOpen={() => void open(row)}
              />
            </Box>
          ))}
        </Box>
      )}
    </Stack>
  );

  const sourceView = source ? (
    <Stack spacing={2} data-compose-source={source.part}>
      <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1 }}>
        <Typography variant="h6" noWrap title={nameOf(source.row)} sx={{ fontSize: 18, minWidth: 0, flexShrink: 1 }}>
          {nameOf(source.row)}
        </Typography>
        {source.parts.length > 1 ? (
          <TextField
            select
            size="small"
            label="Part"
            value={source.part}
            onChange={(event) => void open(source.row, event.target.value)}
            sx={{ minWidth: 160 }}
          >
            {source.parts.map((part, index) => (
              <MenuItem key={part.id} value={part.id}>
                {part.subheader || `Part ${index + 1}`}
              </MenuItem>
            ))}
          </TextField>
        ) : null}
        <Box sx={{ flex: 1 }} />
        <PillButton kind="quiet" onClick={() => setPicking(true)}>
          Choose another project
        </PillButton>
        <PillButton kind="primary" onClick={() => add(null, null)} data-testid="compose-add-whole">
          {sheetReady ? "Add the whole sheet" : "Add the whole project"}
        </PillButton>
      </Stack>
      {step ? (
        <SheetPage key={source.part} step={step} />
      ) : (
        <EmptyState message="This project has no piano sheet yet: it can only be added whole." />
      )}
    </Stack>
  ) : null;

  const rail = (
    <Box
      component="nav"
      aria-label="Passages"
      data-compose-passages
      sx={{ width: { xs: "100%", md: 280 }, flexShrink: 0, position: { md: "sticky" }, top: { md: 16 }, alignSelf: "flex-start" }}
    >
      <Stack direction="row" sx={{ alignItems: "center", pl: 1.5, mb: 0.5 }}>
        <Typography variant="body2" color="text.secondary" sx={{ flex: 1 }}>
          Passages
        </Typography>
        <IconAction
          title="Add a passage"
          icon={<AddIcon fontSize="small" />}
          onClick={() => setPicking(true)}
          data-testid="compose-add"
        />
      </Stack>
      <Stack spacing={0.25}>
        {passages.map((passage, index) => (
          <Box key={passage.key} data-compose-passage={index}>
            {index > 0 ? <JoinControl passage={passage} onChange={(patch) => change(passage.key, patch)} /> : null}
            <RailRow
              leading={index + 1}
              label={passage.title}
              detail={
                passage.fromMs !== null && passage.toMs !== null
                  ? stretchLabel(passage.fromMs, passage.toMs)
                  : "Whole"
              }
              selected={shown === passage.key}
              onClick={() => showPassage(passage)}
              drag={drag(index)}
              menu={[
                {
                  label: "Move up",
                  icon: <ArrowUpwardIcon fontSize="small" />,
                  onClick: () => move(index, index - 1),
                  disabled: index === 0,
                },
                {
                  label: "Move down",
                  icon: <ArrowDownwardIcon fontSize="small" />,
                  onClick: () => move(index, index + 1),
                  disabled: index === passages.length - 1,
                },
                {
                  label: "Remove",
                  icon: <DeleteIcon fontSize="small" />,
                  danger: true,
                  onClick: () => setPassages(passages.filter((one) => one.key !== passage.key)),
                },
              ]}
            />
          </Box>
        ))}
      </Stack>
    </Box>
  );

  const disabled = passages.length === 0;
  return (
    <Box sx={{ px: { xs: 2, md: 3 }, pt: 1, pb: 4 }} data-compose-page>
      <PageHeader
        title="From other projects"
        back={{ to: ROUTES.projects, label: "Back to Projects" }}
        actions={
          <>
            <PillButton kind="secondary" disabled={disabled} onClick={() => setSaving("integratedPlaylist")}>
              Save as integrated playlist
            </PillButton>
            <PillButton kind="primary" disabled={disabled} onClick={() => setSaving("song")}>
              Save as song
            </PillButton>
          </>
        }
      />
      {error ? (
        <Alert severity="error" onClose={() => setError(null)} sx={{ my: 2 }}>
          {error}
        </Alert>
      ) : null}
      <Box sx={{ display: "flex", flexDirection: { xs: "column", md: "row" }, gap: 3, pt: 2 }}>
        {passages.length > 0 ? rail : null}
        <Box sx={{ flex: 1, minWidth: 0, width: "100%" }}>{picking || !source ? picker : sourceView}</Box>
      </Box>
      {saving ? (
        <SaveDialog
          kind={saving}
          passages={passages}
          onClose={() => setSaving(null)}
          onSaved={(row) => {
            setPassages([]);
            navigate(ROUTES.project(row.parts[0] ?? row.id, "sheet"));
          }}
        />
      ) : null}
    </Box>
  );
}

/** How a passage joins the one before it, and the title of a subheader. */
function JoinControl({ passage, onChange }: { passage: DraftPassage; onChange: (patch: Partial<DraftPassage>) => void }) {
  return (
    <Stack spacing={0.75} sx={{ pl: 4.5, py: 0.75, borderLeft: 1, borderColor: "divider", ml: 2.25 }}>
      <Segmented<Join>
        size="small"
        label="Join with the passage before"
        value={passage.join}
        onChange={(join) => onChange({ join })}
        options={[
          { value: "sequential", label: "Sequential", tooltip: "Plays on from the passage before" },
          { value: "subheader", label: "Subheader", tooltip: "Starts a new part, with a title" },
        ]}
      />
      {passage.join === "subheader" ? (
        <TextField
          size="small"
          label="Title"
          placeholder={passage.title}
          value={passage.subheader}
          onChange={(event) => onChange({ subheader: event.target.value })}
          slotProps={{ htmlInput: { maxLength: 300 } }}
        />
      ) : null}
    </Stack>
  );
}

/** The title of the project, and the save. */
function SaveDialog({
  kind,
  passages,
  onClose,
  onSaved,
}: {
  kind: Kind;
  passages: DraftPassage[];
  onClose: () => void;
  onSaved: (row: ProjectRow) => void;
}) {
  const names = [...new Set(passages.map((one) => one.title))];
  const [title, setTitle] = useState(names.length === 1 ? names[0] : names.slice(0, 3).join(" + "));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const label = kind === "song" ? "Save as song" : "Save as integrated playlist";

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      const row = await projectsApi.compose({
        title: title.trim(),
        kind,
        passages: passages.map((one, index) => ({
          part: one.part,
          fromMs: one.fromMs,
          toMs: one.toMs,
          join: index === 0 ? "sequential" : one.join,
          subheader: index === 0 || one.join === "subheader" ? one.subheader.trim() || null : null,
        })),
      });
      onSaved(row);
    } catch (caught) {
      setError(said(caught, "The project could not be made."));
      setBusy(false);
    }
  };

  return (
    <Dialog open onClose={busy ? undefined : onClose} maxWidth="xs" fullWidth>
      <DialogTitle>{label}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <TextField
            label="Title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && title.trim() && !busy) void save();
            }}
            slotProps={{ htmlInput: { maxLength: 300 } }}
            autoFocus
          />
          {error ? <Alert severity="error">{error}</Alert> : null}
        </Stack>
      </DialogContent>
      <DialogActions>
        <PillButton kind="quiet" onClick={onClose} disabled={busy}>
          Cancel
        </PillButton>
        <PillButton kind="primary" busy={busy} disabled={!title.trim()} onClick={() => void save()} data-testid="compose-save">
          {label}
        </PillButton>
      </DialogActions>
    </Dialog>
  );
}

export default ComposePage;
