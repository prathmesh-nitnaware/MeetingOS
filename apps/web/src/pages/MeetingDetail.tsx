import React, { useState, useEffect, useRef } from "react"
import { useParams, Link, useSearchParams } from "react-router-dom"
import { api, MeetingDetailResponse, TranscriptSegment, ExtractedDecision, ExtractedCommitment, ExtractedIssue, ExtractedEvent, ExtractedEntity, ExtractedRelation } from "../services/api"
import { Spinner } from "../components/Spinner"
import { StatusBadge } from "../components/StatusBadge"
import {
  Calendar,
  Clock,
  User,
  Activity,
  FileText,
  AlertCircle,
  TrendingUp,
  Tag,
  GitCommit,
  Share2,
  Users
} from "lucide-react"

export const MeetingDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const highlightId = searchParams.get("highlight")
  const transcriptEndRef = useRef<HTMLDivElement>(null)

  const [meeting, setMeeting] = useState<MeetingDetailResponse | null>(null)
  const [transcript, setTranscript] = useState<TranscriptSegment[]>([])
  const [decisions, setDecisions] = useState<ExtractedDecision[]>([])
  const [actions, setActions] = useState<ExtractedCommitment[]>([])
  const [issues, setIssues] = useState<ExtractedIssue[]>([])
  const [events, setEvents] = useState<ExtractedEvent[]>([])
  const [entities, setEntities] = useState<ExtractedEntity[]>([])
  const [relations, setRelations] = useState<ExtractedRelation[]>([])
  const [topics, setTopics] = useState<string[]>([])

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<"transcript" | "decisions" | "actions" | "issues" | "timeline" | "graph">("transcript")
  const [highlightedSegmentId, setHighlightedSegmentId] = useState<string | null>(null)
  
  // Job Triggers
  const [extracting, setExtracting] = useState(false)
  const [reconciling, setReconciling] = useState(false)
  const [reconResult, setReconResult] = useState<string | null>(null)

  const loadAllData = async (showLoadingSpinner = true) => {
    if (!id) return
    try {
      if (showLoadingSpinner) setLoading(true)
      setError(null)
      
      const mDetail = await api.getMeetingDetail(id)
      setMeeting(mDetail)

      // Fetch all sub-resources in parallel
      const [
        tRes,
        dRes,
        aRes,
        iRes,
        eRes,
        entRes,
        relRes,
        topicsRes
      ] = await Promise.all([
        api.getMeetingTranscript(id).catch(() => ({ segments: [] })),
        api.getMeetingDecisions(id).catch(() => []),
        api.getMeetingActions(id).catch(() => []),
        api.getMeetingIssues(id).catch(() => []),
        api.getMeetingTimeline(id).catch(() => []),
        api.getMeetingEntities(id).catch(() => []),
        api.getMeetingRelations(id).catch(() => []),
        api.getMeetingTopics(id).catch(() => [])
      ])

      setTranscript(tRes.segments)
      setDecisions(dRes)
      setActions(aRes)
      setIssues(iRes)
      setEvents(eRes)
      setEntities(entRes)
      setRelations(relRes)
      setTopics(topicsRes)
    } catch (err: any) {
      setError(err.message || "Failed to load meeting details.")
    } finally {
      if (showLoadingSpinner) setLoading(false)
    }
  }

  useEffect(() => {
    loadAllData()
  }, [id])

  useEffect(() => {
    if (highlightId && transcript.length > 0) {
      jumpToSegment(highlightId)
    }
  }, [highlightId, transcript])

  // Scroll to and highlight segment in transcript
  const jumpToSegment = (segmentId?: string) => {
    if (!segmentId) return
    setHighlightedSegmentId(segmentId)
    setActiveTab("transcript")
    setTimeout(() => {
      const element = document.getElementById(`seg-${segmentId}`)
      if (element) {
        element.scrollIntoView({ behavior: "smooth", block: "center" })
      }
    }, 150)
  }

  const triggerExtraction = async () => {
    if (!id) return
    try {
      setExtracting(true)
      await api.triggerNLPExtraction(id)
      await loadAllData(false) // Reload facts silently
    } catch (err: any) {
      alert(`Extraction failed: ${err.message}`)
    } finally {
      setExtracting(false)
    }
  }

  const triggerReconciliation = async () => {
    if (!id) return
    try {
      setReconciling(true)
      setReconResult(null)
      const res = await api.reconcileLifecycle(id)
      setReconResult(
        `Reconciliation complete: Detected ${res.decision_changes_detected} decision changes, ${res.deadline_changes_detected} deadline changes, and ${res.recurring_issues_detected} recurring issues.`
      )
      await loadAllData(false) // Refresh events
    } catch (err: any) {
      alert(`Reconciliation failed: ${err.message}`)
    } finally {
      setReconciling(false)
    }
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return "N/A"
    const m = Math.floor(seconds / 60)
    const s = Math.round(seconds % 60)
    return `${m}m ${s}s`
  }

  if (loading) return <Spinner message="Loading meeting details & analysis..." />
  if (error || !meeting) {
    return (
      <div className="error-state">
        <AlertCircle size={20} />
        <span>{error || "Meeting not found."}</span>
      </div>
    )
  }

  return (
    <div className="meeting-detail-page">
      <div style={{ marginBottom: "16px" }}>
        <Link to="/meetings" className="link-evidence" style={{ fontSize: "13px" }}>
          &larr; Back to Directory
        </Link>
      </div>

      <header className="page-header" style={{ alignItems: "flex-start", gap: "24px" }}>
        <div style={{ flex: 1 }}>
          <h1 className="page-title" style={{ margin: 0 }}>{meeting.title}</h1>
          <div className="page-subtitle" style={{ display: "flex", flexWrap: "wrap", gap: "16px", marginTop: "8px" }}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
              <Calendar size={14} />
              {new Date(meeting.meeting_date).toLocaleDateString()}
            </span>
            <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
              <Clock size={14} />
              {formatDuration(meeting.duration_seconds)}
            </span>
            <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
              <Users size={14} />
              {meeting.participants.length} Participants
            </span>
            <span>
              Source: <code>{meeting.source_type}</code>
            </span>
          </div>
        </div>

        <div style={{ display: "flex", flexWrap: "wrap", gap: "10px", alignItems: "center" }}>
          <StatusBadge status={meeting.processing_status} />
          
          <button
            className="btn btn-outline"
            onClick={triggerExtraction}
            disabled={extracting || transcript.length === 0}
          >
            {extracting ? "Running NLP..." : "Run NLP Facts"}
          </button>
          
          <button
            className="btn btn-primary"
            onClick={triggerReconciliation}
            disabled={reconciling}
          >
            {reconciling ? "Reconciling..." : "Reconcile History"}
          </button>
        </div>
      </header>

      {reconResult && (
        <div className="error-state" style={{ backgroundColor: "rgba(16, 185, 129, 0.08)", border: "1px solid rgba(16, 185, 129, 0.2)", color: "#a7f3d0", marginBottom: "24px" }}>
          <Activity size={20} />
          <span>{reconResult}</span>
        </div>
      )}

      {topics.length > 0 && (
        <div className="card" style={{ padding: "16px", marginBottom: "24px" }}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center" }}>
            <span style={{ fontSize: "12px", fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)", marginRight: "8px" }}>Topics:</span>
            {topics.map((topic, i) => (
              <span key={i} className="badge" style={{ backgroundColor: "rgba(255, 255, 255, 0.05)", color: "var(--text-primary)" }}>
                <Tag size={10} style={{ marginRight: "4px" }} />
                {topic}
              </span>
            ))}
          </div>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "24px" }}>
        <div className="tabs-header">
          <button className={`tab-btn ${activeTab === "transcript" ? "active" : ""}`} onClick={() => setActiveTab("transcript")}>
            Transcript & Speech
          </button>
          <button className={`tab-btn ${activeTab === "decisions" ? "active" : ""}`} onClick={() => setActiveTab("decisions")}>
            Decisions ({decisions.length})
          </button>
          <button className={`tab-btn ${activeTab === "actions" ? "active" : ""}`} onClick={() => setActiveTab("actions")}>
            Commitments & Actions ({actions.length})
          </button>
          <button className={`tab-btn ${activeTab === "issues" ? "active" : ""}`} onClick={() => setActiveTab("issues")}>
            Issues ({issues.length})
          </button>
          <button className={`tab-btn ${activeTab === "timeline" ? "active" : ""}`} onClick={() => setActiveTab("timeline")}>
            Meeting Timeline ({events.length})
          </button>
          <button className={`tab-btn ${activeTab === "graph" ? "active" : ""}`} onClick={() => setActiveTab("graph")}>
            Entities & Relations
          </button>
        </div>

        <div className="tab-content">
          {activeTab === "transcript" && (
            <div className="card" style={{ padding: "20px" }}>
              {transcript.length === 0 ? (
                <div className="empty-state">
                  <FileText size={48} className="empty-state-icon" />
                  <p>No transcript segments available for this meeting. Check ingestion status or verify file.</p>
                </div>
              ) : (
                <div className="transcript-pane">
                  {transcript.map((seg) => (
                    <div
                      key={seg.segment_id}
                      id={`seg-${seg.segment_id}`}
                      className={`utterance-item ${highlightedSegmentId === seg.segment_id ? "highlighted" : ""}`}
                    >
                      <div className="utterance-meta">
                        <span className="utterance-speaker">
                          <User size={12} style={{ display: "inline", marginRight: "4px", verticalAlign: "middle" }} />
                          {seg.speaker_id}
                        </span>
                        <span className="utterance-time">
                          {Math.floor(seg.start_time / 60)}:
                          {String(Math.floor(seg.start_time % 60)).padStart(2, "0")} -{" "}
                          {Math.floor(seg.end_time / 60)}:
                          {String(Math.floor(seg.end_time % 60)).padStart(2, "0")}
                        </span>
                      </div>
                      <p className="utterance-text">{seg.text}</p>
                    </div>
                  ))}
                  <div ref={transcriptEndRef} />
                </div>
              )}
            </div>
          )}

          {activeTab === "decisions" && (
            <div className="fact-grid">
              {decisions.length === 0 ? (
                <div className="card empty-state">
                  <GitCommit size={48} className="empty-state-icon" />
                  <p>No decisions extracted from this meeting yet.</p>
                </div>
              ) : (
                decisions.map((dec) => (
                  <div key={dec.decision_id} className="fact-item" style={{ borderLeft: "3px solid var(--accent-indigo)" }}>
                    <div className="fact-header">
                      <h4 className="fact-subject">{dec.subject}</h4>
                      <span className="badge" style={{ backgroundColor: "rgba(99,102,241,0.15)", color: "var(--accent-indigo)" }}>
                        {dec.status}
                      </span>
                    </div>
                    {dec.rationale && <p className="fact-body"><span style={{ fontWeight: 600 }}>Rationale:</span> {dec.rationale}</p>}
                    <div className="fact-footer">
                      <span>ID: <code>{dec.decision_id}</code></span>
                      {dec.evidence_segment_id && (
                        <button className="link-evidence" onClick={() => jumpToSegment(dec.evidence_segment_id)}>
                          Jump to Evidence &rarr;
                        </button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === "actions" && (
            <div className="fact-grid">
              {actions.length === 0 ? (
                <div className="card empty-state">
                  <TrendingUp size={48} className="empty-state-icon" />
                  <p>No action items or commitments extracted from this meeting yet.</p>
                </div>
              ) : (
                actions.map((act) => (
                  <div key={act.commitment_id} className="fact-item" style={{ borderLeft: "3px solid var(--accent-emerald)" }}>
                    <div className="fact-header">
                      <h4 className="fact-subject">{act.description}</h4>
                      <span className="badge" style={{ backgroundColor: "rgba(16,185,129,0.15)", color: "var(--accent-emerald)" }}>
                        {act.status}
                      </span>
                    </div>
                    <div className="fact-body" style={{ display: "flex", gap: "24px" }}>
                      <p><span style={{ fontWeight: 600 }}>Owner:</span> <code>{act.owner_id}</code></p>
                      {act.current_deadline && (
                        <p>
                          <span style={{ fontWeight: 600 }}>Deadline:</span>{" "}
                          {new Date(act.current_deadline).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                    <div className="fact-footer">
                      <span>ID: <code>{act.commitment_id}</code></span>
                      {act.evidence_segment_id && (
                        <button className="link-evidence" onClick={() => jumpToSegment(act.evidence_segment_id)}>
                          Jump to Evidence &rarr;
                        </button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === "issues" && (
            <div className="fact-grid">
              {issues.length === 0 ? (
                <div className="card empty-state">
                  <AlertCircle size={48} className="empty-state-icon" />
                  <p>No organizational issues or blockers extracted from this meeting yet.</p>
                </div>
              ) : (
                issues.map((iss) => (
                  <div key={iss.issue_id} className="fact-item" style={{ borderLeft: "3px solid var(--accent-amber)" }}>
                    <div className="fact-header">
                      <h4 className="fact-subject">{iss.description}</h4>
                      <span className="badge" style={{ backgroundColor: "rgba(245,158,11,0.15)", color: "var(--accent-amber)" }}>
                        {iss.status}
                      </span>
                    </div>
                    {iss.owner_id && <p className="fact-body"><span style={{ fontWeight: 600 }}>Assigned To:</span> <code>{iss.owner_id}</code></p>}
                    <div className="fact-footer">
                      <span>ID: <code>{iss.issue_id}</code></span>
                      {iss.evidence_segment_id && (
                        <button className="link-evidence" onClick={() => jumpToSegment(iss.evidence_segment_id)}>
                          Jump to Evidence &rarr;
                        </button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === "timeline" && (
            <div className="card" style={{ padding: "24px" }}>
              {events.length === 0 ? (
                <div className="empty-state">
                  <GitCommit size={48} className="empty-state-icon" />
                  <p>No chronological timeline events associated with this meeting.</p>
                </div>
              ) : (
                <div className="timeline-stream">
                  {events.map((evt) => (
                    <div key={evt.event_id} className={`timeline-event ${evt.event_type.toLowerCase()}`}>
                      <div className="timeline-node"></div>
                      <div className="card timeline-card">
                        <div className="timeline-meta">
                          <span className="timeline-type">{evt.event_type}</span>
                          <span>{new Date(evt.occurred_at).toLocaleTimeString()}</span>
                        </div>
                        <p style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-primary)" }}>
                          Subject Entity ID: <code>{evt.subject_entity_id}</code>
                        </p>
                        {evt.payload_json && (
                          <pre style={{ fontFamily: "var(--font-mono)", fontSize: "11px", backgroundColor: "rgba(0,0,0,0.2)", padding: "10px", borderRadius: "4px", marginTop: "8px", overflowX: "auto" }}>
                            {JSON.stringify(evt.payload_json, null, 2)}
                          </pre>
                        )}
                        {evt.evidence_segment_id && (
                          <div style={{ marginTop: "12px", textAlign: "right" }}>
                            <button className="link-evidence" style={{ fontSize: "12px" }} onClick={() => jumpToSegment(evt.evidence_segment_id)}>
                              View Evidence Segment &rarr;
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === "graph" && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
              <div className="card">
                <h3 className="card-title">Extracted Entities</h3>
                {entities.length === 0 ? (
                  <div className="empty-state" style={{ padding: "30px 0" }}>
                    <Users size={32} className="empty-state-icon" />
                    <p>No entities extracted from this meeting.</p>
                  </div>
                ) : (
                  <div className="table-container">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Canonical Name</th>
                          <th>Type</th>
                        </tr>
                      </thead>
                      <tbody>
                        {entities.map((ent) => (
                          <tr key={ent.entity_id}>
                            <td>
                              <Link to={`/entities`} className="link-evidence" style={{ fontWeight: 600 }}>
                                {ent.name}
                              </Link>
                            </td>
                            <td><code>{ent.entity_type}</code></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              <div className="card">
                <h3 className="card-title">Fact Relationships</h3>
                {relations.length === 0 ? (
                  <div className="empty-state" style={{ padding: "30px 0" }}>
                    <Share2 size={32} className="empty-state-icon" />
                    <p>No relational graph edges extracted from this meeting.</p>
                  </div>
                ) : (
                  <div className="table-container">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Source</th>
                          <th>Relationship</th>
                          <th>Target</th>
                        </tr>
                      </thead>
                      <tbody>
                        {relations.map((rel) => (
                          <tr key={rel.relation_id}>
                            <td><code>{rel.source_entity_id}</code></td>
                            <td>
                              <span className="badge" style={{ backgroundColor: "rgba(245,158,11,0.1)", color: "var(--accent-amber)" }}>
                                {rel.relationship_type}
                              </span>
                            </td>
                            <td><code>{rel.target_entity_id}</code></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
export default MeetingDetail
