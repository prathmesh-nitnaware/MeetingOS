import React, { useCallback, useEffect, useState } from "react"
import { AlertTriangle, CheckCircle2, Clock, GitBranch, MinusCircle, XCircle } from "lucide-react"
import { Notice } from "../components/Notice"
import { Spinner } from "../components/Spinner"
import { api, type ExecutionTrace } from "../services/api"
import { formatDateTime, humanize } from "../utils/format"

const StepIcon: React.FC<{ status: string }> = ({ status }) => {
  if (status === "completed") return <CheckCircle2 size={16} className="text-success" aria-label="completed" />
  if (status === "skipped") return <MinusCircle size={16} className="muted" aria-label="skipped" />
  return <XCircle size={16} className="text-danger" aria-label={status} />
}

export const TraceExplorer: React.FC = () => {
  const [traces, setTraces] = useState<ExecutionTrace[]>([])
  const [selected, setSelected] = useState<ExecutionTrace | null>(null)
  const [filter, setFilter] = useState("")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getTraces(50)
      setTraces(data)
      setSelected((prev) => data.find((t) => t.trace_id === prev?.trace_id) ?? data[0] ?? null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load traces.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const visible = traces.filter(
    (t) => t.query.toLowerCase().includes(filter.toLowerCase()) || t.trace_id.toLowerCase().includes(filter.toLowerCase())
  )

  return (
    <div>
      <header className="page-header">
        <div>
          <h1 className="page-title with-icon">
            <GitBranch aria-hidden="true" /> Agent Trace Explorer
          </h1>
          <p className="page-subtitle">Step-by-step record of every agentic question asked in your organization.</p>
        </div>
        <button type="button" className="btn btn-outline" onClick={() => void load()} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </header>

      {error && <Notice tone="error">{error}</Notice>}

      <div className="split-layout">
        <section className="card split-list" aria-label="Traces">
          <label htmlFor="trace-filter" className="sr-only">Filter traces</label>
          <input
            id="trace-filter"
            className="form-input"
            placeholder="Filter by question or trace ID..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          {loading && traces.length === 0 ? (
            <Spinner message="Loading traces..." />
          ) : visible.length === 0 ? (
            <p className="muted" style={{ marginTop: 16 }}>
              No traces yet. Ask a question in Search &amp; QA → Agentic reasoning.
            </p>
          ) : (
            <ul className="selectable-list">
              {visible.map((t) => (
                <li key={t.trace_id}>
                  <button
                    type="button"
                    className={`selectable-item${selected?.trace_id === t.trace_id ? " selected" : ""}`}
                    onClick={() => setSelected(t)}
                    aria-pressed={selected?.trace_id === t.trace_id}
                  >
                    <span className="selectable-meta">
                      <code>{t.trace_id}</code>
                      <span><Clock size={12} aria-hidden="true" /> {Math.round(t.total_latency_ms)} ms</span>
                    </span>
                    <span className="selectable-title">{t.query}</span>
                    <span className="selectable-meta">
                      <span className={`badge ${t.insufficient_evidence ? "badge-running" : "badge-succeeded"}`}>
                        {t.insufficient_evidence ? "Not enough evidence" : `Confidence ${Math.round(t.confidence * 100)}%`}
                      </span>
                      {t.conflicts.length > 0 && (
                        <span className="badge badge-failed">
                          <AlertTriangle size={10} aria-hidden="true" /> Changes detected
                        </span>
                      )}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="card split-detail" aria-label="Trace detail">
          {!selected ? (
            <p className="muted">Select a trace to see how it was answered.</p>
          ) : (
            <div className="stack">
              <div>
                <p className="muted small">
                  <code>{selected.trace_id}</code> · {formatDateTime(selected.created_at)}
                </p>
                <h2 className="card-title">{selected.query}</h2>
              </div>
              <div className="card inset">
                <p className="kpi-label">Answer</p>
                <p>{selected.answer}</p>
              </div>
              {selected.conflicts.length > 0 && (
                <div className="card inset">
                  <p className="kpi-label">Changes detected across meetings</p>
                  {selected.conflicts.map((c, i) => (
                    <p key={i} className="small">
                      <span className="text-warning">Earlier:</span> {c.earlier_claim}
                      <br />
                      <span className="text-success">Later:</span> {c.latest_claim}
                    </p>
                  ))}
                </div>
              )}
              <div>
                <p className="kpi-label">Agent steps</p>
                <ul className="step-list">
                  {selected.steps.map((s, i) => (
                    <li key={i} className="step-item">
                      <StepIcon status={s.status} />
                      <div>
                        <strong>{humanize(s.agent)} agent</strong> <span className="muted">· {humanize(s.status)}</span>
                        {s.latency_ms ? <span className="muted"> · {s.latency_ms.toFixed(1)} ms</span> : null}
                        {s.output_summary && <div className="muted small">{s.output_summary}</div>}
                        {s.model_name && <div className="muted small">Model: {s.model_name}</div>}
                        {s.error && <div className="text-danger small">Error: {s.error}</div>}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
              {selected.citations.length > 0 && (
                <div>
                  <p className="kpi-label">Citations</p>
                  <div className="chip-row">
                    {selected.citations.map((c, i) => (
                      <span key={i} className="chip">{c}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
export default TraceExplorer
