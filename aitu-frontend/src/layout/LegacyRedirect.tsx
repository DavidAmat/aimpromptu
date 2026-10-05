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
  return <Navigate to={`${target}${search}`} replace />;
}

export default LegacyRedirect;
