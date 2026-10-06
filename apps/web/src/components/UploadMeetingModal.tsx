import React, { useEffect, useId, useState } from "react"
import { api } from "../services/api"
import { Modal } from "./Modal"
import { Notice } from "./Notice"

const ACCEPTED = ".wav,.mp3,.m4a,.mp4,.txt,.srt"

interface Props {
  isOpen: boolean
  onClose: () => void
  onUploaded: (meetingId: string) => void
}

/** Upload form shared by the Dashboard and the Meetings page. */
export const UploadMeetingModal: React.FC<Props> = ({ isOpen, onClose, onUploaded }) => {
  const ids = useId()
  const [title, setTitle] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [meetingDate, setMeetingDate] = useState("")
  const [participants, setParticipants] = useState("")
  const [background, setBackground] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Start from a clean form every time the dialog opens
  useEffect(() => {
    if (isOpen) {
      setTitle("")
      setFile(null)
      setMeetingDate("")
      setParticipants("")
      setBackground(false)
      setError(null)
    }
  }, [isOpen])

  const isMedia = file ? /\.(wav|mp3|m4a|mp4)$/i.test(file.name) : false

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim() || !file) {
      setError("A title and a file are required.")
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const formData = new FormData()
      formData.append("file", file)
      formData.append("title", title.trim())
      if (meetingDate) formData.append("meeting_date", meetingDate)
      const names = participants.split(",").map((p) => p.trim()).filter(Boolean)
      if (names.length) formData.append("participants", JSON.stringify(names))
      formData.append("async_processing", String(background))
      const res = await api.uploadMeeting(formData)
      onUploaded(res.meeting_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={submitting ? () => undefined : onClose} title="Upload and ingest a meeting">
      <form onSubmit={handleSubmit} noValidate>
        {error && <Notice tone="error">{error}</Notice>}
        <div className="form-group">
          <label className="form-label" htmlFor={`${ids}-title`}>
            Meeting title *
          </label>
          <input
            id={`${ids}-title`}
            type="text"
            className="form-input"
            value={title}
            maxLength={500}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Database architecture sync"
            required
          />
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor={`${ids}-date`}>
            Meeting date
          </label>
          <input
            id={`${ids}-date`}
            type="date"
            className="form-input"
            value={meetingDate}
            onChange={(e) => setMeetingDate(e.target.value)}
          />
          <span className="field-hint">Leave empty to use today.</span>
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor={`${ids}-participants`}>
            Participants (comma separated)
          </label>
          <input
            id={`${ids}-participants`}
            type="text"
            className="form-input"
            value={participants}
            onChange={(e) => setParticipants(e.target.value)}
            placeholder="e.g. Rahul Verma, Priya Sharma"
          />
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor={`${ids}-file`}>
            Recording or transcript * (.wav, .mp3, .m4a, .mp4, .txt, .srt)
          </label>
          <input
            id={`${ids}-file`}
            type="file"
            className="form-input"
            accept={ACCEPTED}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            required
          />
          {isMedia && (
            <span className="field-hint">
              Audio and video are transcribed with Whisper on this machine; long recordings can take
              several minutes, so background processing is recommended.
            </span>
          )}
        </div>
        <div className="checkbox-row">
          <input
            type="checkbox"
            id={`${ids}-background`}
            checked={background}
            onChange={(e) => setBackground(e.target.checked)}
          />
          <label htmlFor={`${ids}-background`}>
            Process in the background (the meeting page shows progress)
          </label>
        </div>

        <div className="form-actions">
          <button type="button" className="btn btn-outline" onClick={onClose} disabled={submitting}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? (background ? "Uploading…" : "Uploading and processing…") : "Start ingestion"}
          </button>
        </div>
      </form>
    </Modal>
  )
}
export default UploadMeetingModal
