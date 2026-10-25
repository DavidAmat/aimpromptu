/**
 * **Play mode** (implementation 02, plan section 17, Phase 11): the piano sheet and nothing else.
 *
 * `/play/:projectId` plays a project or a version of the library; `/play/playlist/:playlistId` a
 * songs playlist. The page draws the sheet of every part of the song one after the other (the
 * sub-songs of an integrated playlist, each under its subheader), and in a songs playlist one song
 * at a time, or every song on one page when **All songs** is chosen.
 *
 * On the page: **Close** and, in a songs playlist, **Next** at the top right; **Play / Pause** at
 * the bottom. While the music plays the page keeps the cursor in the middle of the window, each
 * lyrics piece shows while its frames sound, and the buttons fade until the pointer moves. A small
 * menu at the top left (shown with them) switches to **Notes Falling** and, in a songs playlist,
 * between one song and all songs. Space plays and pauses, the arrows scroll, Escape closes.
 *
 * Each part is the Sheet step's own page (`SheetPage` with `step.play`), so the sheet is drawn
 * exactly as it is edited. Each has its own player: the page says which one plays. The parts of one
 * song play on without a stop (an integrated playlist is played nonstop); at the end of a song of a
 * songs playlist the next one opens and waits for Play (a songs playlist is played song by song).
 *
 * The address keeps the choices (`at`, the song; `view=falling`; `all=1`), so a reload keeps them.
 */

import {
  memo,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type RefObject,
} from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import CloseIcon from "@mui/icons-material/Close";
import PauseIcon from "@mui/icons-material/Pause";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import SkipNextIcon from "@mui/icons-material/SkipNext";
import { useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import type { ScorePlayerControls } from "../../components/time/ScorePlayer";
import { ROUTES } from "../../layout/routes";
import { EmptyState, IconAction, Segmented, ui } from "../../ui";
import { said } from "../library/shared";
import SheetPage, { type PlayView, type SheetStep } from "../piece/sheet/SheetPage";
import { FallingView } from "./FallingView";
import {
  createPlayClock,
  playlistQueue,
  projectQueue,
  type PlayClock,
  type PlayPart,
  type PlayQueue,
} from "./playQueue";

/** How long the buttons stay after the pointer stops, while the music plays. */
const AWAKE_MS = 2500;
/** **All songs** is remembered in this browser for the next playlist. */
const ALL_SONGS_KEY = "aitu.play.allSongs";

type PlayerRef = RefObject<ScorePlayerControls | null>;

/** A part on the page: `<song>:<part>`. */
function keyOf(song: number, part: number) {
  return `${song}:${part}`;
}
function partsOfKey(key: string): [number, number] {
  const [song, part] = key.split(":").map(Number);
  return [song ?? 0, part ?? 0];
}

function readAllSongs(): boolean {
  try {
    return window.localStorage.getItem(ALL_SONGS_KEY) === "1";
  } catch {
    return false;
  }
}

/** What every part on the page reports, by its key. Stable functions, so a part is drawn once. */
interface PartEvents {
  playing: (key: string, now: boolean) => void;
  ended: (key: string) => void;
  seek: (key: string) => void;
  time: (key: string, seconds: number | null) => void;
}

export function PlayPage() {
  const { projectId, playlistId } = useParams();
  const isPlaylist = playlistId !== undefined;
  const [params, setParams] = useSearchParams();
  // A playlist of the Public Library (Phase 13): the same items, read from `/public`.
  const isPublic = isPlaylist && params.get("from") === "public";
  const navigate = useNavigate();
  const location = useLocation();

  const [queue, setQueue] = useState<{ key: string; value: PlayQueue } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const queueKey = isPlaylist ? `${isPublic ? "public" : "playlist"}:${playlistId}` : `project:${projectId}`;
  useEffect(() => {
    const controller = new AbortController();
    const load = isPlaylist
      ? playlistQueue(Number(playlistId), controller.signal, isPublic)
      : projectQueue(projectId ?? "", controller.signal);
    load
      .then((value) => setQueue({ key: queueKey, value }))
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "This could not be opened."));
      });
    return () => controller.abort();
  }, [isPlaylist, isPublic, playlistId, projectId, queueKey]);
  const songs = useMemo(() => (queue && queue.key === queueKey ? queue.value.songs : null), [queue, queueKey]);

  const lastSong = Math.max(0, (songs?.length ?? 1) - 1);
  const at = Math.min(lastSong, Math.max(0, Number(params.get("at") ?? 0) || 0));
  const falling = params.get("view") === "falling";
  const allSongs = isPlaylist && (params.has("all") ? params.get("all") === "1" : readAllSongs());
  const change = useCallback(
    (patch: Record<string, string | null>) => {
      setParams(
        (current) => {
          const next = new URLSearchParams(current);
          for (const [name, value] of Object.entries(patch)) {
            if (value === null) next.delete(name);
            else next.set(name, value);
          }
          return next;
        },
        { replace: true },
      );
    },
    [setParams],
  );

  /** The songs on the page: one, or every one (a project has one). */
  const shown = useMemo(
    () =>
      (songs ?? [])
        .map((song, index) => ({ song, index }))
        .filter(({ index }) => !isPlaylist || allSongs || index === at),
    [songs, isPlaylist, allSongs, at],
  );
  const order = useMemo(
    () => shown.flatMap(({ song, index }) => song.parts.map((_, part) => keyOf(index, part))),
    [shown],
  );

  // The part the page plays: the first part of the song opened, until another one plays or is
  // moved on. Kept with the song it was chosen for, so Next starts the next song at its start.
  const [chosen, setChosen] = useState<{ forAt: number; key: string } | null>(null);
  const active = chosen && chosen.forAt === at && order.includes(chosen.key) ? chosen.key : keyOf(at, 0);
  const activeNow = useRef(active);
  useEffect(() => {
    activeNow.current = active;
  }, [active]);
  const choose = useCallback((key: string) => setChosen({ forAt: at, key }), [at]);

  /** Each part's transport, by its key; one object for the page's life, filled as parts appear. */
  const [players] = useState(() => new Map<string, PlayerRef>());
  const playerOf = useCallback(
    (key: string): PlayerRef => {
      let found = players.get(key);
      if (!found) {
        found = { current: null };
        players.set(key, found);
      }
      return found;
    },
    [players],
  );
  /** The parts sounding now: one at most, once the page has stopped the one before. */
  const sounding = useRef(new Set<string>());
  const [playing, setPlaying] = useState(false);
  const clock = useMemo<PlayClock>(() => createPlayClock(), []);

  /** Start a part as soon as its sheet and its player are there (the next part may still load). */
  const startWaiting = useRef<number | null>(null);
  const startWhenReady = useCallback(
    (key: string) => {
      if (startWaiting.current !== null) window.clearInterval(startWaiting.current);
      let tries = 0;
      const attempt = () => {
        const controls = players.get(key)?.current;
        tries += 1;
        if (controls || tries > 100) {
          if (startWaiting.current !== null) window.clearInterval(startWaiting.current);
          startWaiting.current = null;
          controls?.toggle();
        }
      };
      startWaiting.current = window.setInterval(attempt, 100);
      attempt();
    },
    [players],
  );
  useEffect(
    () => () => {
      if (startWaiting.current !== null) window.clearInterval(startWaiting.current);
    },
    [],
  );

  const toggle = useCallback(() => {
    const key = activeNow.current;
    const controls = players.get(key)?.current;
    if (controls) controls.toggle();
  }, [players]);
  const stopAll = useCallback(() => {
    for (const key of sounding.current) players.get(key)?.current?.toggle();
  }, [players]);

  const scrollToSong = useCallback((song: number) => {
    window.requestAnimationFrame(() => {
      document.querySelector(`[data-play-song="${song}"]`)?.scrollIntoView({ block: "start", behavior: "smooth" });
    });
  }, []);

  /** The next song of a songs playlist: opened (one song) or scrolled to (all songs), not started. */
  const nextSong = useCallback(
    (from: number) => {
      if (!songs || from + 1 >= songs.length) return;
      stopAll();
      if (allSongs) {
        setChosen({ forAt: at, key: keyOf(from + 1, 0) });
        scrollToSong(from + 1);
      } else {
        change({ at: String(from + 1) });
        window.scrollTo({ top: 0 });
      }
    },
    [songs, stopAll, allSongs, at, scrollToSong, change],
  );

  const events = useRef<PartEvents>({ playing: () => {}, ended: () => {}, seek: () => {}, time: () => {} });
  const handlers: PartEvents = {
    playing: (key, now) => {
      if (now) {
        // One part sounds at a time: the one starting stops any other.
        for (const other of [...sounding.current]) {
          if (other !== key) players.get(other)?.current?.toggle();
        }
        sounding.current.add(key);
        if (key !== activeNow.current) choose(key);
      } else {
        sounding.current.delete(key);
      }
      setPlaying(sounding.current.size > 0);
    },
    ended: (key) => {
      const [song, part] = partsOfKey(key);
      const parts = songs?.[song]?.parts ?? [];
      if (part + 1 < parts.length) {
        // The sub-songs of one song play on without a stop.
        const next = keyOf(song, part + 1);
        choose(next);
        startWhenReady(next);
      } else if (isPlaylist) {
        nextSong(song);
      }
    },
    seek: (key) => {
      if (key === activeNow.current) return;
      stopAll();
      choose(key);
    },
    time: (key, seconds) => {
      if (key === activeNow.current && seconds !== null) clock.set(seconds);
    },
  };
  // The newest handlers, for the stable functions the parts hold.
  useEffect(() => {
    events.current = handlers;
  });
  const partEvents = useMemo<PartEvents>(
    () => ({
      playing: (key, now) => events.current.playing(key, now),
      ended: (key) => events.current.ended(key),
      seek: (key) => events.current.seek(key),
      time: (key, seconds) => events.current.time(key, seconds),
    }),
    [],
  );

  const close = useCallback(() => {
    if (isPlaylist) {
      const page = isPublic ? ROUTES.publicPlaylist(Number(playlistId)) : ROUTES.libraryPlaylist(Number(playlistId));
      navigate(`${page}?at=${partsOfKey(activeNow.current)[0]}`);
    } else if (location.key !== "default") {
      navigate(-1);
    } else {
      navigate(ROUTES.project(projectId ?? ""));
    }
  }, [isPlaylist, isPublic, playlistId, projectId, location.key, navigate]);

  // The buttons fade while the music plays and the pointer rests; any move brings them back.
  const [awake, setAwake] = useState(true);
  const sleepTimer = useRef<number | null>(null);
  const wake = useCallback(() => {
    setAwake(true);
    if (sleepTimer.current !== null) window.clearTimeout(sleepTimer.current);
    sleepTimer.current = window.setTimeout(() => setAwake(false), AWAKE_MS);
  }, []);
  useEffect(() => {
    window.addEventListener("pointermove", wake);
    window.addEventListener("pointerdown", wake);
    return () => {
      window.removeEventListener("pointermove", wake);
      window.removeEventListener("pointerdown", wake);
      if (sleepTimer.current !== null) window.clearTimeout(sleepTimer.current);
    };
  }, [wake]);
  const chromeShown = awake || !playing;

  // The keys: Space plays and pauses, the arrows scroll, Escape closes.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      const target = event.target as HTMLElement | null;
      if (target?.closest("input, textarea, select, [contenteditable='true'], [role='menu'], [role='listbox']")) return;
      if (event.key === " " || event.code === "Space") {
        // A focused button already answers Space by being pressed.
        if (target?.closest("button, [role='button']")) return;
        event.preventDefault();
        toggle();
      } else if (event.key === "Escape") {
        event.preventDefault();
        close();
      } else if ((event.key === "ArrowDown" || event.key === "ArrowUp") && !falling) {
        event.preventDefault();
        const step = Math.round(window.innerHeight * 0.4) * (event.key === "ArrowDown" ? 1 : -1);
        window.scrollBy({ top: step, behavior: "smooth" });
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggle, close, falling]);

  const [activeSong, activePart] = partsOfKey(active);
  const activePartId = songs?.[activeSong]?.parts[activePart]?.id ?? null;
  const nextKey = order[order.indexOf(active) + 1] ?? null;
  const hasNext = isPlaylist && songs !== null && activeSong + 1 < songs.length;

  const chrome = {
    opacity: chromeShown ? 1 : 0,
    pointerEvents: chromeShown ? "auto" : "none",
    transition: "opacity 300ms ease",
  } as const;

  return (
    <Box data-play-page sx={{ minHeight: "100vh", backgroundColor: ui.bg }}>
      {/* The menu that comes and goes: the view, and one song or all of them. */}
      <Box
        data-play-menu
        sx={{
          ...chrome,
          position: "fixed",
          top: 12,
          left: 16,
          zIndex: 3,
          display: "flex",
          gap: 1,
          flexWrap: "wrap",
          maxWidth: "calc(100% - 128px)",
          p: 0.5,
          borderRadius: "16px",
          backgroundColor: ui.bg,
          boxShadow: "0 2px 12px rgba(0,0,0,0.08)",
        }}
      >
        <Segmented
          label="View"
          value={falling ? "falling" : "sheet"}
          options={[
            { value: "sheet", label: "Sheet" },
            { value: "falling", label: "Notes Falling" },
          ]}
          onChange={(value) => change({ view: value === "falling" ? "falling" : null })}
        />
        {isPlaylist && (songs?.length ?? 0) > 1 && !falling ? (
          <Segmented
            label="Songs on the page"
            value={allSongs ? "all" : "one"}
            options={[
              { value: "one", label: "One song", tooltip: "One song at a time; Next opens the next one" },
              { value: "all", label: "All songs", tooltip: "Every song on one page, one after the other" },
            ]}
            onChange={(value) => {
              try {
                window.localStorage.setItem(ALL_SONGS_KEY, value === "all" ? "1" : "0");
              } catch {
                // The choice still holds in the address.
              }
              stopAll();
              change({ all: value === "all" ? "1" : "0" });
              if (value === "all") scrollToSong(activeSong);
            }}
          />
        ) : null}
      </Box>

      {/* Next and Close: the two buttons of the page. */}
      <Box sx={{ ...chrome, position: "fixed", top: 12, right: 16, zIndex: 3, display: "flex", gap: 0.5 }}>
        {hasNext ? (
          <IconAction
            title={`Next: ${songs?.[activeSong + 1]?.title ?? ""}`}
            icon={<SkipNextIcon />}
            onClick={() => nextSong(activeSong)}
            data-testid="play-next"
          />
        ) : null}
        <IconAction title="Close" shortcut="Esc" icon={<CloseIcon />} onClick={close} data-testid="play-close" />
      </Box>

      {error ? (
        <Box sx={{ pt: 10, px: 2 }}>
          <Alert severity="error">{error}</Alert>
        </Box>
      ) : songs === null ? (
        <Box sx={{ display: "grid", placeItems: "center", minHeight: "60vh" }}>
          <CircularProgress size={22} />
        </Box>
      ) : songs.length === 0 ? (
        <Box sx={{ pt: 10 }}>
          <EmptyState message="This playlist has no songs yet." />
        </Box>
      ) : (
        <Box sx={{ px: { xs: 2, md: 4 }, pt: 9, pb: 16 }}>
          {shown.map(({ song, index }) => (
            <Box key={`${song.projectId}:${index}`} data-play-song={index} sx={{ mb: 8, scrollMarginTop: 72 }}>
              <Box sx={{ mb: 2 }}>
                <Typography component="h1" sx={{ fontSize: 28, fontWeight: 600, lineHeight: 1.25 }} noWrap title={song.title}>
                  {song.title}
                </Typography>
                {song.byline ? (
                  <Typography color="text.secondary" noWrap title={song.byline}>
                    {song.byline}
                  </Typography>
                ) : null}
              </Box>
              {song.parts.map((part, partIndex) => {
                const key = keyOf(index, partIndex);
                return (
                  <PlaySegment
                    key={`${key}:${part.id}`}
                    segment={key}
                    part={part}
                    player={playerOf(key)}
                    events={partEvents}
                    active={key === active}
                    preload={key === active || key === nextKey ? "auto" : "metadata"}
                  />
                );
              })}
            </Box>
          ))}
        </Box>
      )}

      {falling && activePartId ? <FallingView part={activePartId} clock={clock} /> : null}

      {/* Play and Pause, at the foot of the window. */}
      {songs && songs.length > 0 ? (
        <Box
          sx={{
            ...chrome,
            position: "fixed",
            // Above the keyboard of Notes Falling, which is as tall as about an eighth of its width.
            bottom: falling ? "calc(13vw + 24px)" : 24,
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 3,
          }}
        >
          <Tooltip title={playing ? "Pause (Space)" : "Play (Space)"}>
            <IconButton
              aria-label={playing ? "Pause" : "Play"}
              onClick={toggle}
              data-testid="play-toggle"
              data-playing={playing ? "true" : "false"}
              sx={{
                width: 56,
                height: 56,
                backgroundColor: ui.primary,
                color: ui.onPrimary,
                boxShadow: "0 4px 16px rgba(0,0,0,0.18)",
                "&:hover": { backgroundColor: ui.primary, opacity: 0.88 },
              }}
            >
              {playing ? <PauseIcon /> : <PlayArrowIcon />}
            </IconButton>
          </Tooltip>
        </Box>
      ) : null}
    </Box>
  );
}

/**
 * One part on the page: its subheader, when the song has several, and its sheet. Drawn when it
 * comes near the window (a playlist of many songs would otherwise draw them all at once), and kept
 * once drawn. Memoised: the page changes many times a second while it plays, the sheet does not.
 */
const PlaySegment = memo(function PlaySegment({
  segment,
  part,
  player,
  events,
  active,
  preload,
}: {
  segment: string;
  part: PlayPart;
  player: PlayerRef;
  events: PartEvents;
  active: boolean;
  preload: "auto" | "metadata";
}) {
  const holder = useRef<HTMLDivElement | null>(null);
  const [near, setNear] = useState(false);
  const drawn = near || active;
  useEffect(() => {
    const node = holder.current;
    if (!node || near) return undefined;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) setNear(true);
      },
      { rootMargin: "800px 0px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [near]);

  const play = useMemo<PlayView>(
    () => ({
      playerRef: player,
      onPlaying: (now) => events.playing(segment, now),
      onTime: (seconds) => events.time(segment, seconds),
      onEnded: () => events.ended(segment),
      onSeek: () => events.seek(segment),
      fromMs: part.fromMs,
      toMs: part.toMs,
      preload,
    }),
    [player, events, segment, part.fromMs, part.toMs, preload],
  );
  const step = useMemo<SheetStep>(
    () => ({
      audioUuid: part.id,
      label: part.title ?? undefined,
      state: "ready",
      reason: null,
      onChanged: () => undefined,
      readOnly: true,
      play,
      // The new sheet (implementation 03, Phase 5): Play mode draws what the Sheet step shows first.
      newSheet: true,
    }),
    [part.id, part.title, play],
  );

  return (
    <Box ref={holder} data-play-part={segment} data-play-active={active ? "true" : "false"} sx={{ mb: 4 }}>
      {part.title ? (
        <Typography component="h2" sx={{ fontSize: 20, fontWeight: 600, mb: 1, px: 1 }} noWrap title={part.title}>
          {part.title}
        </Typography>
      ) : null}
      {drawn ? <SheetPage step={step} /> : <Box sx={{ minHeight: 480 }} />}
    </Box>
  );
});

export default PlayPage;
