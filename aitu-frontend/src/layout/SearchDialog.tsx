/**
 * **Search** (`⌘K` or `Ctrl+K`): find a song of My library or a project, and open it (plan section
 * 6.2).
 *
 * It looks at the songs of the Private Library (by title and artist) and the projects of Projects
 * (by title). The Public Library joins it in Phase 13. The lists load when the dialog opens, and
 * filtering is live because it is cheap: the arrows move through the results and Enter opens the
 * one marked.
 */

import { useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import InputBase from "@mui/material/InputBase";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import SearchIcon from "@mui/icons-material/Search";
import { useNavigate } from "react-router-dom";
import { libraryApi, projectsApi } from "../api";
import { ROUTES } from "./routes";
import { relativeTime } from "../ui";

export interface SearchDialogProps {
  open: boolean;
  onClose: () => void;
}

const MAX_RESULTS = 50;

/** One thing the search can open. */
interface Found {
  key: string;
  title: string;
  /** What is shown on the right: a song's artists, or when a project changed. */
  detail: string;
  /** What the words are matched against. */
  text: string;
  to: string;
}

export function SearchDialog({ open, onClose }: SearchDialogProps) {
  const navigate = useNavigate();
  const [items, setItems] = useState<Found[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [marked, setMarked] = useState(0);

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    Promise.all([libraryApi.songs(controller.signal), projectsApi.list(["vault"], controller.signal)])
      .then(([songs, projects]) => {
        const found: Found[] = [
          ...songs.map((song) => {
            const artists = song.artists.map((artist) => artist.name).join(", ");
            return {
              key: `song-${song.id}`,
              title: song.title,
              detail: artists || "Song",
              text: `${song.title} ${artists}`.toLowerCase(),
              to: ROUTES.librarySong(song.id),
            };
          }),
          ...projects.map((project) => ({
            key: `project-${project.id}`,
            title: project.title || "Untitled project",
            detail: relativeTime(project.updatedAt ?? project.createdAt),
            text: (project.title || "Untitled project").toLowerCase(),
            to: ROUTES.project(project.parts[0] ?? project.id),
          })),
        ];
        setItems(found);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(caught instanceof Error ? caught.message : "The search could not be loaded.");
      });
    return () => controller.abort();
  }, [open]);

  const results = useMemo(() => {
    const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
    const all = items ?? [];
    const matching = words.length === 0 ? all : all.filter((item) => words.every((word) => item.text.includes(word)));
    return matching.slice(0, MAX_RESULTS);
  }, [items, query]);

  const close = () => {
    setQuery("");
    setMarked(0);
    onClose();
  };

  const openItem = (item: Found | undefined) => {
    if (!item) return;
    close();
    navigate(item.to);
  };

  return (
    <Dialog
      open={open}
      onClose={close}
      fullWidth
      maxWidth="sm"
      slotProps={{ paper: { sx: { alignSelf: "flex-start", mt: "12vh" } } }}
    >
      <Stack direction="row" spacing={1.5} sx={{ alignItems: "center", px: 2, py: 1.5, borderBottom: 1, borderColor: "divider" }}>
        <SearchIcon fontSize="small" sx={{ color: "text.secondary" }} />
        <InputBase
          autoFocus
          fullWidth
          placeholder="Search songs and projects"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setMarked(0);
          }}
          onKeyDown={(event) => {
            if (event.key === "ArrowDown") {
              event.preventDefault();
              setMarked((at) => Math.min(results.length - 1, at + 1));
            } else if (event.key === "ArrowUp") {
              event.preventDefault();
              setMarked((at) => Math.max(0, at - 1));
            } else if (event.key === "Enter") {
              event.preventDefault();
              openItem(results[marked]);
            }
          }}
          inputProps={{ "aria-label": "Search songs and projects" }}
          sx={{ fontSize: 16 }}
        />
      </Stack>
      <Box sx={{ maxHeight: "50vh", overflowY: "auto", p: 0.75 }}>
        {error ? (
          <Typography color="error" sx={{ p: 2 }}>
            {error}
          </Typography>
        ) : items === null ? (
          <Stack spacing={1} sx={{ p: 1 }}>
            {[0, 1, 2].map((row) => (
              <Skeleton key={row} variant="rounded" height={36} />
            ))}
          </Stack>
        ) : results.length === 0 ? (
          <Typography color="text.secondary" sx={{ p: 2 }}>
            {query ? `Nothing matches “${query}”` : "No songs or projects yet"}
          </Typography>
        ) : (
          <List dense disablePadding aria-label="Results">
            {results.map((item, index) => (
              <ListItemButton
                key={item.key}
                selected={index === marked}
                onClick={() => openItem(item)}
                onMouseMove={() => setMarked(index)}
                sx={{ borderRadius: 1, py: 1 }}
              >
                <Typography noWrap title={item.title} sx={{ flex: 1, minWidth: 0 }}>
                  {item.title}
                </Typography>
                <Typography variant="body2" color="text.secondary" noWrap sx={{ ml: 2, flexShrink: 0, maxWidth: "40%" }}>
                  {item.detail}
                </Typography>
              </ListItemButton>
            ))}
          </List>
        )}
      </Box>
    </Dialog>
  );
}

export default SearchDialog;
