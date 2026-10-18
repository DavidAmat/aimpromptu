/**
 * **Conversation**: a request's timeline, laid out like a pull request's (implementation 02,
 * Phase 14, the user's ask of 2026-10-18).
 *
 * - The first box is the request as it was sent: who sent it, their note, and what it proposes
 *   (each item; a piano sheet links to the **Sheet** tab).
 * - Then, in time order, every comment and every event on one line down the left: a comment is a
 *   box with its author and time; a review is a box with the decision of each item and its words;
 *   "sent it again" and "withdrew it" are lines of their own.
 * - A comment on a stretch of the sheet draws that stretch above its words: the notes and marks as
 *   they were when it was written (a project of just that stretch), with its own Play. It says
 *   "Outdated" once the request was sent again with another sheet. Its replies follow it, and
 *   **Reply** answers it.
 * - At the end, **Comment** writes to the request (the author and the master user).
 */

import { useCallback, useRef, useState, type ReactNode } from "react";
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Link from "@mui/material/Link";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import BlockIcon from "@mui/icons-material/Block";
import CheckIcon from "@mui/icons-material/Check";
import EditNoteIcon from "@mui/icons-material/EditNoteOutlined";
import PauseIcon from "@mui/icons-material/Pause";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import ReplayIcon from "@mui/icons-material/Replay";
import UndoIcon from "@mui/icons-material/Undo";
import type { CommentInput, RequestComment, RequestDetail, RequestItem } from "../../api";
import type { ScorePlayerControls } from "../../components/time/ScorePlayer";
import { fullTime, IconAction, PillButton, relativeTime } from "../../ui";
import SheetPage from "../piece/sheet/SheetPage";
import { stretchLabel } from "../library/shared";
import { itemLine } from "./items";
import { ItemBody } from "./RequestItems";
import { DECISION_LABEL } from "./words";

/** The width of the left column, where the line, the avatars and the event marks are. */
const RAIL = 40;

function Avatar({ name, small }: { name: string; small?: boolean }) {
  const side = small ? 24 : 32;
  return (
    <Box
      aria-hidden
      sx={{
        width: side,
        height: side,
        borderRadius: "50%",
        flexShrink: 0,
        display: "grid",
        placeItems: "center",
        backgroundColor: "text.primary",
        color: "background.default",
        fontSize: small ? 11 : 13,
        fontWeight: 600,
      }}
    >
      {(name[0] ?? "?").toUpperCase()}
    </Box>
  );
}

function When({ at }: { at: string }) {
  return (
    <Tooltip title={fullTime(at)}>
      <Box component="span" sx={{ color: "text.secondary" }}>
        {relativeTime(at)}
      </Box>
    </Tooltip>
  );
}

/** One entry of the timeline: the rail on the left (an avatar or a mark), the content on the right. */
function Entry({ mark, children }: { mark: ReactNode; children: ReactNode }) {
  return (
    <Stack direction="row" spacing={1.5} sx={{ position: "relative", alignItems: "flex-start" }}>
      <Box sx={{ width: RAIL, display: "flex", justifyContent: "center", flexShrink: 0, pt: 0.5, zIndex: 1 }}>{mark}</Box>
      <Box sx={{ flex: 1, minWidth: 0 }}>{children}</Box>
    </Stack>
  );
}

/** An event's mark on the line: a small round icon. */
function EventMark({ icon }: { icon: ReactNode }) {
  return (
    <Box
      sx={(theme) => ({
        width: 28,
        height: 28,
        borderRadius: "50%",
        display: "grid",
        placeItems: "center",
        backgroundColor: (theme.vars ?? theme).palette.background.default,
        border: 1,
        borderColor: "divider",
        color: "text.secondary",
        "& svg": { fontSize: 16 },
      })}
    >
      {icon}
    </Box>
  );
}

/** A box of the conversation: a header line with its author and time, then its content. */
function CommentBox({
  author,
  role,
  action,
  at,
  extra,
  children,
  testId,
}: {
  author: string;
  role: string;
  action: string;
  at: string;
  extra?: ReactNode;
  children?: ReactNode;
  testId?: string;
}) {
  return (
    <Box
      data-testid={testId}
      sx={(theme) => ({
        border: 1,
        borderColor: "divider",
        borderRadius: 2,
        overflow: "hidden",
        backgroundColor: (theme.vars ?? theme).palette.background.default,
      })}
    >
      <Stack
        direction="row"
        spacing={1}
        sx={(theme) => ({
          alignItems: "center",
          px: 2,
          py: 1,
          fontSize: 14,
          borderBottom: children ? 1 : 0,
          borderColor: "divider",
          backgroundColor: (theme.vars ?? theme).palette.action.hover,
          flexWrap: "wrap",
          rowGap: 0.5,
        })}
      >
        <Box component="span" sx={{ fontWeight: 600 }}>
          {author}
        </Box>
        <Box component="span" sx={{ color: "text.secondary" }}>
          {action}
        </Box>
        <When at={at} />
        {extra}
        <Box sx={{ flex: 1 }} />
        <Box component="span" sx={{ fontSize: 12, color: "text.secondary", border: 1, borderColor: "divider", borderRadius: 999, px: 1 }}>
          {role}
        </Box>
      </Stack>
      {children}
    </Box>
  );
}

function Body({ text }: { text: string }) {
  return (
    <Typography component="div" sx={{ px: 2, py: 1.5, fontSize: 15, whiteSpace: "pre-line", overflowWrap: "anywhere" }}>
      {text}
    </Typography>
  );
}

/** The stretch a comment is about, drawn as it was, with its own Play. */
function Stretch({ comment, outdated, label }: { comment: RequestComment; outdated: boolean; label: string }) {
  const player = useRef<ScorePlayerControls | null>(null);
  const [playing, setPlaying] = useState(false);
  const report = useCallback((now: boolean) => setPlaying(now), []);
  const details = comment.details;
  if (!details.excerptPart || details.fromMs === undefined || details.toMs === undefined) return null;
  const anchor = details.anchorMs ?? null;
  return (
    <Box sx={{ borderBottom: 1, borderColor: "divider" }} data-testid="stretch-comment">
      <Stack direction="row" spacing={1} sx={{ alignItems: "center", px: 2, pt: 1, fontSize: 13, color: "text.secondary" }}>
        <span>
          {label}, {stretchLabel(details.fromMs, details.toMs)}
        </span>
        {outdated ? (
          <Tooltip title="The request was sent again with another sheet since">
            <Box component="span" sx={{ border: 1, borderColor: "divider", borderRadius: 999, px: 1, fontSize: 12 }}>
              Outdated
            </Box>
          </Tooltip>
        ) : null}
        <Box sx={{ flex: 1 }} />
        <IconAction
          title={playing ? "Pause" : "Play this stretch"}
          icon={playing ? <PauseIcon fontSize="small" /> : <PlayArrowIcon fontSize="small" />}
          onClick={() => player.current?.toggle()}
        />
      </Stack>
      <Box sx={{ pb: 1 }}>
        <SheetPage
          key={details.excerptPart}
          step={{
            audioUuid: details.excerptPart,
            state: "ready",
            reason: null,
            onChanged: () => undefined,
            passage: { role: "current", ...(anchor !== null ? { anchorMs: anchor } : {}), playerRef: player, onPlaying: report },
          }}
        />
      </Box>
    </Box>
  );
}

/** A box to write in: one line until it is used, then the field and its button. */
function Composer({
  placeholder,
  button,
  onSend,
  compact,
  testId,
}: {
  placeholder: string;
  button: string;
  onSend: (body: string) => Promise<boolean>;
  compact?: boolean;
  testId?: string;
}) {
  const [body, setBody] = useState("");
  const [open, setOpen] = useState(!compact);
  const [busy, setBusy] = useState(false);
  const send = async () => {
    setBusy(true);
    const done = await onSend(body);
    setBusy(false);
    if (done) {
      setBody("");
      if (compact) setOpen(false);
    }
  };
  if (!open) {
    return (
      <ButtonBase
        onClick={() => setOpen(true)}
        sx={{ width: "100%", justifyContent: "flex-start", px: 1.5, py: 1, border: 1, borderColor: "divider", borderRadius: 2, color: "text.secondary", fontSize: 14 }}
        data-testid={testId ? `${testId}-open` : undefined}
      >
        {placeholder}
      </ButtonBase>
    );
  }
  return (
    <Stack spacing={1} data-testid={testId}>
      <TextField
        multiline
        minRows={compact ? 2 : 3}
        maxRows={12}
        placeholder={placeholder}
        autoFocus={compact}
        value={body}
        onChange={(event) => setBody(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && (event.metaKey || event.ctrlKey) && body.trim()) void send();
        }}
        slotProps={{ htmlInput: { maxLength: 4000, "aria-label": placeholder } }}
      />
      <Stack direction="row" spacing={1} sx={{ justifyContent: "flex-end" }}>
        {compact ? (
          <PillButton
            kind="quiet"
            size="small"
            onClick={() => {
              setOpen(false);
              setBody("");
            }}
          >
            Cancel
          </PillButton>
        ) : null}
        <PillButton kind={compact ? "secondary" : "primary"} size={compact ? "small" : "medium"} onClick={() => void send()} disabled={!body.trim()} busy={busy}>
          {button}
        </PillButton>
      </Stack>
    </Stack>
  );
}

/** What a review decided, in one verb. */
function reviewVerb(decisions: { decision: string }[]): { verb: string; icon: ReactNode } {
  if (decisions.some((one) => one.decision === "changesAsked")) return { verb: "asked for changes", icon: <EditNoteIcon /> };
  if (decisions.length > 0 && decisions.every((one) => one.decision === "accepted")) return { verb: "accepted", icon: <CheckIcon /> };
  if (decisions.length > 0 && decisions.every((one) => one.decision === "refused")) return { verb: "refused", icon: <BlockIcon /> };
  return { verb: "reviewed", icon: <CheckIcon /> };
}

export interface ConversationProps {
  detail: RequestDetail;
  /** The reader's username, beside the box to write. */
  me: string;
  /** Write a comment; `false` when it was refused (the page says why). */
  onComment: (input: CommentInput) => Promise<boolean>;
  /** Open the Sheet (or Changes) tab. */
  onOpenSheet: () => void;
}

export function Conversation({ detail, me, onComment, onOpenSheet }: ConversationProps) {
  // Only the author and the master user write in a request: anyone else here is the reviewer.
  const role = (name: string) => (name === detail.author ? "Author" : "Reviewer");
  const items = new Map<number, RequestItem>(detail.itemList.map((item) => [item.id, item]));
  const proposedParts = new Set(
    detail.itemList.flatMap((item) => (item.compare?.proposed?.kept ? item.compare.proposed.parts : [])),
  );
  // The note sent with the request opens the conversation, as a pull request's description does.
  const opening = detail.comments.find(
    (one) =>
      one.kind === "comment" &&
      one.parentId === null &&
      !one.details.excerpt &&
      one.author === detail.author &&
      Math.abs(new Date(one.createdAt).getTime() - new Date(detail.createdAt).getTime()) < 10_000,
  );
  const replies = new Map<number, RequestComment[]>();
  for (const one of detail.comments) {
    if (one.parentId !== null) replies.set(one.parentId, [...(replies.get(one.parentId) ?? []), one]);
  }
  const timeline = detail.comments.filter((one) => one.parentId === null && one !== opening);
  const hasSheet = detail.itemList.some((item) => item.compare !== null);

  const entry = (one: RequestComment) => {
    if (one.kind === "sentAgain") {
      return (
        <Entry key={one.id} mark={<EventMark icon={<ReplayIcon />} />}>
          <Typography sx={{ fontSize: 14, pt: 0.75 }}>
            <b>{one.author}</b> <Box component="span" sx={{ color: "text.secondary" }}>sent it again</Box> <When at={one.createdAt} />
          </Typography>
          {one.body ? (
            <Box sx={{ mt: 1, border: 1, borderColor: "divider", borderRadius: 2 }}>
              <Body text={one.body} />
            </Box>
          ) : null}
        </Entry>
      );
    }
    if (one.kind === "withdrawn") {
      return (
        <Entry key={one.id} mark={<EventMark icon={<UndoIcon />} />}>
          <Typography sx={{ fontSize: 14, pt: 0.75 }}>
            <b>{one.author}</b> <Box component="span" sx={{ color: "text.secondary" }}>withdrew it</Box> <When at={one.createdAt} />
          </Typography>
        </Entry>
      );
    }
    if (one.kind === "review") {
      const decisions = one.details.items ?? [];
      const { verb, icon } = reviewVerb(decisions);
      return (
        <Entry key={`review-${one.id}-${one.createdAt}`} mark={<EventMark icon={icon} />}>
          <CommentBox author={one.author} role={role(one.author)} action={verb} at={one.createdAt} testId="review-event">
            <Stack component="ul" spacing={1} sx={{ listStyle: "none", m: 0, px: 2, py: 1.5 }}>
              {decisions.map((decision) => {
                const item = items.get(decision.id);
                return (
                  <Box component="li" key={decision.id} sx={{ fontSize: 14 }}>
                    <Box component="span" sx={{ fontWeight: 600 }}>
                      {DECISION_LABEL[decision.decision]}
                    </Box>
                    <Box component="span" sx={{ color: "text.secondary" }}>
                      {" "}
                      {item ? itemLine(item) : "an item"}
                    </Box>
                    {decision.comment ? (
                      <Typography component="div" sx={{ fontSize: 14, whiteSpace: "pre-line", mt: 0.25 }}>
                        {decision.comment}
                      </Typography>
                    ) : null}
                  </Box>
                );
              })}
            </Stack>
            {one.body ? (
              <Box sx={{ borderTop: 1, borderColor: "divider" }}>
                <Body text={one.body} />
              </Box>
            ) : null}
          </CommentBox>
        </Entry>
      );
    }
    const item = one.itemId !== null ? items.get(one.itemId) : undefined;
    const thread = replies.get(one.id) ?? [];
    const onStretch = Boolean(one.details.excerpt);
    return (
      <Entry key={one.id} mark={<Avatar name={one.author} />}>
        <CommentBox
          author={one.author}
          role={role(one.author)}
          action={onStretch ? "commented on the sheet" : "commented"}
          at={one.createdAt}
          testId={onStretch ? "stretch-thread" : "comment"}
        >
          {onStretch ? (
            <Stretch
              comment={one}
              outdated={!proposedParts.has(one.details.partId ?? "")}
              label={item ? itemLine(item) : "The piano sheet"}
            />
          ) : null}
          <Body text={one.body} />
          {thread.map((reply) => (
            <Stack key={reply.id} direction="row" spacing={1.25} sx={{ px: 2, py: 1.25, borderTop: 1, borderColor: "divider" }} data-testid="reply">
              <Avatar name={reply.author} small />
              <Box sx={{ minWidth: 0, flex: 1 }}>
                <Typography sx={{ fontSize: 13 }}>
                  <b>{reply.author}</b> <When at={reply.createdAt} />
                </Typography>
                <Typography component="div" sx={{ fontSize: 14, whiteSpace: "pre-line", overflowWrap: "anywhere" }}>
                  {reply.body}
                </Typography>
              </Box>
            </Stack>
          ))}
          <Box sx={{ px: 2, py: 1.25, borderTop: 1, borderColor: "divider" }}>
            <Composer
              compact
              placeholder="Reply…"
              button="Reply"
              testId={`reply-${one.id}`}
              onSend={(body) => onComment({ body, parentId: one.id })}
            />
          </Box>
        </CommentBox>
      </Entry>
    );
  };

  return (
    <Box sx={{ position: "relative" }}>
      {/* The line the timeline hangs on, behind the avatars and the marks. */}
      <Box aria-hidden sx={{ position: "absolute", left: RAIL / 2 - 1, top: 16, bottom: 72, width: 2, backgroundColor: "divider" }} />
      <Stack spacing={2.5} sx={{ position: "relative" }}>
        <Entry mark={<Avatar name={detail.author} />}>
          <CommentBox author={detail.author} role="Author" action="sent this request" at={detail.createdAt} testId="opening">
            {opening ? <Body text={opening.body} /> : null}
            <Stack spacing={2} sx={{ px: 2, py: 1.5, borderTop: opening ? 1 : 0, borderColor: "divider" }}>
              {detail.itemList.map((item) => (
                <Box key={item.id}>
                  <Stack direction="row" spacing={1} sx={{ alignItems: "baseline", mb: 1 }}>
                    <Typography sx={{ fontWeight: 600, fontSize: 14 }}>{itemLine(item)}</Typography>
                    <Box sx={{ flex: 1 }} />
                    {item.compare ? (
                      <Link component="button" type="button" onClick={onOpenSheet} sx={{ fontSize: 14 }} color="inherit">
                        See the sheet
                      </Link>
                    ) : null}
                  </Stack>
                  <ItemBody item={item} />
                </Box>
              ))}
            </Stack>
          </CommentBox>
        </Entry>
        {timeline.map(entry)}
        <Entry mark={<Avatar name={me} />}>
          <Composer
            placeholder={hasSheet ? "Leave a comment. To comment on a stretch, mark it on the Sheet tab." : "Leave a comment"}
            button="Comment"
            testId="comment-box"
            onSend={(body) => onComment({ body })}
          />
        </Entry>
      </Stack>
    </Box>
  );
}

export default Conversation;
