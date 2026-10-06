import React, { useCallback, useEffect, useMemo, useState } from "react"
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom"
import { AlertCircle, Calendar, Clock, FileText, GitCommit, Share2, Tag, TrendingUp, User, Users } from "lucide-react"
import { useAuth } from "../auth/AuthContext"
import { Notice } from "../components/Notice"
import { PayloadDetails } from "../components/PayloadDetails"
import { Spinner } from "../components/Spinner"
import { StatusBadge } from "../components/StatusBadge"
import {
  api,
  type ExtractedCommitment,
  type ExtractedDecision,
  type ExtractedEntity,
  type ExtractedEvent,
  type ExtractedIssue,
  type ExtractedRelation,
  type JobStatus,
  type MeetingDetailResponse,
  type TranscriptSegment,
} from "../services/api"
import { formatDate, formatDuration, formatTimestamp, humanize, prettifySpeakerId } from "../utils/format"

type Tab = "transcript" | "decisions" | "actions" | "issues" | "timeline" | "graph"

const ACTIVE_STATUSES = new Set(["queued", "running"])

export const MeetingDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const highlightId = searchParams.get("highlight")
  const { hasPermission } = useAuth()

  const [meeting, setMeeting] = useState<MeetingDetailResponse | null>(null)
  const [transcript, setTranscript] = useState<TranscriptSegment[]>([])
  const [decisions, setDecisions] = useState<ExtractedDecision[]>([])
  const [actions, setActions] = useState<ExtractedCommitment[]>([])
  const [issues, setIssues] = useState<ExtractedIssue[]>([])
  const [events, setEvents] = useState<ExtractedEvent[]>([])
  const [entities, setEntities] = useState<ExtractedEntity[]>([])
  const [relations, setRelations] = useState<ExtractedRelation[]>([])
  const [topics, setTopics] = useState<string[]>([])
  const [failedSections, setFailedSections] = useState<string[]>([])
  const [job, setJob] = useState<JobStatus | null>(null)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>("transcript")
  const [highlightedSegmentId, setHighlightedSegmentId] = useState<string | null>(null)
  const [busy, setBusy] = useState<"extract" | "reconcile" | "delete" | null>(null)
  const [message, setMessage] = useState<{ tone: "success" | "error"; text: string } | null>(null)

  const loadAllData = useCallback(
    async (showSpinner = true) => {
      if (!id) return
      if (showSpinner) setLoading(true)
      setError(null)
      try {
        const detail = await api.getMeetingDetail(id)
        setMeeting(detail)

        const failed: string[] = []
        const safe = async <T,>(label: string, p: Promise<T>, fallback: T): Promise<T> => {
          try {
            return await p
          } catch {
            failed.push(label)
            return fallback
          }
        }
        const [t, d, a, i, e, ent, rel, top] = await Promise.all([
          safe("transcript", api.getMeetingTranscript(id).then((r) => r.segments), [] as TranscriptSegment[]),
          safe("decisions", api.getMeetingDecisions(id), [] as ExtractedDecision[]),
          safe("actions", api.getMeetingActions(id), [] as ExtractedCommitment[]),
          safe("issues", api.getMeetingIssues(id), [] as ExtractedIssue[]),
          safe("timeline", api.getMeetingTimeline(id), [] as ExtractedEvent[]),
          safe("entities", api.getMeetingEntities(id), [] as ExtractedEntity[]),
          safe("relations", api.getMeetingRelations(id), [] as ExtractedRelation[]),
          safe("topics", api.getMeetingTopics(id), [] as string[]),
        ])
        setTranscript(t)
        setDecisions(d)
        setActions(a)
        setIssues(i)
        setEvents(e)
        setEntities(ent)
        setRelations(rel)
        setTopics(top)
        setFailedSections(failed)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load meeting details.")
      } finally {
        if (showSpinner) setLoading(false)
      }
    },
    [id]
  )

  useEffect(() => {
    void loadAllData()
  }, [loadAllData])

  // While a meeting is being processed, poll its job and refresh when it finishes
  const processing = meeting ? ACTIVE_STATUSES.has(meeting.processing_status) : false
  useEffect(() => {
    if (!meeting || !processing) return
    const timer = window.setInterval(async () => {
      try {
        if (meeting.latest_job_id) setJob(await api.getJob(meeting.latest_job_id))
        const detail = await api.getMeetingDetail(meeting.meeting_id)
        if (!ACTIVE_STATUSES.has(detail.processing_status)) {
          setJob(null)
          await loadAllData(false)
        }
      } catch {
        /* transient polling error: try again on the next tick */
      }
    }, 3000)
    return () => window.clearInterval(timer)
  }, [meeting, processing, loadAllData])

  const segmentIds = useMemo(() => new Set(transcript.map((s) => s.segment_id)), [transcript])

  const speakerNames = useMemo(() => {
    const map = new Map<string, string>()
    meeting?.speakers.forEach((s) => {
      if (s.name) map.set(s.speaker_id, s.name)
    })
    return map
  }, [meeting])
  const speakerLabel = (speakerId?: string | null) =>
    (speakerId && speakerNames.get(speakerId)) || prettifySpeakerId(speakerId)

  const entityNames = useMemo(() => new Map(entities.map((e) => [e.entity_id, e.name])), [entities])

  const jumpToSegment = useCallback((segmentId?: string | null) => {
    if (!segmentId) return
    setHighlightedSegmentId(segmentId)
    setActiveTab("transcript")
    window.setTimeout(() => {
      document.getElementById(`seg-${segmentId}`)?.scrollIntoView({ behavior: "smooth", block: "center" })
    }, 150)
  }, [])

  useEffect(() => {
    if (highlightId && transcript.length > 0) jumpToSegment(highlightId)
  }, [highlightId, transcript, jumpToSegment])

  const runAction = async (kind: "extract" | "reconcile") => {
    if (!id) return
    setBusy(kind)
    setMessage(null)
    try {
      if (kind === "extract") {
        const res = await api.triggerNLPExtraction(id)
        setMessage({ tone: "success", text: `Re-extracted ${res.decisions_count} decisions and ${res.entities_count} entities.` })
      } else {
        const res = await api.reconcileLifecycle(id)
        setMessage({
          tone: "success",
          text: `Compared with earlier meetings: ${res.decision_changes_detected} decision changes, ${res.deadline_changes_detected} deadline changes, ${res.recurring_issues_detected} recurring issues.`,
        })
      }
      await loadAllData(false)
    } catch (err) {
      setMessage({ tone: "error", text: err instanceof Error ? err.message : "The action failed." })
    } finally {
      setBusy(null)
    }
  }

  const deleteMeeting = async () => {
    if (!id || !meeting) return
    if (!window.confirm(`Delete "${meeting.title}"? It will disappear from search, answers and the dashboard.`)) return
    setBusy("delete")
    try {
      await api.deleteMeeting(id)
      navigate("/meetings")
    } catch (err) {
      setMessage({ tone: "error", text: err instanceof Error ? err.message : "Delete failed." })
      setBusy(null)
    }
  }

  const EvidenceLink: React.FC<{ segmentId?: string | null; label?: string }> = ({ segmentId, label }) =>
    segmentId && segmentIds.has(segmentId) ? (
      <button type="button" className="link-evidence" onClick={() => jumpToSegment(segmentId)}>
        {label ?? "Jump to evidence"} &rarr;
      </button>
    ) : null

  if (loading) return <Spinner message="Loading meeting details & analysis..." />
  if (error || !meeting) {
    return (
      <div>
        <Link to="/meetings" className="link-evidence back-link">&larr; Back to meetings</Link>
        <Notice tone="error">{error || "Meeting not found."}</Notice>
      </div>
    )
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: "transcript", label: "Transcript" },
    { key: "decisions", label: `Decisions (${decisions.length})` },
    { key: "actions", label: `Commitments & actions (${actions.length})` },
    { key: "issues", label: `Issues (${issues.length})` },
    { key: "timeline", label: `Meeting timeline (${events.length})` },
    { key: "graph", label: "Entities & relations" },
  ]

  return (
    <div className="meeting-detail-page">
      <Link to="/meetings" className="link-evidence back-link">&larr; Back to meetings</Link>

      <header className="page-header detail-header">
        <div style={{ flex: 1, minWidth: 0 }}>
          <h1 className="page-title">{meeting.title}</h1>
          <div className="page-subtitle meta-row">
            <span><Calendar size={14} aria-hidden="true" /> {formatDate(meeting.meeting_date)}</span>
            <span><Clock size={14} aria-hidden="true" /> {formatDuration(meeting.duration_seconds)}</span>
            <span><Users size={14} aria-hidden="true" /> {meeting.participants.length} participants · {meeting.speakers_count} speakers</span>
            <span>Source: <code>{meeting.metadata.source_filename || meeting.source_type}</code></span>
          </div>
        </div>

        <div className="header-actions">
          <StatusBadge status={meeting.processing_status} />
          {hasPermission("meetings.update") && (
            <button className="btn btn-outline" onClick={() => void runAction("extract")} disabled={busy !== null || transcript.length === 0}>
              {busy === "extract" ? "Running NLP..." : "Re-run NLP facts"}
            </button>
          )}
          {hasPermission("meetings.update") && (
            <button className="btn btn-primary" onClick={() => void runAction("reconcile")} disabled={busy !== null || processing}>
              {busy === "reconcile" ? "Reconciling..." : "Reconcile history"}
            </button>
          )}
          {hasPermission("meetings.delete") && (
            <button className="btn btn-danger" onClick={() => void deleteMeeting()} disabled={busy !== null}>
              Delete
            </button>
          )}
        </div>
      </header>

      {processing && (
        <Notice tone="info">
          This meeting is being processed{job ? ` (${humanize(job.stage)}, ${Math.round(job.progress * 100)}%)` : ""}. This page refreshes automatically.
        </Notice>
      )}
      {meeting.processing_status === "failed" && (
        <Notice tone="error">Processing failed: {meeting.latest_job_error || "unknown error"}</Notice>
      )}
      {failedSections.length > 0 && (
        <Notice tone="error">Some sections could not be loaded: {failedSections.join(", ")}.</Notice>
      )}
      {message && (
        <Notice tone={message.tone} onDismiss={() => setMessage(null)}>
          {message.text}
        </Notice>
      )}

      {topics.length > 0 && (
        <div className="card topics-card">
          <span className="kpi-label">Topics</span>
          {topics.map((topic) => (
            <span key={topic} className="badge topic-badge">
              <Tag size={10} aria-hidden="true" /> {topic}
            </span>
          ))}
        </div>
      )}

      <div className="tabs-header" role="tablist" aria-label="Meeting sections">
        {tabs.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={activeTab === t.key}
            className={`tab-btn ${activeTab === t.key ? "active" : ""}`}
            onClick={() => setActiveTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="tab-content" role="tabpanel">
        {activeTab === "transcript" && (
          <div className="card">
            {transcript.length === 0 ? (
              <div className="empty-state">
                <FileText size={48} className="empty-state-icon" aria-hidden="true" />
                <p>{processing ? "The transcript will appear when processing finishes." : "No transcript segments for this meeting."}</p>
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
                        <User size={12} aria-hidden="true" /> {speakerLabel(seg.speaker_id)}
                      </span>
                      <span className="utterance-time">
                        {formatTimestamp(seg.start_time)} – {formatTimestamp(seg.end_time)}
                      </span>
                    </div>
                    <p className="utterance-text">{seg.text}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === "decisions" && (
          <div className="fact-grid">
            {decisions.length === 0 ? (
              <div className="card empty-state">
                <GitCommit size={48} className="empty-state-icon" aria-hidden="true" />
                <p>No decisions extracted from this meeting.</p>
              </div>
            ) : (
              decisions.map((dec) => (
                <div key={dec.decision_id} className="fact-item accent-indigo">
                  <div className="fact-header">
                    <h4 className="fact-subject">{dec.subject}</h4>
                    <StatusBadge status={dec.status} />
                  </div>
                  <div className="fact-footer">
                    <Link to={`/temporal?decision=${dec.decision_id}`} className="link-evidence">
                      View history
                    </Link>
                    <EvidenceLink segmentId={dec.evidence_segment_id} />
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
                <TrendingUp size={48} className="empty-state-icon" aria-hidden="true" />
                <p>No action items or commitments extracted from this meeting.</p>
              </div>
            ) : (
              actions.map((act) => (
                <div key={act.commitment_id} className="fact-item accent-emerald">
                  <div className="fact-header">
                    <h4 className="fact-subject">{act.description}</h4>
                    <StatusBadge status={act.status} />
                  </div>
                  <div className="fact-body fact-meta">
                    <span><strong>Owner:</strong> {speakerLabel(act.owner_id)}</span>
                    {act.current_deadline && (
                      <span>
                        <strong>Deadline:</strong> {formatDate(act.current_deadline)}
                        {act.original_deadline && act.original_deadline !== act.current_deadline && (
                          <> (originally {formatDate(act.original_deadline)})</>
                        )}
                      </span>
                    )}
                  </div>
                  <div className="fact-footer">
                    <Link to={`/temporal?commitment=${act.commitment_id}`} className="link-evidence">
                      View history
                    </Link>
                    <EvidenceLink segmentId={act.evidence_segment_id} />
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
                <AlertCircle size={48} className="empty-state-icon" aria-hidden="true" />
                <p>No issues or blockers extracted from this meeting.</p>
              </div>
            ) : (
              issues.map((iss) => (
                <div key={iss.issue_id} className="fact-item accent-amber">
                  <div className="fact-header">
                    <h4 className="fact-subject">{iss.description}</h4>
                    <StatusBadge status={iss.status} />
                  </div>
                  {iss.owner_id && (
                    <p className="fact-body"><strong>Raised by:</strong> {speakerLabel(iss.owner_id)}</p>
                  )}
                  <div className="fact-footer">
                    <Link to={`/temporal?issue=${iss.issue_id}`} className="link-evidence">
                      View history
                    </Link>
                    <EvidenceLink segmentId={iss.evidence_segment_id} />
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === "timeline" && (
          <div className="card">
            {events.length === 0 ? (
              <div className="empty-state">
                <GitCommit size={48} className="empty-state-icon" aria-hidden="true" />
                <p>No lifecycle events for this meeting.</p>
              </div>
            ) : (
              <div className="timeline-stream">
                {events.map((evt) => (
                  <div key={evt.event_id} className="timeline-event">
                    <div className="timeline-node"></div>
                    <div className="card timeline-card">
                      <div className="timeline-meta">
                        <span className="timeline-type">{humanize(evt.event_type)}</span>
                        <span>{formatDate(evt.occurred_at)}</span>
                      </div>
                      <PayloadDetails payload={evt.payload} />
                      <div className="fact-footer">
                        {evt.subject_entity_id && entityNames.has(evt.subject_entity_id) && (
                          <span className="muted">About {entityNames.get(evt.subject_entity_id)}</span>
                        )}
                        <EvidenceLink segmentId={evt.evidence_segment_id} label="View evidence" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === "graph" && (
          <div className="grid-2">
            <div className="card">
              <h3 className="card-title">Extracted entities</h3>
              {entities.length === 0 ? (
                <div className="empty-state compact">
                  <Users size={32} className="empty-state-icon" aria-hidden="true" />
                  <p>No entities extracted from this meeting.</p>
                </div>
              ) : (
                <div className="table-container">
                  <table className="table">
                    <thead>
                      <tr>
                        <th scope="col">Name</th>
                        <th scope="col">Type</th>
                      </tr>
                    </thead>
                    <tbody>
                      {entities.map((ent) => (
                        <tr key={ent.entity_id}>
                          <td>
                            <Link to={`/entities?focus=${encodeURIComponent(ent.entity_id)}`} className="table-link">
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
              <h3 className="card-title">Relationships</h3>
              {relations.length === 0 ? (
                <div className="empty-state compact">
                  <Share2 size={32} className="empty-state-icon" aria-hidden="true" />
                  <p>No relationships extracted from this meeting.</p>
                </div>
              ) : (
                <div className="table-container">
                  <table className="table">
                    <thead>
                      <tr>
                        <th scope="col">From</th>
                        <th scope="col">Relationship</th>
                        <th scope="col">To</th>
                      </tr>
                    </thead>
                    <tbody>
                      {relations.map((rel) => (
                        <tr key={rel.relation_id}>
                          <td>{entityNames.get(rel.source_entity_id) ?? <code>{rel.source_entity_id}</code>}</td>
                          <td><span className="badge badge-running">{humanize(rel.relationship_type)}</span></td>
                          <td>{entityNames.get(rel.target_entity_id) ?? <code>{rel.target_entity_id}</code>}</td>
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
  )
}
export default MeetingDetail
