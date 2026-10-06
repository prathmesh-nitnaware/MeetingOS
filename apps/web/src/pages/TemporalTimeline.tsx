import React, { useCallback, useEffect, useId, useRef, useState } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { Calendar, Filter, History } from "lucide-react"
import { Modal } from "../components/Modal"
import { Notice } from "../components/Notice"
import { PayloadDetails } from "../components/PayloadDetails"
import { eventTarget } from "../utils/events"
import { Spinner } from "../components/Spinner"
import { StatusBadge } from "../components/StatusBadge"
import {
  api,
  type CommitmentHistoryItem,
  type DecisionHistoryItem,
  type IssueHistoryItem,
  type TimelineEventItem,
} from "../services/api"
import { endOfDayIso, formatDate, humanize, startOfDayIso } from "../utils/format"

// Must match packages/common/enums.py::EventType
const EVENT_TYPES = [
  "DECISION_PROPOSED",
  "DECISION_APPROVED",
  "DECISION_MODIFIED",
  "DECISION_REVERSED",
  "DEADLINE_CHANGED",
  "COMMITMENT_ASSIGNED",
  "COMMITMENT_COMPLETED",
  "COMMITMENT_OVERDUE",
  "COMMITMENT_REASSIGNED",
  "ISSUE_DETECTED",
  "ISSUE_RECURRING",
  "ISSUE_RESOLVED",
  "TECHNOLOGY_REPLACED",
  "PROJECT_LAUNCHED",
]

type HistoryKind = "decision" | "commitment" | "issue"

const eventTone = (type: string): string => {
  const t = type.toLowerCase()
  if (t.includes("approved") || t.includes("resolved") || t.includes("completed")) return "resolved"
  if (t.includes("reversed") || t.includes("overdue")) return "reversed"
  if (t.includes("modified") || t.includes("reassigned") || t.includes("deadline")) return "modified"
  return "detected"
}

const HistoryEvents: React.FC<{ events: TimelineEventItem[] }> = ({ events }) =>
  events.length === 0 ? (
    <p className="muted">No lifecycle events recorded yet.</p>
  ) : (
    <div className="timeline-stream compact">
      {events.map((evt) => (
        <div key={evt.event_id} className={`timeline-event ${eventTone(evt.event_type)}`}>
          <div className="timeline-node"></div>
          <div className="card timeline-card">
            <div className="timeline-meta">
              <span className="timeline-type">{humanize(evt.event_type)}</span>
              <span>{formatDate(evt.occurred_at)}</span>
            </div>
            <p className="muted">In: {evt.meeting_title || evt.meeting_id}</p>
            <PayloadDetails payload={evt.payload} />
          </div>
        </div>
      ))}
    </div>
  )

export const TemporalTimeline: React.FC = () => {
  const ids = useId()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [events, setEvents] = useState<TimelineEventItem[]>([])
  const [initialLoad, setInitialLoad] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [entityInput, setEntityInput] = useState("")
  const [entityFilter, setEntityFilter] = useState("")
  const [typeFilter, setTypeFilter] = useState("")
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")

  const [history, setHistory] = useState<{
    kind: HistoryKind
    id: string
    loading: boolean
    error?: string
    decision?: DecisionHistoryItem
    commitment?: CommitmentHistoryItem
    issue?: IssueHistoryItem
  } | null>(null)

  // Debounce the free-text entity filter so typing does not fire a request per keystroke
  useEffect(() => {
    const timer = window.setTimeout(() => setEntityFilter(entityInput.trim()), 400)
    return () => window.clearTimeout(timer)
  }, [entityInput])

  const requestId = useRef(0)
  const loadTimeline = useCallback(async () => {
    const current = ++requestId.current
    setRefreshing(true)
    setError(null)
    try {
      const res = await api.getGlobalTimeline({
        entity_id: entityFilter || undefined,
        event_type: typeFilter || undefined,
        start_date: startOfDayIso(startDate),
        end_date: endOfDayIso(endDate),
        limit: 200,
      })
      if (current === requestId.current) setEvents(res)
    } catch (err) {
      if (current === requestId.current) setError(err instanceof Error ? err.message : "Failed to load the timeline.")
    } finally {
      if (current === requestId.current) {
        setRefreshing(false)
        setInitialLoad(false)
      }
    }
  }, [entityFilter, typeFilter, startDate, endDate])

  useEffect(() => {
    void loadTimeline()
  }, [loadTimeline])

  const openHistory = useCallback(async (kind: HistoryKind, id: string) => {
    setHistory({ kind, id, loading: true })
    try {
      if (kind === "decision") setHistory({ kind, id, loading: false, decision: await api.getDecisionHistory(id) })
      if (kind === "commitment") setHistory({ kind, id, loading: false, commitment: await api.getCommitmentHistory(id) })
      if (kind === "issue") setHistory({ kind, id, loading: false, issue: await api.getIssueHistory(id) })
    } catch (err) {
      setHistory({ kind, id, loading: false, error: err instanceof Error ? err.message : "Could not load the history." })
    }
  }, [])

  // Deep links from the meeting page: /temporal?decision=<id> etc.
  useEffect(() => {
    for (const kind of ["decision", "commitment", "issue"] as HistoryKind[]) {
      const id = searchParams.get(kind)
      if (id) {
        void openHistory(kind, id)
        break
      }
    }
  }, [searchParams, openHistory])

  const closeHistory = () => {
    setHistory(null)
    if (searchParams.has("decision") || searchParams.has("commitment") || searchParams.has("issue")) {
      setSearchParams({}, { replace: true })
    }
  }

  const historyTitle = history ? `${humanize(history.kind)} history` : ""

  return (
    <div className="temporal-timeline-page">
      <header className="page-header">
        <div>
          <h1 className="page-title">Temporal Decision Intelligence</h1>
          <p className="page-subtitle">How decisions, commitments and issues changed across meetings.</p>
        </div>
      </header>

      <form
        className="card filter-bar"
        onSubmit={(e) => {
          e.preventDefault()
          setEntityFilter(entityInput.trim())
        }}
      >
        <div className="form-group">
          <label className="form-label" htmlFor={`${ids}-entity`}>Entity ID</label>
          <input id={`${ids}-entity`} type="text" className="form-input" value={entityInput} onChange={(e) => setEntityInput(e.target.value)} placeholder="e.g. ent-postgresql" />
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor={`${ids}-type`}>Event type</label>
          <select id={`${ids}-type`} className="form-select" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
            <option value="">All events</option>
            {EVENT_TYPES.map((t) => (
              <option key={t} value={t}>{humanize(t)}</option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor={`${ids}-start`}>From</label>
          <input id={`${ids}-start`} type="date" className="form-input" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor={`${ids}-end`}>To (inclusive)</label>
          <input id={`${ids}-end`} type="date" className="form-input" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        </div>
        <button type="submit" className="btn btn-outline filter-submit">
          <Filter size={14} aria-hidden="true" />
          <span>{refreshing ? "Filtering…" : "Apply"}</span>
        </button>
      </form>

      {error && <Notice tone="error">{error}</Notice>}

      <section className="card" aria-busy={refreshing}>
        {initialLoad ? (
          <Spinner message="Assembling chronological timeline..." />
        ) : events.length === 0 ? (
          <div className="empty-state">
            <History size={48} className="empty-state-icon" aria-hidden="true" />
            <p>No lifecycle events match these filters.</p>
          </div>
        ) : (
          <div className={`timeline-stream${refreshing ? " is-refreshing" : ""}`}>
            {events.map((evt) => {
              const target = eventTarget(evt.payload)
              return (
                <div key={evt.event_id} className={`timeline-event ${eventTone(evt.event_type)}`}>
                  <div className="timeline-node"></div>
                  <div className="card timeline-card">
                    <div className="timeline-meta">
                      <span className="timeline-type">{humanize(evt.event_type)}</span>
                      <span>
                        <Calendar size={12} aria-hidden="true" /> {formatDate(evt.occurred_at)}
                      </span>
                    </div>
                    <p>
                      Meeting:{" "}
                      <Link to={`/meetings/${evt.meeting_id}`} className="link-evidence">
                        {evt.meeting_title || evt.meeting_id}
                      </Link>
                    </p>
                    <PayloadDetails payload={evt.payload} />
                    <div className="fact-footer">
                      {target ? (
                        <button type="button" className="link-evidence" onClick={() => void openHistory(target.kind, target.id)}>
                          Inspect {target.kind} history &rarr;
                        </button>
                      ) : (
                        <span />
                      )}
                      {evt.evidence_segment_id && (
                        <button
                          type="button"
                          className="link-evidence"
                          onClick={() => navigate(`/meetings/${evt.meeting_id}?highlight=${encodeURIComponent(evt.evidence_segment_id ?? "")}`)}
                        >
                          Jump to transcript &rarr;
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section>

      <Modal isOpen={history !== null} onClose={closeHistory} title={historyTitle} wide>
        {history?.loading && <Spinner message="Tracing lifecycle history..." />}
        {history?.error && <Notice tone="error">{history.error}</Notice>}

        {history?.decision && (
          <div className="stack">
            <div className="card accent-indigo">
              <h3 className="card-title">{history.decision.decision.subject}</h3>
              <p className="muted">
                Status: <StatusBadge status={history.decision.status} /> · First recorded in{" "}
                <Link to={`/meetings/${history.decision.meeting_id}`} className="link-evidence" onClick={closeHistory}>
                  {history.decision.meeting_title}
                </Link>{" "}
                ({formatDate(history.decision.meeting_date)})
              </p>
            </div>
            <h4 className="form-label">Lifecycle events ({history.decision.events.length})</h4>
            <HistoryEvents events={history.decision.events} />
          </div>
        )}

        {history?.commitment && (
          <div className="stack">
            <div className="card accent-emerald">
              <h3 className="card-title">{history.commitment.commitment.description}</h3>
              <p className="muted">
                Status: <StatusBadge status={history.commitment.status} />
              </p>
              <p className="muted">
                Original deadline: {formatDate(history.commitment.original_deadline)} · Current deadline:{" "}
                {formatDate(history.commitment.current_deadline)}
              </p>
              {history.commitment.deadline_changes_count > 0 && (
                <p className="text-warning">Deadline changed {history.commitment.deadline_changes_count} time(s)</p>
              )}
            </div>
            <h4 className="form-label">Lifecycle events ({history.commitment.events.length})</h4>
            <HistoryEvents events={history.commitment.events} />
          </div>
        )}

        {history?.issue && (
          <div className="stack">
            <div className="card accent-amber">
              <h3 className="card-title">{history.issue.issue.description}</h3>
              <p className="muted">
                Status: <StatusBadge status={history.issue.status} /> · Seen in {history.issue.meetings_count} meeting(s) ·
                Recurring: {history.issue.is_recurring ? "yes" : "no"} · Resolved: {history.issue.is_resolved ? "yes" : "no"}
              </p>
            </div>
            <h4 className="form-label">Lifecycle events ({history.issue.events.length})</h4>
            <HistoryEvents events={history.issue.events} />
          </div>
        )}
      </Modal>
    </div>
  )
}
export default TemporalTimeline
