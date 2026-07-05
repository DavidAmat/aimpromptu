import { useId } from "react";

export const DEFAULT_PX_PER_NOTE = 30;
export const PX_PER_NOTE_MIN = 18;
export const PX_PER_NOTE_MAX = 120;

export const DEFAULT_LYRICS_GAP = 10;
export const LYRICS_GAP_MIN = 0;
export const LYRICS_GAP_MAX = 60;

export const DEFAULT_LYRICS_FONT_SIZE = 12;
export const LYRICS_FONT_SIZE_MIN = 8;
export const LYRICS_FONT_SIZE_MAX = 24;

type LayoutControlsProps = {
  pxPerNote: number;
  lyricsGap: number;
  lyricsFontSize: number;
  onPxPerNoteChange: (value: number) => void;
  onLyricsGapChange: (value: number) => void;
  onLyricsFontSizeChange: (value: number) => void;
};

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function readFiniteNumber(value: string): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function LayoutControls({
  pxPerNote,
  lyricsGap,
  lyricsFontSize,
  onPxPerNoteChange,
  onLyricsGapChange,
  onLyricsFontSizeChange,
}: LayoutControlsProps) {
  const spacingFieldId = useId();
  const lyricsGapFieldId = useId();
  const lyricsFontFieldId = useId();

  return (
    <section className="spacing-control" aria-label="Layout controls">
      <div className="spacing-control-row">
        <label htmlFor={spacingFieldId}>Note spacing (px per note)</label>
        <input
          id={spacingFieldId}
          type="number"
          min={PX_PER_NOTE_MIN}
          max={PX_PER_NOTE_MAX}
          step={2}
          value={pxPerNote}
          onChange={(e) => {
            const value = readFiniteNumber(e.target.value);
            if (value !== null) {
              onPxPerNoteChange(clamp(value, PX_PER_NOTE_MIN, PX_PER_NOTE_MAX));
            }
          }}
        />
      </div>
      <p className="spacing-hint">
        Each note gets this many pixels of horizontal space inside the measure.
        Range: {PX_PER_NOTE_MIN}-{PX_PER_NOTE_MAX}.
      </p>

      <div className="spacing-control-row">
        <label htmlFor={lyricsGapFieldId}>Lyrics gap (px)</label>
        <input
          id={lyricsGapFieldId}
          type="number"
          min={LYRICS_GAP_MIN}
          max={LYRICS_GAP_MAX}
          step={1}
          value={lyricsGap}
          onChange={(e) => {
            const value = readFiniteNumber(e.target.value);
            if (value !== null) {
              onLyricsGapChange(clamp(value, LYRICS_GAP_MIN, LYRICS_GAP_MAX));
            }
          }}
        />
        <label htmlFor={lyricsFontFieldId}>Lyrics font size (px)</label>
        <input
          id={lyricsFontFieldId}
          type="number"
          min={LYRICS_FONT_SIZE_MIN}
          max={LYRICS_FONT_SIZE_MAX}
          step={1}
          value={lyricsFontSize}
          onChange={(e) => {
            const value = readFiniteNumber(e.target.value);
            if (value !== null) {
              onLyricsFontSizeChange(
                clamp(value, LYRICS_FONT_SIZE_MIN, LYRICS_FONT_SIZE_MAX),
              );
            }
          }}
        />
      </div>
      <p className="spacing-hint">
        Lyric distance above the top staff line and text size. Lower gap = lyrics closer to the
        notes.
      </p>
    </section>
  );
}
