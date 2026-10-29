/**
 * **Songs** (`/library/songs`): the songs of the user's Private Library, finished work (implementation
 * 02, Phase 6, plan sections 6.1 and 15.1).
 *
 * A song comes here from **Save to library** on a project; the page has no button to make one. A
 * table, because songs are compared on the same fields: title, artist, how many versions, when one
 * last changed. A song whose version is being edited in Projects says so beside its title. A row opens
 * the song and its versions.
 *
 * Three pills sit above the table (implementation 04-3, Phase 1): **Folders** (the folders of My Library, opened and
 * closed as the Finder's list view: the rows keep their columns and only the title is indented), **All** (the table
 * as it was, with the text filter) and **Filter** (Artist and the metadata). A row's `⋯` has **Info** (the metadata)
 * and **Folders…**; in the Folders view a row dragged onto a folder moves into it.
 *
 * Songs picked with their checkbox are made into a songs playlist with **Make a playlist** (Phase
 * 10, the app context's dynamic playlist), each on its first version.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import CreateNewFolderIcon from "@mui/icons-material/CreateNewFolderOutlined";
import FolderIcon from "@mui/icons-material/FolderOutlined";
import InfoIcon from "@mui/icons-material/InfoOutlined";
import { useNavigate } from "react-router-dom";
import { AiMark } from "../../components/piece/AiMark";
import { FoldersDialog } from "../../components/folders/FolderChecklist";
import { FolderLeading, TriangleRoom } from "../../components/folders/FolderLeading";
import { folderCount, treeLines, type TreeLine } from "../../components/folders/folderTree";
import { InfoDialog } from "../../components/folders/InfoDialog";
import { FilterBar } from "../../components/folders/FilterBar";
import { filtered, useListFilter } from "../../components/folders/listFilter";
import { useFolderTree } from "../../components/folders/useFolderTree";
import { useListView } from "../../components/folders/listView";
import { ViewPills } from "../../components/folders/ViewPills";
import { foldersApi, libraryApi, playlistsApi, type SongRow } from "../../api";
import { ROUTES } from "../../layout/routes";
import {
  DataTable,
  EmptyState,
  fullTime,
  PageBody,
  PageHeader,
  PillButton,
  relativeTime,
  RowMenu,
  type DataColumn,
} from "../../ui";
import { INDENT_STEP } from "../../ui/ListRow";
import { TextDialog } from "./TextDialog";
import { said } from "./shared";

const artistsOf = (row: SongRow) => row.artists.map((artist) => artist.name).join(", ");
const artistNames = (row: SongRow) => row.artists.map((artist) => artist.name);
const byTitle = (a: SongRow, b: SongRow) => a.title.localeCompare(b.title, undefined, { sensitivity: "base" });

type Line = TreeLine<SongRow>;
const itemLine = (song: SongRow): Line => ({ kind: "item", item: song, depth: 0, from: null });

export function SongsPage() {
  const navigate = useNavigate();
  const [songs, setSongs] = useState<SongRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [text, setText] = useState("");
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [making, setMaking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [makeError, setMakeError] = useState<string | null>(null);
  const [view, setView] = useListView("aitu.library.view");
  const [choice, changeFilter] = useListFilter();
  const [foldering, setFoldering] = useState<SongRow | null>(null);
  const [informing, setInforming] = useState<SongRow | null>(null);
  const [folderError, setFolderError] = useState<string | null>(null);

  /** The picked songs, in the order the table lists them by title. */
  const makePlaylist = async (title: string) => {
    const chosen = (songs ?? []).filter((row) => picked.has(String(row.id)));
    setBusy(true);
    setMakeError(null);
    try {
      const made = await playlistsApi.create(
        title,
        chosen.map((row) => ({ songId: row.id })),
      );
      navigate(ROUTES.libraryPlaylist(made.id));
    } catch (caught) {
      setMakeError(said(caught, "The playlist could not be made."));
      setBusy(false);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    libraryApi
      .songs(controller.signal)
      .then((list) => {
        setSongs(list);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "The songs could not be loaded."));
      });
    return () => controller.abort();
  }, [reload]);

  /** A song's folders changed (the dialog, a drag): the row is updated where it is. */
  const setFolders = useCallback(async (row: SongRow, folders: number[]) => {
    const answer = await foldersApi.setOfSong(row.id, folders);
    setSongs((list) => list?.map((one) => (one.id === row.id ? { ...one, folders: answer.folders } : one)) ?? null);
  }, []);

  const tree = useFolderTree({
    area: "library",
    items: songs ?? [],
    onItemDrop: async (key, from, to) => {
      const row = songs?.find((one) => String(one.id) === key);
      if (!row) return;
      try {
        await setFolders(row, [...new Set([...row.folders.filter((one) => one !== from), to])]);
      } catch (caught) {
        setFolderError(said(caught, "The song could not be moved."));
      }
    },
    onChanged: () => setReload((count) => count + 1),
  });

  const lines = useMemo<Line[]>(() => {
    if (!songs) return [];
    if (view === "folders") return tree.folders ? treeLines(tree.folders, songs, tree.open, byTitle) : [];
    if (view === "filter") return filtered(songs, choice, artistNames, (row) => row.tags).map(itemLine);
    const wanted = text.trim().toLocaleLowerCase();
    const found = wanted ? songs.filter((row) => `${row.title} ${artistsOf(row)}`.toLocaleLowerCase().includes(wanted)) : songs;
    return found.map(itemLine);
  }, [songs, view, tree.folders, tree.open, choice, text]);

  const folders = view === "folders";
  const sorts = !folders;
  const lineKey = (line: Line) =>
    line.kind === "folder" ? `folder-${line.folder.id}` : folders ? `${line.from ?? "top"}-${line.item.id}` : String(line.item.id);
  const indent = (line: Line) => (line.depth > 0 ? { pl: `${line.depth * INDENT_STEP}px` } : {});

  const columns: DataColumn<Line>[] = [
    {
      key: "title",
      label: "Title",
      sortValue: sorts ? (line) => (line.kind === "item" ? line.item.title.toLocaleLowerCase() : null) : undefined,
      render: (line) =>
        line.kind === "folder" ? (
          <Stack direction="row" spacing={1} sx={{ alignItems: "center", minWidth: 0, ...indent(line) }} data-testid={`folder-${line.folder.id}`}>
            <FolderLeading open={line.open} />
            <Typography noWrap title={line.folder.name} sx={{ fontSize: 14, fontWeight: 500 }}>
              {line.folder.name}
            </Typography>
          </Stack>
        ) : (
          <Stack direction="row" spacing={1} sx={{ alignItems: "center", minWidth: 0, ...indent(line) }} data-testid={`song-${line.item.id}`}>
            {folders ? <TriangleRoom /> : null}
            <AiMark enhanced={line.item.enhanced} />
            <Typography noWrap title={line.item.title} sx={{ fontSize: 14, fontWeight: 500 }}>
              {line.item.title}
            </Typography>
            {line.item.editing ? (
              <Typography component="span" sx={{ fontSize: 13, color: "text.secondary", flexShrink: 0 }}>
                Editing
              </Typography>
            ) : null}
          </Stack>
        ),
    },
    {
      key: "artist",
      label: "Artist",
      sortValue: sorts ? (line) => (line.kind === "item" ? artistsOf(line.item).toLocaleLowerCase() : null) : undefined,
      render: (line) =>
        line.kind === "folder" ? (
          <Typography sx={{ fontSize: 14, color: "text.secondary" }}>{folderCount(line.count)}</Typography>
        ) : (
          <Typography noWrap title={artistsOf(line.item)} sx={{ fontSize: 14, color: "text.secondary" }}>
            {artistsOf(line.item) || "–"}
          </Typography>
        ),
    },
    {
      key: "versions",
      label: "Versions",
      align: "right",
      width: 96,
      sortValue: sorts ? (line) => (line.kind === "item" ? line.item.versions : null) : undefined,
      render: (line) => (line.kind === "item" ? line.item.versions : ""),
    },
    {
      key: "changed",
      label: "Changed",
      width: 132,
      sortValue: sorts ? (line) => (line.kind === "item" ? (line.item.updatedAt ?? "") : null) : undefined,
      render: (line) =>
        line.kind === "item" && line.item.updatedAt ? (
          <Tooltip title={fullTime(line.item.updatedAt)} placement="left">
            <span>{relativeTime(line.item.updatedAt)}</span>
          </Tooltip>
        ) : line.kind === "item" ? (
          "–"
        ) : (
          ""
        ),
    },
    {
      key: "menu",
      label: "",
      width: 48,
      render: (line) =>
        line.kind === "folder" ? (
          <RowMenu items={tree.menu(line.folder)} title="Folder actions" />
        ) : (
          <RowMenu
            items={[
              { label: "Info", icon: <InfoIcon fontSize="small" />, onClick: () => setInforming(line.item) },
              { label: "Folders…", icon: <FolderIcon fontSize="small" />, onClick: () => setFoldering(line.item) },
            ]}
          />
        ),
    },
  ];

  const pills = (
    <Stack direction="row" spacing={1.5} sx={{ alignItems: "center", minHeight: 36, flexWrap: "wrap", rowGap: 1 }}>
      <ViewPills value={view} onChange={setView} />
      {folders ? (
        <PillButton kind="quiet" size="small" startIcon={<CreateNewFolderIcon />} onClick={tree.newFolder} data-testid="new-folder">
          New folder
        </PillButton>
      ) : null}
    </Stack>
  );

  return (
    <PageBody>
      <PageHeader
        title="Songs"
        actions={
          picked.size > 0 && !folders ? (
            <PillButton kind="primary" onClick={() => setMaking(true)} data-testid="make-playlist">
              Make a playlist of {picked.size}
            </PillButton>
          ) : undefined
        }
      />
      {error ? (
        <EmptyState
          message={`The songs could not be loaded: ${error}`}
          action={<PillButton onClick={() => setReload((count) => count + 1)}>Try again</PillButton>}
        />
      ) : songs === null ? (
        <Stack spacing={1} sx={{ pt: 1 }} aria-busy>
          {Array.from({ length: 6 }, (_, row) => (
            <Skeleton key={row} variant="rounded" height={44} />
          ))}
        </Stack>
      ) : songs.length === 0 && !folders ? (
        <EmptyState
          message="No songs yet. Save a project to the library to add one."
          action={<PillButton onClick={() => navigate(ROUTES.projects)}>Open Projects</PillButton>}
        />
      ) : (
        <Stack spacing={1.5} sx={{ pt: 1 }}>
          {pills}
          {view === "all" ? (
            <TextField size="small" label="Filter" value={text} onChange={(event) => setText(event.target.value)} sx={{ maxWidth: 320 }} />
          ) : null}
          {view === "filter" ? (
            <FilterBar rows={songs} choice={choice} onChange={changeFilter} artistsOf={artistNames} tagsOf={(row) => row.tags} />
          ) : null}
          {folderError ? (
            <Typography color="error" sx={{ fontSize: 14 }}>
              {folderError}
            </Typography>
          ) : null}
          {folders && tree.error ? (
            <EmptyState message={tree.error} action={<PillButton onClick={tree.reload}>Try again</PillButton>} />
          ) : lines.length === 0 && !folders ? (
            view === "all" ? (
              <EmptyState
                message={`No song or artist matches “${text.trim()}”`}
                action={<PillButton onClick={() => setText("")}>Clear the filter</PillButton>}
              />
            ) : (
              <EmptyState message="No song matches the filter" />
            )
          ) : (
            <Box data-testid={folders ? "folder-tree" : "songs-table"}>
              <DataTable
                // A new table per view: the Folders view has no sort, the other two start by title.
                key={view}
                columns={columns}
                rows={lines}
                rowKey={lineKey}
                onRowClick={(line) => (line.kind === "folder" ? tree.toggle(line.folder.id) : navigate(ROUTES.librarySong(line.item.id)))}
                initialSort={sorts ? { key: "title", direction: "asc" } : undefined}
                rowsPerPageOptions={folders ? [200, 500] : undefined}
                selected={folders ? undefined : picked}
                onSelectedChange={folders ? undefined : setPicked}
                rowProps={
                  folders
                    ? (line) =>
                        line.kind === "folder"
                          ? { ...tree.folderRowProps(line.folder), "aria-expanded": line.open }
                          : tree.itemRowProps(String(line.item.id), line.from)
                    : undefined
                }
              />
            </Box>
          )}
        </Stack>
      )}
      {tree.dialogs}
      {foldering && tree.folders ? (
        <FoldersDialog
          title={`Folders of “${foldering.title}”`}
          folders={tree.folders}
          initial={foldering.folders}
          busy={busy}
          error={folderError}
          onCancel={() => {
            setFoldering(null);
            setFolderError(null);
          }}
          onSave={(chosen) => {
            setBusy(true);
            setFolderError(null);
            setFolders(foldering, chosen)
              .then(() => setFoldering(null))
              .catch((caught: unknown) => setFolderError(said(caught, "The folders could not be saved.")))
              .finally(() => setBusy(false));
          }}
        />
      ) : null}
      {informing ? (
        <InfoDialog
          target={{
            kind: "song",
            projectId: null,
            songId: informing.id,
            title: informing.title,
            artists: artistNames(informing),
            tags: informing.tags,
            folders: informing.folders,
            editable: true,
          }}
          onClose={() => setInforming(null)}
          onSaved={({ tags, folders: saved }) =>
            setSongs((list) => list?.map((one) => (one.id === informing.id ? { ...one, tags, folders: saved } : one)) ?? null)
          }
        />
      ) : null}
      {making ? (
        <TextDialog
          title="Make a playlist"
          label="Title"
          confirmLabel="Make the playlist"
          busy={busy}
          error={makeError}
          onCancel={() => setMaking(false)}
          onConfirm={(title) => void makePlaylist(title)}
        />
      ) : null}
    </PageBody>
  );
}

export default SongsPage;
