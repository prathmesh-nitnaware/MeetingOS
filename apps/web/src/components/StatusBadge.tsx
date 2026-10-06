import React from "react"

interface StatusBadgeProps {
  status: string
}

/** Maps processing and lifecycle statuses onto the four badge colours. */
const TONE: Record<string, string> = {
  succeeded: "succeeded",
  approved: "succeeded",
  implemented: "succeeded",
  completed: "succeeded",
  resolved: "succeeded",
  queued: "queued",
  proposed: "queued",
  discussion: "queued",
  identified: "queued",
  assigned: "queued",
  detected: "queued",
  running: "running",
  "in progress": "running",
  modified: "running",
  reassigned: "running",
  "under investigation": "running",
  recurring: "running",
  failed: "failed",
  reversed: "failed",
  overdue: "failed",
  unresolved: "failed",
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const tone = TONE[status.toLowerCase()] ?? "queued"
  return (
    <span className={`badge badge-${tone}`}>
      <span className="dot" aria-hidden="true">●</span>
      {status}
    </span>
  )
}
export default StatusBadge
