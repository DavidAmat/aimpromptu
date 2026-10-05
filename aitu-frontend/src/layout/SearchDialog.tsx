/**
 * **Search** (`⌘K` or `Ctrl+K`): find a project by its title and open it (plan section 6.2).
 *
 * For now it looks only at the projects, which are today's pieces. The libraries join it when they
 * exist (Phases 6 and 13). The list loads when the dialog opens, and filtering is live because it
 * is cheap: the arrows move through the results and Enter opens the one marked.
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
import { audioApi, type AudioItem } from "../api";
import { ROUTES } from "./routes";
import { relativeTime } from "../ui";

export interface SearchDialogProps {
  open: boolean;
  onClose: () => void;
}

const MAX_RESULTS = 50;

export function SearchDialog({ open, onClose }: SearchDialogProps) {
  const navigate = useNavigate();
  const [items, setItems] = useState<AudioItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [marked, setMarked] = useState(0);

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    audioApi
      .list(controller.signal)
      .then((list) => {
        setItems(list);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(caught instanceof Error ? caught.message : "The projects could not be loaded.");
      });
    return () => controller.abort();
  }, [open]);

  const results = useMemo(() => {
    const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
    const all = items ?? [];
    const matching = words.length === 0 ? all : all.filter((item) => words.every((word) => item.alias.toLowerCase().includes(word)));
    return matching.slice(0, MAX_RESULTS);
  }, [items, query]);

  const close = () => {
    setQuery("");
    setMarked(0);
    onClose();
  };

  const openItem = (item: AudioItem | undefined) => {
    if (!item) return;
    close();
    navigate(ROUTES.project(item.uuid));
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
          placeholder="Search projects"
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
          inputProps={{ "aria-label": "Search projects" }}
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
            {query ? `No project matches “${query}”` : "No projects yet"}
          </Typography>
        ) : (
          <List dense disablePadding aria-label="Results">
            {results.map((item, index) => (
              <ListItemButton
                key={item.uuid}
                selected={index === marked}
                onClick={() => openItem(item)}
                onMouseMove={() => setMarked(index)}
                sx={{ borderRadius: 1, py: 1 }}
              >
                <Typography noWrap title={item.alias} sx={{ flex: 1, minWidth: 0 }}>
                  {item.alias}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ ml: 2, flexShrink: 0 }}>
                  {relativeTime(item.updatedAt ?? item.createdAt)}
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
