/** Shared two-hand dense matrix and optional waveform loader for Epic 8 views. */

import { useEffect, useMemo, useState } from "react";
import { audioApi, matrixApi, type MatrixEnvelope, type WaveformPeaks } from "../api";
import { extractMatrixNotes } from "../playback/matrixNotes";
import type { WorkingArtifact } from "../state/workingArtifactContext";

interface PianoViewState {
  key: string;
  envelope: MatrixEnvelope | null;
  peaks: WaveformPeaks | null;
  error: string | null;
}

export function usePianoViewData(artifact: WorkingArtifact, revision = 0) {
  const audioUuid = artifact.audioUuid ?? null;
  const requestKey = audioUuid
    ? `${audioUuid}:${artifact.granularity}:${artifact.tempoBpm}:${revision}`
    : "";
  const [loaded, setLoaded] = useState<PianoViewState>({
    key: "",
    envelope: null,
    peaks: null,
    error: null,
  });

  useEffect(() => {
    if (!audioUuid) return;
    const controller = new AbortController();
    Promise.all([
      matrixApi.get(
        audioUuid,
        {
          step: "two-hands",
          granularity: artifact.granularity,
          tempoBpm: artifact.tempoBpm,
          sparse: false,
        },
        controller.signal,
      ),
      audioApi.waveform(audioUuid, 1400, controller.signal).catch(() => null),
    ])
      .then(([envelope, peaks]) =>
        setLoaded({ key: requestKey, envelope, peaks, error: null }),
      )
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return;
        setLoaded({
          key: requestKey,
          envelope: null,
          peaks: null,
          error: caught instanceof Error ? caught.message : "Could not load this piano view.",
        });
      });
    return () => controller.abort();
  }, [artifact.granularity, artifact.tempoBpm, audioUuid, requestKey]);

  const current =
    loaded.key === requestKey
      ? loaded
      : { key: requestKey, envelope: null, peaks: null, error: null };
  const right = useMemo(
    () => current.envelope?.denseRMatrix ?? current.envelope?.denseMatrix ?? [],
    [current.envelope],
  );
  const left = current.envelope?.denseLMatrix ?? null;
  const timeStepSeconds = current.envelope?.timeStepSeconds ?? 1;
  const notes = useMemo(
    () => extractMatrixNotes(right, left, timeStepSeconds),
    [left, right, timeStepSeconds],
  );

  return {
    audioUuid,
    envelope: current.envelope,
    peaks: current.peaks,
    error: current.error,
    loading: Boolean(audioUuid) && !current.envelope && !current.error,
    right,
    left,
    notes,
    timeStepSeconds,
    durationSeconds: right.length * timeStepSeconds,
  };
}
