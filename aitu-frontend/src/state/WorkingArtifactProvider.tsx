/** Provider for the shared Playground working artifact. */

import { useCallback, useMemo, useState, type ReactNode } from "react";
import {
  DEFAULT_WORKING_ARTIFACT,
  WORKING_ARTIFACT_STORAGE_KEY,
  WorkingArtifactContext,
  type WorkingArtifact,
} from "./workingArtifactContext";

function readStored(): WorkingArtifact {
  try {
    const raw = window.sessionStorage.getItem(WORKING_ARTIFACT_STORAGE_KEY);
    if (!raw) return DEFAULT_WORKING_ARTIFACT;
    const stored = JSON.parse(raw) as Partial<WorkingArtifact> & Record<string, unknown>;
    // Before physical segment artifacts existed, a temporary range lived in
    // session state and could make a later whole-file run reuse the wrong raw
    // matrix. Drop that legacy state once, on read.
    delete stored.rangeStartSeconds;
    delete stored.rangeEndSeconds;
    return { ...DEFAULT_WORKING_ARTIFACT, ...stored };
  } catch {
    return DEFAULT_WORKING_ARTIFACT;
  }
}

function persist(artifact: WorkingArtifact): void {
  try {
    window.sessionStorage.setItem(WORKING_ARTIFACT_STORAGE_KEY, JSON.stringify(artifact));
  } catch {
    // Private-mode or quota failure: the in-memory state still works.
  }
}

export function WorkingArtifactProvider({ children }: { children: ReactNode }) {
  const [artifact, setArtifact] = useState<WorkingArtifact>(readStored);

  const update = useCallback((patch: Partial<WorkingArtifact>) => {
    setArtifact((current) => {
      const next = { ...current, ...patch };
      persist(next);
      return next;
    });
  }, []);

  const replace = useCallback((next: WorkingArtifact) => {
    persist(next);
    setArtifact(next);
  }, []);

  const clear = useCallback(() => {
    persist(DEFAULT_WORKING_ARTIFACT);
    setArtifact(DEFAULT_WORKING_ARTIFACT);
  }, []);

  const value = useMemo(
    () => ({
      artifact,
      update,
      replace,
      clear,
      hasArtifact: Boolean(artifact.artifactId ?? artifact.audioUuid),
    }),
    [artifact, update, replace, clear],
  );

  return <WorkingArtifactContext value={value}>{children}</WorkingArtifactContext>;
}

export default WorkingArtifactProvider;
