/**
 * The primary keys of the metadata, as one item's row reads them (implementation 04-3, Phase 1): "Film", not the
 * Public Library's list heading "Films" (`tagCategoryLabel`).
 */

/** The primary keys, in the Public Library's order (`TAG_CATEGORIES` of the backend). */
export const TAG_KEYS = ["films", "video_games", "tv_shows", "adverts"] as const;

const WORDS: Record<string, string> = {
  films: "Film",
  video_games: "Video game",
  tv_shows: "TV show",
  adverts: "Advert",
};

export const tagKeyLabel = (key: string) => WORDS[key] ?? key;
