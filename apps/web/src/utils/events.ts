import type { EventPayload } from "../services/api"

/** The fact a lifecycle event refers to, taken from the IDs the backend stores in its payload. */
export function eventTarget(payload?: EventPayload | null): { kind: "decision" | "commitment" | "issue"; id: string } | null {
  const p = payload ?? {}
  const str = (k: string) => (typeof p[k] === "string" && p[k] ? (p[k] as string) : null)
  const decision = str("decision_id") || str("prior_decision_id") || str("new_decision_id")
  if (decision) return { kind: "decision", id: decision }
  const commitment = str("commitment_id")
  if (commitment) return { kind: "commitment", id: commitment }
  const issue = str("issue_id")
  if (issue) return { kind: "issue", id: issue }
  return null
}
