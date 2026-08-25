import React, { useState, useEffect } from "react"
import { useNavigate, Link } from "react-router-dom"
import { api, TimelineEventItem, DecisionHistoryItem, CommitmentHistoryItem, IssueHistoryItem } from "../services/api"
import { Spinner } from "../components/Spinner"
import { Modal } from "../components/Modal"
import {
  History,
  Calendar,
  AlertCircle,
  TrendingUp,
  GitCommit,
  Layers,
  ArrowRight,
  Filter,
  CheckCircle2
} from "lucide-react"

export const TemporalTimeline: React.FC = () => {
  const navigate = useNavigate()
  const [timelineEvents, setTimelineEvents] = useState<TimelineEventItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters state
  const [entityFilter, setEntityFilter] = useState("")
  const [typeFilter, setTypeFilter] = useState("")
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")

  // Lifecycle History Modal States
  const [historyModalOpen, setHistoryModalOpen] = useState(false)
  const [historyTitle, setHistoryTitle] = useState("")
  const [loadingHistory, setLoadingHistory] = useState(false)
  
  // Specific history payloads
  const [decisionHistory, setDecisionHistory] = useState<DecisionHistoryItem | null>(null)
  const [commitmentHistory, setCommitmentHistory] = useState<CommitmentHistoryItem | null>(null)
  const [issueHistory, setIssueHistory] = useState<IssueHistoryItem | null>(null)

  const loadTimeline = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const filters = {
        entity_id: entityFilter || undefined,
        event_type: typeFilter || undefined,
        start_date: startDate ? new Date(startDate).toISOString() : undefined,
        end_date: endDate ? new Date(endDate).toISOString() : undefined,
        limit: 100,
      }
      
      const res = await api.getGlobalTimeline(filters)
      setTimelineEvents(res)
    } catch (err: any) {
      setError(err.message || "Failed to load global timeline.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTimeline()
  }, [entityFilter, typeFilter])

  const handleApplyDateFilters = (e: React.FormEvent) => {
    e.preventDefault()
    loadTimeline()
  }

  const handleViewDecisionHistory = async (decisionId: string) => {
    setLoadingHistory(true)
    setHistoryTitle(`Decision History: ${decisionId}`)
    setDecisionHistory(null)
    setCommitmentHistory(null)
    setIssueHistory(null)
    setHistoryModalOpen(true)
    try {
      const res = await api.getDecisionHistory(decisionId)
      setDecisionHistory(res)
    } catch (err: any) {
      alert(`Failed to load decision history: ${err.message}`)
      setHistoryModalOpen(false)
    } finally {
      setLoadingHistory(false)
    }
  }

  const handleViewCommitmentHistory = async (commitmentId: string) => {
    setLoadingHistory(true)
    setHistoryTitle(`Commitment History: ${commitmentId}`)
    setDecisionHistory(null)
    setCommitmentHistory(null)
    setIssueHistory(null)
    setHistoryModalOpen(true)
    try {
      const res = await api.getCommitmentHistory(commitmentId)
      setCommitmentHistory(res)
    } catch (err: any) {
      alert(`Failed to load commitment history: ${err.message}`)
      setHistoryModalOpen(false)
    } finally {
      setLoadingHistory(false)
    }
  }

  const handleViewIssueHistory = async (issueId: string) => {
    setLoadingHistory(true)
    setHistoryTitle(`Issue History: ${issueId}`)
    setDecisionHistory(null)
    setCommitmentHistory(null)
    setIssueHistory(null)
    setHistoryModalOpen(true)
    try {
      const res = await api.getIssueHistory(issueId)
      setIssueHistory(res)
    } catch (err: any) {
      alert(`Failed to load issue history: ${err.message}`)
      setHistoryModalOpen(false)
    } finally {
      setLoadingHistory(false)
    }
  }

  const getEventClass = (type: string) => {
    const t = type.toLowerCase();
    if (t.includes("approved") || t.includes("resolved") || t.includes("completed")) return "resolved"
    if (t.includes("reversed") || t.includes("slippage") || t.includes("overdue")) return "reversed"
    if (t.includes("modified") || t.includes("reassigned")) return "modified"
    return "detected"
  }

  if (loading) return <Spinner message="Assembling chronological timeline..." />

  return (
    <div className="temporal-timeline-page">
      <header className="page-header">
        <div>
          <h1 className="page-title">Temporal Decision Intelligence</h1>
          <p className="page-subtitle">Reconstruct sequences, view lifecycle changes, and track commitments over time.</p>
        </div>
      </header>

      {error && (
        <div className="error-state">
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {/* Timeline Filters bar */}
      <form onSubmit={handleApplyDateFilters} className="card" style={{ padding: "16px", marginBottom: "24px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px", alignItems: "flex-end" }}>
          <div className="form-group">
            <label className="form-label">Associated Entity ID</label>
            <input
              type="text"
              className="form-input"
              value={entityFilter}
              onChange={(e) => setEntityFilter(e.target.value)}
              placeholder="e.g. ent-postgresql"
            />
          </div>
          <div className="form-group">
            <label className="form-label">Event Type</label>
            <select className="form-select" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
              <option value="">All Events</option>
              <option value="DECISION_APPROVED">DECISION_APPROVED</option>
              <option value="DECISION_MODIFIED">DECISION_MODIFIED</option>
              <option value="DECISION_REVERSED">DECISION_REVERSED</option>
              <option value="COMMITMENT_SLIPPED">COMMITMENT_SLIPPED</option>
              <option value="ISSUE_DETECTED">ISSUE_DETECTED</option>
              <option value="ISSUE_RESOLVED">ISSUE_RESOLVED</option>
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Start Date</label>
            <input type="date" className="form-input" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">End Date</label>
            <input type="date" className="form-input" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </div>
          <button type="submit" className="btn btn-outline" style={{ height: "40px", display: "flex", gap: "6px" }}>
            <Filter size={14} />
            <span>Apply Dates</span>
          </button>
        </div>
      </form>

      <section className="card">
        {timelineEvents.length === 0 ? (
          <div className="empty-state">
            <History size={48} className="empty-state-icon" />
            <p>No lifecycle timeline events found matching the filter criteria.</p>
          </div>
        ) : (
          <div className="timeline-stream">
            {timelineEvents.map((evt) => (
              <div key={evt.event_id} className={`timeline-event ${getEventClass(evt.event_type)}`}>
                <div className="timeline-node"></div>
                <div className="card timeline-card" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  <div className="timeline-meta">
                    <span className="timeline-type" style={{ fontWeight: 700 }}>{evt.event_type}</span>
                    <span>
                      <Calendar size={12} style={{ display: "inline", marginRight: "4px", verticalAlign: "middle" }} />
                      {new Date(evt.occurred_at).toLocaleDateString()} at {new Date(evt.occurred_at).toLocaleTimeString()}
                    </span>
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "12px", fontSize: "14px" }}>
                    <span>
                      Meeting:{" "}
                      <Link to={`/meetings/${evt.meeting_id}`} className="link-evidence" style={{ fontWeight: 600 }}>
                        {evt.meeting_title || evt.meeting_id}
                      </Link>
                    </span>
                    {evt.subject_entity_id && (
                      <span>
                        Subject Entity: <code>{evt.subject_entity_id}</code>
                      </span>
                    )}
                  </div>

                  {evt.payload && (
                    <div style={{ padding: "10px", borderRadius: "6px", backgroundColor: "rgba(0,0,0,0.15)", fontSize: "12.5px" }}>
                      {evt.payload.reason && <p><span style={{ fontWeight: 600 }}>Reason:</span> {evt.payload.reason}</p>}
                      {evt.payload.prior_subject && <p><span style={{ fontWeight: 600 }}>Prior Decision:</span> {evt.payload.prior_subject}</p>}
                      {evt.payload.new_subject && <p><span style={{ fontWeight: 600 }}>New Decision:</span> {evt.payload.new_subject}</p>}
                      {evt.payload.prior_deadline && (
                        <p>
                          <span style={{ fontWeight: 600 }}>Prior Deadline:</span>{" "}
                          {new Date(evt.payload.prior_deadline).toLocaleDateString()}
                        </p>
                      )}
                      {evt.payload.new_deadline && (
                        <p>
                          <span style={{ fontWeight: 600 }}>New Deadline:</span>{" "}
                          {new Date(evt.payload.new_deadline).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                  )}

                  {/* Lifecycle query triggers */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px dotted var(--border-light)", paddingTop: "10px", marginTop: "4px" }}>
                    {evt.payload?.prior_decision_id || evt.event_type.includes("DECISION") ? (
                      <button
                        className="link-evidence"
                        style={{ fontSize: "12px" }}
                        onClick={() => handleViewDecisionHistory(evt.payload?.prior_decision_id || evt.subject_entity_id || "")}
                      >
                        Inspect Decision History &rarr;
                      </button>
                    ) : evt.event_type.includes("COMMITMENT") ? (
                      <button
                        className="link-evidence"
                        style={{ fontSize: "12px" }}
                        onClick={() => handleViewCommitmentHistory(evt.subject_entity_id || "")}
                      >
                        Inspect Commitment History &rarr;
                      </button>
                    ) : evt.event_type.includes("ISSUE") ? (
                      <button
                        className="link-evidence"
                        style={{ fontSize: "12px" }}
                        onClick={() => handleViewIssueHistory(evt.subject_entity_id || "")}
                      >
                        Inspect Issue History &rarr;
                      </button>
                    ) : (
                      <span>ID: <code>{evt.event_id}</code></span>
                    )}

                    {evt.evidence_segment_id && (
                      <button
                        className="link-evidence"
                        style={{ fontSize: "12px" }}
                        onClick={() => navigate(`/meetings/${evt.meeting_id}?highlight=${evt.evidence_segment_id}`)}
                      >
                        Jump to Transcript Segment &rarr;
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Lifecycle History details Modal */}
      <Modal isOpen={historyModalOpen} onClose={() => setHistoryModalOpen(false)} title={historyTitle}>
        {loadingHistory && <Spinner message="Tracing lifecycle history and cross-meeting events..." />}
        
        {!loadingHistory && (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {decisionHistory && (
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div className="card" style={{ padding: "16px", borderLeft: "3px solid var(--accent-indigo)" }}>
                  <h3 className="card-title" style={{ margin: 0 }}>{decisionHistory.decision.subject}</h3>
                  <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "6px" }}>
                    Status: <span className="badge badge-succeeded">{decisionHistory.status}</span>
                  </p>
                  <p style={{ fontSize: "13px", marginTop: "8px" }}><span style={{ fontWeight: 600 }}>Rationale:</span> {decisionHistory.decision.rationale}</p>
                </div>
                
                <div>
                  <h4 className="form-label" style={{ marginBottom: "10px" }}>Decision Lifecycle Events ({decisionHistory.events.length})</h4>
                  <div className="timeline-stream" style={{ paddingLeft: "16px" }}>
                    {decisionHistory.events.map((evt) => (
                      <div key={evt.event_id} className={`timeline-event ${getEventClass(evt.event_type)}`}>
                        <div className="timeline-node"></div>
                        <div className="card timeline-card" style={{ padding: "10px" }}>
                          <div className="timeline-meta" style={{ marginBottom: "2px" }}>
                            <span style={{ fontWeight: 700, fontSize: "10px" }}>{evt.event_type}</span>
                            <span style={{ fontSize: "10px" }}>{new Date(evt.occurred_at).toLocaleDateString()}</span>
                          </div>
                          <p style={{ fontSize: "12.5px" }}>Occurred in: <span style={{ fontWeight: 600 }}>{evt.meeting_title || evt.meeting_id}</span></p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {commitmentHistory && (
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div className="card" style={{ padding: "16px", borderLeft: "3px solid var(--accent-emerald)" }}>
                  <h3 className="card-title" style={{ margin: 0 }}>{commitmentHistory.commitment.description}</h3>
                  <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "6px" }}>
                    Owner: <code>{commitmentHistory.commitment.owner_id}</code> • Status: <span className="badge badge-queued">{commitmentHistory.status}</span>
                  </p>
                  <div style={{ display: "flex", gap: "24px", fontSize: "12px", color: "var(--text-secondary)", marginTop: "8px" }}>
                    {commitmentHistory.original_deadline && <p><span style={{ fontWeight: 600 }}>Original Deadline:</span> {new Date(commitmentHistory.original_deadline).toLocaleDateString()}</p>}
                    {commitmentHistory.current_deadline && <p><span style={{ fontWeight: 600 }}>Current Deadline:</span> {new Date(commitmentHistory.current_deadline).toLocaleDateString()}</p>}
                  </div>
                  <p style={{ fontSize: "11px", color: "var(--accent-rose)", fontWeight: 600, marginTop: "6px" }}>
                    Deadline changed {commitmentHistory.deadline_changes_count} times
                  </p>
                </div>

                <div>
                  <h4 className="form-label" style={{ marginBottom: "10px" }}>Commitment Lifecycle Events ({commitmentHistory.events.length})</h4>
                  <div className="timeline-stream" style={{ paddingLeft: "16px" }}>
                    {commitmentHistory.events.map((evt) => (
                      <div key={evt.event_id} className={`timeline-event ${getEventClass(evt.event_type)}`}>
                        <div className="timeline-node"></div>
                        <div className="card timeline-card" style={{ padding: "10px" }}>
                          <div className="timeline-meta" style={{ marginBottom: "2px" }}>
                            <span style={{ fontWeight: 700, fontSize: "10px" }}>{evt.event_type}</span>
                            <span style={{ fontSize: "10px" }}>{new Date(evt.occurred_at).toLocaleDateString()}</span>
                          </div>
                          <p style={{ fontSize: "12.5px" }}>Occurred in: <span style={{ fontWeight: 600 }}>{evt.meeting_title || evt.meeting_id}</span></p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {issueHistory && (
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div className="card" style={{ padding: "16px", borderLeft: "3px solid var(--accent-amber)" }}>
                  <h3 className="card-title" style={{ margin: 0 }}>{issueHistory.issue.description}</h3>
                  <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "6px" }}>
                    Status: <span className="badge badge-running">{issueHistory.status}</span> • Seen in {issueHistory.meetings_count} meetings
                  </p>
                  <div style={{ display: "flex", gap: "16px", fontSize: "11px", color: "var(--text-secondary)", marginTop: "8px" }}>
                    <p><span style={{ fontWeight: 600 }}>Recurring:</span> {issueHistory.is_recurring ? "Yes" : "No"}</p>
                    <p><span style={{ fontWeight: 600 }}>Resolved:</span> {issueHistory.is_resolved ? "Yes" : "No"}</p>
                  </div>
                </div>

                <div>
                  <h4 className="form-label" style={{ marginBottom: "10px" }}>Issue Lifecycle Events ({issueHistory.events.length})</h4>
                  <div className="timeline-stream" style={{ paddingLeft: "16px" }}>
                    {issueHistory.events.map((evt) => (
                      <div key={evt.event_id} className={`timeline-event ${getEventClass(evt.event_type)}`}>
                        <div className="timeline-node"></div>
                        <div className="card timeline-card" style={{ padding: "10px" }}>
                          <div className="timeline-meta" style={{ marginBottom: "2px" }}>
                            <span style={{ fontWeight: 700, fontSize: "10px" }}>{evt.event_type}</span>
                            <span style={{ fontSize: "10px" }}>{new Date(evt.occurred_at).toLocaleDateString()}</span>
                          </div>
                          <p style={{ fontSize: "12.5px" }}>Occurred in: <span style={{ fontWeight: 600 }}>{evt.meeting_title || evt.meeting_id}</span></p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
export default TemporalTimeline
