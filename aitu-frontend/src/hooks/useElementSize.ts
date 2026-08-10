/**
 * The rendered pixel size of an element, kept current.
 *
 * Both animated views draw into an SVG that used to declare a viewBox in
 * keyboard units and stretch it with `preserveAspectRatio="none"`. That is fine
 * for rectangles and fatal for text: the two axes scale by different factors, so
 * every note name came out squashed one way and stretched the other, and no
 * choice of font size could fix it.
 *
 * Measuring instead lets the views use a viewBox of real pixels — one unit is one
 * pixel on both axes, text is undrawn-distorted, and a stroke width of 2 is
 * actually 2. Lane positions become fractions of the measured box, which is also
 * how the keyboard SVG beside them scales, so the two still line up exactly.
 */

import { useCallback, useLayoutEffect, useRef, useState } from "react";

export interface ElementSize {
  width: number;
  height: number;
}

export function useElementSize<T extends HTMLElement>() {
  const [size, setSize] = useState<ElementSize>({ width: 0, height: 0 });
  const nodeRef = useRef<T | null>(null);

  // A callback ref rather than an object ref: the element arrives on mount and can
  // be replaced by a re-render, and only a callback is told about both.
  const ref = useCallback((node: T | null) => {
    nodeRef.current = node;
  }, []);

  useLayoutEffect(() => {
    const node = nodeRef.current;
    if (!node) return;
    const observer = new ResizeObserver(([entry]) => {
      if (!entry) return;
      const { width, height } = entry.contentRect;
      setSize((current) =>
        // Sub-pixel churn from a scrollbar appearing would otherwise re-render
        // the whole note list on every frame.
        Math.abs(current.width - width) < 0.5 && Math.abs(current.height - height) < 0.5
          ? current
          : { width, height },
      );
    });
    observer.observe(node);
    return () => observer.disconnect();
  });

  return [ref, size] as const;
}

export default useElementSize;
