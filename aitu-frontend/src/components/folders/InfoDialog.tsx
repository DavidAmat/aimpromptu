/**
 * The dialog of the **info button** (implementation 04-3, Phase 1, plan section 4.4), the same on the sheet page,
 * on the song page of My Library and in a row's `⋯` menu: the title and the artist (read only here: they keep their
 * own dialogs), the **metadata** (rows of a primary key and a secondary key) and the **folders** the item is in.
 *
 * What it changes depends on the sheet: a project of My projects changes its own metadata and its folders of My
 * projects; a version of My Library changes its song's metadata and folders of My Library; a version of the Public
 * Library (or of a library shared with the user) is read only.
 */

import { useEffect, useMemo, useState } from "react";
import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import AddIcon from "@mui/icons-material/Add";
import CloseIcon from "@mui/icons-material/Close";
import { foldersApi, metadataApi, type FolderRow, type MetadataKeys, type TagRow } from "../../api";
import { said } from "../../pages/library/shared";
import { IconAction, PillButton } from "../../ui";
import { FolderChecklist } from "./FolderChecklist";
import { tagKeyLabel, TAG_KEYS } from "./tagWords";

/** What the dialog shows and changes. */
export interface InfoTarget {
  /** `project`: My projects; `song`: My Library; `public` and `none`: read only. */
  kind: "project" | "song" | "public" | "none";
  projectId: string | null;
  songId: number | null;
  title: string;
  artists: string[];
  tags: TagRow[];
  folders: number[];
  editable: boolean;
}

const sameRows = (a: readonly TagRow[], b: readonly TagRow[]) =>
  a.length === b.length && a.every((one, index) => one.category === b[index].category && one.value === b[index].value);

export function InfoDialog({
  target,
  onClose,
  onSaved,
}: {
  target: InfoTarget;
  onClose: () => void;
  /** After a save: the item's metadata and folders as the backend stored them. */
  onSaved?: (saved: { tags: TagRow[]; folders: number[] }) => void;
}) {
  const editable = target.editable && (target.kind === "project" || target.kind === "song");
  const [rows, setRows] = useState<TagRow[]>(target.tags);
  const [inFolders, setInFolders] = useState<Set<number>>(() => new Set(target.folders));
  const [keys, setKeys] = useState<MetadataKeys | null>(null);
  const [folders, setFolders] = useState<FolderRow[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!editable) return;
    const controller = new AbortController();
    metadataApi
      .keys(controller.signal)
      .then(setKeys)
      .catch(() => undefined);
    foldersApi
      .list(target.kind === "project" ? "projects" : "library", controller.signal)
      .then(setFolders)
      .catch(() => undefined);
    return () => controller.abort();
  }, [editable, target.kind]);

  const categories = keys?.categories ?? [...TAG_KEYS];
  const offered = useMemo(() => {
    const out = new Map<string, string[]>();
    for (const one of keys?.suggestions ?? []) {
      const list = out.get(one.category) ?? [];
      if (!list.some((value) => value.toLocaleLowerCase() === one.value.toLocaleLowerCase())) list.push(one.value);
      out.set(one.category, list);
    }
    return out;
  }, [keys]);

  const cleaned = rows.map((one) => ({ ...one, value: one.value.trim() })).filter((one) => one.value.length > 0);
  const tagsChanged = !sameRows(cleaned, target.tags);
  const foldersChanged = inFolders.size !== target.folders.length || target.folders.some((one) => !inFolders.has(one));

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      let tags = target.tags;
      let savedFolders = target.folders;
      if (tagsChanged) {
        tags =
          target.kind === "project" && target.projectId
            ? (await metadataApi.setOfProject(target.projectId, cleaned)).tags
            : target.songId !== null
              ? (await metadataApi.setOfSong(target.songId, cleaned)).tags
              : tags;
      }
      if (foldersChanged) {
        savedFolders =
          target.kind === "project" && target.projectId
            ? (await foldersApi.setOfProject(target.projectId, [...inFolders])).folders
            : target.songId !== null
              ? (await foldersApi.setOfSong(target.songId, [...inFolders])).folders
              : savedFolders;
      }
      onSaved?.({ tags, folders: savedFolders });
      onClose();
    } catch (caught) {
      setError(said(caught, "The info could not be saved."));
    } finally {
      setBusy(false);
    }
  };

  const fact = (label: string, value: string) => (
    <Stack direction="row" spacing={2} sx={{ alignItems: "baseline" }}>
      <Typography sx={{ width: 72, flexShrink: 0, fontSize: 13, color: "text.secondary" }}>{label}</Typography>
      <Typography sx={{ fontSize: 14, minWidth: 0 }} noWrap title={value}>
        {value}
      </Typography>
    </Stack>
  );

  return (
    <Dialog open onClose={busy ? undefined : onClose} maxWidth="sm" fullWidth data-testid="info-dialog">
      <DialogTitle>Info</DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ pt: 0.5 }}>
          <Stack spacing={0.75}>
            {fact("Title", target.title || "Untitled")}
            {fact("Artist", target.artists.join(", ") || "–")}
          </Stack>

          <Box>
            <Typography sx={{ fontSize: 13, fontWeight: 600, mb: 1 }}>Metadata</Typography>
            {!editable ? (
              rows.length === 0 ? (
                <Typography color="text.secondary" sx={{ fontSize: 14 }}>
                  No metadata
                </Typography>
              ) : (
                <Stack direction="row" sx={{ flexWrap: "wrap", gap: 1 }} data-testid="info-tags">
                  {rows.map((one) => (
                    <Chip key={`${one.category}:${one.value}`} size="small" label={`${tagKeyLabel(one.category)}: ${one.value}`} />
                  ))}
                </Stack>
              )
            ) : (
              <Stack spacing={1.25} data-testid="info-tags">
                {rows.map((one, index) => (
                  <Stack direction="row" spacing={1} key={index} sx={{ alignItems: "center" }} data-testid="info-tag-row">
                    <TextField
                      select
                      size="small"
                      label="Primary key"
                      value={one.category}
                      disabled={busy}
                      onChange={(event) =>
                        setRows(rows.map((row, at) => (at === index ? { ...row, category: event.target.value } : row)))
                      }
                      sx={{ width: 160, flexShrink: 0 }}
                    >
                      {categories.map((category) => (
                        <MenuItem key={category} value={category}>
                          {tagKeyLabel(category)}
                        </MenuItem>
                      ))}
                    </TextField>
                    <Autocomplete
                      freeSolo
                      size="small"
                      options={offered.get(one.category) ?? []}
                      inputValue={one.value}
                      disabled={busy}
                      onInputChange={(_event, value) =>
                        setRows(rows.map((row, at) => (at === index ? { ...row, value } : row)))
                      }
                      sx={{ flex: 1, minWidth: 0 }}
                      renderInput={(params) => <TextField {...params} label="Secondary key" />}
                    />
                    <IconAction
                      title="Remove this row"
                      icon={<CloseIcon />}
                      size="small"
                      disabled={busy}
                      onClick={() => setRows(rows.filter((_, at) => at !== index))}
                    />
                  </Stack>
                ))}
                <Box>
                  <PillButton
                    kind="quiet"
                    size="small"
                    startIcon={<AddIcon />}
                    disabled={busy}
                    onClick={() => setRows([...rows, { category: categories[0] ?? "films", value: "" }])}
                    data-testid="info-add-tag"
                  >
                    Add metadata
                  </PillButton>
                </Box>
              </Stack>
            )}
          </Box>

          {editable ? (
            <Box>
              <Typography sx={{ fontSize: 13, fontWeight: 600, mb: 0.5 }}>Folders</Typography>
              {folders === null ? (
                <Typography color="text.secondary" sx={{ fontSize: 14 }}>
                  …
                </Typography>
              ) : (
                <FolderChecklist folders={folders} value={inFolders} onChange={setInFolders} disabled={busy} />
              )}
            </Box>
          ) : null}

          {error ? (
            <Typography color="error" sx={{ fontSize: 14 }}>
              {error}
            </Typography>
          ) : null}
        </Stack>
      </DialogContent>
      <DialogActions>
        {editable ? (
          <>
            <PillButton kind="quiet" onClick={onClose} disabled={busy}>
              Cancel
            </PillButton>
            <PillButton
              kind="primary"
              onClick={() => void save()}
              disabled={!tagsChanged && !foldersChanged}
              busy={busy}
              data-testid="info-save"
            >
              Save
            </PillButton>
          </>
        ) : (
          <PillButton kind="quiet" onClick={onClose}>
            Close
          </PillButton>
        )}
      </DialogActions>
    </Dialog>
  );
}

export default InfoDialog;
