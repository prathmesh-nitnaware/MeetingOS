import React, { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { api, KnowledgeSummary, TopicDetail } from "../services/api"
import {
  Brain,
  Hash,
  Sparkles,
  CheckCircle2,
  CheckSquare,
  FileText,
  Clock,
  ArrowRight,
  Search,
  BookOpen,
  Calendar,
  ExternalLink,
  X,
  TrendingUp,
  GitCommit,
  Layers,
  ArrowDown
} from "lucide-react"

export const KnowledgePage: React.FC = () => {
  const navigate = useNavigate()
  const [knowledge, setKnowledge] = useState<KnowledgeSummary | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedTopicName, setSelectedTopicName] = useState<string | null>(null)
  const [topicDetail, setTopicDetail] = useState<TopicDetail | null>(null)
  const [loadingTopic, setLoadingTopic] = useState<boolean>(false)
  const [searchFilter, setSearchFilter] = useState<string>("")

  useEffect(() => {
    loadKnowledge()
  }, [])

  const loadKnowledge = async () => {
    try {
      setLoading(true)
      const data = await api.getKnowledge()
      setKnowledge(data)
    } catch (err: any) {
      setError(err.message || "Failed to load organizational knowledge")
    } finally {
      setLoading(false)
    }
  }

  const handleOpenTopic = async (topicName: string) => {
    setSelectedTopicName(topicName)
    setLoadingTopic(true)
    try {
      const detail = await api.getTopicDetail(topicName)
      setTopicDetail(detail)
    } catch (err: any) {
      console.error("Failed to load topic detail", err)
    } finally {
      setLoadingTopic(false)
    }
  }

  const handleCloseTopic = () => {
    setSelectedTopicName(null)
    setTopicDetail(null)
  }

  const filteredTopics = (knowledge?.topics || []).filter(t =>
    t.name.toLowerCase().includes(searchFilter.toLowerCase())
  )

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "2rem 1.5rem" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "2rem" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.25rem" }}>
            <span style={{ fontSize: "0.8125rem", color: "var(--color-primary-600)", fontWeight: "600", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Organizational Memory 2.0
            </span>
          </div>
          <h1 style={{ fontSize: "1.875rem", fontWeight: "700", color: "var(--color-text-main)", margin: 0, letterSpacing: "-0.025em" }}>
            Organizational Knowledge
          </h1>
          <p style={{ color: "var(--color-text-muted)", fontSize: "0.9375rem", margin: "0.25rem 0 0 0" }}>
            Explore how key topics, decisions, and action items evolve over time across meetings.
          </p>
        </div>

        <button
          onClick={() => navigate("/search")}
          className="btn btn-secondary"
          style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.625rem 1.25rem", fontSize: "0.875rem" }}
        >
          <Search size={16} /> Search Memory
        </button>
      </div>

      {loading ? (
        <div style={{ padding: "4rem 2rem", textAlign: "center", color: "var(--color-text-muted)" }}>
          <div className="spinner" style={{ margin: "0 auto 1rem auto" }}></div>
          Synthesizing organizational knowledge...
        </div>
      ) : error ? (
        <div style={{ padding: "2rem", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "8px", color: "#991b1b" }}>
          {error}
        </div>
      ) : !knowledge ? null : (
        <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
          {/* Top Metrics Cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem" }}>
            <div style={{ background: "white", padding: "1.25rem", borderRadius: "10px", border: "1px solid var(--color-border)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--color-text-muted)", fontSize: "0.8125rem", fontWeight: "600", textTransform: "uppercase" }}>
                <BookOpen size={16} style={{ color: "var(--color-primary-600)" }} /> Total Meetings
              </div>
              <div style={{ fontSize: "1.75rem", fontWeight: "700", color: "var(--color-text-main)", marginTop: "0.5rem" }}>
                {knowledge.total_meetings}
              </div>
            </div>

            <div style={{ background: "white", padding: "1.25rem", borderRadius: "10px", border: "1px solid var(--color-border)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--color-text-muted)", fontSize: "0.8125rem", fontWeight: "600", textTransform: "uppercase" }}>
                <Hash size={16} style={{ color: "#8b5cf6" }} /> Active Topics
              </div>
              <div style={{ fontSize: "1.75rem", fontWeight: "700", color: "var(--color-text-main)", marginTop: "0.5rem" }}>
                {knowledge.active_topics_count}
              </div>
            </div>

            <div style={{ background: "white", padding: "1.25rem", borderRadius: "10px", border: "1px solid var(--color-border)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--color-text-muted)", fontSize: "0.8125rem", fontWeight: "600", textTransform: "uppercase" }}>
                <CheckCircle2 size={16} style={{ color: "#16a34a" }} /> Recorded Decisions
              </div>
              <div style={{ fontSize: "1.75rem", fontWeight: "700", color: "var(--color-text-main)", marginTop: "0.5rem" }}>
                {knowledge.total_decisions}
              </div>
            </div>

            <div style={{ background: "white", padding: "1.25rem", borderRadius: "10px", border: "1px solid var(--color-border)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--color-text-muted)", fontSize: "0.8125rem", fontWeight: "600", textTransform: "uppercase" }}>
                <CheckSquare size={16} style={{ color: "#2563eb" }} /> Open Actions
              </div>
              <div style={{ fontSize: "1.75rem", fontWeight: "700", color: "var(--color-text-main)", marginTop: "0.5rem" }}>
                {knowledge.total_action_items}
              </div>
            </div>
          </div>

          {/* Recurring Topics Section */}
          <div style={{ background: "white", padding: "1.5rem", borderRadius: "10px", border: "1px solid var(--color-border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem", marginBottom: "1.25rem" }}>
              <div>
                <h3 style={{ fontSize: "1.125rem", fontWeight: "600", color: "var(--color-text-main)", margin: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <TrendingUp size={18} style={{ color: "var(--color-primary-600)" }} />
                  Recurring Discussion Topics
                </h3>
                <p style={{ color: "var(--color-text-muted)", fontSize: "0.8125rem", margin: "0.25rem 0 0 0" }}>
                  Click any topic to view its cross-meeting history, timeline evolution, decisions, and action items.
                </p>
              </div>

              <div style={{ position: "relative", minWidth: "220px" }}>
                <Search size={14} style={{ position: "absolute", left: "0.75rem", top: "50%", transform: "translateY(-50%)", color: "var(--color-text-muted)" }} />
                <input
                  type="text"
                  placeholder="Filter topics..."
                  value={searchFilter}
                  onChange={(e) => setSearchFilter(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "0.4rem 0.75rem 0.4rem 2rem",
                    borderRadius: "6px",
                    border: "1px solid var(--color-border)",
                    fontSize: "0.8125rem",
                    outline: "none"
                  }}
                />
              </div>
            </div>

            {filteredTopics.length === 0 ? (
              <div style={{ textAlign: "center", padding: "2rem", color: "var(--color-text-muted)", fontSize: "0.875rem" }}>
                No topics found. Run AI analysis on your meetings to automatically discover organizational topics.
              </div>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "1rem" }}>
                {filteredTopics.map(t => (
                  <div
                    key={t.name}
                    onClick={() => handleOpenTopic(t.name)}
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      justifyContent: "space-between",
                      padding: "1rem 1.25rem",
                      borderRadius: "8px",
                      background: selectedTopicName === t.name ? "var(--color-primary-50)" : "#f8fafc",
                      border: "1px solid",
                      borderColor: selectedTopicName === t.name ? "var(--color-primary-500)" : "#e2e8f0",
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                      boxShadow: selectedTopicName === t.name ? "0 0 0 1px var(--color-primary-500)" : "none"
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
                      <span style={{ fontWeight: "700", fontSize: "0.9375rem", color: "var(--color-text-main)", display: "flex", alignItems: "center", gap: "0.375rem" }}>
                        <Hash size={15} style={{ color: "var(--color-primary-600)" }} />
                        {t.name}
                      </span>
                      <span
                        style={{
                          fontSize: "0.75rem",
                          padding: "0.15rem 0.5rem",
                          borderRadius: "9999px",
                          background: "white",
                          color: "var(--color-primary-700)",
                          fontWeight: "600",
                          border: "1px solid #cbd5e1"
                        }}
                      >
                        {t.count} {t.count === 1 ? "meeting" : "meetings"}
                      </span>
                    </div>

                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.75rem", color: "var(--color-text-muted)", borderTop: "1px solid #e2e8f0", paddingTop: "0.5rem" }}>
                      <span>Organizational Subject</span>
                      <span style={{ color: "var(--color-primary-600)", fontWeight: "600", display: "flex", alignItems: "center", gap: "0.25rem" }}>
                        Explore evolution <ArrowRight size={12} />
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Topic Detail Drawer / Expanded View */}
          {selectedTopicName && (
            <div
              style={{
                background: "white",
                borderRadius: "12px",
                border: "2px solid var(--color-primary-500)",
                padding: "2rem",
                boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04)",
                position: "relative"
              }}
            >
              <button
                onClick={handleCloseTopic}
                style={{
                  position: "absolute",
                  right: "1.5rem",
                  top: "1.5rem",
                  background: "#f1f5f9",
                  border: "none",
                  borderRadius: "50%",
                  width: "32px",
                  height: "32px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  cursor: "pointer",
                  color: "var(--color-text-muted)"
                }}
              >
                <X size={16} />
              </button>

              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--color-primary-600)", fontWeight: "600", fontSize: "0.8125rem", textTransform: "uppercase" }}>
                <Brain size={16} /> Topic Knowledge Detail
              </div>
              <h2 style={{ fontSize: "1.5rem", fontWeight: "700", color: "var(--color-text-main)", margin: "0.25rem 0 1rem 0" }}>
                #{selectedTopicName}
              </h2>

              {loadingTopic ? (
                <div style={{ padding: "3rem", textAlign: "center", color: "var(--color-text-muted)" }}>
                  <div className="spinner" style={{ margin: "0 auto 1rem auto" }}></div>
                  Aggregating topic history and decisions...
                </div>
              ) : topicDetail ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>
                  {/* Synthesis / Current Understanding */}
                  <div style={{ background: "#f8fafc", padding: "1.25rem 1.5rem", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                    <h4 style={{ fontSize: "0.875rem", fontWeight: "700", textTransform: "uppercase", color: "var(--color-text-muted)", margin: "0 0 0.5rem 0" }}>
                      Current Organizational Understanding
                    </h4>
                    <p style={{ fontSize: "0.9375rem", color: "var(--color-text-main)", margin: 0, lineHeight: 1.6 }}>
                      Topic <strong style={{ color: "var(--color-primary-700)" }}>#{topicDetail.topic}</strong> has been discussed across{" "}
                      <strong>{topicDetail.total_meetings} meetings</strong> with{" "}
                      <strong>{topicDetail.decisions.length} recorded decisions</strong> and{" "}
                      <strong>{topicDetail.action_items.length} action items</strong>.
                    </p>
                  </div>

                  {/* Cross-Meeting Knowledge Evolution Timeline */}
                  {topicDetail.evolution && topicDetail.evolution.length > 0 && (
                    <div>
                      <h4 style={{ fontSize: "1rem", fontWeight: "700", color: "var(--color-text-main)", marginBottom: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <Clock size={16} style={{ color: "var(--color-primary-600)" }} />
                        Cross-Meeting Knowledge Evolution
                      </h4>
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", position: "relative", paddingLeft: "1.25rem", borderLeft: "2px solid #e2e8f0", marginLeft: "0.75rem" }}>
                        {topicDetail.evolution.map((ev, i) => (
                          <div
                            key={i}
                            style={{
                              position: "relative",
                              background: "#ffffff",
                              padding: "1rem",
                              borderRadius: "8px",
                              border: "1px solid #e2e8f0"
                            }}
                          >
                            <div
                              style={{
                                position: "absolute",
                                left: "-1.75rem",
                                top: "1.25rem",
                                width: "10px",
                                height: "10px",
                                borderRadius: "50%",
                                background: "var(--color-primary-600)",
                                border: "2px solid white"
                              }}
                            />
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.35rem" }}>
                              <span
                                onClick={() => navigate(`/meetings/${ev.meeting_id}`)}
                                style={{ fontSize: "0.875rem", fontWeight: "700", color: "var(--color-primary-600)", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.35rem" }}
                              >
                                {ev.meeting_title} <ExternalLink size={12} />
                              </span>
                              <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)" }}>
                                {ev.meeting_date ? new Date(ev.meeting_date).toLocaleDateString() : ""}
                              </span>
                            </div>
                            <p style={{ fontSize: "0.875rem", color: "var(--color-text-main)", margin: "0 0 0.5rem 0", lineHeight: 1.5 }}>
                              {ev.summary || "Topic discussed in this meeting."}
                            </p>
                            {(ev.decisions_count > 0 || ev.actions_count > 0) && (
                              <div style={{ display: "flex", gap: "0.5rem", fontSize: "0.75rem" }}>
                                {ev.decisions_count > 0 && (
                                  <span style={{ color: "#16a34a", fontWeight: "600" }}>
                                    ✓ {ev.decisions_count} decisions
                                  </span>
                                )}
                                {ev.actions_count > 0 && (
                                  <span style={{ color: "#2563eb", fontWeight: "600" }}>
                                    📋 {ev.actions_count} action items
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Related Decisions and Actions Grid */}
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1.5rem" }}>
                    {/* Decisions */}
                    <div>
                      <h4 style={{ fontSize: "0.9375rem", fontWeight: "700", color: "var(--color-text-main)", marginBottom: "0.75rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <CheckCircle2 size={16} style={{ color: "#16a34a" }} />
                        Related Decisions ({topicDetail.decisions.length})
                      </h4>
                      {topicDetail.decisions.length === 0 ? (
                        <div style={{ padding: "1rem", background: "#f8fafc", borderRadius: "6px", fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                          No specific decisions recorded for this topic.
                        </div>
                      ) : (
                        <div style={{ display: "flex", flexDirection: "column", gap: "0.625rem" }}>
                          {topicDetail.decisions.map(d => (
                            <div key={d.id} style={{ padding: "0.75rem 1rem", background: "#f8fafc", borderRadius: "6px", border: "1px solid #f1f5f9" }}>
                              <div style={{ fontSize: "0.875rem", fontWeight: "600", color: "var(--color-text-main)" }}>
                                {d.decision}
                              </div>
                              {d.context && (
                                <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", marginTop: "0.25rem" }}>
                                  {d.context}
                                </div>
                              )}
                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "0.5rem", fontSize: "0.75rem" }}>
                                <span
                                  onClick={() => d.meeting_id && navigate(`/meetings/${d.meeting_id}`)}
                                  style={{ color: "var(--color-primary-600)", cursor: "pointer", fontWeight: "500" }}
                                >
                                  {d.meeting_title || "Meeting"} →
                                </span>
                                <span style={{ color: "#16a34a", fontWeight: "600" }}>{d.status || "agreed"}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Action Items */}
                    <div>
                      <h4 style={{ fontSize: "0.9375rem", fontWeight: "700", color: "var(--color-text-main)", marginBottom: "0.75rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <CheckSquare size={16} style={{ color: "#2563eb" }} />
                        Related Action Items ({topicDetail.action_items.length})
                      </h4>
                      {topicDetail.action_items.length === 0 ? (
                        <div style={{ padding: "1rem", background: "#f8fafc", borderRadius: "6px", fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                          No pending action items for this topic.
                        </div>
                      ) : (
                        <div style={{ display: "flex", flexDirection: "column", gap: "0.625rem" }}>
                          {topicDetail.action_items.map(a => (
                            <div key={a.id} style={{ padding: "0.75rem 1rem", background: "#f8fafc", borderRadius: "6px", border: "1px solid #f1f5f9" }}>
                              <div style={{ fontSize: "0.875rem", fontWeight: "600", color: "var(--color-text-main)" }}>
                                {a.task || a.action}
                              </div>
                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "0.5rem", fontSize: "0.75rem" }}>
                                <span style={{ color: "var(--color-text-muted)" }}>
                                  Owner: <strong>{a.owner || "Unassigned"}</strong>
                                </span>
                                <span
                                  onClick={() => a.meeting_id && navigate(`/meetings/${a.meeting_id}`)}
                                  style={{ color: "var(--color-primary-600)", cursor: "pointer", fontWeight: "500" }}
                                >
                                  {a.meeting_title || "Meeting"} →
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          )}

          {/* Dual Column: Recent Decisions & Action Items */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))", gap: "1.5rem" }}>
            {/* Recent Decisions */}
            <div style={{ background: "white", padding: "1.5rem", borderRadius: "10px", border: "1px solid var(--color-border)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                <h3 style={{ fontSize: "1rem", fontWeight: "600", color: "var(--color-text-main)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <CheckCircle2 size={18} style={{ color: "#16a34a" }} /> Recent Organizational Decisions
                </h3>
                <button
                  onClick={() => navigate("/decisions")}
                  style={{ background: "none", border: "none", color: "var(--color-primary-600)", fontSize: "0.8125rem", fontWeight: "500", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.25rem" }}
                >
                  View all <ArrowRight size={12} />
                </button>
              </div>

              {knowledge.recent_decisions.length === 0 ? (
                <div style={{ padding: "2rem 1rem", textAlign: "center", color: "var(--color-text-muted)", fontSize: "0.875rem" }}>
                  No decisions recorded yet.
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                  {knowledge.recent_decisions.map(d => (
                    <div
                      key={d.id}
                      style={{
                        padding: "0.875rem 1rem",
                        borderRadius: "8px",
                        background: "#f8fafc",
                        border: "1px solid #f1f5f9"
                      }}
                    >
                      <div style={{ fontSize: "0.875rem", fontWeight: "600", color: "var(--color-text-main)" }}>
                        {d.decision}
                      </div>
                      {d.context && (
                        <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", marginTop: "0.25rem" }}>
                          {d.context}
                        </div>
                      )}
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "0.5rem", fontSize: "0.75rem", color: "var(--color-text-muted)" }}>
                        <span
                          onClick={() => d.meeting_id && navigate(`/meetings/${d.meeting_id}`)}
                          style={{ cursor: d.meeting_id ? "pointer" : "default", color: d.meeting_id ? "var(--color-primary-600)" : "inherit", fontWeight: "500" }}
                        >
                          {d.meeting_title || "Meeting"}
                        </span>
                        {d.created_at && <span>{new Date(d.created_at).toLocaleDateString()}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Recent Action Items */}
            <div style={{ background: "white", padding: "1.5rem", borderRadius: "10px", border: "1px solid var(--color-border)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                <h3 style={{ fontSize: "1rem", fontWeight: "600", color: "var(--color-text-main)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <CheckSquare size={18} style={{ color: "#2563eb" }} /> Outstanding Action Items
                </h3>
                <button
                  onClick={() => navigate("/action-items")}
                  style={{ background: "none", border: "none", color: "var(--color-primary-600)", fontSize: "0.8125rem", fontWeight: "500", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.25rem" }}
                >
                  View all <ArrowRight size={12} />
                </button>
              </div>

              {(!knowledge.recent_action_items || knowledge.recent_action_items.length === 0) ? (
                <div style={{ padding: "2rem 1rem", textAlign: "center", color: "var(--color-text-muted)", fontSize: "0.875rem" }}>
                  All action items completed!
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                  {knowledge.recent_action_items.map(a => (
                    <div
                      key={a.id}
                      style={{
                        padding: "0.875rem 1rem",
                        borderRadius: "8px",
                        background: "#f8fafc",
                        border: "1px solid #f1f5f9"
                      }}
                    >
                      <div style={{ fontSize: "0.875rem", fontWeight: "600", color: "var(--color-text-main)" }}>
                        {a.task || a.action}
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "0.5rem", fontSize: "0.75rem" }}>
                        <span style={{ color: "var(--color-text-muted)" }}>
                          Owner: <strong style={{ color: "var(--color-text-main)" }}>{a.owner || "Unassigned"}</strong>
                        </span>
                        <span
                          onClick={() => a.meeting_id && navigate(`/meetings/${a.meeting_id}`)}
                          style={{ color: "var(--color-primary-600)", cursor: "pointer", fontWeight: "500" }}
                        >
                          {a.meeting_title || "Meeting"} →
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default KnowledgePage

