import React, { useCallback, useEffect, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { Plus, Video } from "lucide-react"
import { useAuth } from "../auth/AuthContext"
import { Notice } from "../components/Notice"
import { Spinner } from "../components/Spinner"
import { StatusBadge } from "../components/StatusBadge"
import UploadMeetingModal from "../components/UploadMeetingModal"
import { api, type DashboardMetrics, type MeetingSummary } from "../services/api"
import { formatDate, formatDateTime } from "../utils/format"

const KPIS: { key: keyof DashboardMetrics; label: string; accent?: string }[] = [
  { key: "meetings_ingested", label: "Meetings ingested" },
  { key: "decisions_tracked", label: "Decisions tracked", accent: "var(--accent-indigo)" },
  { key: "open_actions", label: "Open action items", accent: "var(--accent-emerald)" },
  { key: "overdue_actions", label: "Overdue actions", accent: "var(--accent-rose)" },
  { key: "unresolved_issues", label: "Unresolved issues", accent: "var(--accent-amber)" },
  { key: "recurring_issues", label: "Recurring issues", accent: "var(--accent-purple)" },
  { key: "canonical_entities_tracked", label: "Entities tracked" },
  { key: "relationships_tracked", label: "Relationships" },
]

export const Dashboard: React.FC = () => {
  const navigate = useNavigate()
  const { hasPermission } = useAuth()
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null)
  const [recentMeetings, setRecentMeetings] = useState<MeetingSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [m, meetings] = await Promise.all([api.getDashboardMetrics(), api.getMeetings(5, 0)])
      setMetrics(m)
      setRecentMeetings(meetings)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard data.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadData()
  }, [loadData])

  const canUpload = hasPermission("meetings.create")

  return (
    <div className="dashboard-container">
      <header className="page-header">
        <div>
          <h1 className="page-title">Organizational Memory Dashboard</h1>
          <p className="page-subtitle">Decisions, commitments and issues across your meetings.</p>
        </div>
        {canUpload && (
          <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
            <Plus size={16} aria-hidden="true" />
            <span>Ingest meeting</span>
          </button>
        )}
      </header>

      {loading && <Spinner message="Loading dashboard metrics..." />}

      {!loading && error && (
        <Notice tone="error">
          {error}{" "}
          <button type="button" className="link-evidence" onClick={() => void loadData()}>
            Retry
          </button>
        </Notice>
      )}

      {!loading && metrics && (
        <section className="kpi-grid" aria-label="Key metrics">
          {KPIS.map(({ key, label, accent }) => (
            <div key={key} className="card kpi-card" style={accent ? { borderLeft: `3px solid ${accent}` } : undefined}>
              <span className="kpi-label">{label}</span>
              <span className="kpi-value">{metrics[key]}</span>
            </div>
          ))}
        </section>
      )}

      {!loading && !error && (
        <section className="card" style={{ marginTop: "24px" }}>
          <h2 className="card-title">Recent ingestion activity</h2>
          {recentMeetings.length === 0 ? (
            <div className="empty-state">
              <Video size={48} className="empty-state-icon" aria-hidden="true" />
              <p>No meetings have been ingested yet.</p>
              {canUpload && (
                <button className="btn btn-outline" style={{ marginTop: "16px" }} onClick={() => setIsModalOpen(true)}>
                  Upload your first meeting
                </button>
              )}
            </div>
          ) : (
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th scope="col">Meeting</th>
                    <th scope="col">Date</th>
                    <th scope="col">Source</th>
                    <th scope="col">Status</th>
                    <th scope="col">Segments</th>
                    <th scope="col">Ingested</th>
                  </tr>
                </thead>
                <tbody>
                  {recentMeetings.map((m) => (
                    <tr key={m.meeting_id}>
                      <td>
                        <Link to={`/meetings/${m.meeting_id}`} className="table-link">
                          {m.title}
                        </Link>
                      </td>
                      <td>{formatDate(m.meeting_date)}</td>
                      <td><code>{m.source_type}</code></td>
                      <td><StatusBadge status={m.processing_status} /></td>
                      <td>{m.segment_count}</td>
                      <td>{formatDateTime(m.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      <UploadMeetingModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onUploaded={(id) => {
          setIsModalOpen(false)
          navigate(`/meetings/${id}`)
        }}
      />
    </div>
  )
}
export default Dashboard
