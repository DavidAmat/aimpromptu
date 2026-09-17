/**
 * Which video the three Video to Notes tabs are working on.
 *
 * The three tabs are the order of the work — bring the video in, fit the piano
 * on it, read it — so moving between them must not lose which video it is. The
 * selection lives in session storage rather than in a context, because a tab is
 * a route and every route already remounts: reading it on mount is all the
 * sharing these three screens need, and it survives a reload as well.
 */

const KEY = "aitu.video.selected";

/**
 * The video the user last worked on, or `null` if there is not one.
 *
 * A `?video=<uuid>` in the address wins and is kept, so a link can open one
 * video's tab directly.
 */
export function readSelectedVideo(): string | null {
  try {
    const named = new URLSearchParams(window.location.search).get("video");
    if (named) {
      writeSelectedVideo(named);
      return named;
    }
  } catch {
    // No address to read: fall through to what was kept.
  }
  try {
    return window.sessionStorage.getItem(KEY);
  } catch {
    return null; // Private mode or blocked storage: the page still works.
  }
}

export function writeSelectedVideo(audioUuid: string | null): void {
  try {
    if (audioUuid === null) window.sessionStorage.removeItem(KEY);
    else window.sessionStorage.setItem(KEY, audioUuid);
  } catch {
    // The in-memory selection of the page that set it still works.
  }
}
