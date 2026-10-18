/**
 * **Sheet**: the whole piano sheet a request proposes (implementation 02, Phase 14), the tab beside
 * Conversation, as a pull request has its changes beside its conversation.
 *
 * The proposed sheet takes the page's width, read only, with its own player. When the Public
 * Library has a version it would replace (the author's own of that name, or the fixed version of
 * that name), **Proposed** and **Now** switch between the two. A project of several parts shows one
 * part at a time.
 *
 * Marking a stretch of the proposed sheet offers **Comment on this stretch**: the comment goes to
 * the Conversation, with that stretch drawn above it.
 */

import { useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import OpenInFullIcon from "@mui/icons-material/OpenInFull";
import { useNavigate } from "react-router-dom";
import type { CommentInput, ProjectSide, RequestItem } from "../../api";
import { ROUTES } from "../../layout/routes";
import { IconAction, PillButton, Segmented } from "../../ui";
import SheetPage from "../piece/sheet/SheetPage";
import { stretchLabel } from "../library/shared";
import { itemLine } from "./items";

type Side = "proposed" | "current";

export interface RequestSheetProps {
  item: RequestItem;
  onComment: (input: CommentInput) => Promise<boolean>;
  /** Open the Conversation tab. */
  onOpenConversation: () => void;
}

export function RequestSheet({ item, onComment, onOpenConversation }: RequestSheetProps) {
  const navigate = useNavigate();
  const compare = item.compare;
  const [side, setSide] = useState<Side>("proposed");
  const [part, setPart] = useState(0);
  const [stretch, setStretch] = useState<{ fromMs: number; toMs: number } | null>(null);
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [added, setAdded] = useState(false);

  const shown: ProjectSide | null = side === "current" ? (compare?.current ?? null) : (compare?.proposed ?? null);
  const parts = shown?.kept ? shown.parts : [];
  const partId = parts[Math.min(part, parts.length - 1)];
  const proposed = side === "proposed";

  const send = async () => {
    if (!stretch || !partId) return;
    setBusy(true);
    const done = await onComment({ body, itemId: item.id, partId, fromMs: stretch.fromMs, toMs: stretch.toMs });
    setBusy(false);
    if (done) {
      setStretch(null);
      setBody("");
      setAdded(true);
    }
  };

  return (
    <Box>
      <Stack direction="row" spacing={1.5} useFlexGap sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1, mb: 1.5 }}>
        <Typography sx={{ fontWeight: 600, fontSize: 14 }}>{itemLine(item)}</Typography>
        {shown ? (
          <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
            by {shown.creator}
          </Typography>
        ) : null}
        {compare?.current ? (
          <Segmented<Side>
            label="Which sheet"
            value={side}
            onChange={(value) => {
              setSide(value);
              setPart(0);
            }}
            options={[
              { value: "proposed", label: "Proposed" },
              { value: "current", label: "Now", tooltip: "The version the Public library has now" },
            ]}
          />
        ) : null}
        {parts.length > 1 ? (
          <Segmented<string>
            label="Part"
            value={String(part)}
            onChange={(value) => setPart(Number(value))}
            options={parts.map((_, index) => ({ value: String(index), label: `Part ${index + 1}` }))}
          />
        ) : null}
        <Box sx={{ flex: 1 }} />
        {proposed ? (
          <Typography sx={{ fontSize: 13, color: "text.secondary", display: { xs: "none", md: "block" } }}>
            Mark a stretch to comment on it
          </Typography>
        ) : null}
        {shown?.kept ? (
          <IconAction title="Open in Play mode" icon={<OpenInFullIcon fontSize="small" />} onClick={() => navigate(ROUTES.play(shown.projectId))} />
        ) : null}
      </Stack>
      {added ? (
        <Alert
          severity="success"
          onClose={() => setAdded(false)}
          sx={{ mb: 1.5 }}
          action={
            <PillButton kind="quiet" size="small" onClick={onOpenConversation}>
              Open the conversation
            </PillButton>
          }
        >
          Comment added
        </Alert>
      ) : null}
      {partId ? (
        <Box sx={{ border: 1, borderColor: "divider", borderRadius: 2, overflow: "hidden" }} data-testid={`request-sheet-${side}`}>
          <SheetPage
            key={partId}
            step={{
              audioUuid: partId,
              state: "ready",
              reason: null,
              onChanged: () => undefined,
              readOnly: true,
              ...(proposed
                ? { stretchAction: { label: "Comment on this stretch", onStretch: (fromMs: number, toMs: number) => setStretch({ fromMs, toMs }) } }
                : {}),
            }}
          />
        </Box>
      ) : (
        <Typography sx={{ color: "text.secondary", fontSize: 14 }}>
          {shown ? "This project is no longer kept." : "Nothing to show."}
        </Typography>
      )}

      <Dialog open={stretch !== null} onClose={busy ? undefined : () => setStretch(null)} maxWidth="xs" fullWidth>
        <DialogTitle>Comment on {stretch ? stretchLabel(stretch.fromMs, stretch.toMs) : ""}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            multiline
            minRows={3}
            maxRows={10}
            placeholder="What about this stretch?"
            value={body}
            onChange={(event) => setBody(event.target.value)}
            sx={{ mt: 1 }}
            slotProps={{ htmlInput: { maxLength: 4000, "aria-label": "Comment" } }}
          />
        </DialogContent>
        <DialogActions>
          <PillButton kind="quiet" onClick={() => setStretch(null)} disabled={busy}>
            Cancel
          </PillButton>
          <PillButton kind="primary" onClick={() => void send()} disabled={!body.trim()} busy={busy} data-testid="send-stretch-comment">
            Comment
          </PillButton>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default RequestSheet;
