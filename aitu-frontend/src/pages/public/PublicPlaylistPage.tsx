/**
 * **One public playlist** (`/public/playlists/:id`): its songs in order, each with its version and
 * stretch (implementation 02, Phase 13, plan sections 15.1 and 17). **Play** opens Play mode on it
 * (from the song shaded by `?at=`, as Play mode's **Close** comes back); a row plays from that song,
 * and its `⋯` opens the public song. **Add to my library** makes the user's own songs playlist of
 * it, with its songs and versions pulled; a song with no version is left out.
 */

import { useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import LaunchIcon from "@mui/icons-material/Launch";
import LibraryAddIcon from "@mui/icons-material/LibraryAddOutlined";
import PlayIcon from "@mui/icons-material/PlayArrowRounded";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { publicApi, type PublicPlaylistDetail } from "../../api";
import { ROUTES } from "../../layout/routes";
import { EmptyState, ListRow, PageBody, PageHeader, PillButton } from "../../ui";
import { said, stretchLabel } from "../library/shared";
import { versionLabel } from "./shared";

export function PublicPlaylistPage() {
  const { id } = useParams();
  const playlistId = Number(id);
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const shaded = params.has("at") ? Number(params.get("at")) : null;
  const [playlist, setPlaylist] = useState<PublicPlaylistDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<{ text: string; id: number } | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    publicApi
      .playlist(playlistId, controller.signal)
      .then((found) => {
        setPlaylist(found);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "The playlist could not be loaded."));
      });
    return () => controller.abort();
  }, [playlistId]);

  const playable = playlist?.items.filter((item) => item.projectId !== null && item.parts.length > 0) ?? [];

  const add = async () => {
    setBusy(true);
    setActionError(null);
    try {
      const pulled = await publicApi.pullPlaylist(playlistId);
      setNotice({ text: `“${playlist?.title ?? ""}” added to My library`, id: pulled.id });
    } catch (caught) {
      setActionError(said(caught, "The playlist could not be added to your library."));
    } finally {
      setBusy(false);
    }
  };

  if (error) {
    return (
      <PageBody>
        <PageHeader title="Playlist" back={{ to: ROUTES.publicPlaylists, label: "Back to Public playlists" }} />
        <EmptyState message={error} action={<PillButton onClick={() => navigate(ROUTES.publicPlaylists)}>Open Public playlists</PillButton>} />
      </PageBody>
    );
  }

  return (
    <PageBody>
      <PageHeader
        title={playlist?.title ?? ""}
        back={{ to: ROUTES.publicPlaylists, label: "Back to Public playlists" }}
        actions={
          playlist ? (
            <>
              <PillButton kind="primary" startIcon={<PlayIcon />} disabled={playable.length === 0} onClick={() => navigate(ROUTES.playPublicPlaylist(playlistId))}>
                Play
              </PillButton>
              <PillButton kind="secondary" startIcon={<LibraryAddIcon />} disabled={playable.length === 0} busy={busy} onClick={() => void add()}>
                Add to my library
              </PillButton>
            </>
          ) : undefined
        }
      />
      {notice ? (
        <Alert
          severity="success"
          onClose={() => setNotice(null)}
          action={
            <PillButton kind="quiet" size="small" onClick={() => navigate(ROUTES.libraryPlaylist(notice.id))}>
              Open
            </PillButton>
          }
          sx={{ mb: 1 }}
        >
          {notice.text}
        </Alert>
      ) : null}
      {actionError ? <Alert severity="error" sx={{ mb: 1 }}>{actionError}</Alert> : null}
      {playlist === null ? (
        <Stack spacing={1} sx={{ pt: 1 }} aria-busy>
          {Array.from({ length: 4 }, (_, row) => (
            <Skeleton key={row} variant="rounded" height={44} />
          ))}
        </Stack>
      ) : playlist.items.length === 0 ? (
        <EmptyState message="This playlist has no songs." />
      ) : (
        <Stack spacing={0.25} sx={{ pt: 1 }}>
          {playlist.items.map((item, index) => {
            const at = playable.indexOf(item);
            return (
              <ListRow
                key={item.id}
                title={item.artists.length ? `${item.songTitle}, ${item.artists.join(", ")}` : item.songTitle}
                status={item.versionName ? versionLabel(item.versionName) : "No version"}
                meta={item.fromMs !== null && item.toMs !== null ? stretchLabel(item.fromMs, item.toMs) : "Whole"}
                selected={shaded !== null && at === shaded}
                onOpen={at >= 0 ? () => navigate(ROUTES.playPublicPlaylist(playlistId, at)) : undefined}
                leading={
                  <Typography sx={{ width: 20, fontSize: 13, color: "text.secondary", textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                    {index + 1}
                  </Typography>
                }
                menu={
                  item.songId !== null
                    ? [{ label: "Open the song", icon: <LaunchIcon fontSize="small" />, onClick: () => navigate(ROUTES.publicSong(item.songId ?? 0)) }]
                    : []
                }
              />
            );
          })}
        </Stack>
      )}
    </PageBody>
  );
}

export default PublicPlaylistPage;
