/**
 * **One public song** (`/public/songs/:id`): its metadata, its chart history, its versions, and
 * **Add to my library** (implementation 02, Phase 13, plan sections 15.1 to 15.3).
 *
 * - The header: the title, its artists (each a link to the public artist), **Play** on the default
 *   version, and **Add to my library**. A song with no version yet cannot be added (the user's rule:
 *   every song of My library has its piano sheet), and the button says why on hover. Once the song
 *   is in My library, **Open in My library** goes to the user's own song.
 * - The facts of section 15.3 that the song has: year and decade, album, region, genres, tags,
 *   popularity (0 to 100, all time).
 * - **On the chart**: the best place, the weeks, and the line of its places (`ChartHistory`).
 * - **Versions**: the fixed versions (Hard, Medium, Easy, a custom name; **Default** marked), then
 *   **Other versions**, grouped by the user who made them, each group by likes. A version row has
 *   **Play**, a like (once per user, with the count), and in its `⋯`: **Add to my library** (that
 *   version only) or **Open in My library** when it is there.
 * - **Lyrics**, shown on request.
 *
 * Versions arrive by accepted requests (Phase 14). **Suggest a change** (the header's `⋯`) sends a
 * request to change the song's metadata; on the user's own version among the Other versions,
 * **Ask for a fixed version** asks for it to become Hard, Medium, Easy or a new name.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Checkbox from "@mui/material/Checkbox";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import Link from "@mui/material/Link";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import FavoriteIcon from "@mui/icons-material/Favorite";
import FavoriteBorderIcon from "@mui/icons-material/FavoriteBorder";
import EditNoteIcon from "@mui/icons-material/EditNoteOutlined";
import LibraryAddIcon from "@mui/icons-material/LibraryAddOutlined";
import StarIcon from "@mui/icons-material/StarBorder";
import LibraryMusicIcon from "@mui/icons-material/LibraryMusicOutlined";
import PlayIcon from "@mui/icons-material/PlayArrowRounded";
import PlayCircleIcon from "@mui/icons-material/PlayCircleOutlined";
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom";
import { publicApi, type PublicSongDetail, type PublicVersion } from "../../api";
import { ROUTES } from "../../layout/routes";
import { EmptyState, IconAction, PageBody, PageHeader, PillButton, RowMenu, Section } from "../../ui";
import { said } from "../library/shared";
import { FixedVersionDialog } from "../requests/SmallRequestDialogs";
import { SuggestChangeDialog } from "../requests/SuggestChangeDialog";
import { COUNTS_EVENT } from "../requests/words";
import { useAuth } from "../../state/authContext";
import { ChartHistory } from "./ChartHistory";
import { BASIS_HINT, defaultVersion, popularityText, versionLabel } from "./shared";

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Box sx={{ minWidth: 0 }}>
      <Typography sx={{ fontSize: 13, color: "text.secondary" }}>{label}</Typography>
      <Typography component="div" sx={{ fontSize: 15 }}>
        {children}
      </Typography>
    </Box>
  );
}

/** One version: its name, who made it, its likes, **Play**, and its `⋯`. */
function VersionLine({
  version,
  title,
  isDefault,
  onPlay,
  onLike,
  onAdd,
  onOpenMine,
  onAskFixed,
}: {
  version: PublicVersion;
  title: string;
  isDefault: boolean;
  onPlay: () => void;
  onLike: () => void;
  onAdd: () => void;
  onOpenMine: () => void;
  /** The user's own version: ask for it to become a fixed version (Phase 14). */
  onAskFixed?: () => void;
}) {
  return (
    <Stack
      direction="row"
      spacing={1}
      data-testid="public-version"
      sx={(theme) => ({
        alignItems: "center",
        borderRadius: 2,
        pr: 0.5,
        "&:hover": { backgroundColor: (theme.vars ?? theme).palette.action.hover },
      })}
    >
      <ButtonBase
        onClick={onPlay}
        disabled={!version.ready}
        sx={{ flex: 1, minWidth: 0, justifyContent: "flex-start", gap: 1.5, px: 1.5, py: 1.25, borderRadius: 2, textAlign: "left" }}
      >
        <Typography noWrap sx={{ fontWeight: 500, minWidth: 0, flexShrink: 0, maxWidth: "60%" }} title={title}>
          {title}
        </Typography>
        {isDefault ? (
          <Typography component="span" sx={{ fontSize: 13, color: "text.secondary", flexShrink: 0 }}>
            Default
          </Typography>
        ) : null}
        {version.inLibrary ? (
          <Typography component="span" sx={{ fontSize: 13, color: "text.secondary", flexShrink: 0, display: { xs: "none", sm: "inline" } }}>
            In My library
          </Typography>
        ) : null}
        <Box sx={{ flex: 1 }} />
        {version.creator ? (
          <Typography noWrap sx={{ fontSize: 13, color: "text.secondary", display: { xs: "none", sm: "block" } }}>
            by {version.creator}
          </Typography>
        ) : null}
      </ButtonBase>
      <Tooltip title={version.liked ? "Remove your like" : "Like this version"}>
        <ButtonBase
          onClick={onLike}
          aria-pressed={version.liked}
          aria-label={`${version.liked ? "Liked" : "Like"}, ${version.likes} ${version.likes === 1 ? "like" : "likes"}`}
          data-testid="like"
          sx={{ gap: 0.5, px: 1, height: 32, borderRadius: 16, color: "text.secondary", fontSize: 13, fontVariantNumeric: "tabular-nums" }}
        >
          {version.liked ? <FavoriteIcon sx={{ fontSize: 18, color: "text.primary" }} /> : <FavoriteBorderIcon sx={{ fontSize: 18 }} />}
          {version.likes}
        </ButtonBase>
      </Tooltip>
      <IconAction title="Play this version" icon={<PlayCircleIcon fontSize="small" />} onClick={onPlay} disabled={!version.ready} />
      <RowMenu
        title="Version actions"
        items={[
          version.inLibrary
            ? { label: "Open in My library", icon: <LibraryMusicIcon fontSize="small" />, onClick: onOpenMine }
            : { label: "Add to my library", icon: <LibraryAddIcon fontSize="small" />, onClick: onAdd, disabled: !version.ready },
          ...(onAskFixed ? [{ label: "Ask for a fixed version", icon: <StarIcon fontSize="small" />, onClick: onAskFixed }] : []),
        ]}
      />
    </Stack>
  );
}

/** **Add to my library**: which versions; the default one is ticked, the ones already there are shown done. */
function AddDialog({
  song,
  onClose,
  onAdded,
}: {
  song: PublicSongDetail;
  onClose: () => void;
  onAdded: (songId: number) => void;
}) {
  const every = useMemo(
    () => [
      ...song.fixed.map((one) => ({ version: one, label: versionLabel(one.name) })),
      ...song.others.flatMap((group) =>
        group.versions.map((one) => ({ version: one, label: `${versionLabel(one.name)} (${group.username})` })),
      ),
    ],
    [song],
  );
  const first = defaultVersion(song);
  const [picked, setPicked] = useState<Set<string>>(
    new Set(first && !first.inLibrary ? [first.projectId] : every.filter((one) => !one.version.inLibrary && one.version.ready).slice(0, 1).map((one) => one.version.projectId)),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const add = async () => {
    setBusy(true);
    setError(null);
    try {
      const pulled = await publicApi.pullSong(song.id, Array.from(picked));
      onAdded(pulled.id);
    } catch (caught) {
      setError(said(caught, "The song could not be added to your library."));
      setBusy(false);
    }
  };
  return (
    <Dialog open onClose={busy ? undefined : onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Add to my library</DialogTitle>
      <DialogContent>
        <Stack>
          {every.map(({ version, label }) => (
            <FormControlLabel
              key={version.projectId}
              control={
                <Checkbox
                  size="small"
                  checked={version.inLibrary !== null || picked.has(version.projectId)}
                  disabled={version.inLibrary !== null || !version.ready}
                  onChange={() =>
                    setPicked((current) => {
                      const next = new Set(current);
                      if (next.has(version.projectId)) next.delete(version.projectId);
                      else next.add(version.projectId);
                      return next;
                    })
                  }
                />
              }
              label={version.inLibrary ? `${label}, in My library` : label}
            />
          ))}
          {error ? (
            <Typography role="alert" color="error" sx={{ fontSize: 14, mt: 1 }}>
              {error}
            </Typography>
          ) : null}
        </Stack>
      </DialogContent>
      <DialogActions>
        <PillButton kind="quiet" onClick={onClose} disabled={busy}>
          Cancel
        </PillButton>
        <PillButton kind="primary" onClick={() => void add()} disabled={picked.size === 0} busy={busy} data-testid="add-confirm">
          {picked.size === 1 ? "Add 1 version" : `Add ${picked.size} versions`}
        </PillButton>
      </DialogActions>
    </Dialog>
  );
}

export function PublicSongPage() {
  const { id } = useParams();
  const songId = Number(id);
  const navigate = useNavigate();
  const [song, setSong] = useState<PublicSongDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [adding, setAdding] = useState(false);
  const [noticed, setNotice] = useState<{ text: string; songId: number; on: number } | null>(null);
  const notice = noticed?.on === songId ? noticed : null;
  const [actionError, setActionError] = useState<string | null>(null);
  const [shown, setLyrics] = useState<{ on: number; text: string } | null>(null);
  const lyrics = shown?.on === songId ? shown.text : null;
  const [lyricsError, setLyricsError] = useState<string | null>(null);
  const { user } = useAuth();
  const [suggesting, setSuggesting] = useState(false);
  const [askingFixed, setAskingFixed] = useState<PublicVersion | null>(null);
  const [sent, setSent] = useState<number | null>(null);
  const requestSent = (requestId: number) => {
    setSuggesting(false);
    setAskingFixed(null);
    setSent(requestId);
    window.dispatchEvent(new Event(COUNTS_EVENT));
  };

  useEffect(() => {
    const controller = new AbortController();
    publicApi
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

  const play = (version: PublicVersion) => navigate(ROUTES.play(version.parts[0] ?? version.projectId));

  const like = useCallback(async (version: PublicVersion) => {
    setActionError(null);
    try {
      const answer = version.liked ? await publicApi.unlike(version.projectId) : await publicApi.like(version.projectId);
      const update = (one: PublicVersion) =>
        one.projectId === version.projectId ? { ...one, likes: answer.likes, liked: answer.liked } : one;
      setSong((current) =>
        current
          ? {
              ...current,
              fixed: current.fixed.map(update),
              others: current.others.map((group) => ({ ...group, versions: group.versions.map(update) })),
            }
          : current,
      );
    } catch (caught) {
      setActionError(said(caught, "The like could not be saved."));
    }
  }, []);

  const addOne = async (version: PublicVersion) => {
    setActionError(null);
    try {
      const pulled = await publicApi.pullSong(songId, [version.projectId]);
      setNotice({ text: `“${versionLabel(version.name)}” added to My library`, songId: pulled.id, on: songId });
      setReload((count) => count + 1);
    } catch (caught) {
      setActionError(said(caught, "The version could not be added to your library."));
    }
  };

  const showLyrics = async () => {
    setLyricsError(null);
    try {
      setLyrics({ on: songId, text: (await publicApi.lyrics(songId)).text });
    } catch (caught) {
      setLyricsError(said(caught, "The lyrics could not be loaded."));
    }
  };

  if (error) {
    return (
      <PageBody>
        <PageHeader title="Song" back={{ to: ROUTES.publicSongs, label: "Back to Public songs" }} />
        <EmptyState message={error} action={<PillButton onClick={() => navigate(ROUTES.publicSongs)}>Open Public songs</PillButton>} />
      </PageBody>
    );
  }

  const chosen = song ? defaultVersion(song) : null;
  const versions = song ? song.fixed.length + song.others.reduce((sum, group) => sum + group.versions.length, 0) : 0;
  const allIn = song !== null && versions > 0 && [...song.fixed, ...song.others.flatMap((group) => group.versions)].every((one) => one.inLibrary || !one.ready);

  return (
    <PageBody>
      <PageHeader
        title={song?.title ?? ""}
        back={{ to: ROUTES.publicSongs, label: "Back to Public songs" }}
        actions={
          song ? (
            <>
              {chosen ? (
                <PillButton kind="primary" startIcon={<PlayIcon />} onClick={() => play(chosen)} data-testid="public-play">
                  Play
                </PillButton>
              ) : null}
              {song.inLibrary !== null ? (
                <PillButton kind="secondary" onClick={() => navigate(ROUTES.librarySong(song.inLibrary ?? 0))} data-testid="open-mine">
                  Open in My library
                </PillButton>
              ) : null}
              {!allIn ? (
                <Tooltip title={versions === 0 ? "No version yet: a song of your library needs its piano sheet" : ""}>
                  <span>
                    <PillButton
                      kind={chosen ? "secondary" : "primary"}
                      startIcon={<LibraryAddIcon />}
                      disabled={versions === 0}
                      onClick={() => setAdding(true)}
                      data-testid="add-to-library"
                    >
                      Add to my library
                    </PillButton>
                  </span>
                </Tooltip>
              ) : null}
              <RowMenu
                title="Song actions"
                items={[{ label: "Suggest a change", icon: <EditNoteIcon fontSize="small" />, onClick: () => setSuggesting(true) }]}
              />
            </>
          ) : undefined
        }
      />
      {song === null ? (
        <Stack spacing={1.5} sx={{ pt: 1 }} aria-busy>
          <Skeleton variant="text" width={200} />
          <Skeleton variant="rounded" height={112} />
          <Skeleton variant="rounded" height={44} />
        </Stack>
      ) : (
        <Stack spacing={3} sx={{ pt: 0.5, pb: 4 }}>
          <Typography sx={{ fontSize: 15, color: "text.secondary" }} data-testid="public-byline">
            {song.artists.length === 0
              ? "No artist"
              : song.artists.map((artist, index) => (
                  <span key={artist.artistId}>
                    {index > 0 ? ", " : ""}
                    <Link component={RouterLink} to={ROUTES.publicArtist(artist.artistId)} color="inherit" underline="hover">
                      {artist.name}
                    </Link>
                  </span>
                ))}
          </Typography>

          {notice ? (
            <Alert
              severity="success"
              onClose={() => setNotice(null)}
              action={
                <PillButton kind="quiet" size="small" onClick={() => navigate(ROUTES.librarySong(notice.songId))}>
                  Open
                </PillButton>
              }
            >
              {notice.text}
            </Alert>
          ) : null}
          {actionError ? <Alert severity="error" onClose={() => setActionError(null)}>{actionError}</Alert> : null}
          {sent !== null ? (
            <Alert
              severity="success"
              onClose={() => setSent(null)}
              action={
                <PillButton kind="quiet" size="small" onClick={() => navigate(ROUTES.request(sent))}>
                  Open
                </PillButton>
              }
            >
              Request sent to the master user
            </Alert>
          ) : null}

          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "repeat(2, minmax(0, 1fr))", sm: "repeat(auto-fill, minmax(150px, 1fr))" }, gap: 2, maxWidth: 760 }}>
            <Fact label="Year">{song.year !== null ? `${song.year} (${song.decade})` : "Unknown"}</Fact>
            {song.regionPopularity.length === 0 || song.regions.includes("Worldwide") ? (
              <Fact label={song.regionPopularity.length > 0 ? "Popularity worldwide" : "Popularity"}>
                {popularityText(song.popularity)} of 100
              </Fact>
            ) : null}
            {song.regionPopularity.map((one) => (
              <Fact key={one.region} label={one.region === "Worldwide" ? "Popularity worldwide" : `Popularity in ${one.region}`}>
                <Box component="span" title={BASIS_HINT[one.basis]}>
                  {one.basis === "weeks" ? "" : "≈ "}
                  {popularityText(one.popularity)} of 100
                </Box>
              </Fact>
            ))}
            {song.albums.length > 0 ? (
              <Fact label={song.albums.length > 1 ? "Albums" : "Album"}>
                {song.albums.map((album) => album.title).join(", ")}
              </Fact>
            ) : null}
            {song.regions.length > 0 ? <Fact label="Region">{song.regions.join(", ")}</Fact> : null}
            {song.genres.length > 0 ? <Fact label="Genre">{song.genres.join(", ")}</Fact> : null}
            {song.tags.length > 0 ? <Fact label="Tags">{song.tags.map(([category, value]) => `${value} (${category.replace("_", " ")})`).join(", ")}</Fact> : null}
          </Box>

          {song.charts.length > 0 ? (
            <Section title={song.charts.length > 1 ? "On the charts" : "On the chart"}>
              <Stack spacing={3}>
                {song.charts.map((chart) => (
                  <ChartHistory key={chart.name} chart={chart} named={song.charts.length > 1 || chart.region !== "Worldwide"} />
                ))}
              </Stack>
            </Section>
          ) : null}

          <Section title="Versions">
            {song.fixed.length === 0 ? (
              <Typography sx={{ fontSize: 14, color: "text.secondary", px: 1.5 }}>No version yet.</Typography>
            ) : (
              <Stack spacing={0.25}>
                {song.fixed.map((version) => (
                  <VersionLine
                    key={version.projectId}
                    version={version}
                    title={versionLabel(version.name)}
                    isDefault={chosen?.projectId === version.projectId}
                    onPlay={() => play(version)}
                    onLike={() => void like(version)}
                    onAdd={() => void addOne(version)}
                    onOpenMine={() => song.inLibrary !== null && navigate(ROUTES.librarySong(song.inLibrary))}
                  />
                ))}
              </Stack>
            )}
          </Section>

          {song.others.length > 0 ? (
            <Section title="Other versions">
              <Stack spacing={1.5}>
                {song.others.map((group) => (
                  <Box key={group.username}>
                    <Typography sx={{ fontSize: 13, color: "text.secondary", px: 1.5, pb: 0.25 }}>{group.username}</Typography>
                    <Stack spacing={0.25}>
                      {group.versions.map((version) => (
                        <VersionLine
                          key={version.projectId}
                          version={{ ...version, creator: null }}
                          title={version.name}
                          isDefault={chosen?.projectId === version.projectId && song.fixed.length === 0}
                          onPlay={() => play(version)}
                          onLike={() => void like(version)}
                          onAdd={() => void addOne(version)}
                          onOpenMine={() => song.inLibrary !== null && navigate(ROUTES.librarySong(song.inLibrary))}
                          onAskFixed={group.username === user?.username ? () => setAskingFixed(version) : undefined}
                        />
                      ))}
                    </Stack>
                  </Box>
                ))}
              </Stack>
            </Section>
          ) : null}

          {song.hasLyrics ? (
            <Section
              title="Lyrics"
              actions={
                lyrics === null ? (
                  <PillButton kind="secondary" size="small" onClick={() => void showLyrics()} data-testid="show-lyrics">
                    Show lyrics
                  </PillButton>
                ) : (
                  <PillButton kind="quiet" size="small" onClick={() => setLyrics(null)}>
                    Hide lyrics
                  </PillButton>
                )
              }
            >
              {lyricsError ? <Typography color="error" sx={{ fontSize: 14 }}>{lyricsError}</Typography> : null}
              {lyrics !== null ? (
                <Typography data-testid="lyrics" sx={{ whiteSpace: "pre-line", fontSize: 15, lineHeight: 1.7, maxWidth: "62ch" }}>
                  {lyrics}
                </Typography>
              ) : null}
            </Section>
          ) : null}
        </Stack>
      )}

      {suggesting && song ? (
        <SuggestChangeDialog target={{ kind: "song", song }} onClose={() => setSuggesting(false)} onSent={requestSent} />
      ) : null}
      {askingFixed && song ? (
        <FixedVersionDialog
          songTitle={song.title}
          version={{ projectId: askingFixed.projectId, name: askingFixed.name }}
          onClose={() => setAskingFixed(null)}
          onSent={requestSent}
        />
      ) : null}
      {adding && song ? (
        <AddDialog
          song={song}
          onClose={() => setAdding(false)}
          onAdded={(mine) => {
            setAdding(false);
            setNotice({ text: `“${song.title}” added to My library`, songId: mine, on: song.id });
            setReload((count) => count + 1);
          }}
        />
      ) : null}
    </PageBody>
  );
}

export default PublicSongPage;
