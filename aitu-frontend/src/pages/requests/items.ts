/**
 * Helpers of a request's items (implementation 02, Phase 14): the name the master user may change
 * on accepting, one line naming an item, and the master user's decision being written.
 */

import type { ItemDecisionValue, ItemKind, RequestItem } from "../../api";
import { nameLabel, validName } from "./words";

/** The name the master user may change on accepting, by item kind: `[payload field, label]`. */
export const EDITABLE: Partial<Record<ItemKind, [string, string]>> = {
  newArtist: ["name", "Accept with the name"],
  newSong: ["title", "Accept with the title"],
  project: ["versionName", "Accept with the version name"],
  versionPointer: ["name", "Accept with the name"],
  playlist: ["title", "Accept with the title"],
};

/** A payload field as text. */
export const text = (value: unknown) =>
  typeof value === "string" ? value : value === null || value === undefined ? "" : String(value);

/** One line saying what an item is: "Piano sheet “easy”", "New artist Aitana". */
export function itemLine(item: RequestItem): string {
  const payload = item.payload;
  switch (item.kind) {
    case "newArtist":
      return `New artist ${text(payload.name)}`;
    case "newSong":
      return `New song “${text(payload.title)}”`;
    case "metadata":
      return payload.target === "song" ? "Metadata of the song" : "Names of the artist";
    case "project":
      return `Piano sheet “${text(payload.versionName)}”`;
    case "versionPointer":
      return `“${text(payload.userVersionName)}” as ${nameLabel(text(payload.name))}`;
    case "playlist":
      return `Playlist “${text(payload.title)}”`;
  }
}

export interface Draft {
  decision: ItemDecisionValue | "";
  comment: string;
  /** The value of the editable field, when it is changed. */
  value: string | null;
}

export const EMPTY_DRAFT: Draft = { decision: "", comment: "", value: null };

/** A version name is checked by its rule; another name only needs to be there. */
export function draftComplete(item: RequestItem, draft: Draft): boolean {
  if (!draft.decision) return false;
  if (draft.decision === "changesAsked" && !draft.comment.trim()) return false;
  const editable = EDITABLE[item.kind];
  if (draft.decision === "accepted" && editable && draft.value !== null) {
    const nameField = item.kind === "project" || item.kind === "versionPointer";
    return nameField ? validName(draft.value) : draft.value.trim().length > 0;
  }
  return true;
}
