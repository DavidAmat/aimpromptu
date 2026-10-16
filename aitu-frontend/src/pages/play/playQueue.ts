/**
 * What Play mode draws (implementation 02, plan section 17, Phase 11): a list of songs, each with
 * the parts it plays, in order.
 *
 * - **A project** (or a version of the library) is one song. Its parts are its sub-songs: one for a
 *   song, several for an integrated playlist, drawn one after the other and played without a stop.
 * - **A songs playlist** is its songs, each on the version chosen for it. A song with a stretch
 *   plays only that stretch, of its first part (a stretch is chosen on the part on show, and the
 *   playlist keeps no part: Phase 10).
 */

import { playlistsApi, projectsApi, publicApi, type PartRow, type ProjectRow } from "../../api";

export interface PlayPart {
  /** The uuid of the part, the one the step routes take. */
  id: string;
  /** Its subheader, or "Part N", when the song has more than one part; `null` otherwise. */
  title: string | null;
  fromMs: number | null;
  toMs: number | null;
}

export interface PlaySong {
  projectId: string;
  title: string;
  /** The artists and the version, when it is a song of the library. */
  byline: string;
  parts: PlayPart[];
}

export interface PlayQueue {
  /** The playlist's title, or the project's. */
  title: string;
  songs: PlaySong[];
}

function partsOf(rows: readonly PartRow[] | readonly string[]): PlayPart[] {
  const several = rows.length > 1;
  return rows.map((row, index) => {
    const id = typeof row === "string" ? row : row.id;
    const subheader = typeof row === "string" ? null : row.subheader;
    return { id, title: several ? subheader || `Part ${index + 1}` : null, fromMs: null, toMs: null };
  });
}

function titleOf(row: ProjectRow): { title: string; byline: string } {
  if (row.library) {
    return {
      title: row.library.songTitle,
      byline: [row.library.artists.join(", "), row.library.versionName].filter(Boolean).join(" · "),
    };
  }
  return { title: row.title || "Untitled project", byline: "" };
}

/** One project, its parts in order. */
export async function projectQueue(projectId: string, signal?: AbortSignal): Promise<PlayQueue> {
  const [row, parts] = await Promise.all([
    projectsApi.get(projectId, signal),
    projectsApi.parts(projectId, signal),
  ]);
  const { title, byline } = titleOf(row);
  return { title, songs: [{ projectId: row.id, title, byline, parts: partsOf(parts.parts) }] };
}

/**
 * One songs playlist, its songs in order on their versions. A song with no version is left out.
 * `fromPublic`: a playlist of the Public Library (Phase 13), whose items have the same fields.
 */
export async function playlistQueue(playlistId: number, signal?: AbortSignal, fromPublic = false): Promise<PlayQueue> {
  const playlist = fromPublic ? await publicApi.playlist(playlistId, signal) : await playlistsApi.get(playlistId, signal);
  const songs = await Promise.all(
    playlist.items
      .filter((item) => item.projectId !== null && item.parts.length > 0)
      .map(async (item): Promise<PlaySong> => {
        const projectId = item.projectId as string;
        const byline = [item.artists.join(", "), item.versionName].filter(Boolean).join(" · ");
        if (item.fromMs !== null && item.toMs !== null) {
          return {
            projectId,
            title: item.songTitle,
            byline,
            parts: [{ id: item.parts[0], title: null, fromMs: item.fromMs, toMs: item.toMs }],
          };
        }
        // The subheaders of a version of several parts (an integrated playlist in the playlist).
        const parts =
          item.parts.length > 1
            ? partsOf((await projectsApi.parts(projectId, signal)).parts)
            : partsOf(item.parts);
        return { projectId, title: item.songTitle, byline, parts };
      }),
  );
  return { title: playlist.title, songs };
}

/** Where Play mode is on the clock, read by Notes Falling without drawing the sheets again. */
export interface PlayClock {
  get: () => number;
  set: (seconds: number) => void;
  subscribe: (listener: () => void) => () => void;
}

export function createPlayClock(): PlayClock {
  let seconds = 0;
  const listeners = new Set<() => void>();
  return {
    get: () => seconds,
    set: (next) => {
      if (next === seconds) return;
      seconds = next;
      listeners.forEach((listener) => listener());
    },
    subscribe: (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}
