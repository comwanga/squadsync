// Formats a wall-clock event datetime (e.g. "2026-07-15T14:00") for display.
export function formatEventDate(value?: string): string {
  if (!value) return "No date";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "No date";
  return d.toLocaleString(undefined, {
    year: "numeric", month: "short", day: "numeric",
    hour: "numeric", minute: "2-digit",
  });
}
