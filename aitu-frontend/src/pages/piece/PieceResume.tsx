/**
 * `/piece/<uuid>`: open the piece on the step it reached (plan section 7.1).
 *
 * A piece with a piano sheet opens on the Sheet tab, a piece that was only transcribed on the
 * Notes tab, a new one on the Audio tab. The backend decides which (`resume` in the status), so
 * the rule lives in one place.
 */

import { Navigate } from "react-router-dom";
import { ROUTES } from "../../layout/routes";
import { usePiece } from "./pieceContext";

export function PieceResume() {
  const { uuid, status } = usePiece();
  if (!uuid || !status) return null;
  return <Navigate to={ROUTES.piece(uuid, status.resume)} replace />;
}

export default PieceResume;
