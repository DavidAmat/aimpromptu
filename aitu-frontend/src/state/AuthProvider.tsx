/**
 * Asks the backend who is signed in when the page opens, and forgets it when any request answers
 * **401** (`SIGNED_OUT_EVENT` of `api/client.ts`): the session ended elsewhere, a password was
 * reset, or 30 days passed. The guards of `layout/RequireUser.tsx` then open the sign-in page.
 */

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { ApiError, authApi, SIGNED_OUT_EVENT, type Me } from "../api";
import { AuthContext, type AuthState } from "./authContext";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null | undefined>(undefined);

  useEffect(() => {
    const controller = new AbortController();
    authApi
      .me(controller.signal)
      .then(setUser)
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return;
        // 401: nobody is signed in. Anything else (the backend is down) also opens the sign-in page,
        // which says what is wrong when the user tries.
        setUser(null);
        if (!(caught instanceof ApiError)) console.warn("Could not ask who is signed in", caught);
      });
    const signedOut = () => setUser(null);
    window.addEventListener(SIGNED_OUT_EVENT, signedOut);
    return () => {
      controller.abort();
      window.removeEventListener(SIGNED_OUT_EVENT, signedOut);
    };
  }, []);

  const signIn = useCallback(async (username: string, password: string) => {
    const me = await authApi.login(username, password);
    setUser(me);
    return me;
  }, []);

  const signOut = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setUser(null);
    }
  }, []);

  const value = useMemo<AuthState>(() => ({ user, signIn, signOut }), [user, signIn, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
