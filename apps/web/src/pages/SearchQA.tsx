import React, { useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { api, QueryResponse, SearchResponse, QueryPlan, AgenticQueryResponse } from "../services/api"
import { Spinner } from "../components/Spinner"
import {
  Search,
  MessageSquare,
  Filter,
  Activity,
  AlertCircle,
  HelpCircle,
  Calendar,
  User,
  ArrowRight,
  TrendingUp,
  Cpu
} from "lucide-react"

export const SearchQA: React.FC = () => {
  const navigate = useNavigate()
  const [activeMode, setActiveMode] = useState<"qa" | "agentic" | "search">("qa")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Grounded QA States
  const [question, setQuestion] = useState("")
  const [qaResponse, setQaResponse] = useState<QueryResponse | null>(null)
  
  // Agentic QA States
  const [agenticQuestion, setAgenticQuestion] = useState("")
  const [agenticResponse, setAgenticResponse] = useState<AgenticQueryResponse | null>(null)
  
  // Advanced Query Plan Override States
  const [showOverride, setShowOverride] = useState(false)
  const [overridePerson, setOverridePerson] = useState("")
  const [overrideTopic, setOverrideTopic] = useState("")
  const [overrideType, setOverrideType] = useState("")
  const [overrideEntities, setOverrideEntities] = useState("")
  const [overrideIntent, setOverrideIntent] = useState("qa")

  // Hybrid Search States
  const [searchQuery, setSearchQuery] = useState("")
  const [searchType, setSearchType] = useState("")
  const [searchPerson, setSearchPerson] = useState("")
  const [searchTopic, setSearchTopic] = useState("")
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null)

  const handleAgentic = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!agenticQuestion.trim()) return

    setLoading(true)
    setError(null)
    setAgenticResponse(null)

    try {
      const res = await api.queryAgentic(agenticQuestion)
      setAgenticResponse(res)
    } catch (err: any) {
      setError(err.message || "Failed to execute agentic query.")
    } finally {
      setLoading(false)
    }
  }

  const handleQA = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!question.trim()) return

    setLoading(true)
    setError(null)
    setQaResponse(null)

    try {
      let planOverride: QueryPlan | undefined = undefined
      if (showOverride) {
        planOverride = {
          person: overridePerson || undefined,
          topic: overrideTopic || undefined,
          type: overrideType || undefined,
          entities: overrideEntities ? overrideEntities.split(",").map(e => e.trim()).filter(Boolean) : [],
          intent: overrideIntent,
        }
      }

      const res = await api.queryRAG(question, planOverride)
      setQaResponse(res)
    } catch (err: any) {
      setError(err.message || "Failed to retrieve grounded QA answer.")
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSearchResults(null)

    try {
      const filters = {
        q: searchQuery || undefined,
        type: searchType || undefined,
        person: searchPerson || undefined,
        topic: searchTopic || undefined,
        start_date: startDate ? new Date(startDate).toISOString() : undefined,
        end_date: endDate ? new Date(endDate).toISOString() : undefined,
      }
      const res = await api.search(filters)
      setSearchResults(res)
    } catch (err: any) {
      setError(err.message || "Search query failed.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="search-qa-page">
      <header className="page-header">
        <div>
          <h1 className="page-title">Search & Decisions QA</h1>
          <p className="page-subtitle">Ask questions across meetings or run multi-channel hybrid searches.</p>
        </div>
        <div style={{ display: "flex", gap: "8px", background: "var(--bg-glass)", border: "1px solid var(--border-light)", borderRadius: "8px", padding: "4px" }}>
          <button
            className={`btn ${activeMode === "qa" ? "btn-primary" : "btn-outline"}`}
            style={{ padding: "8px 16px" }}
            onClick={() => { setActiveMode("qa"); setError(null); }}
          >
            <MessageSquare size={14} />
            <span>Grounded QA</span>
          </button>
          <button
            className={`btn ${activeMode === "agentic" ? "btn-primary" : "btn-outline"}`}
            style={{ padding: "8px 16px" }}
            onClick={() => { setActiveMode("agentic"); setError(null); }}
          >
            <Cpu size={14} />
            <span>Agentic Reasoning</span>
          </button>
          <button
            className={`btn ${activeMode === "search" ? "btn-primary" : "btn-outline"}`}
            style={{ padding: "8px 16px" }}
            onClick={() => { setActiveMode("search"); setError(null); }}
          >
            <Search size={14} />
            <span>Hybrid Search</span>
          </button>
        </div>
      </header>

      {error && (
        <div className="error-state">
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {activeMode === "qa" && (
        <div className="search-panel">
          <form onSubmit={handleQA} className="card" style={{ padding: "24px" }}>
            <h2 className="card-title">Ask Organizational Memory</h2>
            <div className="search-box">
              <input
                type="text"
                className="form-input search-input"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="e.g. Why are we adopting PostgreSQL instead of MongoDB?"
                required
              />
              <button type="submit" className="btn btn-primary" style={{ padding: "0 28px" }} disabled={loading}>
                {loading ? "Thinking..." : "Ask"}
              </button>
            </div>

            <div style={{ marginTop: "16px" }}>
              <button
                type="button"
                className="link-evidence"
                style={{ fontSize: "13px" }}
                onClick={() => setShowOverride(!showOverride)}
              >
                {showOverride ? "Hide Advanced Planner Parameters" : "Show Advanced Planner Parameters"}
              </button>

              {showOverride && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginTop: "14px", padding: "16px", border: "1px solid var(--border-light)", borderRadius: "8px", backgroundColor: "rgba(0,0,0,0.15)" }}>
                  <div className="form-group">
                    <label className="form-label">Plan Override: Person</label>
                    <input
                      type="text"
                      className="form-input"
                      value={overridePerson}
                      onChange={(e) => setOverridePerson(e.target.value)}
                      placeholder="e.g. Rahul"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Plan Override: Topic</label>
                    <input
                      type="text"
                      className="form-input"
                      value={overrideTopic}
                      onChange={(e) => setOverrideTopic(e.target.value)}
                      placeholder="e.g. Database"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Plan Override: Type</label>
                    <select
                      className="form-select"
                      value={overrideType}
                      onChange={(e) => setOverrideType(e.target.value)}
                    >
                      <option value="">(None)</option>
                      <option value="decision">Decision</option>
                      <option value="action">Action / Commitment</option>
                      <option value="issue">Issue</option>
                      <option value="timeline">Timeline</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Plan Override: Entities (comma separated)</label>
                    <input
                      type="text"
                      className="form-input"
                      value={overrideEntities}
                      onChange={(e) => setOverrideEntities(e.target.value)}
                      placeholder="e.g. PostgreSQL, Redis"
                    />
                  </div>
                </div>
              )}
            </div>
          </form>

          {loading && <Spinner message="Querying RAG and synthesizing answer..." />}

          {qaResponse && (
            <div className="search-results-panel" style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
              <div className="card answer-card">
                <div className="answer-header">
                  <h3 className="card-title" style={{ margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                    <TrendingUp size={18} className="text-accent-indigo" />
                    <span>Grounded Answer Synthesis</span>
                  </h3>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span className="form-label" style={{ margin: 0 }}>Confidence:</span>
                    <div className="confidence-bar-bg">
                      <div className="confidence-bar" style={{ width: `${qaResponse.confidence * 100}%` }}></div>
                    </div>
                    <span style={{ fontSize: "12px", fontWeight: 700 }}>
                      {Math.round(qaResponse.confidence * 100)}%
                    </span>
                  </div>
                </div>
                <p className="answer-text">{qaResponse.answer}</p>
                
                {qaResponse.reasoning_path && qaResponse.reasoning_path.length > 0 && (
                  <div className="reasoning-list">
                    <span style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)", marginBottom: "4px" }}>Reasoning Steps:</span>
                    {qaResponse.reasoning_path.map((step, idx) => (
                      <div key={idx} className="reasoning-step">
                        <span>[{idx + 1}]</span>
                        <span>{step}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <h4 className="evidence-title">Retrieved Evidence & Citations</h4>
                {qaResponse.evidence.length === 0 ? (
                  <div className="card empty-state" style={{ padding: "30px 0" }}>
                    <HelpCircle size={32} className="empty-state-icon" />
                    <p>No direct transcript evidence links returned for this query.</p>
                  </div>
                ) : (
                  <div className="evidence-grid">
                    {qaResponse.evidence.map((ev, i) => (
                      <div key={i} className="card evidence-card" style={{ borderLeft: "3px solid var(--accent-purple)" }}>
                        <div className="evidence-header">
                          <span style={{ fontWeight: 600 }}>Citing segment <code>{ev.segment_id}</code></span>
                          <span>
                            Timestamp: {Math.floor(ev.start_time / 60)}:
                            {String(Math.floor(ev.start_time % 60)).padStart(2, "0")} -{" "}
                            {Math.floor(ev.end_time / 60)}:
                            {String(Math.floor(ev.end_time % 60)).padStart(2, "0")}
                          </span>
                        </div>
                        <p className="evidence-snippet">"{ev.text_snapshot}"</p>
                        <div style={{ marginTop: "12px", textAlign: "right" }}>
                          <button
                            className="link-evidence"
                            style={{ fontSize: "12px" }}
                            onClick={() => navigate(`/meetings/${ev.meeting_id}?highlight=${ev.segment_id}`)}
                          >
                            Go to Source Segment <ArrowRight size={12} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {activeMode === "agentic" && (
        <div className="search-panel">
          <form onSubmit={handleAgentic} className="card" style={{ padding: "24px" }}>
            <h2 className="card-title">Ask Agentic Organizational Reasoning</h2>
            <div className="search-box">
              <input
                type="text"
                className="form-input search-input"
                value={agenticQuestion}
                onChange={(e) => setAgenticQuestion(e.target.value)}
                placeholder="e.g. Why was PostgreSQL chosen instead of MongoDB?"
                required
              />
              <button type="submit" className="btn btn-primary" style={{ padding: "0 28px" }} disabled={loading}>
                {loading ? "Reasoning..." : "Execute"}
              </button>
            </div>
          </form>

          {loading && <Spinner message="Orchestrating agent workflow and synthesizing grounded answer..." />}

          {agenticResponse && (
            <div className="search-results-panel" style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
              <div className="card answer-card">
                <div className="answer-header">
                  <h3 className="card-title" style={{ margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                    <Cpu size={18} style={{ color: "var(--accent-purple)" }} />
                    <span>Agentic Answer Synthesis</span>
                  </h3>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span className="form-label" style={{ margin: 0 }}>Confidence:</span>
                    <div className="confidence-bar-bg">
                      <div className="confidence-bar" style={{ width: `${agenticResponse.confidence * 100}%` }}></div>
                    </div>
                    <span style={{ fontSize: "12px", fontWeight: 700 }}>
                      {Math.round(agenticResponse.confidence * 100)}%
                    </span>
                  </div>
                </div>
                
                {agenticResponse.insufficient_evidence && (
                  <div className="error-state" style={{ marginTop: "12px", marginBottom: "12px", background: "rgba(220, 53, 69, 0.1)", border: "1px solid rgba(220, 53, 69, 0.3)", color: "#ea868f" }}>
                    <AlertCircle size={16} />
                    <span>INSUFFICIENT EVIDENCE: Unconfirmed assertions rejected.</span>
                  </div>
                )}
                
                <p className="answer-text" style={{ fontStyle: agenticResponse.insufficient_evidence ? "italic" : "normal" }}>
                  {agenticResponse.answer}
                </p>

                {agenticResponse.reasoning_summary && (
                  <div style={{ marginTop: "16px", display: "flex", flexWrap: "wrap", alignItems: "center", gap: "8px" }}>
                    <span style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)" }}>Agent Flow:</span>
                    <code style={{ fontSize: "12px", background: "rgba(255,255,255,0.08)", padding: "4px 8px", borderRadius: "4px", color: "#a78bfa" }}>
                      {agenticResponse.reasoning_summary}
                    </code>
                  </div>
                )}

                {agenticResponse.trace && agenticResponse.trace.length > 0 && (
                  <div className="reasoning-list" style={{ marginTop: "20px" }}>
                    <span style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)", marginBottom: "8px", display: "block" }}>Agent Trace Metrics:</span>
                    {agenticResponse.trace.map((t, idx) => (
                      <div key={idx} className="reasoning-step" style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                        <span style={{ fontWeight: 600 }}>{t.agent.charAt(0).toUpperCase() + t.agent.slice(1)} Agent</span>
                        <span style={{ color: t.status === "completed" ? "#34d399" : t.status === "skipped" ? "var(--text-muted)" : "#f87171" }}>
                          {t.status.toUpperCase()} {t.duration_seconds !== undefined && t.duration_seconds > 0 ? `(${t.duration_seconds}s)` : ""}
                          {t.evidence_count !== undefined && t.evidence_count > 0 ? ` [${t.evidence_count} evidence]` : ""}
                          {t.events_count !== undefined && t.events_count > 0 ? ` [${t.events_count} events]` : ""}
                          {t.relations_count !== undefined && t.relations_count > 0 ? ` [${t.relations_count} relations]` : ""}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {agenticResponse.citations && agenticResponse.citations.length > 0 && (
                  <div style={{ marginTop: "20px", borderTop: "1px solid var(--border-light)", paddingTop: "12px" }}>
                    <span style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)", display: "block", marginBottom: "6px" }}>Source Citations:</span>
                    <ul style={{ paddingLeft: "16px", margin: 0, fontSize: "13px", display: "flex", flexDirection: "column", gap: "4px" }}>
                      {agenticResponse.citations.map((c, i) => (
                        <li key={i}>{c}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              <div>
                <h4 className="evidence-title">Retrieved Evidence & Citations</h4>
                {agenticResponse.evidence.length === 0 ? (
                  <div className="card empty-state" style={{ padding: "30px 0" }}>
                    <HelpCircle size={32} className="empty-state-icon" />
                    <p>No direct transcript evidence links returned for this query.</p>
                  </div>
                ) : (
                  <div className="evidence-grid">
                    {agenticResponse.evidence.map((ev, i) => (
                      <div key={i} className="card evidence-card" style={{ borderLeft: "3px solid var(--accent-purple)" }}>
                        <div className="evidence-header">
                          <span style={{ fontWeight: 600 }}>Citing segment <code>{ev.segment_id}</code></span>
                          <span>
                            Timestamp: {Math.floor(ev.start_time / 60)}:
                            {String(Math.floor(ev.start_time % 60)).padStart(2, "0")} -{" "}
                            {Math.floor(ev.end_time / 60)}:
                            {String(Math.floor(ev.end_time % 60)).padStart(2, "0")}
                          </span>
                        </div>
                        <p className="evidence-snippet">"{ev.content}"</p>
                        <div style={{ marginTop: "12px", textAlign: "right" }}>
                          <button
                            className="link-evidence"
                            style={{ fontSize: "12px" }}
                            onClick={() => navigate(`/meetings/${ev.meeting_id}?highlight=${ev.segment_id}`)}
                          >
                            Go to Source Segment <ArrowRight size={12} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {activeMode === "search" && (
        <div className="search-panel">
          <form onSubmit={handleSearch} className="card" style={{ padding: "24px" }}>
            <h2 className="card-title">Run Hybrid Relational/Vector Search</h2>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <div className="form-group" style={{ gridColumn: "1 / -1" }}>
                <label className="form-label">Search Query (q)</label>
                <input
                  type="text"
                  className="form-input"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="e.g. Postgres vs Mongo decision"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Result Type Filter</label>
                <select className="form-select" value={searchType} onChange={(e) => setSearchType(e.target.value)}>
                  <option value="">All Result Types</option>
                  <option value="transcript">Transcript Segment</option>
                  <option value="decision">Decision</option>
                  <option value="action">Action / Commitment</option>
                  <option value="issue">Issue</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Associated Person</label>
                <input
                  type="text"
                  className="form-input"
                  value={searchPerson}
                  onChange={(e) => setSearchPerson(e.target.value)}
                  placeholder="e.g. Rahul"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Associated Topic</label>
                <input
                  type="text"
                  className="form-input"
                  value={searchTopic}
                  onChange={(e) => setSearchTopic(e.target.value)}
                  placeholder="e.g. Database"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Start Date</label>
                <input
                  type="date"
                  className="form-input"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">End Date</label>
                <input
                  type="date"
                  className="form-input"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                />
              </div>
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "20px" }}>
              <button type="submit" className="btn btn-primary" style={{ padding: "10px 24px" }} disabled={loading}>
                {loading ? "Searching..." : "Search"}
              </button>
            </div>
          </form>

          {loading && <Spinner message="Searching organizational memory..." />}

          {searchResults && (
            <div>
              <h4 className="evidence-title">Search Results ({searchResults.total_results} found)</h4>
              {searchResults.results.length === 0 ? (
                <div className="card empty-state" style={{ padding: "40px 0" }}>
                  <Search size={48} className="empty-state-icon" />
                  <p>No records matched your search query and filters.</p>
                </div>
              ) : (
                <div className="evidence-grid">
                  {searchResults.results.map((res) => (
                    <div key={res.id} className="card evidence-card" style={{ borderLeft: "3px solid var(--accent-sky)" }}>
                      <div className="evidence-header">
                        <span style={{ fontWeight: 600, color: "var(--accent-sky)" }}>
                          {res.meeting_title}
                        </span>
                        <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                          <Calendar size={12} />
                          {new Date(res.meeting_date).toLocaleDateString()}
                        </span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", margin: "6px 0", fontSize: "11px", color: "var(--text-muted)" }}>
                        <span>Type: <code>{res.source_type}</code></span>
                        <span>Score: <code>{res.score}</code></span>
                      </div>
                      <p className="evidence-snippet">"{res.text}"</p>
                      
                      <div style={{ marginTop: "12px", display: "flex", justifyContent: "flex-end" }}>
                        <button
                          className="link-evidence"
                          style={{ fontSize: "12px" }}
                          onClick={() => {
                            if (res.segment_id) {
                              navigate(`/meetings/${res.meeting_id}?highlight=${res.segment_id}`)
                            } else {
                              navigate(`/meetings/${res.meeting_id}`)
                            }
                          }}
                        >
                          Open Meeting View <ArrowRight size={12} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
export default SearchQA
