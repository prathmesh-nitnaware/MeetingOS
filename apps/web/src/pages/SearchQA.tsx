import React, { useId, useState } from "react"
import { Link } from "react-router-dom"
import { AlertCircle, ArrowRight, Cpu, HelpCircle, MessageSquare, Search, TrendingUp } from "lucide-react"
import { Notice } from "../components/Notice"
import { Spinner } from "../components/Spinner"
import {
  api,
  type AgenticQueryResponse,
  type QueryPlan,
  type QueryResponse,
  type SearchResponse,
} from "../services/api"
import { endOfDayIso, formatDate, formatScore, formatSpan, humanize, startOfDayIso } from "../utils/format"

type Mode = "qa" | "agentic" | "search"

interface ModeState<T> {
  loading: boolean
  error: string | null
  result: T | null
}

const initial = <T,>(): ModeState<T> => ({ loading: false, error: null, result: null })

async function runMode<T>(set: React.Dispatch<React.SetStateAction<ModeState<T>>>, call: () => Promise<T>) {
  set((s) => ({ ...s, loading: true, error: null }))
  try {
    const result = await call()
    set({ loading: false, error: null, result })
  } catch (err) {
    set((s) => ({ ...s, loading: false, error: err instanceof Error ? err.message : "Request failed." }))
  }
}

const Confidence: React.FC<{ value: number }> = ({ value }) => (
  <div className="confidence">
    <span className="form-label">Confidence</span>
    <div className="confidence-bar-bg" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(value * 100)}>
      <div className="confidence-bar" style={{ width: `${Math.round(value * 100)}%` }}></div>
    </div>
    <strong>{Math.round(value * 100)}%</strong>
  </div>
)

const SourceLink: React.FC<{ meetingId: string; segmentId?: string | null; label?: string }> = ({ meetingId, segmentId, label }) => (
  <Link
    to={segmentId ? `/meetings/${meetingId}?highlight=${encodeURIComponent(segmentId)}` : `/meetings/${meetingId}`}
    className="link-evidence"
  >
    {label ?? "Open source"} <ArrowRight size={12} aria-hidden="true" />
  </Link>
)

export const SearchQA: React.FC = () => {
  const ids = useId()
  const [mode, setMode] = useState<Mode>("qa")

  // Grounded Q&A
  const [question, setQuestion] = useState("")
  const [qa, setQa] = useState<ModeState<QueryResponse>>(initial)
  const [showOverride, setShowOverride] = useState(false)
  const [overridePerson, setOverridePerson] = useState("")
  const [overrideTopic, setOverrideTopic] = useState("")
  const [overrideType, setOverrideType] = useState("")
  const [overrideEntities, setOverrideEntities] = useState("")

  // Agentic
  const [agenticQuestion, setAgenticQuestion] = useState("")
  const [agentic, setAgentic] = useState<ModeState<AgenticQueryResponse>>(initial)

  // Hybrid search
  const [searchQuery, setSearchQuery] = useState("")
  const [searchType, setSearchType] = useState("")
  const [searchPerson, setSearchPerson] = useState("")
  const [searchTopic, setSearchTopic] = useState("")
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")
  const [search, setSearch] = useState<ModeState<SearchResponse>>(initial)

  const handleQA = (e: React.FormEvent) => {
    e.preventDefault()
    if (!question.trim()) return
    const plan: QueryPlan | undefined = showOverride
      ? {
          person: overridePerson || undefined,
          topic: overrideTopic || undefined,
          type: overrideType || undefined,
          entities: overrideEntities.split(",").map((x) => x.trim()).filter(Boolean),
          intent: "qa",
        }
      : undefined
    void runMode(setQa, () => api.queryRAG(question.trim(), plan))
  }

  const handleAgentic = (e: React.FormEvent) => {
    e.preventDefault()
    if (!agenticQuestion.trim()) return
    void runMode(setAgentic, () => api.queryAgentic(agenticQuestion.trim()))
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    void runMode(setSearch, () =>
      api.search({
        q: searchQuery || undefined,
        type: searchType || undefined,
        person: searchPerson || undefined,
        topic: searchTopic || undefined,
        start_date: startOfDayIso(startDate),
        end_date: endOfDayIso(endDate),
      })
    )
  }

  const modes: { key: Mode; label: string; icon: React.ReactNode }[] = [
    { key: "qa", label: "Grounded Q&A", icon: <MessageSquare size={14} aria-hidden="true" /> },
    { key: "agentic", label: "Agentic reasoning", icon: <Cpu size={14} aria-hidden="true" /> },
    { key: "search", label: "Hybrid search", icon: <Search size={14} aria-hidden="true" /> },
  ]

  return (
    <div className="search-qa-page">
      <header className="page-header">
        <div>
          <h1 className="page-title">Search & Decisions Q&A</h1>
          <p className="page-subtitle">Ask questions across meetings or search the organisation's memory.</p>
        </div>
        <div className="segmented" role="tablist" aria-label="Search mode">
          {modes.map((m) => (
            <button
              key={m.key}
              type="button"
              role="tab"
              aria-selected={mode === m.key}
              className={`btn ${mode === m.key ? "btn-primary" : "btn-outline"}`}
              onClick={() => setMode(m.key)}
            >
              {m.icon}
              <span>{m.label}</span>
            </button>
          ))}
        </div>
      </header>

      {mode === "qa" && (
        <div className="search-panel">
          <form onSubmit={handleQA} className="card">
            <h2 className="card-title">Ask your organizational memory</h2>
            <label htmlFor={`${ids}-q`} className="sr-only">Question</label>
            <div className="search-box">
              <input id={`${ids}-q`} type="text" className="form-input search-input" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="e.g. Which database did we decide on?" required />
              <button type="submit" className="btn btn-primary" disabled={qa.loading}>
                {qa.loading ? "Thinking..." : "Ask"}
              </button>
            </div>
            <button type="button" className="link-evidence" style={{ marginTop: 14 }} onClick={() => setShowOverride((v) => !v)} aria-expanded={showOverride}>
              {showOverride ? "Hide advanced planner settings" : "Show advanced planner settings"}
            </button>
            {showOverride && (
              <div className="grid-2 override-panel">
                <div className="form-group">
                  <label className="form-label" htmlFor={`${ids}-op`}>Person</label>
                  <input id={`${ids}-op`} className="form-input" value={overridePerson} onChange={(e) => setOverridePerson(e.target.value)} placeholder="e.g. Rahul" />
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor={`${ids}-ot`}>Topic</label>
                  <input id={`${ids}-ot`} className="form-input" value={overrideTopic} onChange={(e) => setOverrideTopic(e.target.value)} placeholder="e.g. Database" />
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor={`${ids}-oty`}>Fact type</label>
                  <select id={`${ids}-oty`} className="form-select" value={overrideType} onChange={(e) => setOverrideType(e.target.value)}>
                    <option value="">Any</option>
                    <option value="decision">Decision</option>
                    <option value="action">Action / commitment</option>
                    <option value="issue">Issue</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor={`${ids}-oe`}>Entities (comma separated)</label>
                  <input id={`${ids}-oe`} className="form-input" value={overrideEntities} onChange={(e) => setOverrideEntities(e.target.value)} placeholder="e.g. PostgreSQL, Redis" />
                </div>
              </div>
            )}
          </form>

          {qa.loading && <Spinner message="Retrieving evidence and composing an answer..." />}
          {qa.error && <Notice tone="error">{qa.error}</Notice>}
          {!qa.loading && qa.result && (
            <div className="stack">
              <div className="card answer-card">
                <div className="answer-header">
                  <h3 className="card-title with-icon">
                    <TrendingUp size={18} aria-hidden="true" /> Answer
                  </h3>
                  <Confidence value={qa.result.confidence} />
                </div>
                <p className="answer-text">{qa.result.answer}</p>
                {qa.result.model_name && <p className="muted small">Answered by: {qa.result.model_name}</p>}
                {qa.result.reasoning_path.length > 0 && (
                  <details className="reasoning-list">
                    <summary>How this answer was produced</summary>
                    <ol>
                      {qa.result.reasoning_path.map((step, idx) => (
                        <li key={idx} className="reasoning-step">{step}</li>
                      ))}
                    </ol>
                  </details>
                )}
              </div>
              <h4 className="evidence-title">Evidence ({qa.result.evidence.length})</h4>
              {qa.result.evidence.length === 0 ? (
                <div className="card empty-state compact">
                  <HelpCircle size={32} className="empty-state-icon" aria-hidden="true" />
                  <p>No transcript evidence was returned for this question.</p>
                </div>
              ) : (
                <div className="evidence-grid">
                  {qa.result.evidence.map((ev, i) => (
                    <div key={`${ev.segment_id}-${i}`} className="card evidence-card accent-purple">
                      <div className="evidence-header">
                        <span className="muted">{formatSpan(ev.start_time, ev.end_time) ?? "Timestamp unavailable"}</span>
                      </div>
                      <p className="evidence-snippet">“{ev.text_snapshot}”</p>
                      <div className="card-actions">
                        <SourceLink meetingId={ev.meeting_id} segmentId={ev.segment_id} label="Go to the transcript" />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {mode === "agentic" && (
        <div className="search-panel">
          <form onSubmit={handleAgentic} className="card">
            <h2 className="card-title">Multi-agent reasoning</h2>
            <label htmlFor={`${ids}-aq`} className="sr-only">Question</label>
            <div className="search-box">
              <input id={`${ids}-aq`} type="text" className="form-input search-input" value={agenticQuestion} onChange={(e) => setAgenticQuestion(e.target.value)} placeholder="e.g. What happened to the storage layer decision?" required />
              <button type="submit" className="btn btn-primary" disabled={agentic.loading}>
                {agentic.loading ? "Reasoning..." : "Ask"}
              </button>
            </div>
          </form>

          {agentic.loading && <Spinner message="Running planner, retrieval, temporal and evidence agents..." />}
          {agentic.error && <Notice tone="error">{agentic.error}</Notice>}
          {!agentic.loading && agentic.result && (
            <div className="stack">
              <div className="card answer-card">
                <div className="answer-header">
                  <h3 className="card-title with-icon">
                    <Cpu size={18} aria-hidden="true" /> Answer
                  </h3>
                  <Confidence value={agentic.result.confidence} />
                </div>
                {agentic.result.insufficient_evidence && (
                  <Notice tone="info">
                    <AlertCircle size={14} aria-hidden="true" /> The meetings do not contain enough evidence to answer this.
                  </Notice>
                )}
                <p className="answer-text">{agentic.result.answer}</p>
                <p className="muted small">Agents: {agentic.result.reasoning_summary}</p>
                <table className="table compact-table">
                  <thead>
                    <tr>
                      <th scope="col">Agent</th>
                      <th scope="col">Status</th>
                      <th scope="col">Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {agentic.result.trace.map((t, idx) => (
                      <tr key={idx}>
                        <td>{humanize(t.agent)}</td>
                        <td className={t.status === "failed" ? "text-danger" : t.status === "skipped" ? "muted" : "text-success"}>{humanize(t.status)}</td>
                        <td className="muted">
                          {t.error ??
                            [
                              t.evidence_count ? `${t.evidence_count} evidence` : null,
                              t.events_count ? `${t.events_count} events` : null,
                              t.relations_count ? `${t.relations_count} relations` : null,
                              t.duration_seconds ? `${Math.round(t.duration_seconds * 1000)} ms` : null,
                            ]
                              .filter(Boolean)
                              .join(" · ")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {agentic.result.conflicts && agentic.result.conflicts.length > 0 && (
                  <div className="conflicts">
                    <h4 className="form-label">Changes detected over time</h4>
                    {agentic.result.conflicts.map((c, i) => (
                      <p key={i} className="small">
                        <span className="text-warning">Earlier:</span> {c.earlier_claim}
                        <br />
                        <span className="text-success">Later:</span> {c.latest_claim}
                      </p>
                    ))}
                  </div>
                )}
              </div>

              <h4 className="evidence-title">Evidence ({agentic.result.evidence.length})</h4>
              {agentic.result.evidence.length === 0 ? (
                <div className="card empty-state compact">
                  <HelpCircle size={32} className="empty-state-icon" aria-hidden="true" />
                  <p>No evidence was retrieved.</p>
                </div>
              ) : (
                <div className="evidence-grid">
                  {agentic.result.evidence.map((ev, i) => (
                    <div key={`${ev.segment_id}-${i}`} className="card evidence-card accent-purple">
                      <div className="evidence-header">
                        <strong>{ev.meeting_title || "Meeting"}</strong>
                        <span className="muted">
                          {formatDate(ev.meeting_date)}
                          {formatSpan(ev.start_time, ev.end_time) ? ` · ${formatSpan(ev.start_time, ev.end_time)}` : ""}
                        </span>
                      </div>
                      <p className="evidence-snippet">“{ev.content}”</p>
                      <div className="card-actions">
                        <span className="muted small">{humanize(ev.source_type)}</span>
                        <SourceLink meetingId={ev.meeting_id} segmentId={ev.segment_id} label="Go to the transcript" />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {mode === "search" && (
        <div className="search-panel">
          <form onSubmit={handleSearch} className="card">
            <h2 className="card-title">Hybrid search</h2>
            <div className="grid-2">
              <div className="form-group span-2">
                <label className="form-label" htmlFor={`${ids}-sq`}>Search text</label>
                <input id={`${ids}-sq`} type="text" className="form-input" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="e.g. storage layer decision" />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor={`${ids}-st`}>Result type</label>
                <select id={`${ids}-st`} className="form-select" value={searchType} onChange={(e) => setSearchType(e.target.value)}>
                  <option value="">All result types</option>
                  <option value="transcript">Transcript segment</option>
                  <option value="decision">Decision</option>
                  <option value="action">Action / commitment</option>
                  <option value="issue">Issue</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor={`${ids}-sp`}>Action owner</label>
                <input id={`${ids}-sp`} type="text" className="form-input" value={searchPerson} onChange={(e) => setSearchPerson(e.target.value)} placeholder="e.g. rahul" />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor={`${ids}-stp`}>Topic</label>
                <input id={`${ids}-stp`} type="text" className="form-input" value={searchTopic} onChange={(e) => setSearchTopic(e.target.value)} placeholder="e.g. Database" />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor={`${ids}-sd`}>From</label>
                <input id={`${ids}-sd`} type="date" className="form-input" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor={`${ids}-ed`}>To (inclusive)</label>
                <input id={`${ids}-ed`} type="date" className="form-input" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
              </div>
            </div>
            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={search.loading}>
                {search.loading ? "Searching..." : "Search"}
              </button>
            </div>
          </form>

          {search.loading && <Spinner message="Searching..." />}
          {search.error && <Notice tone="error">{search.error}</Notice>}
          {!search.loading && search.result && (
            <div>
              <h4 className="evidence-title">
                {search.result.total_results} result{search.result.total_results === 1 ? "" : "s"}
              </h4>
              {search.result.results.length === 0 ? (
                <div className="card empty-state compact">
                  <Search size={32} className="empty-state-icon" aria-hidden="true" />
                  <p>Nothing matched your search and filters.</p>
                </div>
              ) : (
                <div className="evidence-grid">
                  {search.result.results.map((res) => (
                    <div key={res.id} className="card evidence-card accent-sky">
                      <div className="evidence-header">
                        <strong>{res.meeting_title}</strong>
                        <span className="muted">{formatDate(res.meeting_date)}</span>
                      </div>
                      <div className="evidence-header muted small">
                        <span>{humanize(res.source_type)}{formatSpan(res.start_time, res.end_time) ? ` · ${formatSpan(res.start_time, res.end_time)}` : ""}</span>
                        <span>Relevance {formatScore(res.score)}</span>
                      </div>
                      <p className="evidence-snippet">“{res.text}”</p>
                      <div className="card-actions">
                        <SourceLink meetingId={res.meeting_id} segmentId={res.segment_id} label="Open meeting" />
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
