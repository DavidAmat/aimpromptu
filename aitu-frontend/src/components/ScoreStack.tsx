import { PianoSheet } from "./PianoSheet";
import type { MatrixScore } from "../music/types";

type ScoreStackProps = {
  scores: MatrixScore[];
  pxPerNote: number;
  lyricsGap: number;
  lyricsFontSize: number;
};

export function ScoreStack({ scores, pxPerNote, lyricsGap, lyricsFontSize }: ScoreStackProps) {
  return (
    <div className="score-stack">
      {scores.map((score, index) => (
        <section key={`${score.title ?? "score"}-${index}`} className="score-section">
          {score.title ? <h2 className="score-title">{score.title}</h2> : null}
          <PianoSheet
            score={score}
            pxPerNote={pxPerNote}
            lyricsGap={lyricsGap}
            lyricsFontSize={lyricsFontSize}
          />
        </section>
      ))}
    </div>
  );
}
