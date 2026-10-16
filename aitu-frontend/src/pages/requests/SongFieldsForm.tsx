/**
 * The fields of a song in a request (implementation 02, Phase 14, plan section 15.3): title,
 * artists, year, genres (at most two of the fixed list), regions and tags. Used to propose a new
 * song (the **Publish** dialog, **Propose a song**) and to suggest a change of a public song.
 *
 * Each artist is either a public artist, chosen from the Public Library's suggestions, or a new
 * one proposed by its name; the line under it says which. No private id is ever sent as a public
 * one (app context): a new artist gets its public id when the master user accepts it.
 */

import { useEffect, useState } from "react";
import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import AddIcon from "@mui/icons-material/Add";
import CloseIcon from "@mui/icons-material/Close";
import { publicApi, type PublicArtistRow, type PublicLists } from "../../api";
import { IconAction, PillButton } from "../../ui";
import { tagWord, type ArtistDraft, type SongDraft } from "./songDraft";

/** One artist: the Public Library's suggestions, or a new name as typed. */
function ArtistField({
  value,
  label,
  onChange,
}: {
  value: ArtistDraft;
  label: string;
  onChange: (next: ArtistDraft) => void;
}) {
  const [options, setOptions] = useState<PublicArtistRow[]>([]);
  useEffect(() => {
    const typed = value.name.trim();
    if (typed.length < 2 || value.publicId !== null) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      publicApi
        .suggest(typed, { limit: 8 }, controller.signal)
        .then((found) => setOptions(found.artists))
        .catch(() => undefined);
    }, 200);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [value.name, value.publicId]);

  return (
    <Autocomplete<PublicArtistRow, false, false, true>
      freeSolo
      sx={{ flex: 1, minWidth: 0 }}
      options={value.name.trim().length >= 2 ? options : []}
      filterOptions={(found) => found}
      getOptionLabel={(option) => (typeof option === "string" ? option : option.name)}
      renderOption={(props, option) => (
        <li {...props} key={option.id}>
          <Stack sx={{ minWidth: 0 }}>
            <Typography noWrap sx={{ fontSize: 14 }}>
              {option.name}
            </Typography>
            <Typography noWrap sx={{ fontSize: 13, color: "text.secondary" }}>
              {option.songs} {option.songs === 1 ? "song" : "songs"}
            </Typography>
          </Stack>
        </li>
      )}
      inputValue={value.name}
      onInputChange={(_, typed, reason) => {
        if (reason === "input") onChange({ ...value, name: typed, publicId: null });
      }}
      onChange={(_, chosen) => {
        if (chosen && typeof chosen !== "string") onChange({ ...value, name: chosen.name, publicId: chosen.id });
      }}
      renderInput={(params) => (
        <TextField
          {...params}
          label={label}
          size="small"
          helperText={
            value.name.trim() ? (value.publicId !== null ? "From the Public Library" : "A new artist") : undefined
          }
        />
      )}
    />
  );
}

export interface SongFieldsFormProps {
  value: SongDraft;
  onChange: (next: SongDraft) => void;
  lists: PublicLists | null;
  autoFocus?: boolean;
}

export function SongFieldsForm({ value, onChange, lists, autoFocus }: SongFieldsFormProps) {
  const set = (patch: Partial<SongDraft>) => onChange({ ...value, ...patch });
  const regionName = (code: string) => lists?.regions.find((one) => one.code === code)?.name ?? code;
  return (
    <Stack spacing={2}>
      <TextField
        label="Title"
        required
        size="small"
        autoFocus={autoFocus}
        value={value.title}
        onChange={(event) => set({ title: event.target.value })}
        slotProps={{ htmlInput: { maxLength: 300 } }}
      />
      <Stack spacing={1}>
        {value.artists.map((artist, index) => (
          <Stack key={index} direction="row" spacing={0.5} sx={{ alignItems: "flex-start" }}>
            <ArtistField
              value={artist}
              label={index === 0 ? "Artist" : `Artist ${index + 1}`}
              onChange={(next) => set({ artists: value.artists.map((one, at) => (at === index ? next : one)) })}
            />
            {value.artists.length > 1 ? (
              <Box sx={{ pt: 0.25 }}>
                <IconAction
                  title="Remove this artist"
                  icon={<CloseIcon fontSize="small" />}
                  onClick={() => set({ artists: value.artists.filter((_, at) => at !== index) })}
                />
              </Box>
            ) : null}
          </Stack>
        ))}
        <Box>
          <PillButton
            kind="quiet"
            size="small"
            startIcon={<AddIcon />}
            onClick={() => set({ artists: [...value.artists, { name: "", publicId: null }] })}
          >
            Add an artist
          </PillButton>
        </Box>
      </Stack>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
        <TextField
          label="Year"
          size="small"
          value={value.year}
          onChange={(event) => set({ year: event.target.value.replace(/\D/g, "").slice(0, 4) })}
          error={value.year !== "" && value.year.length !== 4}
          sx={{ width: { xs: "100%", sm: 120 }, flexShrink: 0 }}
          slotProps={{ htmlInput: { inputMode: "numeric" } }}
        />
        <Autocomplete<string, true>
          multiple
          size="small"
          sx={{ flex: 1 }}
          options={lists?.genres ?? []}
          value={value.genres}
          getOptionDisabled={(option) => value.genres.length >= 2 && !value.genres.includes(option)}
          onChange={(_, chosen) => set({ genres: chosen.slice(0, 2) })}
          renderInput={(params) => <TextField {...params} label="Genres" helperText="One or two" />}
        />
      </Stack>
      <Autocomplete<string, true>
        multiple
        size="small"
        options={lists?.regions.map((one) => one.code) ?? []}
        getOptionLabel={regionName}
        value={value.regions}
        onChange={(_, chosen) => set({ regions: chosen })}
        renderInput={(params) => <TextField {...params} label="Regions" helperText="Where the song was popular" />}
      />
      <Stack spacing={1}>
        {value.tags.map((tag, index) => (
          <Stack key={index} direction="row" spacing={1} sx={{ alignItems: "center" }}>
            <TextField
              select
              size="small"
              label="Tag"
              value={tag.category}
              onChange={(event) =>
                set({ tags: value.tags.map((one, at) => (at === index ? { ...one, category: event.target.value } : one)) })
              }
              sx={{ width: 150, flexShrink: 0 }}
            >
              {(lists?.tagCategories ?? []).map((category) => (
                <MenuItem key={category} value={category}>
                  {tagWord(category)}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              size="small"
              label="Name"
              placeholder="Shrek"
              value={tag.value}
              onChange={(event) =>
                set({ tags: value.tags.map((one, at) => (at === index ? { ...one, value: event.target.value } : one)) })
              }
              sx={{ flex: 1, minWidth: 0 }}
              slotProps={{ htmlInput: { maxLength: 200 } }}
            />
            <IconAction
              title="Remove this tag"
              icon={<CloseIcon fontSize="small" />}
              onClick={() => set({ tags: value.tags.filter((_, at) => at !== index) })}
            />
          </Stack>
        ))}
        <Box>
          <PillButton
            kind="quiet"
            size="small"
            startIcon={<AddIcon />}
            disabled={!lists}
            onClick={() => set({ tags: [...value.tags, { category: lists?.tagCategories[0] ?? "films", value: "" }] })}
          >
            Add a tag
          </PillButton>
        </Box>
      </Stack>
    </Stack>
  );
}

export default SongFieldsForm;
