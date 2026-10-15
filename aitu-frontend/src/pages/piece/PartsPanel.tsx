/**
 * The parts of a project, beside its Sheet step (implementation 02, plan section 14.1, Phase 10):
 * the sub-songs of an integrated playlist, or the parts a split made.
 *
 * One row per part, in the order they play, named by the title above it (its subheader). A click
 * opens that part's sheet (every step works on a part, so the step tabs then follow it). A row is
 * dragged to another place; its `⋯` renames it, moves it, or joins it to the part before it (one
 * part, played without a break). **Start a new part here** in the range toolbox splits a part.
 * Shown only for a project of more than one part.
 */

import { useCallback, useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import EditIcon from "@mui/icons-material/EditOutlined";
import MergeIcon from "@mui/icons-material/CallMerge";
import { useNavigate } from "react-router-dom";
import { projectsApi, type PartRow } from "../../api";
import { ROUTES } from "../../layout/routes";
import { movedOrder, RailRow, useRowDrag } from "../../ui";
import { TextDialog } from "../library/TextDialog";
import { said } from "../library/shared";

/** A length as `m:ss`. */
function clock(ms: number): string {
  const seconds = Math.round(ms / 1000);
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

/** What a part is called on the panel: its subheader, or its place. */
function partName(part: PartRow, index: number): string {
  return part.subheader || `Part ${index + 1}`;
}

export interface PartsPanelProps {
  projectId: string;
  /** The part on show. */
  current: string;
  readOnly: boolean;
  /** Changes when a write elsewhere (a split) changed the parts. */
  version: number;
  /** A change that rewrote the music of a part (a join): the sheet on show is read again. */
  onMusicChanged: () => void;
  /** The parts, each time they are read or changed. */
  onParts?: (parts: PartRow[]) => void;
}

export function PartsPanel({ projectId, current, readOnly, version, onMusicChanged, onParts }: PartsPanelProps) {
  const navigate = useNavigate();
  const [parts, setParts] = useState<PartRow[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [renaming, setRenaming] = useState<{ part: PartRow; index: number } | null>(null);

  useEffect(() => {
    if (parts) onParts?.(parts);
  }, [parts, onParts]);

  useEffect(() => {
    const controller = new AbortController();
    projectsApi
      .parts(projectId, controller.signal)
      .then((answer) => setParts(answer.parts))
      .catch(() => {
        if (!controller.signal.aborted) setParts(null);
      });
    return () => controller.abort();
  }, [projectId, version]);

  const run = useCallback(
    async (action: () => Promise<{ parts: PartRow[]; part: string | null }>, fallback: string) => {
      setBusy(true);
      setError(null);
      try {
        const answer = await action();
        setParts(answer.parts);
        return answer;
      } catch (caught) {
        setError(said(caught, fallback));
        return null;
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  const move = (from: number, to: number) => {
    if (!parts || from === to || to < 0 || to >= parts.length) return;
    const order = movedOrder(parts.length, from, to).map((index) => parts[index].id);
    // Shown at once; the answer confirms it.
    setParts(order.map((id) => parts.find((part) => part.id === id) as PartRow));
    void run(() => projectsApi.reorderParts(projectId, order), "The parts could not be moved.");
  };
  const drag = useRowDrag(parts?.length ?? 0, move, readOnly || busy);

  const join = async (part: PartRow) => {
    const answer = await run(() => projectsApi.joinPart(projectId, part.id), "The parts could not be joined.");
    if (!answer) return;
    onMusicChanged();
    if (answer.part && answer.part !== current) navigate(ROUTES.project(answer.part, "sheet"));
  };

  if (!parts || parts.length < 2) return null;

  return (
    <Box
      component="nav"
      aria-label="Parts"
      data-parts-panel
      sx={{
        width: { xs: "100%", md: 240 },
        flexShrink: 0,
        position: { md: "sticky" },
        top: { md: 16 },
        alignSelf: "flex-start",
      }}
    >
      <Stack spacing={0.25} aria-busy={busy}>
        {parts.map((part, index) => (
          <RailRow
            key={part.id}
            leading={index + 1}
            label={partName(part, index)}
            detail={clock(part.durationMs)}
            selected={part.id === current}
            onClick={() => navigate(ROUTES.project(part.id, "sheet"))}
            drag={readOnly ? undefined : drag(index)}
            testId={`part-${index}`}
            menu={
              readOnly
                ? undefined
                : [
                    {
                      label: "Rename",
                      icon: <EditIcon fontSize="small" />,
                      onClick: () => setRenaming({ part, index }),
                    },
                    {
                      label: "Move up",
                      icon: <ArrowUpwardIcon fontSize="small" />,
                      onClick: () => move(index, index - 1),
                      disabled: index === 0 || busy,
                    },
                    {
                      label: "Move down",
                      icon: <ArrowDownwardIcon fontSize="small" />,
                      onClick: () => move(index, index + 1),
                      disabled: index === parts.length - 1 || busy,
                    },
                    {
                      label: `Join with “${partName(parts[Math.max(0, index - 1)], Math.max(0, index - 1))}”`,
                      icon: <MergeIcon fontSize="small" />,
                      onClick: () => void join(part),
                      disabled: index === 0 || busy,
                    },
                  ]
            }
          />
        ))}
      </Stack>
      {error ? (
        <Alert severity="error" onClose={() => setError(null)} sx={{ mt: 1 }}>
          {error}
        </Alert>
      ) : null}
      {renaming ? (
        <TextDialog
          title="Rename the part"
          label="Title"
          initial={renaming.part.subheader ?? ""}
          confirmLabel="Rename"
          busy={busy}
          error={error}
          onCancel={() => setRenaming(null)}
          onConfirm={(value) => {
            void run(
              () => projectsApi.renamePart(projectId, renaming.part.id, value.trim() || null),
              "The part could not be renamed.",
            ).then((answer) => {
              if (answer) setRenaming(null);
            });
          }}
        />
      ) : null}
    </Box>
  );
}

export default PartsPanel;
