/**
 * Space plays and pauses, on any view that has a transport.
 *
 * The one rule worth stating: it is ignored while the reader is typing. Space is
 * a character in the `Seek` box and in every number field on the toolbar, and a
 * global handler that swallowed it would make those fields feel broken. So the
 * handler stands down for form controls and anything `contenteditable`.
 *
 * `preventDefault` matters too: on a scrollable page, Space is Page Down, and a
 * view that jumped down half a screen every time you started playing would be
 * unusable.
 */

import { useEffect } from "react";

function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  if (target.isContentEditable) return true;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
}

export function useSpacebarPlay(toggle: () => void, enabled = true): void {
  useEffect(() => {
    if (!enabled) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.code !== "Space" && event.key !== " ") return;
      // A modifier means the reader is asking for something else entirely.
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      if (isTyping(event.target)) return;
      event.preventDefault();
      toggle();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [enabled, toggle]);
}

export default useSpacebarPlay;
