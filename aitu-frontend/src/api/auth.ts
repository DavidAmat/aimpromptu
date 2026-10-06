/**
 * `/auth`: sign in, sign out, who am I, change my password (implementation 02, plan section 9.2).
 * The session is an `HttpOnly` cookie the browser keeps and sends by itself; no script reads it.
 */

import { request } from "./client";

export interface Me {
  id: number;
  username: string;
  role: "master" | "user";
  isMaster: boolean;
}

export const authApi = {
  me: (signal?: AbortSignal) => request<Me>("/auth/me", { signal }),
  login: (username: string, password: string) =>
    request<Me>("/auth/login", { method: "POST", body: { username, password } }),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  changePassword: (current: string, next: string) =>
    request<void>("/auth/password", { method: "PUT", body: { current, new: next } }),
};
