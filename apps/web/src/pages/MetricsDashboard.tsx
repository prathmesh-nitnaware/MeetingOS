import React, { useEffect, useState } from "react"
import { BarChart3, Coins, Zap, ShieldAlert, Cpu } from "lucide-react"

interface UsageSummary {
  total_requests: number
  total_tokens: number
  total_prompt_tokens: number
  total_completion_tokens: number
  total_cost_usd: number
  avg_tokens_per_query: number
  avg_latency_ms: number
  p50_latency_ms: number
  p95_latency_ms: number
  p99_latency_ms: number
  fallback_count: number
  fallback_rate: number
  error_count: number
}

export const MetricsDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<UsageSummary | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchMetrics()
  }, [])

  const fetchMetrics = async () => {
    try {
      setLoading(true)
      const res = await fetch("/api/v1/admin/metrics/usage", {
        headers: { Authorization: "Bearer viewer-secret-token" },
      })
      if (res.ok) {
        const data = await res.json()
        setMetrics(data)
      }
    } catch (err) {
      console.error("Failed to fetch metrics", err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            <BarChart3 className="text-indigo-400" />
            Model Usage & Telemetry Metrics
          </h1>
          <p className="text-slate-400 mt-1">
            Aggregate provider token consumption, latency percentiles, cost tracking, and fallback rates.
          </p>
        </div>
        <button
          onClick={fetchMetrics}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-white font-medium transition text-sm"
        >
          Refresh Metrics
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-5">
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-2">
          <div className="flex justify-between items-center text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Total Requests</span>
            <Cpu size={16} className="text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {loading ? "..." : metrics?.total_requests || 0}
          </div>
          <div className="text-xs text-slate-500">Across local & LLM providers</div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-2">
          <div className="flex justify-between items-center text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Total Cost (USD)</span>
            <Coins size={16} className="text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400">
            {loading ? "..." : `$${(metrics?.total_cost_usd || 0).toFixed(4)}`}
          </div>
          <div className="text-xs text-slate-500">Based on catalog pricing per 1M tokens</div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-2">
          <div className="flex justify-between items-center text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>p95 Latency</span>
            <Zap size={16} className="text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400">
            {loading ? "..." : `${(metrics?.p95_latency_ms || 0).toFixed(1)} ms`}
          </div>
          <div className="text-xs text-slate-500">p50: {(metrics?.p50_latency_ms || 0).toFixed(1)} ms</div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-2">
          <div className="flex justify-between items-center text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Fallback Rate</span>
            <ShieldAlert size={16} className="text-sky-400" />
          </div>
          <div className="text-2xl font-bold text-sky-400">
            {loading ? "..." : `${((metrics?.fallback_rate || 0) * 100).toFixed(1)}%`}
          </div>
          <div className="text-xs text-slate-500">{metrics?.fallback_count || 0} fallbacks triggered</div>
        </div>
      </div>

      {/* Latency Percentiles Breakdown */}
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
          <h2 className="text-base font-semibold text-white">Latency Distribution</h2>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between items-center py-2 border-b border-slate-800">
              <span className="text-slate-400">Average Latency</span>
              <span className="font-mono text-slate-200 font-medium">{(metrics?.avg_latency_ms || 0).toFixed(2)} ms</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-slate-800">
              <span className="text-slate-400">Median (p50)</span>
              <span className="font-mono text-emerald-400 font-medium">{(metrics?.p50_latency_ms || 0).toFixed(2)} ms</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-slate-800">
              <span className="text-slate-400">95th Percentile (p95)</span>
              <span className="font-mono text-amber-400 font-medium">{(metrics?.p95_latency_ms || 0).toFixed(2)} ms</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-slate-400">99th Percentile (p99)</span>
              <span className="font-mono text-rose-400 font-medium">{(metrics?.p99_latency_ms || 0).toFixed(2)} ms</span>
            </div>
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
          <h2 className="text-base font-semibold text-white">Token Usage Breakdown</h2>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between items-center py-2 border-b border-slate-800">
              <span className="text-slate-400">Prompt Tokens</span>
              <span className="font-mono text-slate-200 font-medium">{metrics?.total_prompt_tokens || 0}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-slate-800">
              <span className="text-slate-400">Completion Tokens</span>
              <span className="font-mono text-slate-200 font-medium">{metrics?.total_completion_tokens || 0}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-slate-800">
              <span className="text-slate-400">Total Tokens</span>
              <span className="font-mono text-indigo-400 font-bold">{metrics?.total_tokens || 0}</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-slate-400">Avg Tokens / Query</span>
              <span className="font-mono text-slate-300 font-medium">{(metrics?.avg_tokens_per_query || 0).toFixed(1)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default MetricsDashboard
