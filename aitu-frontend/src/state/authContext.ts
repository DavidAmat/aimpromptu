/**
 * Who is signed in (implementation 02, Phase 4). `AuthProvider` fills it; `useAuth` reads it.
 *
 * `user` is `undefined` while the page asks the backend, `null` when nobody is signed in.
 */

import { createContext, useContext } from "react";
import type { Me } from "../api";

export interface AuthState {
  user: Me | null | undefined;
  /** Sign in; answers the user, or throws the backend's sentence. */
  signIn: (username: string, password: string) => Promise<Me>;
  signOut: () => Promise<void>;
}

export const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const state = useContext(AuthContext);
  if (!state) throw new Error("useAuth needs an <AuthProvider> above it");
  return state;
}
