import React, { useState, useEffect, useMemo } from "react"
import { useNavigate } from "react-router-dom"
import { api, Decision } from "../services/api"
import {
  CheckCircle2,
  Calendar,
  Layers,
  Search,
  Plus,
  Check,
  Edit2,
  FileText,
  Clock,
  Sparkles,
  ExternalLink,
  ChevronRight,
  ShieldCheck,
  XCircle,
  FolderGit2
} from "lucide-react"

export const DecisionsPage: React.FC = () => {
  const navigate = useNavigate()
  const [decisions, setDecisions] = useState<Decision[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [editingDecisionId, setEditingDecisionId] = useState<string | null>(null)
  const [editDecisionText, setEditDecisionText] = useState("")
  const [editContextText, setEditContextText] = useState("")
  const [editStatus, setEditStatus] = useState("agreed")

  useEffect(() => {
    loadDecisions()
  }, [])

  const loadDecisions = async () => {
    try {
      setLoading(true)
      const data = await api.getDecisions()
      setDecisions(data)
    } catch (err: any) {
      setError(err.message || "Failed to load decisions")
    } finally {
      setLoading(false)
    }
  }

  const handleStartEdit = (d: Decision) => {
    setEditingDecisionId(d.id || d.decision_id || null)
    setEditDecisionText(d.decision || d.title || d.subject || "")
    setEditContextText(d.context || "")
    setEditStatus(d.status || "agreed")
  }

  const handleSaveEdit = async (id: string) => {
    try {
      const updated = await api.updateDecision(id, {
        decision: editDecisionText,
        context: editContextText,
        status: editStatus
      })
      setDecisions(prev => prev.map(d => ((d.id || d.decision_id) === id ? { ...d, ...updated } : d)))
      setEditingDecisionId(null)
    } catch (err: any) {
      alert("Failed to update decision: " + err.message)
    }
  }

  const handleReviewDecision = async (d: Decision, newReviewStatus: string) => {
    if (!d.meeting_id) return
    const decId = d.id || d.decision_id
    if (!decId) return
    try {
      await api.updateMeetingDecisionReview(d.meeting_id, decId, newReviewStatus)
      setDecisions(prev =>
        prev.map(item =>
          (item.id || item.decision_id) === decId
            ? { ...item, review_status: newReviewStatus }
            : item
        )
      )
    } catch (err: any) {
      alert("Failed to update review status: " + err.message)
    }
  }

  const filteredDecisions = useMemo(() => {
    return decisions.filter(d => {
      const decText = d.decision || d.title || d.subject || ""
      const matchesSearch =
        decText.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (d.context && d.context.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (d.meeting_title && d.meeting_title.toLowerCase().includes(searchQuery.toLowerCase()))

      const matchesStatus =
        statusFilter === "all" ? true : (d.status || "agreed") === statusFilter

      return matchesSearch && matchesStatus
    })
  }, [decisions, searchQuery, statusFilter])

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "2rem 1.5rem" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "2rem" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.25rem" }}>
            <span style={{ fontSize: "0.8125rem", color: "var(--color-primary-600)", fontWeight: "600", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Organizational Registry
            </span>
          </div>
          <h1 style={{ fontSize: "1.875rem", fontWeight: "700", color: "var(--color-text-main)", margin: 0, letterSpacing: "-0.025em" }}>
            Decisions
          </h1>
          <p style={{ color: "var(--color-text-muted)", fontSize: "0.9375rem", margin: "0.25rem 0 0 0" }}>
            Browse, search, and audit key organizational commitments and agreements backed by source transcript evidence.
          </p>
        </div>

        <button
          onClick={() => navigate("/meetings/new")}
          className="btn btn-primary"
          style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.625rem 1.25rem", fontSize: "0.875rem" }}
        >
          <Plus size={16} /> Record in Meeting
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem", alignItems: "center", justifyContent: "space-between", background: "white", padding: "1rem", borderRadius: "10px", border: "1px solid var(--color-border)", marginBottom: "1.5rem" }}>
        {/* Search */}
        <div style={{ position: "relative", minWidth: "280px", flex: 1 }}>
          <Search size={16} style={{ position: "absolute", left: "0.875rem", top: "50%", transform: "translateY(-50%)", color: "var(--color-text-muted)" }} />
          <input
            type="text"
            placeholder="Search decisions, context, or meeting..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{
              width: "100%",
              padding: "0.5625rem 0.875rem 0.5625rem 2.25rem",
              borderRadius: "6px",
              border: "1px solid var(--color-border)",
              fontSize: "0.875rem",
              outline: "none"
            }}
          />
        </div>

        {/* Status Filters */}
        <div style={{ display: "flex", gap: "0.375rem" }}>
          {[
            { id: "all", label: "All Decisions" },
            { id: "agreed", label: "Agreed" },
            { id: "proposed", label: "Proposed" },
            { id: "superseded", label: "Superseded" },
            { id: "deprecated", label: "Deprecated" }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setStatusFilter(tab.id)}
              style={{
                padding: "0.4375rem 0.875rem",
                borderRadius: "6px",
                fontSize: "0.8125rem",
                fontWeight: "500",
                cursor: "pointer",
                border: "1px solid",
                borderColor: statusFilter === tab.id ? "var(--color-primary-600)" : "transparent",
                background: statusFilter === tab.id ? "var(--color-primary-50)" : "#f8fafc",
                color: statusFilter === tab.id ? "var(--color-primary-700)" : "var(--color-text-muted)",
                transition: "all 0.15s ease"
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Decision Count & Stats Banner */}
      <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem" }}>
        <div style={{ flex: 1, background: "white", padding: "1rem 1.25rem", borderRadius: "8px", border: "1px solid var(--color-border)" }}>
          <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", textTransform: "uppercase", fontWeight: "600" }}>Total Decisions</div>
          <div style={{ fontSize: "1.5rem", fontWeight: "700", color: "var(--color-text-main)", marginTop: "0.25rem" }}>{decisions.length}</div>
        </div>
        <div style={{ flex: 1, background: "white", padding: "1rem 1.25rem", borderRadius: "8px", border: "1px solid var(--color-border)" }}>
          <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", textTransform: "uppercase", fontWeight: "600" }}>Agreed & Active</div>
          <div style={{ fontSize: "1.5rem", fontWeight: "700", color: "#16a34a", marginTop: "0.25rem" }}>
            {decisions.filter(d => (d.status || "agreed") === "agreed").length}
          </div>
        </div>
        <div style={{ flex: 1, background: "white", padding: "1rem 1.25rem", borderRadius: "8px", border: "1px solid var(--color-border)" }}>
          <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", textTransform: "uppercase", fontWeight: "600" }}>Under Consideration</div>
          <div style={{ fontSize: "1.5rem", fontWeight: "700", color: "#d97706", marginTop: "0.25rem" }}>
            {decisions.filter(d => d.status === "proposed").length}
          </div>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div style={{ padding: "4rem 2rem", textAlign: "center", color: "var(--color-text-muted)" }}>
          <div className="spinner" style={{ margin: "0 auto 1rem auto" }}></div>
          Loading organizational decisions...
        </div>
      ) : error ? (
        <div style={{ padding: "1.25rem 1.5rem", background: "#450a0a", border: "1px solid #7f1d1d", borderRadius: "8px", color: "#fca5a5", fontSize: "13.5px" }}>
          {error}
        </div>
      ) : filteredDecisions.length === 0 ? (
        <div style={{ padding: "4rem 2rem", textAlign: "center", background: "white", borderRadius: "10px", border: "1px solid var(--color-border)" }}>
          <div style={{ width: "48px", height: "48px", borderRadius: "50%", background: "var(--color-primary-50)", color: "var(--color-primary-600)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 1rem auto" }}>
            <CheckCircle2 size={24} />
          </div>
          <h3 style={{ fontSize: "1.125rem", fontWeight: "600", color: "var(--color-text-main)", marginBottom: "0.5rem" }}>
            No decisions recorded yet
          </h3>
          <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem", maxWidth: "420px", margin: "0 auto 1.5rem auto" }}>
            Decisions are extracted automatically by AI when you paste transcripts or notes into meeting workspaces.
          </p>
          <button onClick={() => navigate("/meetings/new")} className="btn btn-primary" style={{ padding: "0.5625rem 1.25rem", fontSize: "0.875rem" }}>
            <Plus size={16} style={{ marginRight: "0.375rem" }} /> Create Meeting
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {filteredDecisions.map(d => {
            const isEditing = editingDecisionId === (d.id || d.decision_id)

            return (
              <div
                key={d.id || d.decision_id}
                style={{
                  background: "white",
                  borderRadius: "10px",
                  border: "1px solid var(--color-border)",
                  padding: "1.25rem 1.5rem",
                  transition: "box-shadow 0.15s ease",
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.75rem"
                }}
              >
                {isEditing ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                    <div>
                      <label style={{ fontSize: "0.75rem", fontWeight: "600", color: "var(--color-text-muted)", display: "block", marginBottom: "0.25rem" }}>
                        Decision Title / Statement
                      </label>
                      <input
                        type="text"
                        value={editDecisionText}
                        onChange={e => setEditDecisionText(e.target.value)}
                        style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid var(--color-border)", fontSize: "0.9375rem", fontWeight: "600" }}
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: "0.75rem", fontWeight: "600", color: "var(--color-text-muted)", display: "block", marginBottom: "0.25rem" }}>
                        Context / Rationale
                      </label>
                      <textarea
                        rows={2}
                        value={editContextText}
                        onChange={e => setEditContextText(e.target.value)}
                        style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid var(--color-border)", fontSize: "0.875rem" }}
                      />
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <select
                        value={editStatus}
                        onChange={e => setEditStatus(e.target.value)}
                        style={{ padding: "0.375rem 0.75rem", borderRadius: "6px", border: "1px solid var(--color-border)", fontSize: "0.8125rem" }}
                      >
                        <option value="agreed">Agreed</option>
                        <option value="proposed">Proposed</option>
                        <option value="superseded">Superseded</option>
                        <option value="deprecated">Deprecated</option>
                      </select>
                      <div style={{ display: "flex", gap: "0.5rem" }}>
                        <button onClick={() => setEditingDecisionId(null)} className="btn btn-secondary" style={{ padding: "0.375rem 0.75rem", fontSize: "0.8125rem" }}>
                          Cancel
                        </button>
                        <button onClick={() => handleSaveEdit(d.id || d.decision_id || "")} className="btn btn-primary" style={{ padding: "0.375rem 0.875rem", fontSize: "0.8125rem" }}>
                          Save
                        </button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem" }}>
                      <div style={{ display: "flex", alignItems: "flex-start", gap: "0.75rem", flex: 1 }}>
                        <div style={{ marginTop: "0.125rem", color: "#16a34a" }}>
                          <CheckCircle2 size={18} />
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: "1rem", fontWeight: "600", color: "var(--color-text-main)", lineHeight: "1.4" }}>
                            {d.decision || d.title || d.subject}
                          </div>
                          {d.context && (
                            <div style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginTop: "0.25rem", lineHeight: "1.4" }}>
                              {d.context}
                            </div>
                          )}
                          {d.source_text && (
                            <div style={{ marginTop: "0.35rem", fontSize: "0.75rem", color: "#64748b", fontStyle: "italic", background: "#f8fafc", padding: "0.25rem 0.5rem", borderRadius: "4px", border: "1px solid #e2e8f0" }}>
                              Evidence: "{d.source_text}"
                            </div>
                          )}
                        </div>
                      </div>

                      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        {/* Review Status */}
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            padding: "0.2rem 0.5rem",
                            borderRadius: "9999px",
                            fontSize: "0.7rem",
                            fontWeight: "700",
                            textTransform: "uppercase",
                            letterSpacing: "0.025em",
                            background: d.review_status === "confirmed" ? "#dcfce7" : d.review_status === "rejected" ? "#fee2e2" : "#fef3c7",
                            color: d.review_status === "confirmed" ? "#15803d" : d.review_status === "rejected" ? "#b91c1c" : "#b45309"
                          }}
                        >
                          {d.review_status || "Needs Review"}
                        </span>

                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            padding: "0.2rem 0.5rem",
                            borderRadius: "9999px",
                            fontSize: "0.75rem",
                            fontWeight: "600",
                            textTransform: "uppercase",
                            letterSpacing: "0.025em",
                            background: (d.status || "agreed") === "agreed" ? "#dcfce7" : "#fef3c7",
                            color: (d.status || "agreed") === "agreed" ? "#15803d" : "#b45309"
                          }}
                        >
                          {d.status || "agreed"}
                        </span>

                        {d.review_status !== "confirmed" && d.meeting_id && (
                          <button
                            onClick={() => handleReviewDecision(d, "confirmed")}
                            style={{ border: "none", background: "transparent", color: "#16a34a", cursor: "pointer", padding: "0.25rem" }}
                            title="Confirm decision"
                          >
                            <ShieldCheck size={16} />
                          </button>
                        )}

                        <button
                          onClick={() => handleStartEdit(d)}
                          style={{ background: "transparent", border: "none", color: "var(--color-text-muted)", cursor: "pointer", padding: "0.25rem", borderRadius: "4px" }}
                          title="Edit decision"
                        >
                          <Edit2 size={14} />
                        </button>
                      </div>
                    </div>

                    {/* Metadata Footer */}
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: "0.5rem", borderTop: "1px solid #f1f5f9", fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                        {d.meeting_title && (
                          <div
                            onClick={() => d.meeting_id && navigate(`/meetings/${d.meeting_id}`)}
                            style={{ display: "flex", alignItems: "center", gap: "0.375rem", cursor: d.meeting_id ? "pointer" : "default", color: d.meeting_id ? "var(--color-primary-600)" : "inherit", fontWeight: "500" }}
                          >
                            <FileText size={13} />
                            <span>{d.meeting_title}</span>
                            {d.meeting_id && <ExternalLink size={11} />}
                          </div>
                        )}
                        {d.confidence && (
                          <div style={{ display: "flex", alignItems: "center", gap: "0.25rem", color: "#64748b" }}>
                            <Sparkles size={12} style={{ color: "#d97706" }} />
                            <span>Confidence: {Math.round(d.confidence * 100)}%</span>
                          </div>
                        )}
                      </div>

                      {d.created_at && (
                        <div style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
                          <Clock size={12} />
                          <span>{new Date(d.created_at).toLocaleDateString()}</span>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default DecisionsPage

