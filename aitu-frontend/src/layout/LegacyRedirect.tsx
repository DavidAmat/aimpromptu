/**
 * An old path, sent to its new home (`LEGACY_REDIRECTS` in `routes.ts`). The named parts and the
 * rest of the old path are carried over, and so is the query string.
 */

import { Navigate, useLocation, useParams } from "react-router-dom";

export function LegacyRedirect({ to }: { to: string }) {
  const params = useParams();
  const { search } = useLocation();
  const target = to
    .replace(/:([A-Za-z]+)/g, (_match, name: string) => params[name] ?? "")
    .replace(/\/\*$/, params["*"] ? `/${params["*"]}` : "");
  // A new home with a query of its own (Notes Falling, now a view of Play mode) keeps the old one too.
  const query = target.includes("?") && search ? `&${search.slice(1)}` : search;
  return <Navigate to={`${target}${query}`} replace />;
}

export default LegacyRedirect;
