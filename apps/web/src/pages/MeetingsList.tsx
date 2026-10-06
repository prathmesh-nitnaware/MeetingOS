import React, { useCallback, useEffect, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { Plus, Search, Video } from "lucide-react"
import { useAuth } from "../auth/AuthContext"
import { Notice } from "../components/Notice"
import { Spinner } from "../components/Spinner"
import { StatusBadge } from "../components/StatusBadge"
import UploadMeetingModal from "../components/UploadMeetingModal"
import { api, type MeetingSummary } from "../services/api"
import { formatDate, formatDateTime, formatDuration } from "../utils/format"

const PAGE_SIZE = 25

export const MeetingsList: React.FC = () => {
  const navigate = useNavigate()
  const { hasPermission } = useAuth()
  const [meetings, setMeetings] = useState<MeetingSummary[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState("")
  const [isModalOpen, setIsModalOpen] = useState(false)

  const loadMeetings = useCallback(async (pageIndex: number) => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.getMeetingsPage(PAGE_SIZE, pageIndex * PAGE_SIZE)
      setMeetings(res.items)
      setTotal(res.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load meetings.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadMeetings(page)
  }, [loadMeetings, page])

  const filtered = meetings.filter((m) => m.title.toLowerCase().includes(searchTerm.toLowerCase()))
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="meetings-list-page">
      <header className="page-header">
        <div>
          <h1 className="page-title">Meeting Directory</h1>
          <p className="page-subtitle">Recordings, transcripts and their processing status.</p>
        </div>
        {hasPermission("meetings.create") && (
          <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
            <Plus size={16} aria-hidden="true" />
            <span>Ingest meeting</span>
          </button>
        )}
      </header>

      {error && (
        <Notice tone="error">
          {error}{" "}
          <button type="button" className="link-evidence" onClick={() => void loadMeetings(page)}>
            Retry
          </button>
        </Notice>
      )}

      <div className="card search-box inline-search">
        <Search size={18} className="text-secondary" aria-hidden="true" />
        <label htmlFor="meeting-filter" className="sr-only">
          Filter meetings on this page by title
        </label>
        <input
          id="meeting-filter"
          type="text"
          className="form-input bare-input"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Filter meetings on this page by title..."
        />
      </div>

      <section className="card">
        {loading ? (
          <Spinner message="Fetching meetings..." />
        ) : filtered.length === 0 ? (
          <div className="empty-state">
            <Video size={48} className="empty-state-icon" aria-hidden="true" />
            <p>{searchTerm ? "No meetings on this page match your filter." : "No meetings yet."}</p>
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">Meeting</th>
                  <th scope="col">Date</th>
                  <th scope="col">Duration</th>
                  <th scope="col">Source</th>
                  <th scope="col">Status</th>
                  <th scope="col">Segments</th>
                  <th scope="col">Ingested</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((m) => (
                  <tr key={m.meeting_id}>
                    <td>
                      <Link to={`/meetings/${m.meeting_id}`} className="table-link">
                        {m.title}
                      </Link>
                    </td>
                    <td>{formatDate(m.meeting_date)}</td>
                    <td>{formatDuration(m.duration_seconds)}</td>
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

        {total > PAGE_SIZE && (
          <nav className="pagination" aria-label="Meeting pages">
            <button type="button" className="btn btn-outline" disabled={page === 0 || loading} onClick={() => setPage((p) => p - 1)}>
              Previous
            </button>
            <span className="muted">
              Page {page + 1} of {pageCount} · {total} meetings
            </span>
            <button type="button" className="btn btn-outline" disabled={page + 1 >= pageCount || loading} onClick={() => setPage((p) => p + 1)}>
              Next
            </button>
          </nav>
        )}
      </section>

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
export default MeetingsList
