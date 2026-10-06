/**
 * **Sign in** (`/login`): the logo, Username, Password, Sign in. Nothing else (implementation 02,
 * plan section 9.2). There is no sign-up and no "forgot password": the master user makes the users
 * and resets a password in Admin → Users.
 *
 * After five wrong passwords in a minute the backend answers more slowly; the button shows that it
 * is working, so a slow answer does not look like a frozen page.
 */

import { useState, type FormEvent } from "react";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { ApiError } from "../api";
import { ROUTES } from "../layout/routes";
import { useAuth } from "../state/authContext";
import { PillButton } from "../ui";

/** Only an address of this app: `?next=https://elsewhere` must not send anyone away. */
function safeNext(next: string | null): string {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : ROUTES.projects;
}

export function LoginPage() {
  const { user, signIn } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (user) return <Navigate to={next} replace />;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!username.trim() || !password) return;
    setBusy(true);
    setError(null);
    try {
      await signIn(username.trim(), password);
      navigate(next, { replace: true });
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : caught instanceof Error ? caught.message : "Sign in failed.");
      setPassword("");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: "100dvh",
        display: "grid",
        placeItems: "center",
        px: 2,
        backgroundColor: "background.default",
      }}
    >
      <Box component="form" onSubmit={submit} noValidate sx={{ width: "100%", maxWidth: 340 }}>
        <Stack spacing={2.5}>
          <Stack direction="row" spacing={1.25} sx={{ mb: 1, alignItems: "center", justifyContent: "center" }}>
            <Box component="img" src="/favicon.svg" alt="" sx={{ width: 32, height: 32 }} />
            <Typography component="h1" sx={{ fontWeight: 600, fontSize: 22, letterSpacing: "-0.01em" }}>
              AImpromptu
            </Typography>
          </Stack>
          <TextField
            label="Username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            autoFocus
            fullWidth
          />
          <TextField
            label="Password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            fullWidth
          />
          {error ? (
            <Typography role="alert" sx={{ color: "error.main", fontSize: 14 }}>
              {error}
            </Typography>
          ) : null}
          <PillButton
            kind="primary"
            type="submit"
            busy={busy}
            disabled={!username.trim() || !password}
            fullWidth
          >
            Sign in
          </PillButton>
        </Stack>
      </Box>
    </Box>
  );
}

export default LoginPage;
