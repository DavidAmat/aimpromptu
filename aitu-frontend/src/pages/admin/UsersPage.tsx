/**
 * **Admin → Users** (`/admin/users`), the master user's (implementation 02, plan sections 9.1 and
 * 16.3): every user, **New user** (a username and a first password, which the user changes from
 * their own menu), and per row **Reset password** and **Disable** / **Enable**. There is no sign-up
 * (P-7). A reset or a disable ends the user's sessions at once.
 */

import { useCallback, useEffect, useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import AddIcon from "@mui/icons-material/Add";
import BlockIcon from "@mui/icons-material/BlockOutlined";
import KeyIcon from "@mui/icons-material/KeyOutlined";
import RestoreIcon from "@mui/icons-material/SettingsBackupRestoreOutlined";
import { adminApi, ApiError, type AdminUser } from "../../api";
import {
  ConfirmDialog,
  DataTable,
  EmptyState,
  fullTime,
  PageBody,
  PageHeader,
  PillButton,
  relativeTime,
  RowMenu,
  type DataColumn,
} from "../../ui";

const MIN_PASSWORD = 8;

const said = (caught: unknown) =>
  caught instanceof ApiError ? caught.detail : caught instanceof Error ? caught.message : "It did not work.";

/** One dialog for both: a new user (username and password), or a new password for one user. */
function UserDialog({
  user,
  open,
  onClose,
  onDone,
}: {
  /** `null`: a new user. */
  user: AdminUser | null;
  open: boolean;
  onClose: () => void;
  onDone: () => void;
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /** Leaving the dialog forgets what was typed, so the next opening starts empty. */
  const reset = () => {
    setUsername("");
    setPassword("");
    setError(null);
  };
  const close = () => {
    reset();
    onClose();
  };

  const ready = password.length >= MIN_PASSWORD && (user !== null || username.trim().length >= 2);
  const submit = async () => {
    if (!ready) return;
    setBusy(true);
    setError(null);
    try {
      if (user) await adminApi.changeUser(user.id, { password });
      else await adminApi.createUser(username.trim(), password);
      reset();
      onDone();
    } catch (caught) {
      setError(said(caught));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onClose={close} fullWidth maxWidth="xs">
      <DialogTitle>{user ? `New password for ${user.username}` : "New user"}</DialogTitle>
      <DialogContent>
        <Stack
          component="form"
          spacing={2}
          sx={{ pt: 1 }}
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
        >
          {user ? null : (
            <TextField
              label="Username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="off"
              autoFocus
              helperText="Letters, digits, dots, dashes; no space"
            />
          )}
          <TextField
            label={user ? "New password" : "First password"}
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="new-password"
            autoFocus={user !== null}
            helperText={`At least ${MIN_PASSWORD} characters; the user changes it from their menu`}
          />
          {error ? (
            <Typography role="alert" sx={{ color: "error.main", fontSize: 14 }}>
              {error}
            </Typography>
          ) : null}
          <button type="submit" hidden />
        </Stack>
      </DialogContent>
      <DialogActions>
        <PillButton onClick={close}>Cancel</PillButton>
        <PillButton kind="primary" busy={busy} disabled={!ready} onClick={() => void submit()}>
          {user ? "Set the password" : "Create user"}
        </PillButton>
      </DialogActions>
    </Dialog>
  );
}

export function UsersPage() {
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [editing, setEditing] = useState<{ user: AdminUser | null } | null>(null);
  const [disabling, setDisabling] = useState<AdminUser | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    adminApi
      .users(controller.signal)
      .then((list) => {
        setUsers(list);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught));
      });
    return () => controller.abort();
  }, [reload]);

  const refresh = useCallback(() => setReload((value) => value + 1), []);

  const setDisabled = async (user: AdminUser, disabled: boolean) => {
    setBusy(true);
    setActionError(null);
    try {
      await adminApi.changeUser(user.id, { disabled });
      setDisabling(null);
      refresh();
    } catch (caught) {
      setActionError(said(caught));
    } finally {
      setBusy(false);
    }
  };

  const columns: DataColumn<AdminUser>[] = [
    {
      key: "username",
      label: "Username",
      render: (user) => (
        <Typography noWrap sx={{ fontSize: 14, fontWeight: 500 }} title={user.username}>
          {user.username}
        </Typography>
      ),
      sortValue: (user) => user.username.toLowerCase(),
    },
    {
      key: "role",
      label: "Role",
      width: 120,
      render: (user) => (user.role === "master" ? "Master user" : "User"),
      sortValue: (user) => user.role,
    },
    {
      key: "status",
      label: "Status",
      width: 140,
      render: (user) => (user.disabled ? "Disabled" : user.hasPassword ? "Active" : "No password yet"),
      sortValue: (user) => (user.disabled ? 1 : 0),
    },
    {
      key: "created",
      label: "Created",
      width: 120,
      align: "right",
      render: (user) => <span title={fullTime(user.createdAt)}>{relativeTime(user.createdAt)}</span>,
      sortValue: (user) => user.createdAt,
    },
    {
      key: "menu",
      label: "",
      width: 56,
      align: "right",
      render: (user) => (
        <RowMenu
          title={`Actions for ${user.username}`}
          items={[
            {
              label: "Reset password",
              icon: <KeyIcon fontSize="small" />,
              onClick: () => setEditing({ user }),
            },
            user.disabled
              ? {
                  label: "Enable",
                  icon: <RestoreIcon fontSize="small" />,
                  onClick: () => void setDisabled(user, false),
                }
              : {
                  label: "Disable",
                  icon: <BlockIcon fontSize="small" />,
                  danger: true,
                  disabled: user.role === "master",
                  onClick: () => setDisabling(user),
                },
          ]}
        />
      ),
    },
  ];

  return (
    <PageBody>
      <PageHeader
        title="Users"
        actions={
          <PillButton kind="primary" startIcon={<AddIcon />} onClick={() => setEditing({ user: null })}>
            New user
          </PillButton>
        }
      />
      {error ? (
        <EmptyState
          message={`The users could not be loaded: ${error}`}
          action={<PillButton onClick={refresh}>Try again</PillButton>}
        />
      ) : users === null ? (
        <Stack spacing={1}>
          {[0, 1, 2].map((row) => (
            <Skeleton key={row} variant="rounded" height={40} />
          ))}
        </Stack>
      ) : (
        <DataTable
          columns={columns}
          rows={users}
          rowKey={(user) => String(user.id)}
          initialSort={{ key: "username", direction: "asc" }}
        />
      )}
      {actionError ? (
        <Typography role="alert" sx={{ color: "error.main", fontSize: 14, mt: 1 }}>
          {actionError}
        </Typography>
      ) : null}
      <UserDialog
        user={editing?.user ?? null}
        open={editing !== null}
        onClose={() => setEditing(null)}
        onDone={() => {
          setEditing(null);
          refresh();
        }}
      />
      <ConfirmDialog
        open={disabling !== null}
        title={`Disable ${disabling?.username ?? ""}?`}
        message="They are signed out at once and cannot sign in until you enable them again. Their projects stay."
        confirmLabel={`Disable ${disabling?.username ?? ""}`}
        danger
        busy={busy}
        onConfirm={() => disabling && void setDisabled(disabling, true)}
        onCancel={() => setDisabling(null)}
      />
    </PageBody>
  );
}

export default UsersPage;
