/**
 * **One request** (implementation 02, Phase 14, plan sections 16.2 and 16.3), laid out like a pull
 * request (the user's ask of 2026-10-18). The same page for its author (`/requests/:id`) and for
 * the master user's review (`/admin/requests/:id`).
 *
 * - The header: the title, the status in words, and one line saying who asks for what.
 * - Two tabs, each its own address: **Conversation** (the timeline: the request as sent, comments,
 *   comments on a stretch of the sheet with that stretch drawn, the reviews, "sent it again"; a box
 *   to write, `Conversation`) and **Sheet** (`/sheet`: the whole proposed sheet, read only, where a
 *   marked stretch takes a comment, `RequestSheet`). A request with no piano sheet has **Changes**
 *   there instead: what each item proposes.
 * - Beside the conversation, a narrow column: the items with their decisions, the kind, the dates.
 * - **The author**: **Withdraw** while it waits; **Change and send again** when changes are asked,
 *   which opens the dialog that sent it, filled as it was.
 * - **The master user**, on a request waiting for review: **Review** opens **Finish your review**
 *   (`ReviewDialog`), a decision per item.
 */

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { publicApi, requestsApi, type CommentInput, type RequestDetail } from "../../api";
import { ROUTES } from "../../layout/routes";
import { useAuth } from "../../state/authContext";
import { ConfirmDialog, EmptyState, fullTime, PageBody, PageHeader, PillButton, relativeTime, Section, TabBar } from "../../ui";
import { said } from "../library/shared";
import { Conversation } from "./Conversation";
import { itemLine, text } from "./items";
import { PublishDialog } from "./PublishDialog";
import { ItemBody } from "./RequestItems";
import { RequestSheet } from "./RequestSheet";
import { ReviewDialog } from "./ReviewDialog";
import { FixedVersionDialog, PublishPlaylistDialog } from "./SmallRequestDialogs";
import { SuggestChangeDialog, type ChangeTarget } from "./SuggestChangeDialog";
import { COUNTS_EVENT, DECISION_LABEL, KIND_LABEL, STATUS_LABEL } from "./words";

/** Who asks for what, in one line: "wants to publish “easy” of 7 Years". */
function asking(detail: RequestDetail): string {
  switch (detail.kind) {
    case "userVersion":
      return `wants to publish “${detail.subject}” of ${detail.title}`;
    case "fixedVersion":
      return `asks for ${detail.subject} on ${detail.title}`;
    case "playlist":
      return `wants to publish the playlist ${detail.title}`;
    case "metadata":
      return detail.subject === "new song"
        ? `proposes the song ${detail.title}`
        : detail.subject === "new artist"
          ? `proposes the artist ${detail.title}`
          : `suggests changes to ${detail.title}`;
  }
}

/** The status as a pill: outlined while it waits, filled once it is over. */
function StatusPill({ detail }: { detail: RequestDetail }) {
  const over = !["open", "changesAsked"].includes(detail.status);
  return (
    <Box
      component="span"
      data-testid="request-status"
      sx={(theme) => ({
        display: "inline-flex",
        alignItems: "center",
        height: 26,
        px: 1.25,
        borderRadius: 999,
        fontSize: 13,
        fontWeight: 600,
        border: 1,
        borderColor: over ? "transparent" : "text.primary",
        backgroundColor: over ? (theme.vars ?? theme).palette.text.primary : "transparent",
        color: over ? (theme.vars ?? theme).palette.background.default : "text.primary",
        flexShrink: 0,
      })}
    >
      {STATUS_LABEL[detail.status]}
    </Box>
  );
}

function SideFact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <Box sx={{ py: 1.5, borderBottom: 1, borderColor: "divider" }}>
      <Typography sx={{ fontSize: 13, color: "text.secondary", fontWeight: 600, mb: 0.5 }}>{label}</Typography>
      <Box sx={{ fontSize: 14 }}>{children}</Box>
    </Box>
  );
}

export function RequestPage() {
  const { id } = useParams();
  const requestId = Number(id);
  const { pathname } = useLocation();
  const review = pathname.startsWith(ROUTES.adminRequests);
  const base = review ? ROUTES.adminRequest(requestId) : ROUTES.request(requestId);
  const onSheet = pathname.endsWith("/sheet");
  const navigate = useNavigate();
  const { user } = useAuth();
  const [detail, setDetail] = useState<RequestDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [withdrawing, setWithdrawing] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [resending, setResending] = useState<ReactNode>(null);

  useEffect(() => {
    const controller = new AbortController();
    requestsApi
      .one(requestId, controller.signal)
      .then((found) => {
        setDetail(found);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "The request could not be loaded."));
      });
    return () => controller.abort();
  }, [requestId, reload]);

  const back = review ? { to: ROUTES.adminRequests, label: "Back to Review" } : { to: ROUTES.requests, label: "Back to Requests" };
  const sheetItem = useMemo(() => detail?.itemList.find((item) => item.compare !== null) ?? null, [detail]);

  const comment = useCallback(
    async (input: CommentInput) => {
      setActionError(null);
      try {
        setDetail(await requestsApi.comment(requestId, input));
        return true;
      } catch (caught) {
        setActionError(said(caught, "The comment could not be added."));
        return false;
      }
    },
    [requestId],
  );

  const withdraw = async () => {
    if (!detail) return;
    setBusy(true);
    setActionError(null);
    try {
      setDetail(await requestsApi.withdraw(detail.id));
      window.dispatchEvent(new Event(COUNTS_EVENT));
    } catch (caught) {
      setActionError(said(caught, "The request could not be withdrawn."));
    } finally {
      setWithdrawing(false);
      setBusy(false);
    }
  };

  const sent = useCallback(() => {
    setResending(null);
    setReload((count) => count + 1);
    window.dispatchEvent(new Event(COUNTS_EVENT));
  }, []);

  /** The dialog that sent the request, filled as it was sent. */
  const openResend = async () => {
    if (!detail) return;
    const proposal = detail.proposal;
    const resend = { requestId: detail.id, proposal };
    const close = () => setResending(null);
    setActionError(null);
    try {
      if (detail.kind === "userVersion" && proposal.version) {
        setResending(<PublishDialog versionId={proposal.version} resend={resend} onClose={close} onSent={sent} />);
      } else if (detail.kind === "fixedVersion" && proposal.userVersion) {
        const item = detail.itemList.find((one) => one.kind === "versionPointer");
        setResending(
          <FixedVersionDialog
            songTitle={text(item?.payload.songTitle)}
            version={{ projectId: proposal.userVersion, name: text(item?.payload.userVersionName) }}
            resend={resend}
            onClose={close}
            onSent={sent}
          />,
        );
      } else if (detail.kind === "playlist" && proposal.playlist) {
        setResending(<PublishPlaylistDialog playlistId={proposal.playlist} resend={resend} onClose={close} onSent={sent} />);
      } else if (detail.kind === "metadata") {
        let target: ChangeTarget = { kind: "newSong" };
        if (proposal.artist?.publicId) target = { kind: "artist", artist: await publicApi.artist(proposal.artist.publicId) };
        else if (proposal.song?.publicId) target = { kind: "song", song: await publicApi.song(proposal.song.publicId) };
        setResending(<SuggestChangeDialog target={target} resend={resend} onClose={close} onSent={sent} />);
      }
    } catch (caught) {
      setActionError(said(caught, "The request could not be opened again."));
    }
  };

  if (error) {
    return (
      <PageBody>
        <PageHeader title="Request" back={back} />
        <EmptyState message={error} action={<PillButton onClick={() => navigate(back.to)}>{back.label.replace("Back to ", "Open ")}</PillButton>} />
      </PageBody>
    );
  }

  const waiting = detail !== null && (detail.status === "open" || detail.status === "changesAsked");
  const canReview = Boolean(user?.isMaster) && detail?.status === "open";
  return (
    <PageBody wide>
      <Box sx={{ maxWidth: onSheet ? "none" : 1180, mx: "auto" }}>
        <PageHeader
          title={detail?.title || "Request"}
          back={back}
          actions={
            detail ? (
              <>
                {detail.mine && waiting ? (
                  <PillButton kind="secondary" onClick={() => setWithdrawing(true)} data-testid="withdraw">
                    Withdraw
                  </PillButton>
                ) : null}
                {detail.mine && detail.status === "changesAsked" ? (
                  <PillButton kind="primary" onClick={() => void openResend()} data-testid="resend">
                    Change and send again
                  </PillButton>
                ) : null}
                {canReview ? (
                  <PillButton kind="primary" onClick={() => setReviewing(true)} data-testid="review">
                    Review
                  </PillButton>
                ) : null}
              </>
            ) : undefined
          }
        />
        {detail === null ? (
          <Stack spacing={1.5} sx={{ pt: 1, maxWidth: 760 }} aria-busy>
            <Skeleton variant="text" width={320} />
            <Skeleton variant="rounded" height={160} />
            <Skeleton variant="rounded" height={96} />
          </Stack>
        ) : (
          <>
            <Stack direction="row" spacing={1.25} useFlexGap sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 0.5, mb: 2 }}>
              <StatusPill detail={detail} />
              <Typography sx={{ fontSize: 14, color: "text.secondary" }}>
                <Box component="span" sx={{ color: "text.primary", fontWeight: 600 }}>
                  {detail.author}
                </Box>{" "}
                {asking(detail)},{" "}
                <Tooltip title={fullTime(detail.createdAt)}>
                  <span>{relativeTime(detail.createdAt)}</span>
                </Tooltip>
              </Typography>
            </Stack>
            <TabBar
              items={[
                { label: "Conversation", to: base },
                { label: sheetItem ? "Sheet" : "Changes", to: `${base}/sheet` },
              ]}
            />
            {actionError ? (
              <Alert severity="error" onClose={() => setActionError(null)} sx={{ mt: 2 }}>
                {actionError}
              </Alert>
            ) : null}
            <Box sx={{ pt: 3 }}>
              {onSheet ? (
                sheetItem ? (
                  <RequestSheet item={sheetItem} onComment={comment} onOpenConversation={() => navigate(base)} />
                ) : (
                  <Box sx={{ maxWidth: 860 }}>
                    {detail.itemList.map((item) => (
                      <Section key={item.id} title={itemLine(item)}>
                        <ItemBody item={item} />
                      </Section>
                    ))}
                  </Box>
                )
              ) : (
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "minmax(0, 1fr)", md: "minmax(0, 1fr) 240px" },
                    gap: { xs: 3, md: 4 },
                    alignItems: "start",
                  }}
                >
                  <Conversation
                    detail={detail}
                    me={user?.username ?? ""}
                    onComment={comment}
                    onOpenSheet={() => navigate(`${base}/sheet`)}
                  />
                  <Box component="aside" aria-label="About this request" sx={{ order: { xs: -1, md: 0 } }}>
                    <SideFact label="Items">
                      <Stack spacing={0.75}>
                        {detail.itemList.map((item) => (
                          <Stack key={item.id} direction="row" spacing={1} sx={{ justifyContent: "space-between" }}>
                            <Box component="span" sx={{ minWidth: 0, overflowWrap: "anywhere" }}>
                              {itemLine(item)}
                            </Box>
                            <Box
                              component="span"
                              sx={{ flexShrink: 0, fontWeight: item.decision ? 600 : 400, color: item.decision ? "text.primary" : "text.secondary" }}
                              data-testid={`decision-${item.id}`}
                            >
                              {item.decision ? DECISION_LABEL[item.decision] : "Waiting"}
                            </Box>
                          </Stack>
                        ))}
                      </Stack>
                    </SideFact>
                    <SideFact label="Kind">{KIND_LABEL[detail.kind]}</SideFact>
                    <SideFact label="Sent">
                      {detail.author}, {relativeTime(detail.createdAt)}
                    </SideFact>
                    {detail.decidedAt ? <SideFact label="Closed">{relativeTime(detail.decidedAt)}</SideFact> : null}
                  </Box>
                </Box>
              )}
            </Box>
          </>
        )}
      </Box>

      <ConfirmDialog
        open={withdrawing}
        title="Withdraw this request?"
        message="The master user will not review it. What was already accepted stays in the Public library."
        confirmLabel="Withdraw request"
        danger
        busy={busy}
        onCancel={() => setWithdrawing(false)}
        onConfirm={() => void withdraw()}
      />
      {reviewing && detail ? (
        <ReviewDialog
          detail={detail}
          onClose={() => setReviewing(false)}
          onDecided={(answer) => {
            setDetail(answer);
            setReviewing(false);
            window.dispatchEvent(new Event(COUNTS_EVENT));
            navigate(base);
          }}
        />
      ) : null}
      {resending}
    </PageBody>
  );
}

export default RequestPage;
