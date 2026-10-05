/**
 * "2 h ago", "yesterday", "3 Oct": when something changed, in the words of a list row.
 *
 * Exact to the minute within the hour, then by hours, then "yesterday", then the day and month
 * (and the year when it is not this one). The full date and time go in the row's tooltip.
 */

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function relativeTime(iso: string | null | undefined, now: Date = new Date()): string {
  if (!iso) return "–";
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return "–";
  const minutes = Math.round((now.getTime() - then.getTime()) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  if (then.getTime() >= startOfToday) return `${hours} h ago`;
  if (then.getTime() >= startOfToday - 86400000) return "yesterday";
  const day = `${then.getDate()} ${MONTHS[then.getMonth()]}`;
  return then.getFullYear() === now.getFullYear() ? day : `${day} ${then.getFullYear()}`;
}

/** The full date and time, for a tooltip. */
export function fullTime(iso: string | null | undefined): string {
  if (!iso) return "";
  const then = new Date(iso);
  return Number.isNaN(then.getTime()) ? "" : then.toLocaleString();
}
