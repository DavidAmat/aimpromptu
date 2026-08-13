/** `/library` — browse promoted pieces and the playground staging list (Epic 10, Story 10.1). */

import { useCallback, useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import LocalOfferOutlinedIcon from "@mui/icons-material/LocalOfferOutlined";
import ReportProblemOutlinedIcon from "@mui/icons-material/ReportProblemOutlined";
import { useNavigate } from "react-router-dom";
import {
  libraryApi,
  type LibraryTrack,
  type PlaygroundTrack,
  type Promotion,
  type VersionHistoryEntry,
} from "../api";
import { ROUTES } from "../layout/routes";
import { activePromotions, libraryPlayId } from "../library/playId";
import { useWorkingArtifact } from "../state/useWorkingArtifact";
import { PageContainer, Pill, Placeholder, SectionCard, semantic } from "../ui";

interface BrowseState {
  query: string;
  tracks: LibraryTrack[] | null;
  playground: PlaygroundTrack[] | null;
  tags: string[];
  error: string | null;
}

export function LibraryPage() {
  const navigate = useNavigate();
  const { replace } = useWorkingArtifact();
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [tag, setTag] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [state, setState] = useState<BrowseState>({
    query: "",
    tracks: null,
    playground: null,
    tags: [],
    error: null,
  });
  const [renameTarget, setRenameTarget] = useState<PlaygroundTrack | null>(null);
  const [tagsTarget, setTagsTarget] = useState<LibraryTrack | null>(null);

  useEffect(() => {
    const handle = window.setTimeout(() => setSearch(searchInput.trim()), 200);
    return () => window.clearTimeout(handle);
  }, [searchInput]);

  const query = `${reloadToken}|${search}|${tag ?? ""}`;
  const current = state.query === query ? state : { ...state, query, tracks: null, playground: null };

  const load = useCallback(
    (signal?: AbortSignal) => {
      const needle = search || undefined;
      Promise.all([
        libraryApi.listTracks({ tag: tag ?? undefined, search: needle }, signal),
        libraryApi.listPlayground(needle, signal),
        libraryApi.listTags(signal),
      ])
        .then(([tracks, playground, tags]) =>
          setState({ query, tracks, playground, tags, error: null }),
        )
        .catch((caught: unknown) => {
          if (signal?.aborted) return;
          setState({
            query,
            tracks: [],
            playground: [],
            tags: [],
            error: caught instanceof Error ? caught.message : "Could not load the library.",
          });
        });
    },
    [search, tag, query],
  );

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const refresh = () => setReloadToken((value) => value + 1);

  const openPerformance = (track: LibraryTrack, promotion: Promotion) => {
    if (promotion.needsRederivation) return;
    const path = ROUTES.libraryPlay(libraryPlayId(track.artistSlug, track.trackSlug));
    const query = new URLSearchParams({ promotion: promotion.promotionName });
    navigate(`${path}?${query.toString()}`);
  };

  const openPlayground = (track: PlaygroundTrack, version?: VersionHistoryEntry) => {
    const chosen = version ?? track.versions.at(-1);
    if (!chosen?.audioUuid) return;
    replace({
      audioUuid: chosen.audioUuid,
      label: `${track.trackName} — ${track.artistName}`,
      frameMs: chosen.frameMs,
    });
    navigate(ROUTES.playgroundInput);
  };

  const { tracks, playground, tags, error } = current;
  const loading = tracks === null || playground === null;

  return (
    <PageContainer
      title="Piano Library"
      subtitle="Promoted pieces ready to play, and the playground staging list."
      actions={
        <TextField
          size="small"
          label="Search"
          placeholder="Artist, piece, or promotion name"
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          sx={{ minWidth: { sm: 280 } }}
        />
      }
    >
      {error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : null}

      <SectionCard
        title="Ready to play"
        description="Promoted pieces. Open the performance view only when the transcription is current."
        actions={
          loading ? <CircularProgress size={16} /> : (
            <Typography variant="caption" color="text.secondary">
              {tracks?.length ?? 0} piece{(tracks?.length ?? 0) === 1 ? "" : "s"}
            </Typography>
          )
        }
      >
        {tags.length > 0 ? (
          <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap", mb: 2 }}>
            <Pill label="All" selected={tag === null} onClick={() => setTag(null)} />
            {tags.map((item) => (
              <Pill
                key={item}
                label={item}
                selected={tag === item}
                onClick={() => setTag(tag === item ? null : item)}
              />
            ))}
          </Stack>
        ) : null}

        {loading ? (
          <LoadingLine />
        ) : tracks.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            Nothing promoted yet. Save a playground version and promote it.
          </Typography>
        ) : (
          <Stack spacing={2}>
            {tracks.map((track) => (
              <LibraryTrackRow
                key={`${track.artistSlug}/${track.trackSlug}`}
                track={track}
                onOpen={openPerformance}
                onEditTags={() => setTagsTarget(track)}
                onSelectTag={setTag}
              />
            ))}
          </Stack>
        )}
      </SectionCard>

      <SectionCard
        title="Playground"
        description="Staging before promotion. Rename the labels; slugs and folders never move."
      >
        {loading ? (
          <LoadingLine />
        ) : playground.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            The playground is empty. Transcribe a piece to put it here.
          </Typography>
        ) : (
          <Stack spacing={2}>
            {playground.map((track) => (
              <PlaygroundTrackRow
                key={`${track.artistSlug}/${track.trackSlug}`}
                track={track}
                onOpen={openPlayground}
                onRename={() => setRenameTarget(track)}
              />
            ))}
          </Stack>
        )}
      </SectionCard>

      <SectionCard title="Playlists">
        <Placeholder
          epic="Epic 10 (Piano Library), Story 10.3"
          what="Spotify-like playlists: CRUD, ordering, version-by-name selection and a playing mode with Next."
        />
      </SectionCard>

      {renameTarget ? (
        <RenameDialog track={renameTarget} onClose={() => setRenameTarget(null)} onSaved={refresh} />
      ) : null}
      {tagsTarget ? (
        <TagsDialog track={tagsTarget} onClose={() => setTagsTarget(null)} onSaved={refresh} />
      ) : null}
    </PageContainer>
  );
}

function LoadingLine() {
  return (
    <Stack direction="row" spacing={1} sx={{ alignItems: "center", py: 1 }}>
      <CircularProgress size={16} />
      <Typography variant="body2" color="text.secondary">
        Loading…
      </Typography>
    </Stack>
  );
}

function LibraryTrackRow({
  track,
  onOpen,
  onEditTags,
  onSelectTag,
}: {
  track: LibraryTrack;
  onOpen: (track: LibraryTrack, promotion: Promotion) => void;
  onEditTags: () => void;
  onSelectTag: (tag: string) => void;
}) {
  const live = activePromotions(track.promotions);
  const rows = live.length > 0 ? live : track.promotions;

  return (
    <Box sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 1.5 }}>
      <Stack direction="row" spacing={1} sx={{ alignItems: "flex-start", mb: 1 }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="subtitle1">
            {track.trackName}
            <Typography component="span" variant="body2" color="text.secondary">
              {" "}
              — {track.artistName}
            </Typography>
          </Typography>
          {track.tags.length > 0 ? (
            <Stack direction="row" spacing={0.5} useFlexGap sx={{ flexWrap: "wrap", mt: 0.5 }}>
              {track.tags.map((item) => (
                <Pill key={item} label={item} onClick={() => onSelectTag(item)} />
              ))}
            </Stack>
          ) : null}
        </Box>
        <Tooltip title="Edit tags">
          <IconButton size="small" aria-label={`Edit tags for ${track.trackName}`} onClick={onEditTags}>
            <LocalOfferOutlinedIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Stack>
      <Stack spacing={1}>
        {rows.map((promotion) => (
          <PromotionRow
            key={promotion.promotionName + promotion.promotedAt}
            track={track}
            promotion={promotion}
            showName={rows.length > 1 || promotion.promotionName !== `${track.trackName} - ${track.artistName}`}
            onOpen={onOpen}
          />
        ))}
      </Stack>
    </Box>
  );
}

function PromotionRow({
  track,
  promotion,
  showName,
  onOpen,
}: {
  track: LibraryTrack;
  promotion: Promotion;
  showName: boolean;
  onOpen: (track: LibraryTrack, promotion: Promotion) => void;
}) {
  const blocked = Boolean(promotion.needsRederivation);
  const rhythmLabel = promotion.hasSavedRhythm ? "Rhythm saved" : "Needs naming";

  return (
    <Stack
      direction={{ xs: "column", sm: "row" }}
      spacing={1}
      sx={{ alignItems: { sm: "center" }, justifyContent: "space-between" }}
    >
      <Box sx={{ minWidth: 0 }}>
        {showName ? (
          <Typography variant="body2">{promotion.promotionName}</Typography>
        ) : null}
        <Typography variant="caption" color="text.secondary">
          {promotion.sourceVersionFolder} · {rhythmLabel}
        </Typography>
        {blocked ? (
          <Stack direction="row" spacing={0.5} sx={{ alignItems: "center", mt: 0.5 }}>
            <ReportProblemOutlinedIcon fontSize="small" sx={{ color: semantic.status.warning }} />
            <Typography variant="caption" sx={{ color: semantic.status.warning }}>
              {promotion.needsRederivation}
            </Typography>
          </Stack>
        ) : null}
      </Box>
      <Tooltip title={blocked ? promotion.needsRederivation ?? "Cannot open in the performance view" : "Open performance view"}>
        <span>
          <Button
            size="small"
            variant="contained"
            disabled={blocked}
            onClick={() => onOpen(track, promotion)}
          >
            Open
          </Button>
        </span>
      </Tooltip>
    </Stack>
  );
}

function PlaygroundTrackRow({
  track,
  onOpen,
  onRename,
}: {
  track: PlaygroundTrack;
  onOpen: (track: PlaygroundTrack, version?: VersionHistoryEntry) => void;
  onRename: () => void;
}) {
  const latest = track.versions.at(-1);
  const canOpen = Boolean(latest?.audioUuid);

  return (
    <Box sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 1.5 }}>
      <Stack direction="row" spacing={1} sx={{ alignItems: "flex-start" }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="subtitle1">
            {track.trackName}
            <Typography component="span" variant="body2" color="text.secondary">
              {" "}
              — {track.artistName}
            </Typography>
          </Typography>
          {track.versions.length > 0 ? (
            <Stack direction="row" spacing={0.5} useFlexGap sx={{ flexWrap: "wrap", mt: 0.75 }}>
              {track.versions.map((version) => (
                <Pill
                  key={version.folder}
                  label={version.folder}
                  title={
                    version.audioUuid
                      ? `Open ${version.folder} in the Playground`
                      : `${version.folder} has no linked audio`
                  }
                  disabled={!version.audioUuid}
                  onClick={version.audioUuid ? () => onOpen(track, version) : undefined}
                />
              ))}
            </Stack>
          ) : (
            <Typography variant="caption" color="text.secondary">
              No wall-clock versions saved.
            </Typography>
          )}
          {track.needsRederivation ? (
            <Stack direction="row" spacing={0.5} sx={{ alignItems: "center", mt: 0.75 }}>
              <ReportProblemOutlinedIcon fontSize="small" sx={{ color: semantic.status.warning }} />
              <Typography variant="caption" sx={{ color: semantic.status.warning }}>
                {track.needsRederivation}
              </Typography>
            </Stack>
          ) : null}
        </Box>
        <Stack direction="row" spacing={0.5} sx={{ alignItems: "center", flexShrink: 0 }}>
          <Tooltip title="Rename display names">
            <IconButton size="small" aria-label={`Rename ${track.trackName}`} onClick={onRename}>
              <EditOutlinedIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title={canOpen ? "Open in Playground" : "This version has no linked audio"}>
            <span>
              <Button size="small" variant="outlined" disabled={!canOpen} onClick={() => onOpen(track)}>
                Open in Playground
              </Button>
            </span>
          </Tooltip>
        </Stack>
      </Stack>
    </Box>
  );
}

function RenameDialog({
  track,
  onClose,
  onSaved,
}: {
  track: PlaygroundTrack;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [artistName, setArtistName] = useState(track.artistName);
  const [trackName, setTrackName] = useState(track.trackName);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      await libraryApi.renamePlaygroundTrack(track.artistSlug, track.trackSlug, {
        artistName: artistName.trim(),
        trackName: trackName.trim(),
      });
      onSaved();
      onClose();
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught.message : "Could not rename.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Rename playground piece</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Folders stay at {`${track.artistSlug}/${track.trackSlug}`}. Only the names people read
          change.
        </Typography>
        {error ? (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        ) : null}
        <Stack spacing={2} sx={{ mt: 0.5 }}>
          <TextField
            label="Artist"
            value={artistName}
            onChange={(event) => setArtistName(event.target.value)}
            autoFocus
          />
          <TextField
            label="Piece"
            value={trackName}
            onChange={(event) => setTrackName(event.target.value)}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          onClick={() => void save()}
          disabled={saving || !artistName.trim() || !trackName.trim()}
        >
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function TagsDialog({
  track,
  onClose,
  onSaved,
}: {
  track: LibraryTrack;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [value, setValue] = useState(track.tags.join(", "));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const tags = value
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
      await libraryApi.setTags(track.artistSlug, track.trackSlug, tags);
      onSaved();
      onClose();
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught.message : "Could not save tags.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Tags</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Genre, mood, anything useful. Comma-separated. Combined with the search box.
        </Typography>
        {error ? (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        ) : null}
        <TextField
          label="Tags"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="edm, easy"
          fullWidth
          autoFocus
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={() => void save()} disabled={saving}>
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default LibraryPage;
