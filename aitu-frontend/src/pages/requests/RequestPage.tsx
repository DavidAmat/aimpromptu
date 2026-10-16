/**
 * **One request** (implementation 02, Phase 14, plan sections 16.2 and 16.3). The same page for its
 * author (`/requests/:id`) and for the master user's review (`/admin/requests/:id`).
 *
 * The page lists the request's items, one per proposed change, each with what it proposes and its
 * decision: a new artist (its name), a new song (its fields), a change of metadata (each field now
 * and proposed, the changed ones in bold), a piano sheet or a fixed version (**side by side**, the
 * version now and the proposal, both read-only sheets that play), a playlist (its songs). Then the
 * notes of the author and of the master user.
 *
 * - **The author**: **Withdraw** while it waits; **Change and send again** when changes are asked,
 *   which opens the dialog that sent it, filled as it was.
 * - **The review** (the master user, an open request): each item waiting gets **Accept**, **Ask for
 *   a change** or **Refuse**, with a comment; on **Accept** the name can be changed ("Accept as").
 *   **Send decision** writes everything accepted at once. An item cannot be accepted without what
 *   it needs (a song without its new artist): the backend says so.
 */

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Link from "@mui/material/Link";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { Link as RouterLink, useLocation, useNavigate, useParams } from "react-router-dom";
import {
  publicApi,
  requestsApi,
  type ArtistInRequest,
  type ItemDecisionValue,
  type ItemKind,
  type RequestDetail,
  type RequestItem,
  type SongState,
} from "../../api";
import { ROUTES } from "../../layout/routes";
import { ConfirmDialog, EmptyState, fullTime, PageBody, PageHeader, PillButton, relativeTime, Section, Segmented } from "../../ui";
import { said } from "../library/shared";
import { CompareSheets } from "./CompareSheets";
import { PublishDialog } from "./PublishDialog";
import { FixedVersionDialog, PublishPlaylistDialog } from "./SmallRequestDialogs";
import { tagWord } from "./songDraft";
import { SuggestChangeDialog, type ChangeTarget } from "./SuggestChangeDialog";
import { COUNTS_EVENT, DECISION_LABEL, ITEM_LABEL, KIND_LABEL, nameLabel, NAME_RULE, STATUS_LABEL, validName } from "./words";

/** The name the master user may change on accepting, by item kind: `[payload field, label]`. */
const EDITABLE: Partial<Record<ItemKind, [string, string]>> = {
  newArtist: ["name", "Accept with the name"],
  newSong: ["title", "Accept with the title"],
  project: ["versionName", "Accept with the version name"],
  versionPointer: ["name", "Accept with the name"],
  playlist: ["title", "Accept with the title"],
};

interface Draft {
  decision: ItemDecisionValue | "";
  comment: string;
  /** The value of the editable field, when it is changed. */
  value: string | null;
}

const text = (value: unknown) => (typeof value === "string" ? value : value === null || value === undefined ? "" : String(value));

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <Box sx={{ minWidth: 0 }}>
      <Typography sx={{ fontSize: 13, color: "text.secondary" }}>{label}</Typography>
      <Typography component="div" sx={{ fontSize: 15, overflowWrap: "anywhere" }}>
        {children}
      </Typography>
    </Box>
  );
}

function Facts({ children }: { children: ReactNode }) {
  return (
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "repeat(2, minmax(0, 1fr))", sm: "repeat(auto-fill, minmax(170px, 1fr))" }, gap: 2, maxWidth: 760 }}>
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
        maxWidth: 760,
        fontSize: 14,
        "& th, & td": { textAlign: "left", py: 0.75, pr: 2, verticalAlign: "top", borderBottom: 1, borderColor: "divider" },
        "& th": { fontWeight: 500, color: "text.secondary", fontSize: 13 },
      }}
    >
      <thead>
        <tr>
          <th style={{ width: 96 }} />
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

function ItemBody({ item }: { item: RequestItem }) {
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
        <Stack spacing={2}>
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
          </Facts>
          {item.compare ? <CompareSheets current={item.compare.current} proposed={item.compare.proposed} /> : null}
        </Stack>
      );
    }
    case "versionPointer":
      return (
        <Stack spacing={2}>
          <Facts>
            <Fact label="Song">
              <Link component={RouterLink} to={ROUTES.publicSong(Number(payload.songId))} color="inherit">
                {text(payload.songTitle)}
              </Link>
            </Fact>
            <Fact label="Version">“{text(payload.userVersionName)}”</Fact>
            <Fact label="As">{nameLabel(text(payload.name))}</Fact>
          </Facts>
          {item.compare ? (
            <CompareSheets
              current={item.compare.current}
              proposed={item.compare.proposed}
              empty={`The song has no ${nameLabel(text(payload.name))} version yet`}
            />
          ) : null}
        </Stack>
      );
    case "playlist": {
      const songs = (payload.items as { title: string; versionName: string | null }[] | undefined) ?? [];
      const left = (payload.left as string[] | undefined) ?? [];
      return (
        <Stack spacing={1.5} sx={{ maxWidth: 760 }}>
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
          {left.length > 0 ? (
            <Typography sx={{ fontSize: 14, color: "text.secondary" }}>Left out: {left.join(", ")}</Typography>
          ) : null}
        </Stack>
      );
    }
  }
}

/** The master user's decision on one waiting item. */
function DecisionControls({
  item,
  draft,
  onChange,
}: {
  item: RequestItem;
  draft: Draft;
  onChange: (next: Draft) => void;
}) {
  const editable = EDITABLE[item.kind];
  const initial = editable ? text(item.payload[editable[0]]) : "";
  const value = draft.value ?? initial;
  const nameField = item.kind === "project" || item.kind === "versionPointer";
  return (
    <Stack spacing={1.5} sx={{ maxWidth: 560, pt: 1 }} data-testid={`decide-${item.id}`}>
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
          onChange={(event) => onChange({ ...draft, value: nameField ? event.target.value.toLowerCase().replace(/\s/g, "-") : event.target.value })}
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

export function RequestPage() {
  const { id } = useParams();
  const requestId = Number(id);
  const { pathname } = useLocation();
  const review = pathname.startsWith(ROUTES.adminRequests);
  const navigate = useNavigate();
  const [detail, setDetail] = useState<RequestDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [drafts, setDrafts] = useState<Record<number, Draft>>({});
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [withdrawing, setWithdrawing] = useState(false);
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
  const waiting = useMemo(() => detail?.itemList.filter((item) => item.decision === null) ?? [], [detail]);
  const deciding = review && detail?.status === "open";
  const draftOf = (item: RequestItem): Draft => drafts[item.id] ?? { decision: "", comment: "", value: null };
  const complete = waiting.every((item) => {
    const draft = draftOf(item);
    if (!draft.decision) return false;
    if (draft.decision === "changesAsked" && !draft.comment.trim()) return false;
    const editable = EDITABLE[item.kind];
    if (draft.decision === "accepted" && editable && draft.value !== null) {
      const nameField = item.kind === "project" || item.kind === "versionPointer";
      return nameField ? validName(draft.value) : draft.value.trim().length > 0;
    }
    return true;
  });

  const decide = async () => {
    if (!detail) return;
    setBusy(true);
    setActionError(null);
    try {
      const answer = await requestsApi.decide(
        detail.id,
        waiting.map((item) => {
          const draft = draftOf(item);
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
      setDetail(answer);
      setDrafts({});
      setNote("");
      window.dispatchEvent(new Event(COUNTS_EVENT));
    } catch (caught) {
      setActionError(said(caught, "The decision could not be sent."));
    } finally {
      setBusy(false);
    }
  };

  const withdraw = async () => {
    if (!detail) return;
    setBusy(true);
    setActionError(null);
    try {
      setDetail(await requestsApi.withdraw(detail.id));
      setWithdrawing(false);
      window.dispatchEvent(new Event(COUNTS_EVENT));
    } catch (caught) {
      setActionError(said(caught, "The request could not be withdrawn."));
      setWithdrawing(false);
    } finally {
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

  const waitingForAuthor = detail?.mine && (detail.status === "open" || detail.status === "changesAsked");
  return (
    <PageBody wide>
      <PageHeader
        title={detail?.title || "Request"}
        back={back}
        actions={
          detail && !review ? (
            <>
              {waitingForAuthor ? (
                <PillButton kind="secondary" onClick={() => setWithdrawing(true)} data-testid="withdraw">
                  Withdraw
                </PillButton>
              ) : null}
              {detail.mine && detail.status === "changesAsked" ? (
                <PillButton kind="primary" onClick={() => void openResend()} data-testid="resend">
                  Change and send again
                </PillButton>
              ) : null}
            </>
          ) : undefined
        }
      />
      {detail === null ? (
        <Stack spacing={1.5} sx={{ pt: 1, maxWidth: 760 }} aria-busy>
          <Skeleton variant="text" width={260} />
          <Skeleton variant="rounded" height={96} />
          <Skeleton variant="rounded" height={240} />
        </Stack>
      ) : (
        <Box sx={{ pt: 0.5 }}>
          <Stack direction="row" spacing={2} sx={{ alignItems: "baseline", flexWrap: "wrap", rowGap: 0.5, mb: 3 }}>
            <Typography sx={{ fontSize: 15, fontWeight: 600 }} data-testid="request-status">
              {STATUS_LABEL[detail.status]}
            </Typography>
            <Tooltip title={fullTime(detail.createdAt)}>
              <Typography sx={{ fontSize: 14, color: "text.secondary" }}>
                {KIND_LABEL[detail.kind]} request by {detail.author}, sent {relativeTime(detail.createdAt)}
              </Typography>
            </Tooltip>
          </Stack>
          {actionError ? (
            <Alert severity="error" onClose={() => setActionError(null)} sx={{ mb: 2, maxWidth: 760 }}>
              {actionError}
            </Alert>
          ) : null}

          {detail.itemList.map((item) => (
            // Text items keep the width of a page of lists; an item with sheets takes the window.
            <Box key={item.id} sx={{ maxWidth: item.compare ? "none" : 960 }}>
              <Section
                title={ITEM_LABEL[item.kind]}
                actions={
                  item.decision ? (
                    <Typography sx={{ fontSize: 14, fontWeight: 600 }} data-testid={`decision-${item.id}`}>
                      {DECISION_LABEL[item.decision]}
                    </Typography>
                  ) : deciding ? null : (
                    <Typography sx={{ fontSize: 14, color: "text.secondary" }}>Waiting</Typography>
                  )
                }
              >
                <Stack spacing={1.5}>
                  <ItemBody item={item} />
                  {item.comment ? (
                    <Typography sx={{ fontSize: 14, maxWidth: 760 }}>
                      <Box component="span" sx={{ color: "text.secondary" }}>
                        Reviewer:{" "}
                      </Box>
                      {item.comment}
                    </Typography>
                  ) : null}
                  {deciding && item.decision === null ? (
                    <DecisionControls
                      item={item}
                      draft={draftOf(item)}
                      onChange={(next) => setDrafts((current) => ({ ...current, [item.id]: next }))}
                    />
                  ) : null}
                </Stack>
              </Section>
            </Box>
          ))}

          {detail.comments.length > 0 ? (
            <Section title="Notes">
              <Stack spacing={1.5} sx={{ maxWidth: 760 }}>
                {detail.comments.map((comment, index) => (
                  <Box key={index}>
                    <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
                      {comment.author}, {relativeTime(comment.createdAt)}
                    </Typography>
                    <Typography sx={{ fontSize: 15, whiteSpace: "pre-line" }}>{comment.body}</Typography>
                  </Box>
                ))}
              </Stack>
            </Section>
          ) : null}

          {deciding ? (
            <Section title="Decision">
              <Stack spacing={2} sx={{ maxWidth: 560 }}>
                <TextField
                  label="Note for the author"
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  multiline
                  maxRows={4}
                  slotProps={{ htmlInput: { maxLength: 2000 } }}
                />
                <Box>
                  <Tooltip title={complete ? "" : "Decide every item first"}>
                    <span>
                      <PillButton kind="primary" onClick={() => void decide()} disabled={!complete} busy={busy} data-testid="send-decision">
                        Send decision
                      </PillButton>
                    </span>
                  </Tooltip>
                </Box>
              </Stack>
            </Section>
          ) : null}
        </Box>
      )}

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
      {resending}
    </PageBody>
  );
}

export default RequestPage;
