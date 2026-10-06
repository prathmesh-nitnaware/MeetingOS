/**
 * Shared display helpers.
 *
 * Meeting dates entered as YYYY-MM-DD are stored as midnight UTC. Formatting those in the
 * browser's local time shifted them by a day west of UTC (2026-08-03 showed as 8/2/2026),
 * and events showed a meaningless "5:30 AM" in India. Date-only values are therefore
 * formatted in UTC and shown without a time.
 */

const isDateOnly = (d: Date): boolean =>
  d.getUTCHours() === 0 && d.getUTCMinutes() === 0 && d.getUTCSeconds() === 0 && d.getUTCMilliseconds() === 0

const parse = (value?: string | null): Date | null => {
  if (!value) return null
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? null : d
}

/** Calendar date of a meeting/event (date-only values are not shifted by the local time zone). */
export function formatDate(value?: string | null): string {
  const d = parse(value)
  if (!d) return "—"
  return d.toLocaleDateString(undefined, isDateOnly(d) ? { timeZone: "UTC" } : undefined)
}

/** Date plus time, except for date-only values where a time would be meaningless. */
export function formatDateTime(value?: string | null): string {
  const d = parse(value)
  if (!d) return "—"
  if (isDateOnly(d)) return formatDate(value)
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })
}

/** Seconds -> "1:05" or "1:02:05". */
export function formatTimestamp(seconds?: number | null): string {
  if (seconds === undefined || seconds === null || Number.isNaN(seconds)) return "—"
  const total = Math.max(0, Math.floor(seconds))
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  const ss = String(s).padStart(2, "0")
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${ss}` : `${m}:${ss}`
}

/** "3m 05s" / "1h 02m" style meeting duration. */
export function formatDuration(seconds?: number | null): string {
  if (!seconds || seconds <= 0) return "—"
  const total = Math.round(seconds)
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  if (h > 0) return `${h}h ${String(m).padStart(2, "0")}m`
  return `${m}m ${String(s).padStart(2, "0")}s`
}

/** A time range for a transcript slice, or null when the source has no real timestamps. */
export function formatSpan(start?: number | null, end?: number | null): string | null {
  if (start === undefined || start === null || end === undefined || end === null) return null
  if (start === 0 && end === 0) return null
  return `${formatTimestamp(start)} – ${formatTimestamp(end)}`
}

/** Start of a YYYY-MM-DD day (UTC) as ISO string, for API filters. */
export function startOfDayIso(day: string): string | undefined {
  return day ? `${day}T00:00:00Z` : undefined
}

/** End of a YYYY-MM-DD day (UTC) so "End date" includes that whole day. */
export function endOfDayIso(day: string): string | undefined {
  return day ? `${day}T23:59:59.999Z` : undefined
}

/** "spk_priya_sharma" -> "Priya Sharma"; "spk_0" -> "Speaker 1". */
export function prettifySpeakerId(id?: string | null): string {
  if (!id) return "Unknown"
  const raw = id.replace(/^spk_/, "")
  if (/^\d+$/.test(raw)) return `Speaker ${Number(raw) + 1}`
  return raw
    .split(/[_-]+/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ")
}

/** Human label for enum-like values such as "DECISION_REVERSED". */
export function humanize(value?: string | null): string {
  if (!value) return ""
  return value
    .toLowerCase()
    .split(/[_\s]+/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ")
}

export function formatScore(score?: number | null): string {
  if (score === undefined || score === null) return "—"
  return `${Math.round(score * 100)}%`
}
