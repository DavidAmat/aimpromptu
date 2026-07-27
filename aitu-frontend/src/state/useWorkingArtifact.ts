/** Access the shared Playground working artifact. Throws outside its provider. */

import { useContext } from "react";
import { WorkingArtifactContext, type WorkingArtifactContextValue } from "./workingArtifactContext";

export function useWorkingArtifact(): WorkingArtifactContextValue {
  const value = useContext(WorkingArtifactContext);
  if (value === null) {
    throw new Error("useWorkingArtifact must be used inside <WorkingArtifactProvider>");
  }
  return value;
}

export default useWorkingArtifact;
