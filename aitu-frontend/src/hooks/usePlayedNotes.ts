/**
 * The one loader behind Piano Roll and Notes Falling.
 *
 * It asks for two things: the notes as the engine heard them, and the waveform
 * of the recording they came from. The waveform is optional — it is a watermark
 * on the roll and the reason the "Original audio" button can be offered — so a
 * failure there is swallowed rather than failing the view.
 *
 * The Epic 8 version of this hook took the tempo and the resolution as part of
 * its cache key, because changing either produced a different matrix. Neither
 * exists here. `frameMs` is the key instead, and it changes one thing only:
 * which hand each note is labelled with.
 */

import { useEffect, useMemo, useState } from "react";
import { audioApi, matrixApi, type RawEvents, type WaveformPeaks } from "../api";
import { playedNotesOf, type PlayedNote } from "../playback/playedNotes";
import type { WorkingArtifact } from "../state/workingArtifactContext";

interface LoadedState {
  key: string;
  events: RawEvents | null;
  peaks: WaveformPeaks | null;
  error: string | null;
}

const EMPTY: PlayedNote[] = [];

export function usePlayedNotes(artifact: WorkingArtifact, revision = 0) {
  const audioUuid = artifact.audioUuid ?? null;
  const requestKey = audioUuid ? `${audioUuid}:${artifact.frameMs}:${revision}` : "";
  const [loaded, setLoaded] = useState<LoadedState>({
    key: "",
    events: null,
    peaks: null,
    error: null,
  });

  useEffect(() => {
    if (!audioUuid) return;
    const controller = new AbortController();
    Promise.all([
      matrixApi.events(audioUuid, artifact.frameMs, controller.signal),
      audioApi.waveform(audioUuid, 1400, controller.signal).catch(() => null),
    ])
      .then(([events, peaks]) => setLoaded({ key: requestKey, events, peaks, error: null }))
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return;
        setLoaded({
          key: requestKey,
          events: null,
          peaks: null,
          error:
            caught instanceof Error
              ? caught.message
              : "The recorded notes for this piece could not be loaded.",
        });
      });
    return () => controller.abort();
  }, [artifact.frameMs, audioUuid, requestKey]);

  // A response from the previous key is not shown against the new one: a stale
  // set of rectangles under a fresh caption is worse than an empty view.
  const current =
    loaded.key === requestKey ? loaded : { key: requestKey, events: null, peaks: null, error: null };

  const notes = useMemo(
    () => (current.events ? playedNotesOf(current.events.events) : EMPTY),
    [current.events],
  );

  return {
    audioUuid,
    events: current.events,
    peaks: current.peaks,
    error: current.error,
    loading: Boolean(audioUuid) && !current.events && !current.error,
    notes,
    artifactCount: current.events?.artifactCount ?? 0,
    durationSeconds: current.events?.durationSeconds ?? 0,
  };
}

export default usePlayedNotes;
