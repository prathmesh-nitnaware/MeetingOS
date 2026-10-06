import React from "react"
import type { EventPayload } from "../services/api"
import { formatDate } from "../utils/format"

const PAYLOAD_LABELS: Record<string, string> = {
  text: "Statement",
  reason: "Reason",
  prior_subject: "Previous decision",
  new_subject: "New decision",
  previous_deadline: "Previous deadline",
  new_deadline: "New deadline",
  description: "Description",
  status: "Status",
  new_status: "New status",
}

const DATE_KEYS = new Set(["previous_deadline", "new_deadline", "first_detected_at", "last_mentioned_at"])

/** Readable key/value view of a lifecycle event payload (unknown/internal keys are hidden). */
export const PayloadDetails: React.FC<{ payload?: EventPayload | null }> = ({ payload }) => {
  const rows = Object.entries(payload ?? {}).filter(
    ([key, value]) => key in PAYLOAD_LABELS && value !== null && value !== undefined && value !== ""
  )
  if (rows.length === 0) return null
  return (
    <dl className="payload-list">
      {rows.map(([key, value]) => (
        <div key={key} className="payload-row">
          <dt>{PAYLOAD_LABELS[key]}</dt>
          <dd>{DATE_KEYS.has(key) ? formatDate(String(value)) : String(value)}</dd>
        </div>
      ))}
    </dl>
  )
}

export default PayloadDetails
