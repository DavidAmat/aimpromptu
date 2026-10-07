/** What the pages of My library share: the words of a refused request, and a download link. */

import { ApiError } from "../../api";

/** The backend's own words for a refusal ("This song already has a version named …"). */
export const said = (caught: unknown, fallback: string) =>
  caught instanceof ApiError ? caught.detail : caught instanceof Error ? caught.message : fallback;

/** The browser saves the file of a link; the session cookie goes with it. */
export function download(url: string) {
  const link = document.createElement("a");
  link.href = url;
  link.download = "";
  document.body.appendChild(link);
  link.click();
  link.remove();
}
