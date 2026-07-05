import { useEffect, useState } from "react";
import {
  DEFAULT_LYRICS_FONT_SIZE,
  DEFAULT_LYRICS_GAP,
  DEFAULT_PX_PER_NOTE,
  LayoutControls,
} from "./components/LayoutControls";
import { ScoreStack } from "./components/ScoreStack";
import { SequenceComposer } from "./components/SequenceComposer";
import type { MatrixScore } from "./music/types";
import "./App.css";

const matrixApiBase = (import.meta.env.VITE_AITU_API_URL ?? "http://127.0.0.1:8765").replace(/\/$/, "");

export default function App() {
  const [pxPerNote, setPxPerNote] = useState(DEFAULT_PX_PER_NOTE);
  const [lyricsGap, setLyricsGap] = useState(DEFAULT_LYRICS_GAP);
  const [lyricsFontSize, setLyricsFontSize] = useState(DEFAULT_LYRICS_FONT_SIZE);

  const [scores, setScores] = useState<MatrixScore[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadScores() {
      setLoadError(null);
      try {
        const res = await fetch(`${matrixApiBase}/scores`);
        if (!res.ok) {
          throw new Error(`Scores request failed (${res.status} ${res.statusText})`);
        }
        const data = (await res.json()) as MatrixScore[];
        if (!cancelled) {
          setScores(data);
        }
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : "Could not load scores from API";
          setLoadError(message);
          setScores(null);
        }
      }
    }

    void loadScores();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Matrix-driven notation</p>
        <h1>Professional Piano Notation MVP</h1>
        <p>
          The matrix remains the source of truth. Consecutive <code>1</code>s become duration-aware note
          events, then VexFlow renders the score with real engraving rules.
        </p>
      </section>

      <LayoutControls
        pxPerNote={pxPerNote}
        lyricsGap={lyricsGap}
        lyricsFontSize={lyricsFontSize}
        onPxPerNoteChange={setPxPerNote}
        onLyricsGapChange={setLyricsGap}
        onLyricsFontSizeChange={setLyricsFontSize}
      />

      {loadError !== null ? (
        <section className="score-load-error" aria-live="polite">
          <h2>Could not load scores</h2>
          <p>{loadError}</p>
          <p className="score-load-hint">
            Start the API from <code>aitu-backend</code>:{" "}
            <code>make serve</code> (defaults to <code>{matrixApiBase}</code>), then refresh.
          </p>
        </section>
      ) : scores === null ? (
        <p className="score-loading" aria-busy="true">
          Loading scores…
        </p>
      ) : (
        <ScoreStack
          scores={scores}
          pxPerNote={pxPerNote}
          lyricsGap={lyricsGap}
          lyricsFontSize={lyricsFontSize}
        />
      )}

      <SequenceComposer apiBase={matrixApiBase} />
    </main>
  );
}
