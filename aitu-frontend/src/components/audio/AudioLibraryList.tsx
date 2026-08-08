/**
 * "Load from library": every audio in the store, with rename and delete.
 * Selecting one hands its uuid to the parent.
 */

import { useCallback, useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlined";
import ReportProblemOutlinedIcon from "@mui/icons-material/ReportProblemOutlined";
import { audioApi, type AudioItem } from "../../api";
import { formatTimeShort } from "../../audio/time";

export interface AudioLibraryListProps {
  selectedUuid?: string | null;
  onSelect?: (audio: AudioItem) => void;
  /** Bump to force a reload — e.g. after a recording is saved. */
  reloadToken?: number;
}

/** State tagged with the request it belongs to, so nothing stale leaks through. */
interface ListState {
  token: number;
  items: AudioItem[] | null;
  error: string | null;
}

export function AudioLibraryList({ selectedUuid, onSelect, reloadToken = 0 }: AudioLibraryListProps) {
  const [state, setState] = useState<ListState>({ token: -1, items: null, error: null });
  const [localToken, setLocalToken] = useState(0);
  const token = reloadToken * 1000 + localToken;

  // Derived, not assigned in an effect: a new token means "loading", full stop.
  const current = state.token === token ? state : { token, items: null, error: null };

  const load = useCallback(
    (signal?: AbortSignal) => {
      audioApi
        .list(signal)
        .then((items) => setState({ token, items, error: null }))
        .catch((caught: unknown) => {
          if (signal?.aborted) return;
          setState({
            token,
            items: [],
            error:
              caught instanceof Error ? caught.message : "Could not load the audio library.",
          });
        });
    },
    [token],
  );

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const remove = async (uuid: string) => {
    await audioApi.remove(uuid);
    setLocalToken((value) => value + 1);
  };

  const { items, error } = current;

  if (error) return <Alert severity="error">{error}</Alert>;
  if (!items) {
    return (
      <Stack direction="row" spacing={1} sx={{ alignItems: "center", py: 1 }}>
        <CircularProgress size={16} />
        <Typography variant="body2" color="text.secondary">
          Loading…
        </Typography>
      </Stack>
    );
  }
  if (items.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        Nothing here yet. Upload a file, record something, or download from YouTube.
      </Typography>
    );
  }

  return (
    <List dense disablePadding>
      {items.map((item) => (
        <ListItemButton
          key={item.uuid}
          selected={item.uuid === selectedUuid}
          onClick={() => onSelect?.(item)}
        >
          <ListItemText
            primary={item.alias}
            secondary={
              <Box component="span">
                {item.durationSeconds ? formatTimeShort(item.durationSeconds) : "—"} ·{" "}
                {item.format.toUpperCase()}
                {item.needsRederivation ? (
                  <Box component="span" sx={{ display: "block", color: "warning.main" }}>
                    {item.needsRederivation}
                  </Box>
                ) : null}
              </Box>
            }
          />
          {item.needsRederivation ? (
            <ReportProblemOutlinedIcon
              fontSize="small"
              color="warning"
              sx={{ mr: 1 }}
              titleAccess="This piece cannot be drawn yet"
            />
          ) : null}
          <Chip label={item.source} size="small" variant="outlined" sx={{ mr: 1 }} />
          <IconButton
            edge="end"
            size="small"
            aria-label={`Delete ${item.alias}`}
            onClick={(event) => {
              event.stopPropagation();
              void remove(item.uuid);
            }}
          >
            <DeleteOutlineIcon fontSize="small" />
          </IconButton>
        </ListItemButton>
      ))}
    </List>
  );
}

export default AudioLibraryList;
