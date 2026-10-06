import React, { useCallback, useEffect, useState } from "react"
import { BarChart3 } from "lucide-react"
import { Notice } from "../components/Notice"
import { Spinner } from "../components/Spinner"
import { api, type UsageSummary } from "../services/api"

export const MetricsDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<UsageSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setMetrics(await api.getUsageMetrics())
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load usage metrics.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const ms = (v?: number) => `${(v ?? 0).toFixed(1)} ms`

  return (
    <div>
      <header className="page-header">
        <div>
          <h1 className="page-title with-icon">
            <BarChart3 aria-hidden="true" /> Model Usage & Telemetry
          </h1>
          <p className="page-subtitle">
            Reasoning and embedding calls handled by this API process since it started.
          </p>
        </div>
        <button type="button" className="btn btn-outline" onClick={() => void load()} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </header>

      {error && <Notice tone="error">{error}</Notice>}
      {loading && !metrics && <Spinner message="Loading metrics..." />}

      {metrics && (
        <>
          <section className="kpi-grid">
            <div className="card kpi-card">
              <span className="kpi-label">Model requests</span>
              <span className="kpi-value">{metrics.total_requests}</span>
            </div>
            <div className="card kpi-card" style={{ borderLeft: "3px solid var(--accent-amber)" }}>
              <span className="kpi-label">Estimated cost (USD)</span>
              <span className="kpi-value">${metrics.total_cost_usd.toFixed(4)}</span>
            </div>
            <div className="card kpi-card" style={{ borderLeft: "3px solid var(--accent-emerald)" }}>
              <span className="kpi-label">p95 latency</span>
              <span className="kpi-value">{ms(metrics.p95_latency_ms)}</span>
            </div>
            <div className="card kpi-card" style={{ borderLeft: "3px solid var(--accent-sky)" }}>
              <span className="kpi-label">Fallback rate</span>
              <span className="kpi-value">{(metrics.fallback_rate * 100).toFixed(1)}%</span>
            </div>
          </section>

          {metrics.total_requests === 0 && (
            <Notice tone="info">
              No model calls recorded yet. Ask a question in Search &amp; QA or ingest a meeting, then refresh.
            </Notice>
          )}

          <div className="grid-2">
            <section className="card">
              <h2 className="card-title">Latency</h2>
              <dl className="stat-list">
                <div><dt>Average</dt><dd>{ms(metrics.avg_latency_ms)}</dd></div>
                <div><dt>Median (p50)</dt><dd>{ms(metrics.p50_latency_ms)}</dd></div>
                <div><dt>p95</dt><dd>{ms(metrics.p95_latency_ms)}</dd></div>
                <div><dt>p99</dt><dd>{ms(metrics.p99_latency_ms)}</dd></div>
              </dl>
            </section>
            <section className="card">
              <h2 className="card-title">Tokens</h2>
              <dl className="stat-list">
                <div><dt>Prompt tokens</dt><dd>{metrics.total_prompt_tokens}</dd></div>
                <div><dt>Completion tokens</dt><dd>{metrics.total_completion_tokens}</dd></div>
                <div><dt>Total tokens</dt><dd>{metrics.total_tokens}</dd></div>
                <div><dt>Average per request</dt><dd>{metrics.avg_tokens_per_query.toFixed(1)}</dd></div>
                <div><dt>Errors / fallbacks</dt><dd>{metrics.error_count} / {metrics.fallback_count}</dd></div>
              </dl>
            </section>
          </div>
        </>
      )}
    </div>
  )
}
export default MetricsDashboard
