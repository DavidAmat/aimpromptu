/**
 * Drag to reorder the rows of a list (implementation 02, Phase 10): the passages of From other
 * projects, the parts of a project, the songs of a playlist. `RailRow` draws a row with it.
 */

import { useState } from "react";
import type { RowDrag } from "./RailRow";

/** `[0, 1, …, count - 1]` with the item at `from` moved to `to`. */
export function movedOrder(count: number, from: number, to: number): number[] {
  const order = Array.from({ length: count }, (_, index) => index);
  const [item] = order.splice(from, 1);
  order.splice(to, 0, item);
  return order;
}

/**
 * Drag to reorder the rows of a list: `drag(index)` gives a row its handlers; a drop calls
 * `onMove(from, to)`. No drag while `disabled`, nor in a list of one.
 */
export function useRowDrag(count: number, onMove: (from: number, to: number) => void, disabled = false) {
  const [dragging, setDragging] = useState<number | null>(null);
  const [over, setOver] = useState<number | null>(null);
  return (index: number): RowDrag => ({
    row: {
      onDragOver: (event) => {
        if (dragging === null) return;
        event.preventDefault();
        setOver(index);
      },
      onDrop: (event) => {
        event.preventDefault();
        if (dragging !== null && dragging !== index) onMove(dragging, index);
        setDragging(null);
        setOver(null);
      },
    },
    handle: {
      draggable: count > 1 && !disabled,
      onDragStart: (event) => {
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", String(index));
        setDragging(index);
      },
      onDragEnd: () => {
        setDragging(null);
        setOver(null);
      },
    },
    dragging: dragging === index,
    dropMark: over === index && dragging !== null && dragging !== index ? (dragging < index ? "below" : "above") : null,
  });
}
