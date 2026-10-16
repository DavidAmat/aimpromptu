/**
 * A song being written in a request (implementation 02, Phase 14): the form's own state, how it is
 * sent, and how a sent proposal fills it again. Used by `SongFieldsForm` and the dialogs.
 */

import { publicApi, type SongFields } from "../../api";

export interface ArtistDraft {
  name: string;
  /** The public artist chosen; `null` proposes a new artist of this name. */
  publicId: number | null;
  /** The user's own artist it stands for. */
  privateId?: number;
}

export interface SongDraft {
  title: string;
  year: string;
  artists: ArtistDraft[];
  genres: string[];
  regions: string[];
  tags: { category: string; value: string }[];
}

export const EMPTY_SONG: SongDraft = { title: "", year: "", artists: [{ name: "", publicId: null }], genres: [], regions: ["worldwide"], tags: [] };

/** The draft as the backend takes it. */
export function toFields(draft: SongDraft): SongFields {
  const year = Number(draft.year);
  return {
    title: draft.title.trim(),
    year: draft.year.trim() && Number.isInteger(year) ? year : null,
    artists: draft.artists
      .filter((one) => one.name.trim() || one.publicId !== null)
      .map((one) =>
        one.publicId !== null
          ? { publicId: one.publicId, ...(one.privateId ? { privateId: one.privateId } : {}) }
          : { newName: one.name.trim(), ...(one.privateId ? { privateId: one.privateId } : {}) },
      ),
    genres: draft.genres,
    regions: draft.regions,
    tags: draft.tags.filter((tag) => tag.value.trim()).map((tag) => ({ category: tag.category, value: tag.value.trim() })),
  };
}

export function draftReady(draft: SongDraft): boolean {
  const year = draft.year.trim();
  return (
    draft.title.trim().length > 0 &&
    draft.artists.some((one) => one.name.trim().length > 0) &&
    (year === "" || /^\d{4}$/.test(year))
  );
}

const TAG_WORDS: Record<string, string> = { films: "Film", video_games: "Video game", tv_shows: "TV show", adverts: "Advert" };
export const tagWord = (category: string) => TAG_WORDS[category] ?? category;

/** A song's fields from a proposal, with the names of its public artists. */
export async function draftOf(fields: SongFields): Promise<SongDraft> {
  const artists = await Promise.all(
    fields.artists.map(async (one) =>
      one.publicId
        ? {
            name: await publicApi.artist(one.publicId).then(
              (found) => found.name,
              () => "",
            ),
            publicId: one.publicId,
            ...(one.privateId ? { privateId: one.privateId } : {}),
          }
        : { name: one.newName ?? "", publicId: null, ...(one.privateId ? { privateId: one.privateId } : {}) },
    ),
  );
  return {
    title: fields.title,
    year: fields.year ? String(fields.year) : "",
    artists: artists.length > 0 ? artists : [{ name: "", publicId: null }],
    genres: fields.genres ?? [],
    regions: fields.regions?.length ? fields.regions : ["worldwide"],
    tags: fields.tags ?? [],
  };
}
