import React, { useState, useEffect } from "react"
import { useNavigate, Link } from "react-router-dom"
import { api, DashboardMetrics, MeetingSummary } from "../services/api"
import { Spinner } from "../components/Spinner"
import { Modal } from "../components/Modal"
import { StatusBadge } from "../components/StatusBadge"
import { Plus, Video, Calendar, AlertCircle } from "lucide-react"

export const Dashboard: React.FC = () => {
  const navigate = useNavigate()
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null)
  const [recentMeetings, setRecentMeetings] = useState<MeetingSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Ingest Form States
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [title, setTitle] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [meetingDate, setMeetingDate] = useState("")
  const [participants, setParticipants] = useState("")
  const [asyncProcessing, setAsyncProcessing] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      const [mRes, meetingsRes] = await Promise.all([
        api.getDashboardMetrics(),
        api.getMeetings(5, 0)
      ])
      setMetrics(mRes)
      setRecentMeetings(meetingsRes)
    } catch (err: any) {
      setError(err.message || "Failed to load dashboard data.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title || !file) {
      setSubmitError("Title and Meeting File are required.")
      return
    }

    setSubmitting(true)
    setSubmitError(null)

    try {
      const formData = new FormData()
      formData.append("file", file)
      formData.append("title", title)
      if (meetingDate) {
        formData.append("meeting_date", meetingDate)
      }
      if (participants) {
        const partsList = participants.split(",").map(p => p.trim()).filter(Boolean)
        formData.append("participants", JSON.stringify(partsList))
      }
      formData.append("async_processing", String(asyncProcessing))

      const res = await api.uploadMeeting(formData)
      setIsModalOpen(false)
      // Reset form
      setTitle("")
      setFile(null)
      setMeetingDate("")
      setParticipants("")
      setAsyncProcessing(false)
      
      // Load updated data
      loadData()
      
      // Redirect to new meeting detail
      navigate(`/meetings/${res.meeting_id}`)
    } catch (err: any) {
      setSubmitError(err.message || "Failed to upload meeting.")
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <Spinner message="Loading dashboard metrics..." />

  return (
    <div className="dashboard-container">
      <header className="page-header">
        <div>
          <h1 className="page-title">Organizational Memory Dashboard</h1>
          <p className="page-subtitle">Historical decision intelligence and meeting analytics summary.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
          <Plus size={16} />
          <span>Ingest Meeting</span>
        </button>
      </header>

      {error && (
        <div className="error-state">
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {metrics && (
        <section className="kpi-grid">
          <div className="card kpi-card">
            <span className="kpi-label">Meetings Ingested</span>
            <span className="kpi-value">{metrics.meetings_ingested}</span>
          </div>
          <div className="card kpi-card" style={{ borderLeft: "3px solid var(--accent-indigo)" }}>
            <span className="kpi-label">Decisions Tracked</span>
            <span className="kpi-value">{metrics.decisions_tracked}</span>
          </div>
          <div className="card kpi-card" style={{ borderLeft: "3px solid var(--accent-emerald)" }}>
            <span className="kpi-label">Open Action Items</span>
            <span className="kpi-value">{metrics.open_actions}</span>
          </div>
          <div className="card kpi-card" style={{ borderLeft: "3px solid var(--accent-rose)" }}>
            <span className="kpi-label">Overdue Actions</span>
            <span className="kpi-value">{metrics.overdue_actions}</span>
          </div>
          <div className="card kpi-card" style={{ borderLeft: "3px solid var(--accent-amber)" }}>
            <span className="kpi-label">Unresolved Issues</span>
            <span className="kpi-value">{metrics.unresolved_issues}</span>
          </div>
          <div className="card kpi-card" style={{ borderLeft: "3px solid var(--accent-purple)" }}>
            <span className="kpi-label">Recurring Issues</span>
            <span className="kpi-value">{metrics.recurring_issues}</span>
          </div>
          <div className="card kpi-card">
            <span className="kpi-label">Entities Tracked</span>
            <span className="kpi-value">{metrics.canonical_entities_tracked}</span>
          </div>
          <div className="card kpi-card">
            <span className="kpi-label">Relationships</span>
            <span className="kpi-value">{metrics.relationships_tracked}</span>
          </div>
        </section>
      )}

      <section className="card" style={{ marginTop: "24px" }}>
        <h2 className="card-title">Recent Ingestion Activity</h2>
        {recentMeetings.length === 0 ? (
          <div className="empty-state">
            <Video size={48} className="empty-state-icon" />
            <p>No meetings have been ingested yet.</p>
            <button className="btn btn-outline" style={{ marginTop: "16px" }} onClick={() => setIsModalOpen(true)}>
              Upload First Meeting
            </button>
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Meeting Title</th>
                  <th>Date</th>
                  <th>Source Type</th>
                  <th>Processing Status</th>
                  <th>Segments</th>
                  <th>Created At</th>
                </tr>
              </thead>
              <tbody>
                {recentMeetings.map((m) => (
                  <tr key={m.meeting_id} style={{ cursor: "pointer" }} onClick={() => navigate(`/meetings/${m.meeting_id}`)}>
                    <td style={{ fontWeight: 600, color: "var(--accent-sky)" }}>{m.title}</td>
                    <td>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                        <Calendar size={13} />
                        {new Date(m.meeting_date).toLocaleDateString()}
                      </span>
                    </td>
                    <td><code>{m.source_type}</code></td>
                    <td>
                      <StatusBadge status={m.processing_status} />
                    </td>
                    <td>{m.segment_count}</td>
                    <td>{new Date(m.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Meeting upload Modal */}
      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Upload and Ingest Meeting">
        <form onSubmit={handleSubmit}>
          {submitError && (
            <div className="error-state" style={{ marginBottom: "16px" }}>
              <AlertCircle size={16} />
              <span>{submitError}</span>
            </div>
          )}
          <div className="form-group">
            <label className="form-label">Meeting Title *</label>
            <input
              type="text"
              className="form-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Database Architecture Sync"
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Meeting Date (YYYY-MM-DD or ISO)</label>
            <input
              type="text"
              className="form-input"
              value={meetingDate}
              onChange={(e) => setMeetingDate(e.target.value)}
              placeholder="e.g. 2026-08-25"
            />
          </div>
          <div className="form-group">
            <label className="form-label">Participants (comma separated)</label>
            <input
              type="text"
              className="form-input"
              value={participants}
              onChange={(e) => setParticipants(e.target.value)}
              placeholder="e.g. Rahul Verma, Priya Sharma"
            />
          </div>
          <div className="form-group">
            <label className="form-label">Source File * (.wav, .mp3, .srt, .txt, .mp4)</label>
            <input
              type="file"
              className="form-input"
              onChange={handleFileChange}
              accept=".wav,.mp3,.srt,.txt,.mp4"
              required
            />
          </div>
          <div className="form-group" style={{ flexDirection: "row", alignItems: "center", gap: "10px", marginTop: "10px" }}>
            <input
              type="checkbox"
              id="asyncCheckbox"
              checked={asyncProcessing}
              onChange={(e) => setAsyncProcessing(e.target.checked)}
            />
            <label htmlFor="asyncCheckbox" className="form-label" style={{ margin: 0, cursor: "pointer" }}>
              Process asynchronously via Celery Queue
            </label>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px", marginTop: "24px" }}>
            <button type="button" className="btn btn-outline" onClick={() => setIsModalOpen(false)} disabled={submitting}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? "Uploading..." : "Start Ingestion"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
export default Dashboard
