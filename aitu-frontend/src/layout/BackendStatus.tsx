/**
 * Small "is the API up?" indicator in the app bar. The backend has to be
 * running for anything here to work, so surfacing it beats a failed request
 * on every page.
 */

import { useEffect, useState } from "react";
import Chip from "@mui/material/Chip";
import { API_BASE, health } from "../api";

type State = "checking" | "up" | "down";

export function BackendStatus() {
  const [state, setState] = useState<State>("checking");

  useEffect(() => {
    const controller = new AbortController();
    health(controller.signal)
      .then(() => setState("up"))
      .catch(() => {
        if (!controller.signal.aborted) setState("down");
      });
    return () => controller.abort();
  }, []);

  const label = state === "up" ? "API online" : state === "down" ? "API offline" : "…";

  return (
    <Chip
      size="small"
      variant="outlined"
      color={state === "up" ? "success" : state === "down" ? "error" : "default"}
      label={label}
      title={API_BASE}
    />
  );
}

export default BackendStatus;
