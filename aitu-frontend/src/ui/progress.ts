/**
 * The width of a progress bar that stands on its own.
 *
 * A bar across the whole page of a wide screen is hard to read: the eye has to travel a metre to
 * see how far it is. A bar that belongs to something wide (the bar under the piano roll
 * visualization, which is also its time axis) keeps that width; every other one takes this.
 */
export const PROGRESS_MAX_WIDTH = 520;

export const progressSx = { width: "100%", maxWidth: PROGRESS_MAX_WIDTH } as const;
