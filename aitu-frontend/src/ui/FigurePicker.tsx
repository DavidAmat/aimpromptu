/**
 * The figures as a row of their icons, to pick one (plan section 7.4): the **From** and **To** of a
 * figures transposition, the figure of a note. No names on the buttons: the shape is the name, and
 * the Spanish name is in the tooltip.
 */

import type { FigureName } from "../api";
import FigureGlyph from "../components/time/FigureGlyph";
import { FIGURE_SHORT, PLAIN_FIGURES } from "../music/figures";
import Segmented from "./Segmented";

export interface FigurePickerProps {
  value: FigureName;
  onChange: (figure: FigureName) => void;
  /** What the figure is for, for a screen reader: "Transpose from". */
  label: string;
  /** The figures offered; the seven plain figures by default. */
  figures?: readonly FigureName[];
  disabled?: boolean;
}

export function FigurePicker({ value, onChange, label, figures = PLAIN_FIGURES, disabled }: FigurePickerProps) {
  return (
    <Segmented<FigureName>
      label={label}
      value={value}
      onChange={onChange}
      disabled={disabled}
      options={figures.map((figure) => ({
        value: figure,
        tooltip: FIGURE_SHORT[figure],
        icon: <FigureGlyph figure={figure} size={22} />,
      }))}
    />
  );
}

export default FigurePicker;
