/**
 * **One song of a shared library** (`/library/shared/songs/:id`, implementation 02, Phase 14, plan
 * section 15.4): its versions, read only.
 *
 * **Play** opens Play mode on the first version; a version row opens its sheet read only (a copy of
 * a passage from it works, as from any library). **Add to my library** copies the versions into the
 * user's own library, under their own song (the same public song, or the same title and artist),
 * named "<version> (<owner>)"; once there, **Open in My library** goes to it.
 */

import { useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import LaunchIcon from "@mui/icons-material/Launch";
import LibraryAddIcon from "@mui/icons-material/LibraryAddOutlined";
import PlayIcon from "@mui/icons-material/PlayCircleOutlined";
import { useNavigate, useParams } from "react-router-dom";
import { sharesApi, type SharedSong } from "../../api";
import { ROUTES } from "../../layout/routes";
import { EmptyState, ListRow, PageBody, PageHeader, PillButton, Section } from "../../ui";
import { said } from "./shared";

export function SharedSongPage() {
  const { id } = useParams();
  const songId = Number(id);
  const navigate = useNavigate();
  const [song, setSong] = useState<SharedSong | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ text: string; mine: number } | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    sharesApi
      .song(songId, controller.signal)
      .then((found) => {
        setSong(found);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "The song could not be loaded."));
      });
    return () => controller.abort();
  }, [songId, reload]);

  const add = async (versions: number[] = []) => {
    setBusy(true);
    setActionError(null);
    try {
      const added = await sharesApi.pull(songId, versions);
      setNotice({
        text: added.versions === 1 ? "1 version added to My library" : `${added.versions} versions added to My library`,
        mine: added.songId,
      });
      setReload((count) => count + 1);
    } catch (caught) {
      setActionError(said(caught, "The song could not be added to your library."));
    } finally {
      setBusy(false);
    }
  };

  const back = song
    ? { to: ROUTES.librarySharedFrom(song.ownerId), label: `Back to the library of ${song.owner}` }
    : { to: ROUTES.libraryShared, label: "Back to Shared" };

  if (error) {
    return (
      <PageBody>
        <PageHeader title="Song" back={{ to: ROUTES.libraryShared, label: "Back to Shared" }} />
        <EmptyState message={error} action={<PillButton onClick={() => navigate(ROUTES.libraryShared)}>Open Shared</PillButton>} />
      </PageBody>
    );
  }

  const allIn = song !== null && song.versions.length > 0 && song.versions.every((one) => one.inLibrary);
  const first = song?.versions[0];
  return (
    <PageBody>
      <PageHeader
        title={song?.title ?? ""}
        back={back}
        actions={
          song ? (
            <>
              {first ? (
                <PillButton kind="primary" startIcon={<PlayIcon />} onClick={() => navigate(ROUTES.play(first.projectId))} data-testid="shared-play">
                  Play
                </PillButton>
              ) : null}
              {song.inLibrary !== null ? (
                <PillButton kind="secondary" onClick={() => navigate(ROUTES.librarySong(song.inLibrary ?? 0))}>
                  Open in My library
                </PillButton>
              ) : null}
              {!allIn && song.versions.length > 0 ? (
                <PillButton kind="secondary" startIcon={<LibraryAddIcon />} busy={busy} onClick={() => void add()} data-testid="shared-add">
                  Add to my library
                </PillButton>
              ) : null}
            </>
          ) : undefined
        }
      />
      {song === null ? (
        <Stack spacing={1} sx={{ pt: 1 }} aria-busy>
          <Skeleton variant="text" width={180} />
          <Skeleton variant="rounded" height={44} />
        </Stack>
      ) : (
        <>
          <Typography sx={{ color: "text.secondary", fontSize: 14, mb: 2 }}>
            {song.artists.join(", ") || "No artist"}
            <Box component="span" sx={{ ml: 2 }}>
              From the library of {song.owner}
            </Box>
          </Typography>
          {notice ? (
            <Alert
              severity="success"
              onClose={() => setNotice(null)}
              sx={{ mb: 2 }}
              action={
                <PillButton kind="quiet" size="small" onClick={() => navigate(ROUTES.librarySong(notice.mine))}>
                  Open
                </PillButton>
              }
            >
              {notice.text}
            </Alert>
          ) : null}
          {actionError ? (
            <Alert severity="error" onClose={() => setActionError(null)} sx={{ mb: 2 }}>
              {actionError}
            </Alert>
          ) : null}
          <Section title="Versions">
            {song.versions.length === 0 ? (
              <Typography color="text.secondary" sx={{ px: 1.5 }}>
                No versions
              </Typography>
            ) : (
              <Box role="list" aria-label="Versions">
                {song.versions.map((version) => {
                  const part = version.parts[0] ?? version.projectId;
                  return (
                    <Box role="listitem" key={version.id}>
                      <ListRow
                        data-testid={`shared-version-${version.id}`}
                        title={version.name}
                        status={version.inLibrary ? "In My library" : undefined}
                        onOpen={() => navigate(ROUTES.project(part, "sheet"))}
                        menu={[
                          { label: "Open", icon: <LaunchIcon fontSize="small" />, onClick: () => navigate(ROUTES.project(part, "sheet")) },
                          { label: "Play", icon: <PlayIcon fontSize="small" />, onClick: () => navigate(ROUTES.play(version.projectId)) },
                          {
                            label: "Add to my library",
                            icon: <LibraryAddIcon fontSize="small" />,
                            onClick: () => void add([version.id]),
                            disabled: version.inLibrary !== null,
                          },
                        ]}
                      />
                    </Box>
                  );
                })}
              </Box>
            )}
          </Section>
        </>
      )}
    </PageBody>
  );
}

export default SharedSongPage;
