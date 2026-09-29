import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  FileText,
  Sparkles,
  Users,
  Calendar as CalendarIcon,
  Tag,
  ArrowRight,
  CheckCircle2,
  X,
  Plus,
  Loader2,
  AlignLeft,
  MessageSquare,
  FolderGit2,
  Clock,
  Download
} from "lucide-react";
import { api, Project, CalendarEvent } from "../services/api";

const SAMPLE_TRANSCRIPT = `Alex: We need to finalize the API architecture and release plan this week.
Sarah: The frontend flows are ready. We need the authentication module completed.
David: I will finish the authentication module and JWT token rotation by Thursday.
Maya: Let's target Friday for the internal staging release.
Alex: Agreed. Decision: We will use Friday as our target for internal staging deployment.
David: I will also prepare the deployment checklist and verify load testing.`;

const SAMPLE_NOTES = `- Discussed Q4 API architecture and database connection pooling
- David will complete authentication module by Thursday
- Decision: Internal staging deployment scheduled for Friday
- Maya will prepare marketing release notes
- Need load testing verification before production`;

export const CreateMeeting: React.FC = () => {
  const navigate = useNavigate();

  // Projects & Calendar states
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [calendarEvents, setCalendarEvents] = useState<CalendarEvent[]>([]);
  const [showCalendarModal, setShowCalendarModal] = useState<boolean>(false);
  const [loadingEvents, setLoadingEvents] = useState<boolean>(false);

  // Step 1: Details
  const [title, setTitle] = useState("");
  const [meetingDate, setMeetingDate] = useState(new Date().toISOString().split("T")[0]);
  const [participantInput, setParticipantInput] = useState("");
  const [participants, setParticipants] = useState<string[]>(["Alex", "Sarah", "David"]);
  const [customTag, setCustomTag] = useState("Product Launch");

  // Step 2: Content
  const [contentType, setContentType] = useState<"transcript" | "notes" | "discussion">("transcript");
  const [content, setContent] = useState(SAMPLE_TRANSCRIPT);

  // Step 3: AI Processing State
  const [submitting, setSubmitting] = useState(false);
  const [analysisStep, setAnalysisStep] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const data = await api.getProjects();
      setProjects(data || []);
      if (data && data.length > 0) {
        setSelectedProjectId(data[0].id || data[0].project_id || "");
      }
    } catch (err) {
      console.error("Failed to load projects", err);
    }
  };

  const handleOpenCalendarImport = async () => {
    setShowCalendarModal(true);
    setLoadingEvents(true);
    try {
      const events = await api.getCalendarEvents("google_calendar", 5);
      setCalendarEvents(events || []);
    } catch (err) {
      console.error("Failed to load calendar events", err);
    } finally {
      setLoadingEvents(false);
    }
  };

  const handleSelectCalendarEvent = (event: CalendarEvent) => {
    setTitle(event.title);
    if (event.start_time) {
      setMeetingDate(event.start_time.split("T")[0]);
    }
    if (event.participants && event.participants.length > 0) {
      const names = event.participants.map((p) => p.name).filter(Boolean);
      if (names.length > 0) {
        setParticipants(names);
      }
    }
    setShowCalendarModal(false);
  };

  const handleAddParticipant = () => {
    if (participantInput.trim() && !participants.includes(participantInput.trim())) {
      setParticipants([...participants, participantInput.trim()]);
      setParticipantInput("");
    }
  };

  const handleRemoveParticipant = (name: string) => {
    setParticipants(participants.filter((p) => p !== name));
  };

  const handleCreate = async (autoAnalyze: boolean) => {
    if (!title.trim()) {
      setErrorMessage("Please enter a meeting title.");
      return;
    }
    if (!content.trim()) {
      setErrorMessage("Please provide meeting transcript or notes.");
      return;
    }

    setSubmitting(true);
    setErrorMessage(null);

    if (autoAnalyze) {
      setAnalysisStep(1); // Reading meeting content
      setTimeout(() => setAnalysisStep(2), 300); // Identifying key topics
      setTimeout(() => setAnalysisStep(3), 600); // Extracting decisions
      setTimeout(() => setAnalysisStep(4), 900); // Finding action items
      setTimeout(() => setAnalysisStep(5), 1200); // Generating summary
    }

    try {
      const res = await api.createMeetingText({
        title: title.trim(),
        meeting_date: meetingDate,
        participants,
        content_type: contentType,
        content: content.trim(),
        project_id: selectedProjectId || customTag || undefined,
        auto_analyze: autoAnalyze,
      });

      setTimeout(() => {
        navigate(`/meetings/${res.meeting_id}`);
      }, autoAnalyze ? 1500 : 300);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to create meeting.");
      setSubmitting(false);
      setAnalysisStep(0);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.25rem" }}>
            <span style={{ fontSize: "0.8125rem", color: "var(--color-primary-600)", fontWeight: "600", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Meeting Ingestion
            </span>
          </div>
          <h1 className="page-title">New Meeting Workspace</h1>
          <p className="page-subtitle">
            Transform transcripts, rough notes, or discussions into connected organizational intelligence.
          </p>
        </div>

        <button
          type="button"
          className="btn btn-secondary"
          onClick={handleOpenCalendarImport}
          style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.875rem" }}
        >
          <CalendarIcon size={16} /> Import from Calendar
        </button>
      </div>

      {errorMessage && (
        <div className="alert-banner error" style={{ marginBottom: "1.5rem" }}>
          <X size={16} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Calendar Import Modal */}
      {showCalendarModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0, 0, 0, 0.5)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", padding: "1rem" }}>
          <div style={{ background: "white", borderRadius: "12px", maxWidth: "540px", width: "100%", padding: "1.5rem", boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <h3 style={{ fontSize: "1.125rem", fontWeight: "700", color: "var(--color-text-main)", margin: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <CalendarIcon size={18} style={{ color: "var(--color-primary-600)" }} />
                Upcoming Calendar Events
              </h3>
              <button
                type="button"
                onClick={() => setShowCalendarModal(false)}
                style={{ background: "none", border: "none", cursor: "pointer", color: "var(--color-text-muted)" }}
              >
                <X size={18} />
              </button>
            </div>
            <p style={{ color: "var(--color-text-muted)", fontSize: "0.8125rem", marginBottom: "1rem" }}>
              Select a scheduled event to auto-populate meeting title, date, and participant roster.
            </p>

            {loadingEvents ? (
              <div style={{ padding: "2rem", textAlign: "center", color: "var(--color-text-muted)" }}>
                <Loader2 size={24} className="spinner" style={{ margin: "0 auto 0.5rem auto" }} />
                Checking calendar providers...
              </div>
            ) : calendarEvents.length === 0 ? (
              <div style={{ padding: "2rem", textAlign: "center", color: "var(--color-text-muted)", fontSize: "0.875rem" }}>
                No upcoming calendar events discovered.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", maxHeight: "300px", overflowY: "auto" }}>
                {calendarEvents.map((evt) => (
                  <div
                    key={evt.external_event_id}
                    onClick={() => handleSelectCalendarEvent(evt)}
                    style={{
                      padding: "0.875rem 1rem",
                      borderRadius: "8px",
                      border: "1px solid #e2e8f0",
                      background: "#f8fafc",
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center"
                    }}
                  >
                    <div>
                      <div style={{ fontSize: "0.9375rem", fontWeight: "600", color: "var(--color-text-main)" }}>
                        {evt.title}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", marginTop: "0.25rem", display: "flex", alignItems: "center", gap: "0.75rem" }}>
                        <span><Clock size={11} style={{ display: "inline", marginRight: "3px" }} /> {new Date(evt.start_time).toLocaleDateString()}</span>
                        <span><Users size={11} style={{ display: "inline", marginRight: "3px" }} /> {evt.participants.length} attendees</span>
                      </div>
                    </div>
                    <span style={{ fontSize: "0.75rem", color: "var(--color-primary-600)", fontWeight: "600" }}>
                      Select →
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Main Creation Flow Card */}
      <div className="create-meeting-card">
        {/* Step 1: Meeting Details */}
        <section className="form-section">
          <div className="section-header-compact">
            <span className="step-number">1</span>
            <h3 className="section-title">Meeting Details & Organization</h3>
          </div>

          <div className="form-grid-two">
            <div className="form-group">
              <label className="form-label" htmlFor="meeting-title">
                Meeting Title <span className="required">*</span>
              </label>
              <input
                id="meeting-title"
                type="text"
                className="form-input"
                placeholder="e.g. Q4 Product Launch Kickoff"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="meeting-date">
                Meeting Date
              </label>
              <input
                id="meeting-date"
                type="date"
                className="form-input"
                value={meetingDate}
                onChange={(e) => setMeetingDate(e.target.value)}
              />
            </div>
          </div>

          {/* Project & Topic Association */}
          <div className="form-grid-two" style={{ marginTop: "16px" }}>
            <div className="form-group">
              <label className="form-label" htmlFor="project-select">
                Associated Project
              </label>
              <select
                id="project-select"
                className="form-select"
                value={selectedProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
              >
                <option value="">(No specific project)</option>
                {projects.map((p) => (
                  <option key={p.id || p.project_id} value={p.id || p.project_id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="project-topic">
                Primary Topic Tag
              </label>
              <input
                id="project-topic"
                type="text"
                className="form-input"
                placeholder="e.g. Product Launch, API Architecture"
                value={customTag}
                onChange={(e) => setCustomTag(e.target.value)}
              />
            </div>
          </div>

          {/* Participants */}
          <div className="form-group" style={{ marginTop: "16px" }}>
            <label className="form-label">Participants & Attendees</label>
            <div className="participant-chips-container">
              {participants.map((p) => (
                <span key={p} className="participant-chip">
                  <Users size={12} />
                  <span>{p}</span>
                  <button
                    type="button"
                    className="chip-remove"
                    onClick={() => handleRemoveParticipant(p)}
                    aria-label={`Remove ${p}`}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
            <div className="participant-input-row">
              <input
                type="text"
                className="form-input input-sm"
                placeholder="Add attendee name..."
                value={participantInput}
                onChange={(e) => setParticipantInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleAddParticipant();
                  }
                }}
              />
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={handleAddParticipant}
              >
                <Plus size={14} /> Add
              </button>
            </div>
          </div>
        </section>

        <hr className="divider" />

        {/* Step 2: Meeting Content */}
        <section className="form-section">
          <div className="section-header-compact">
            <span className="step-number">2</span>
            <h3 className="section-title">Meeting Content / Notes</h3>
          </div>

          <div className="content-type-tabs">
            <button
              type="button"
              className={`tab-btn ${contentType === "transcript" ? "active" : ""}`}
              onClick={() => {
                setContentType("transcript");
                if (content === SAMPLE_NOTES) setContent(SAMPLE_TRANSCRIPT);
              }}
            >
              <MessageSquare size={14} />
              <span>Transcript</span>
            </button>
            <button
              type="button"
              className={`tab-btn ${contentType === "notes" ? "active" : ""}`}
              onClick={() => {
                setContentType("notes");
                if (content === SAMPLE_TRANSCRIPT) setContent(SAMPLE_NOTES);
              }}
            >
              <FileText size={14} />
              <span>Meeting Notes</span>
            </button>
            <button
              type="button"
              className={`tab-btn ${contentType === "discussion" ? "active" : ""}`}
              onClick={() => setContentType("discussion")}
            >
              <AlignLeft size={14} />
              <span>Freeform Discussion</span>
            </button>
          </div>

          <div className="editor-wrapper">
            <textarea
              className="meeting-content-textarea"
              rows={10}
              placeholder={
                contentType === "transcript"
                  ? "Paste your meeting transcript here...\nExample:\nAlice: We need to finalize the roadmap.\nBob: I will handle the deployment."
                  : "Enter your meeting notes here...\nExample:\n- Discussed API architecture\n- Bob will finish auth module by Friday"
              }
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
          </div>

          <div className="editor-footer-presets">
            <span className="text-muted text-xs">Need an example?</span>
            <button
              type="button"
              className="btn-link text-xs"
              onClick={() => {
                setContentType("transcript");
                setContent(SAMPLE_TRANSCRIPT);
              }}
            >
              Insert Sample Transcript
            </button>
            <span className="dot-separator">•</span>
            <button
              type="button"
              className="btn-link text-xs"
              onClick={() => {
                setContentType("notes");
                setContent(SAMPLE_NOTES);
              }}
            >
              Insert Sample Notes
            </button>
          </div>
        </section>

        {/* Progressive AI Processing State */}
        {submitting && analysisStep > 0 && (
          <div className="ai-processing-banner">
            <div className="processing-header">
              <Sparkles size={18} className="text-brand-accent spinner" />
              <span className="processing-title">Analyzing meeting intelligence...</span>
            </div>
            <ul className="processing-steps-list">
              <li className={analysisStep >= 1 ? "step-done" : ""}>
                {analysisStep >= 1 ? <CheckCircle2 size={14} /> : "○"} Reading meeting content
              </li>
              <li className={analysisStep >= 2 ? "step-done" : ""}>
                {analysisStep >= 2 ? <CheckCircle2 size={14} /> : "○"} Identifying key topics
              </li>
              <li className={analysisStep >= 3 ? "step-done" : ""}>
                {analysisStep >= 3 ? <CheckCircle2 size={14} /> : "○"} Extracting decisions
              </li>
              <li className={analysisStep >= 4 ? "step-done" : ""}>
                {analysisStep >= 4 ? <CheckCircle2 size={14} /> : "○"} Finding action items & assignees
              </li>
              <li className={analysisStep >= 5 ? "step-done" : ""}>
                {analysisStep >= 5 ? <CheckCircle2 size={14} /> : "○"} Generating executive summary
              </li>
            </ul>
          </div>
        )}

        <hr className="divider" />

        {/* Step 3: Action Buttons */}
        <div className="form-actions-row">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => navigate("/meetings")}
            disabled={submitting}
          >
            Cancel
          </button>

          <div className="form-actions-right">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => handleCreate(false)}
              disabled={submitting}
            >
              Save Without Analysis
            </button>

            <button
              type="button"
              className="btn btn-primary btn-analyze-cta"
              onClick={() => handleCreate(true)}
              disabled={submitting}
            >
              {submitting ? (
                <>
                  <Loader2 size={16} className="spinner" />
                  <span>Processing...</span>
                </>
              ) : (
                <>
                  <Sparkles size={16} />
                  <span>Analyze Meeting</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CreateMeeting;

