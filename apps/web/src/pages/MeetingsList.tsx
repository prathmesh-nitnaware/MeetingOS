import React, { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { api, MeetingSummary } from "../services/api"
import { Spinner } from "../components/Spinner"
import { Modal } from "../components/Modal"
import { StatusBadge } from "../components/StatusBadge"
import { Plus, Video, Calendar, Search, AlertCircle } from "lucide-react"

export const MeetingsList: React.FC = () => {
  const navigate = useNavigate()
  const [meetings, setMeetings] = useState<MeetingSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState("")

  // Ingest Form States
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [title, setTitle] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [meetingDate, setMeetingDate] = useState("")
  const [participants, setParticipants] = useState("")
  const [asyncProcessing, setAsyncProcessing] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const loadMeetings = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await api.getMeetings(100, 0)
      setMeetings(data)
    } catch (err: any) {
      setError(err.message || "Failed to load meetings.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadMeetings()
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
      
      // Reload meetings list
      loadMeetings()

      // Redirect to detail
      navigate(`/meetings/${res.meeting_id}`)
    } catch (err: any) {
      setSubmitError(err.message || "Failed to upload meeting.")
    } finally {
      setSubmitting(false)
    }
  }

  const filteredMeetings = meetings.filter((m) =>
    m.title.toLowerCase().includes(searchTerm.toLowerCase())
  )

  if (loading) return <Spinner message="Fetching organizational meetings..." />

  return (
    <div className="meetings-list-page">
      <header className="page-header">
        <div>
          <h1 className="page-title">Meeting Directory</h1>
          <p className="page-subtitle">Manage, view, and analyze meeting recordings and transcript details.</p>
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

      <div className="card search-box" style={{ marginBottom: "24px", display: "flex", alignItems: "center", padding: "12px 20px" }}>
        <Search size={18} className="text-secondary" style={{ marginRight: "8px" }} />
        <input
          type="text"
          className="form-input"
          style={{ border: "none", background: "none", padding: 0 }}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Filter meetings by title..."
        />
      </div>

      <section className="card">
        {filteredMeetings.length === 0 ? (
          <div className="empty-state">
            <Video size={48} className="empty-state-icon" />
            <p>{searchTerm ? "No meetings match your search query." : "No meetings are currently registered."}</p>
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Meeting Title</th>
                  <th>Meeting Date</th>
                  <th>Source Type</th>
                  <th>Processing Status</th>
                  <th>Segments Count</th>
                  <th>Ingested At</th>
                </tr>
              </thead>
              <tbody>
                {filteredMeetings.map((m) => (
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

      {/* Ingestion Modal */}
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
              placeholder="e.g. Sprint Sync"
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
              placeholder="e.g. Sarah Connor, John Connor"
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
              id="asyncCheckboxMeetings"
              checked={asyncProcessing}
              onChange={(e) => setAsyncProcessing(e.target.checked)}
            />
            <label htmlFor="asyncCheckboxMeetings" className="form-label" style={{ margin: 0, cursor: "pointer" }}>
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
export default MeetingsList
