import { useId, useState } from "react";
import { KEY_SIGNATURES } from "../music/notes";
import type { MatrixScore } from "../music/types";
import {
  DEFAULT_LYRICS_FONT_SIZE,
  DEFAULT_LYRICS_GAP,
  DEFAULT_PX_PER_NOTE,
  LayoutControls,
} from "./LayoutControls";
import { PianoSheet } from "./PianoSheet";

type SequenceComposerProps = {
  apiBase: string;
};

const DEFAULT_SEQUENCE = `*Do-4 || *Mi-4
*Re-4
Re-4
*Mi-4
Mi-4
Mi-4
Mi-4
*Fa#-5
*Fa#-5
*Sol#-5
*Fa#-5`;

const DEFAULT_LEFT_SEQUENCE = `*Do-3 || *Mi-3
*Re-3
Re-3
*Mi-3
Mi-3
Mi-3
Mi-3
*Fa#-4
*Fa#-4
*Fa#-4
*Fa#-4`;

const DEFAULT_LYRICS = `Ho
la
la
dron


de

paz`;

/** One frame per line. A blank line is a silent frame (""). */
function parseFrames(text: string): string[] {
  const lines = text.replace(/\r\n/g, "\n").split("\n").map((l) => l.trim());
  while (lines.length > 0 && lines[lines.length - 1] === "") lines.pop();
  return lines;
}

export function SequenceComposer({ apiBase }: SequenceComposerProps) {
  const titleId = useId();
  const tempoId = useId();
  const stepId = useId();
  const seqId = useId();
  const leftSeqId = useId();
  const lyricsId = useId();
  const keyId = useId();

  const [title, setTitle] = useState("My passage");
  const [tempoBpm, setTempoBpm] = useState(60);
  const [timeStepSeconds, setTimeStepSeconds] = useState(0.5);
  const [keySignature, setKeySignature] = useState(KEY_SIGNATURES[0].vex);
  const [sequenceText, setSequenceText] = useState(DEFAULT_SEQUENCE);
  // Optional left hand. Empty = one hand (treble only). Non-empty = two
  // hands: the sequence above is the right hand (treble), this is the left
  // hand, always rendered on the bass clef. Must have the same frame count.
  const [leftSequenceText, setLeftSequenceText] = useState(DEFAULT_LEFT_SEQUENCE);
  const [lyricsText, setLyricsText] = useState(DEFAULT_LYRICS);

  // The composed passage has its own layout controls, independent of the
  // controls that style the loaded scores above.
  const [pxPerNote, setPxPerNote] = useState(DEFAULT_PX_PER_NOTE);
  const [lyricsGap, setLyricsGap] = useState(DEFAULT_LYRICS_GAP);
  const [lyricsFontSize, setLyricsFontSize] = useState(DEFAULT_LYRICS_FONT_SIZE);

  const [score, setScore] = useState<MatrixScore | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleRender() {
    setBusy(true);
    setError(null);
    try {
      const sequence = parseFrames(sequenceText);
      if (sequence.length === 0) {
        throw new Error("Add at least one time frame.");
      }
      const lyrics = lyricsText.trim() ? parseFrames(lyricsText) : undefined;
      const leftSequence = leftSequenceText.trim()
        ? parseFrames(leftSequenceText)
        : undefined;
      if (leftSequence && leftSequence.length !== sequence.length) {
        throw new Error(
          `Right and left hand must have the same number of frames ` +
            `(${sequence.length} vs ${leftSequence.length}).`,
        );
      }

      const res = await fetch(`${apiBase}/sequence`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title.trim() || undefined,
          tempoBpm,
          timeStepSeconds,
          keySignature,
          sequence,
          leftSequence,
          lyrics,
        }),
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(`Backend rejected the sequence (${res.status}): ${detail}`);
      }
      setScore((await res.json()) as MatrixScore);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not build the sequence");
      setScore(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="sequence-composer" aria-label="Compose a custom passage">
      <h2>Compose a passage</h2>
      <p className="spacing-hint">
        One time frame per line. Prefix a note with <code>*</code> to{" "}
        <strong>strike</strong> it (an onset); the same note without{" "}
        <code>*</code> on later lines <strong>sustains</strong> it into one
        longer note. Use <code>||</code> for simultaneous notes and an empty
        line for a silent frame. So <code>*Re-4</code> then <code>Re-4</code>{" "}
        is one 2-frame note, while <code>*Re-4</code> then <code>*Re-4</code>{" "}
        is two struck notes. Fill the <strong>Left hand</strong> box to get
        two hands: it renders on the <strong>bass clef</strong> below the
        right hand and must have the same number of frames.
      </p>

      <div className="spacing-control-row">
        <label htmlFor={titleId}>Title</label>
        <input
          id={titleId}
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <label htmlFor={tempoId}>Tempo (BPM)</label>
        <input
          id={tempoId}
          type="number"
          min={1}
          step={1}
          value={tempoBpm}
          onChange={(e) => setTempoBpm(Number(e.target.value) || 1)}
        />
        <label htmlFor={stepId}>Time step (s)</label>
        <input
          id={stepId}
          type="number"
          min={0.01}
          step={0.05}
          value={timeStepSeconds}
          onChange={(e) => setTimeStepSeconds(Number(e.target.value) || 0.5)}
        />
        <label htmlFor={keyId}>Key signature</label>
        <select
          id={keyId}
          value={keySignature}
          onChange={(e) => setKeySignature(e.target.value)}
        >
          {KEY_SIGNATURES.map(({ label, accidentals, vex }) => (
            <option key={vex} value={vex}>
              {label}
              {accidentals ? ` (${accidentals})` : ""}
            </option>
          ))}
        </select>
      </div>

      <div className="sequence-grid">
        <div>
          <label htmlFor={seqId}>Right hand — treble (one frame per line)</label>
          <textarea
            id={seqId}
            rows={10}
            spellCheck={false}
            value={sequenceText}
            onChange={(e) => setSequenceText(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor={leftSeqId}>Left hand — bass clef (optional)</label>
          <textarea
            id={leftSeqId}
            rows={10}
            spellCheck={false}
            placeholder={"leave empty for one hand\n*Do-2\nDo-2\n…"}
            value={leftSequenceText}
            onChange={(e) => setLeftSequenceText(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor={lyricsId}>Lyrics (optional, one per line)</label>
          <textarea
            id={lyricsId}
            rows={10}
            spellCheck={false}
            placeholder={"Ho\nla\n…"}
            value={lyricsText}
            onChange={(e) => setLyricsText(e.target.value)}
          />
        </div>
      </div>

      <button type="button" onClick={handleRender} disabled={busy}>
        {busy ? "Rendering…" : "Render passage"}
      </button>

      {error !== null ? (
        <p className="score-load-error" aria-live="polite">
          {error}
        </p>
      ) : null}

      {score !== null ? (
        <div className="score-section">
          {score.title ? <h3 className="score-title">{score.title}</h3> : null}
          <LayoutControls
            pxPerNote={pxPerNote}
            lyricsGap={lyricsGap}
            lyricsFontSize={lyricsFontSize}
            onPxPerNoteChange={setPxPerNote}
            onLyricsGapChange={setLyricsGap}
            onLyricsFontSizeChange={setLyricsFontSize}
          />
          <PianoSheet
            score={score}
            pxPerNote={pxPerNote}
            lyricsGap={lyricsGap}
            lyricsFontSize={lyricsFontSize}
          />
        </div>
      ) : null}
    </section>
  );
}
