/** What the Public Library pages share: how a popularity, a version name and a date read. */

import type { PublicSongDetail, PublicVersion } from "../../api";

/** 0 to 100 with its one decimal ("99.8"): the top songs differ in the decimal. */
export const popularityText = (value: number) => value.toFixed(1);

/** `hard` → "Hard"; a custom name stays as it is. */
export const versionLabel = (name: string) =>
  ["hard", "medium", "easy"].includes(name) ? name[0].toUpperCase() + name.slice(1) : name;

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** `1977-12-10` → "Dec 1977". */
export const monthYear = (day: string) => `${MONTHS[Number(day.slice(5, 7)) - 1]} ${day.slice(0, 4)}`;

/**
 * The version Default points at: the fixed version of that name, else the first fixed version,
 * else the most liked of the Other versions (the backend's own choice for **Add to my library**).
 */
export function defaultVersion(song: PublicSongDetail): PublicVersion | null {
  const fixed = song.fixed.filter((one) => one.ready);
  const named = fixed.find((one) => one.name === song.defaultVersion);
  if (named) return named;
  if (fixed[0]) return fixed[0];
  const others = song.others.flatMap((group) => group.versions).filter((one) => one.ready);
  return others.sort((a, b) => b.likes - a.likes)[0] ?? null;
}
