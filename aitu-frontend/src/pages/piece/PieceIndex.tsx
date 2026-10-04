/**
 * `/piece`, the **Piece** entry of the top bar: back to the working piece, or to a new one.
 *
 * The working piece is the one the Playground tabs share, so moving between the Playground and the
 * flow page keeps the same piece in front of the reader.
 */

import { Navigate } from "react-router-dom";
import { ROUTES } from "../../layout/routes";
import { useWorkingArtifact } from "../../state/useWorkingArtifact";

export function PieceIndex() {
  const { artifact } = useWorkingArtifact();
  return (
    <Navigate to={artifact.audioUuid ? ROUTES.piece(artifact.audioUuid) : ROUTES.pieceNew} replace />
  );
}

export default PieceIndex;
