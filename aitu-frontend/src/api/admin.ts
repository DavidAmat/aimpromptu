/** `/admin`: the master user's pages. Phase 4: the users (implementation 02, plan section 16.3). */

import { request } from "./client";

export interface AdminUser {
  id: number;
  username: string;
  role: "master" | "user";
  disabled: boolean;
  createdAt: string;
  hasPassword: boolean;
}

export const adminApi = {
  users: (signal?: AbortSignal) => request<AdminUser[]>("/admin/users", { signal }),
  createUser: (username: string, password: string) =>
    request<AdminUser>("/admin/users", { method: "POST", body: { username, password } }),
  changeUser: (id: number, change: { disabled?: boolean; password?: string }) =>
    request<AdminUser>(`/admin/users/${id}`, { method: "PATCH", body: change }),
};
