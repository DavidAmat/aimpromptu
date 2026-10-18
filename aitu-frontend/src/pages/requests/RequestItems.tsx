/**
 * What each item of a request proposes, as the request's pages show it (implementation 02,
 * Phase 14): a new artist, a new song (its fields), a change of metadata (each field now and
 * proposed, the changed ones in bold), a piano sheet or a fixed version (the song and the name;
 * the sheet itself is on the **Sheet** tab), a playlist (its songs). And the master user's decision
 * on one waiting item (`DecisionControls`), used by **Finish your review**.
 */

import type { ReactNode } from "react";
import Box from "@mui/material/Box";
import Link from "@mui/material/Link";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { Link as RouterLink } from "react-router-dom";
import type { ArtistInRequest, ItemDecisionValue, RequestItem, SongState } from "../../api";
import { ROUTES } from "../../layout/routes";
import { Segmented } from "../../ui";
import { EDITABLE, text, type Draft } from "./items";
import { tagWord } from "./songDraft";
import { ITEM_LABEL, nameLabel, NAME_RULE, validName } from "./words";

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <Box sx={{ minWidth: 0 }}>
      <Typography sx={{ fontSize: 13, color: "text.secondary" }}>{label}</Typography>
      <Typography component="div" sx={{ fontSize: 14, overflowWrap: "anywhere" }}>
        {children}
      </Typography>
    </Box>
  );
}

function Facts({ children }: { children: ReactNode }) {
  return (
    <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 1.5 }}>
      {children}
    </Box>
  );
}

function artistsText(artists: ArtistInRequest[]): string {
  return artists.length === 0 ? "No artist" : artists.map((one) => (one.isNew ? `${one.name} (new)` : one.name)).join(", ");
}

/** A song's fields, each as the reader sees it. */
function fieldsOf(state: SongState): [string, string][] {
  return [
    ["Title", state.title],
    ["Year", state.year ? String(state.year) : "Unknown"],
    ["Artists", artistsText(state.artists)],
    ["Genres", state.genres.join(", ") || "None"],
    ["Regions", (state.regionNames ?? state.regions).join(", ") || "None"],
    ["Tags", state.tags.map(([category, value]) => `${value} (${tagWord(category)})`).join(", ") || "None"],
  ];
}

/** Each field of a public song now and proposed; the changed ones in bold. */
function ChangeTable({ before, after }: { before: SongState; after: SongState }) {
  const now = fieldsOf(before);
  const proposed = fieldsOf(after);
  return (
    <Box
      component="table"
      sx={{
        borderCollapse: "collapse",
        width: "100%",
        fontSize: 14,
        "& th, & td": { textAlign: "left", py: 0.75, pr: 2, verticalAlign: "top", borderBottom: 1, borderColor: "divider" },
        "& th": { fontWeight: 500, color: "text.secondary", fontSize: 13 },
      }}
    >
      <thead>
        <tr>
          <th style={{ width: 88 }} />
          <th>Now</th>
          <th>Proposed</th>
        </tr>
      </thead>
      <tbody>
        {now.map(([label, value], index) => {
          const next = proposed[index]?.[1] ?? "";
          const changed = next !== value;
          return (
            <tr key={label} data-changed={changed || undefined}>
              <Box component="td" sx={{ color: "text.secondary" }}>
                {label}
              </Box>
              <td>{value}</td>
              <Box component="td" sx={{ fontWeight: changed ? 600 : 400 }}>
                {changed ? next : "Same"}
              </Box>
            </tr>
          );
        })}
      </tbody>
    </Box>
  );
}

/** What an item proposes. A piano sheet's own sheet is on the Sheet tab, not here. */
export function ItemBody({ item }: { item: RequestItem }) {
  const payload = item.payload;
  const made = payload.made ?? {};
  switch (item.kind) {
    case "newArtist":
      return (
        <Facts>
          <Fact label="Name">
            {made.artistId ? (
              <Link component={RouterLink} to={ROUTES.publicArtist(made.artistId)} color="inherit">
                {text(payload.name)}
              </Link>
            ) : (
              text(payload.name)
            )}
          </Fact>
        </Facts>
      );
    case "newSong": {
      const song = payload as unknown as SongState;
      return (
        <Facts>
          {fieldsOf(song).map(([label, value]) => (
            <Fact key={label} label={label}>
              {label === "Title" && made.songId ? (
                <Link component={RouterLink} to={ROUTES.publicSong(made.songId)} color="inherit">
                  {value}
                </Link>
              ) : (
                value
              )}
            </Fact>
          ))}
        </Facts>
      );
    }
    case "metadata": {
      if (payload.target === "song") {
        return (
          <Stack spacing={1}>
            <Link component={RouterLink} to={ROUTES.publicSong(Number(payload.songId))} color="inherit" sx={{ fontSize: 14 }}>
              Open the song
            </Link>
            <ChangeTable before={payload.before as SongState} after={payload.after as SongState} />
          </Stack>
        );
      }
      const before = payload.before as { name: string; names: string[] };
      const added = (payload.addNames as string[] | undefined) ?? [];
      return (
        <Facts>
          <Fact label="Name now">
            <Link component={RouterLink} to={ROUTES.publicArtist(Number(payload.artistId))} color="inherit">
              {before.name}
            </Link>
          </Fact>
          <Fact label="Proposed name">
            <Box component="span" sx={{ fontWeight: payload.name ? 600 : 400 }}>
              {text(payload.name) || "Same"}
            </Box>
          </Fact>
          <Fact label="Other names now">{before.names.filter((one) => one !== before.name).join(", ") || "None"}</Fact>
          <Fact label="Names to add">
            <Box component="span" sx={{ fontWeight: added.length ? 600 : 400 }}>
              {added.join(", ") || "None"}
            </Box>
          </Fact>
        </Facts>
      );
    }
    case "project": {
      const song = payload.song as { title: string; isNew: boolean; publicId?: number };
      const songId = song.publicId ?? made.songId;
      return (
        <Facts>
          <Fact label="Song">
            {songId ? (
              <Link component={RouterLink} to={ROUTES.publicSong(songId)} color="inherit">
                {song.title}
              </Link>
            ) : (
              `${song.title} (new)`
            )}
          </Fact>
          <Fact label="Version name">{text(payload.versionName)}</Fact>
          <Fact label="Replaces">{item.compare?.current ? `Your “${item.compare.current.name}”` : "Nothing: a new version"}</Fact>
        </Facts>
      );
    }
    case "versionPointer":
      return (
        <Facts>
          <Fact label="Song">
            <Link component={RouterLink} to={ROUTES.publicSong(Number(payload.songId))} color="inherit">
              {text(payload.songTitle)}
            </Link>
          </Fact>
          <Fact label="Version">“{text(payload.userVersionName)}”</Fact>
          <Fact label="As">{nameLabel(text(payload.name))}</Fact>
          <Fact label="Replaces">
            {item.compare?.current ? `“${item.compare.current.name}” by ${item.compare.current.creator}` : "Nothing yet"}
          </Fact>
        </Facts>
      );
    case "playlist": {
      const songs = (payload.items as { title: string; versionName: string | null }[] | undefined) ?? [];
      const left = (payload.left as string[] | undefined) ?? [];
      return (
        <Stack spacing={1.5}>
          <Facts>
            <Fact label="Title">
              {made.playlistId ? (
                <Link component={RouterLink} to={ROUTES.publicPlaylist(made.playlistId)} color="inherit">
                  {text(payload.title)}
                </Link>
              ) : (
                text(payload.title)
              )}
            </Fact>
            <Fact label="Songs">{songs.length}</Fact>
          </Facts>
          <Box component="ol" sx={{ m: 0, pl: 3, fontSize: 14 }}>
            {songs.map((one, index) => (
              <li key={index}>
                {one.title}
                {one.versionName ? <Box component="span" sx={{ color: "text.secondary" }}>{`, “${one.versionName}”`}</Box> : null}
              </li>
            ))}
          </Box>
          {left.length > 0 ? <Typography sx={{ fontSize: 14, color: "text.secondary" }}>Left out: {left.join(", ")}</Typography> : null}
        </Stack>
      );
    }
  }
}

/** The master user's decision on one waiting item. */
export function DecisionControls({ item, draft, onChange }: { item: RequestItem; draft: Draft; onChange: (next: Draft) => void }) {
  const editable = EDITABLE[item.kind];
  const initial = editable ? text(item.payload[editable[0]]) : "";
  const value = draft.value ?? initial;
  const nameField = item.kind === "project" || item.kind === "versionPointer";
  return (
    <Stack spacing={1.5} data-testid={`decide-${item.id}`}>
      <Segmented<ItemDecisionValue | "">
        label={`Decision on ${ITEM_LABEL[item.kind]}`}
        value={draft.decision}
        onChange={(decision) => onChange({ ...draft, decision })}
        options={[
          { value: "accepted", label: "Accept" },
          { value: "changesAsked", label: "Ask for a change" },
          { value: "refused", label: "Refuse" },
        ]}
      />
      {draft.decision === "accepted" && editable ? (
        <TextField
          size="small"
          label={editable[1]}
          value={value}
          onChange={(event) =>
            onChange({ ...draft, value: nameField ? event.target.value.toLowerCase().replace(/\s/g, "-") : event.target.value })
          }
          error={nameField && !validName(value)}
          helperText={nameField && !validName(value) ? NAME_RULE : undefined}
        />
      ) : null}
      {draft.decision === "changesAsked" || draft.decision === "refused" ? (
        <TextField
          size="small"
          label={draft.decision === "changesAsked" ? "What to change" : "Why (optional)"}
          value={draft.comment}
          onChange={(event) => onChange({ ...draft, comment: event.target.value })}
          multiline
          maxRows={4}
          required={draft.decision === "changesAsked"}
        />
      ) : null}
    </Stack>
  );
}
