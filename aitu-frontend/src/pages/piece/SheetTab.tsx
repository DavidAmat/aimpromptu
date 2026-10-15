/**
 * Step 5 (**Sheet**): the piano sheet of the Playground, inside the flow page (plan section 9.7).
 *
 * The page is `sheet/SheetPage`, with every tool it has. The flow page gives it the piece and
 * the state of the Sheet step, so it can open a stale reading with its banner (plan section 8.3),
 * and asks the backend again after a save or **Remove all**, so the tick of the tab follows.
 *
 * A project of several parts (implementation 02, Phase 10: an integrated playlist, or a part split
 * in two) shows its parts beside the sheet (`PartsPanel`); **Start a new part here** of the range
 * toolbox splits the part on show. A version of the library offers **Add to a playlist** on a
 * marked stretch.
 */

import { useCallback, useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import { projectsApi, type PartRow, type SavedRhythm } from "../../api";
import SheetPage, { type SheetStep } from "./sheet/SheetPage";
import { PartsPanel } from "./PartsPanel";
import { AddToPlaylistDialog } from "../library/AddToPlaylistDialog";
import { said } from "../library/shared";
import { stepStatus, usePiece } from "./pieceContext";

export function SheetTab() {
  const { uuid, audio, status, refresh, readOnly } = usePiece();
  const here = stepStatus(status, "sheet");
  const state = here?.state ?? null;
  const reason = here?.reason ?? null;
  /** In a project of several parts, a part's sheet is titled by its subheader. */
  const [partTitle, setPartTitle] = useState<string | null>(null);
  const label = partTitle ?? (audio ? audio.alias || "Untitled project" : undefined);
  const audioRevision = status?.revisions.audio ?? undefined;
  const projectId = audio?.projectId ?? uuid;
  const library = audio?.layer === "private";

  /** Bumped when a change of parts rewrote this part's music: the sheet is read again. */
  const [sheetVersion, setSheetVersion] = useState(0);
  const [partsVersion, setPartsVersion] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [toPlaylist, setToPlaylist] = useState<{ fromMs: number; toMs: number } | null>(null);

  const onParts = useCallback(
    (parts: PartRow[]) => {
      const index = parts.findIndex((part) => part.id === uuid);
      setPartTitle(parts.length > 1 && index >= 0 ? parts[index].subheader || `Part ${index + 1}` : null);
    },
    [uuid],
  );

  const split = useCallback(
    async (atMs: number, sheet: SavedRhythm | null): Promise<boolean> => {
      if (!uuid || !projectId) return false;
      setError(null);
      try {
        await projectsApi.splitPart(projectId, uuid, { atMs, sheet });
        setPartsVersion((value) => value + 1);
        setSheetVersion((value) => value + 1);
        void refresh();
        return true;
      } catch (caught) {
        setError(said(caught, "The part could not be split."));
        return false;
      }
    },
    [uuid, projectId, refresh],
  );

  const step = useMemo<SheetStep | null>(
    () =>
      uuid && state
        ? {
            audioUuid: uuid,
            label,
            state,
            reason,
            readOnly,
            audioRevision,
            onChanged: () => void refresh(),
            ...(readOnly ? {} : { onSplit: split }),
            ...(library
              ? {
                  stretchAction: {
                    label: "Add to a playlist",
                    onStretch: (fromMs: number, toMs: number) => setToPlaylist({ fromMs, toMs }),
                  },
                }
              : {}),
          }
        : null,
    [uuid, label, state, reason, readOnly, audioRevision, refresh, split, library],
  );

  if (!step || !projectId) return null;
  return (
    <Box sx={{ display: "flex", flexDirection: { xs: "column", md: "row" }, gap: 3, alignItems: "flex-start" }}>
      <PartsPanel
        projectId={projectId}
        current={step.audioUuid}
        readOnly={readOnly}
        version={partsVersion}
        onParts={onParts}
        onMusicChanged={() => {
          setSheetVersion((value) => value + 1);
          void refresh();
        }}
      />
      <Box sx={{ flex: 1, minWidth: 0, width: "100%" }}>
        {error ? (
          <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
            {error}
          </Alert>
        ) : null}
        {/* Keyed by the piece, so nothing of one piece's sheet is shown over the next one. */}
        <SheetPage key={`${step.audioUuid}:${sheetVersion}`} step={step} />
      </Box>
      {toPlaylist && audio?.projectId ? (
        <AddToPlaylistDialog
          projectId={audio.projectId}
          stretch={toPlaylist}
          onClose={() => setToPlaylist(null)}
        />
      ) : null}
    </Box>
  );
}

export default SheetTab;
