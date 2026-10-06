/**
 * The guards of the pages (implementation 02, Phase 4).
 *
 * `RequireUser` opens the sign-in page when nobody is signed in, and comes back to the same address
 * after (`?next=`). While the page asks the backend who is signed in, it draws nothing: the answer
 * takes a few milliseconds.
 *
 * `RequireMaster` shows "Page not found" to a user who is not the master user, so the address of an
 * Admin page tells them nothing. The backend refuses those routes on its own (403).
 */

import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import NotFoundPage from "../pages/NotFoundPage";
import { useAuth } from "../state/authContext";
import { ROUTES } from "./routes";

export function RequireUser({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const location = useLocation();
  if (user === undefined) return null;
  if (user === null) {
    const next = `${location.pathname}${location.search}`;
    return <Navigate to={ROUTES.signIn(next)} replace />;
  }
  return children;
}

export function RequireMaster({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  if (!user?.isMaster) return <NotFoundPage />;
  return children;
}
