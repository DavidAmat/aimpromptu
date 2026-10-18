/**
 * The words of the requests (implementation 02, Phase 14): what a kind, a status and an item are
 * called on screen, and the simple form of a version name.
 */

import type { ItemKind, RequestKind, RequestStatus } from "../../api";

export const KIND_LABEL: Record<RequestKind, string> = {
  userVersion: "Version",
  metadata: "Metadata",
  fixedVersion: "Fixed version",
  playlist: "Playlist",
};

export const STATUS_LABEL: Record<RequestStatus, string> = {
  open: "Waiting for review",
  changesAsked: "Changes asked",
  accepted: "Accepted",
  partlyAccepted: "Partly accepted",
  refused: "Refused",
  withdrawn: "Withdrawn",
};

export const ITEM_LABEL: Record<ItemKind, string> = {
  newArtist: "New artist",
  newSong: "New song",
  metadata: "Metadata",
  project: "Piano sheet",
  versionPointer: "Fixed version",
  playlist: "Playlist",
};

export const DECISION_LABEL = {
  accepted: "Accepted",
  refused: "Refused",
  changesAsked: "Changes asked",
} as const;

/** A public version name: lowercase letters, digits and hyphens, at most 24 characters. */
export const NAME_RULE = "Lowercase letters, digits and hyphens, at most 24 characters";

/** The simple form of a version name, as the backend makes it: "Easy (left hand)" → `easy-left-hand`. */
export function simpleName(text: string): string {
  const folded = text.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase();
  let out = "";
  for (const char of folded) {
    if (/[a-z0-9]/.test(char)) out += char;
    else if (out && !out.endsWith("-")) out += "-";
  }
  return out.replace(/^-+|-+$/g, "").slice(0, 24).replace(/-+$/, "");
}

export function validName(name: string): boolean {
  return /^[a-z0-9][a-z0-9-]{0,23}$/.test(name);
}

/** "hard" → "Hard"; a custom name stays as it is. */
export function nameLabel(name: string): string {
  return ["hard", "medium", "easy"].includes(name) ? name[0].toUpperCase() + name.slice(1) : name;
}

/** Sent on `window` when a request changes, so the sidebar counts its numbers again. */
export const COUNTS_EVENT = "aitu:request-counts";
