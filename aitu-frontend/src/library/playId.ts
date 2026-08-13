/** Identity of a piece opened in the performance view. */

export interface LibraryPlayRef {
  artistSlug: string;
  trackSlug: string;
  promotionName?: string;
}

/** `avicii--levels`, optionally with a promotion name in the query string. */
export function libraryPlayId(artistSlug: string, trackSlug: string): string {
  return `${artistSlug}--${trackSlug}`;
}

export function parseLibraryPlayId(id: string | undefined): LibraryPlayRef | null {
  if (!id) return null;
  const separator = id.indexOf("--");
  if (separator <= 0 || separator === id.length - 2) return null;
  const artistSlug = id.slice(0, separator);
  const trackSlug = id.slice(separator + 2);
  if (!artistSlug || !trackSlug || trackSlug.includes("--")) return null;
  return { artistSlug, trackSlug };
}

export function activePromotions<T extends { active: boolean }>(items: T[]): T[] {
  return items.filter((item) => item.active);
}
