/**
 * **Finish your review** (implementation 02, Phase 14, plan section 16.3): the master user's
 * decision on every item still waiting, as a pull request's "Review changes". Each item gets
 * **Accept** (its name can be changed), **Ask for a change** (what to change) or **Refuse**; a note
 * for the author goes with them. **Send decision** writes what is accepted at once; the decision
 * then appears in the Conversation.
 */

import { useState } from "react";
import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { requestsApi, type ItemDecisionValue, type RequestDetail } from "../../api";
import { PillButton } from "../../ui";
import { said } from "../library/shared";
import { draftComplete, EDITABLE, EMPTY_DRAFT, itemLine, text, type Draft } from "./items";
import { DecisionControls } from "./RequestItems";

export function ReviewDialog({
  detail,
  onClose,
  onDecided,
}: {
  detail: RequestDetail;
  onClose: () => void;
  onDecided: (answer: RequestDetail) => void;
}) {
  const waiting = detail.itemList.filter((item) => item.decision === null);
  const [drafts, setDrafts] = useState<Record<number, Draft>>({});
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const draftOf = (id: number) => drafts[id] ?? EMPTY_DRAFT;
  const complete = waiting.every((item) => draftComplete(item, draftOf(item.id)));

  const send = async () => {
    setBusy(true);
    setError(null);
    try {
      const answer = await requestsApi.decide(
        detail.id,
        waiting.map((item) => {
          const draft = draftOf(item.id);
          const editable = EDITABLE[item.kind];
          const changed = editable && draft.value !== null && draft.value !== text(item.payload[editable[0]]);
          return {
            id: item.id,
            decision: draft.decision as ItemDecisionValue,
            ...(draft.comment.trim() ? { comment: draft.comment.trim() } : {}),
            ...(draft.decision === "accepted" && changed && editable ? { changes: { [editable[0]]: draft.value } } : {}),
          };
        }),
        note.trim() || undefined,
      );
      onDecided(answer);
    } catch (caught) {
      setError(said(caught, "The decision could not be sent."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open onClose={busy ? undefined : onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Finish your review</DialogTitle>
      <DialogContent>
        <Stack spacing={2} divider={<Divider flexItem />} sx={{ pt: 1 }}>
          {waiting.map((item) => (
            <Box key={item.id}>
              <Typography sx={{ fontWeight: 600, fontSize: 14, mb: 1 }}>{itemLine(item)}</Typography>
              <DecisionControls
                item={item}
                draft={draftOf(item.id)}
                onChange={(next) => setDrafts((current) => ({ ...current, [item.id]: next }))}
              />
            </Box>
          ))}
          <TextField
            label="Note for the author"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            multiline
            maxRows={6}
            slotProps={{ htmlInput: { maxLength: 2000 } }}
          />
        </Stack>
        {error ? (
          <Typography role="alert" color="error" sx={{ fontSize: 14, pt: 1.5 }}>
            {error}
          </Typography>
        ) : null}
      </DialogContent>
      <DialogActions>
        <PillButton kind="quiet" onClick={onClose} disabled={busy}>
          Cancel
        </PillButton>
        <PillButton kind="primary" onClick={() => void send()} disabled={!complete} busy={busy} data-testid="send-decision">
          Send decision
        </PillButton>
      </DialogActions>
    </Dialog>
  );
}

export default ReviewDialog;
