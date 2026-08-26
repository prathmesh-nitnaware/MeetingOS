import React, { useEffect, useState } from "react"
import { GitBranch, Clock, AlertTriangle, ShieldCheck, CheckCircle2, XCircle, Search } from "lucide-react"

interface AgentTraceStep {
  agent: string
  status: string
  duration_seconds?: number
  latency_ms?: number
  evidence_count?: number
  events_count?: number
  relations_count?: number
  model_name?: string
  output_summary?: string
  error?: string
}

interface ExecutionTrace {
  trace_id: string
  query_id: string
  query: string
  answer: string
  confidence: number
  insufficient_evidence: boolean
  total_latency_ms: number
  steps: AgentTraceStep[]
  citations: string[]
  conflicts: Array<{
    conflict_type: string
    earlier_meeting_id: string
    later_meeting_id: string
    earlier_claim: string
    latest_claim: string
  }>
  created_at: string
}

export const TraceExplorer: React.FC = () => {
  const [traces, setTraces] = useState<ExecutionTrace[]>([])
  const [selectedTrace, setSelectedTrace] = useState<ExecutionTrace | null>(null)
  const [searchFilter, setSearchFilter] = useState("")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchTraces()
  }, [])

  const fetchTraces = async () => {
    try {
      setLoading(true)
      const res = await fetch("/api/v1/query/traces?limit=30", {
        headers: { Authorization: "Bearer viewer-secret-token" },
      })
      if (res.ok) {
        const data = await res.json()
        setTraces(data)
        if (data.length > 0) {
          setSelectedTrace(data[0])
        }
      }
    } catch (err) {
      console.error("Failed to fetch traces", err)
    } finally {
      setLoading(false)
    }
  }

  const filteredTraces = traces.filter(
    (t) =>
      t.query.toLowerCase().includes(searchFilter.toLowerCase()) ||
      t.trace_id.toLowerCase().includes(searchFilter.toLowerCase())
  )

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            <GitBranch className="text-indigo-400" />
            Agent Trace Explorer
          </h1>
          <p className="text-slate-400 mt-1">
            Real-time execution traces, specialist routing breakdowns, and chronological conflict reconciliations.
          </p>
        </div>
        <button
          onClick={fetchTraces}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-white font-medium transition text-sm"
        >
          Refresh Traces
        </button>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Left List */}
        <div className="col-span-5 bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col h-[700px]">
          <div className="relative mb-3">
            <Search className="absolute left-3 top-2.5 text-slate-500" size={16} />
            <input
              type="text"
              placeholder="Filter by query or trace ID..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="overflow-y-auto flex-1 space-y-2 pr-1">
            {loading ? (
              <p className="text-slate-500 text-sm p-4 text-center">Loading traces...</p>
            ) : filteredTraces.length === 0 ? (
              <p className="text-slate-500 text-sm p-4 text-center">No execution traces found.</p>
            ) : (
              filteredTraces.map((trace) => (
                <div
                  key={trace.trace_id}
                  onClick={() => setSelectedTrace(trace)}
                  className={`p-3.5 rounded-lg border cursor-pointer transition ${
                    selectedTrace?.trace_id === trace.trace_id
                      ? "bg-indigo-950/40 border-indigo-500/50"
                      : "bg-slate-800/40 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <div className="flex justify-between items-start gap-2 mb-1">
                    <span className="text-xs font-mono text-indigo-400 truncate">{trace.trace_id}</span>
                    <span className="text-xs text-slate-500 flex items-center gap-1 shrink-0">
                      <Clock size={12} />
                      {trace.total_latency_ms.toFixed(1)}ms
                    </span>
                  </div>
                  <p className="text-sm font-medium text-slate-200 line-clamp-2">{trace.query}</p>
                  <div className="mt-2 flex items-center gap-2">
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        trace.insufficient_evidence
                          ? "bg-amber-950/50 text-amber-400 border border-amber-800/40"
                          : "bg-emerald-950/50 text-emerald-400 border border-emerald-800/40"
                      }`}
                    >
                      {trace.insufficient_evidence ? "Refused (Insufficient)" : `Confidence ${(trace.confidence * 100).toFixed(0)}%`}
                    </span>
                    {trace.conflicts.length > 0 && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-rose-950/50 text-rose-400 border border-rose-800/40 flex items-center gap-1">
                        <AlertTriangle size={10} />
                        Reversal Handled
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Detail Pane */}
        <div className="col-span-7 bg-slate-900/60 border border-slate-800 rounded-xl p-6 h-[700px] overflow-y-auto space-y-6">
          {selectedTrace ? (
            <>
              <div>
                <div className="flex justify-between items-center">
                  <span className="text-xs font-mono text-indigo-400">{selectedTrace.trace_id}</span>
                  <span className="text-xs text-slate-400">{new Date(selectedTrace.created_at).toLocaleString()}</span>
                </div>
                <h2 className="text-xl font-bold text-white mt-1">{selectedTrace.query}</h2>
              </div>

              <div className="bg-slate-800/60 border border-slate-700/60 rounded-lg p-4 space-y-2">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">Synthesized Answer</div>
                <p className="text-slate-200 text-sm leading-relaxed">{selectedTrace.answer}</p>
              </div>

              {/* Conflict Reconciliations */}
              {selectedTrace.conflicts.length > 0 && (
                <div className="bg-rose-950/20 border border-rose-800/40 rounded-lg p-4 space-y-3">
                  <div className="text-xs font-semibold uppercase tracking-wider text-rose-400 flex items-center gap-1.5">
                    <AlertTriangle size={14} />
                    Chronological Conflict Reconciled
                  </div>
                  {selectedTrace.conflicts.map((c, idx) => (
                    <div key={idx} className="text-xs space-y-1 bg-slate-900/50 p-2.5 rounded border border-rose-900/30">
                      <div className="text-slate-400 font-mono">Transition: {c.earlier_meeting_id} → {c.later_meeting_id}</div>
                      <div className="text-slate-300">
                        <span className="text-amber-400">Superseded:</span> {c.earlier_claim}
                      </div>
                      <div className="text-slate-200 font-medium">
                        <span className="text-emerald-400">Authoritative:</span> {c.latest_claim}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Specialist Execution Pipeline */}
              <div className="space-y-3">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">Specialist Execution Chain</div>
                <div className="space-y-2">
                  {selectedTrace.steps.map((step, idx) => (
                    <div
                      key={idx}
                      className="flex items-start gap-3 p-3 bg-slate-800/40 border border-slate-800 rounded-lg"
                    >
                      <div className="mt-0.5">
                        {step.status === "completed" ? (
                          <CheckCircle2 size={16} className="text-emerald-400" />
                        ) : (
                          <XCircle size={16} className="text-rose-400" />
                        )}
                      </div>
                      <div className="flex-1 text-xs space-y-1">
                        <div className="flex justify-between">
                          <span className="font-semibold text-slate-200 capitalize">{step.agent} Agent</span>
                          <span className="text-slate-500 font-mono">
                            {step.latency_ms ? `${step.latency_ms.toFixed(1)}ms` : step.duration_seconds ? `${(step.duration_seconds * 1000).toFixed(1)}ms` : "0ms"}
                          </span>
                        </div>
                        {step.output_summary && <div className="text-slate-400">{step.output_summary}</div>}
                        {step.model_name && (
                          <div className="text-indigo-400 font-mono">Model: {step.model_name}</div>
                        )}
                        {step.error && <div className="text-rose-400 font-mono">Error: {step.error}</div>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Citations */}
              {selectedTrace.citations.length > 0 && (
                <div className="space-y-2">
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <ShieldCheck size={14} className="text-emerald-400" />
                    Verified Citations
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {selectedTrace.citations.map((cite, i) => (
                      <span key={i} className="text-xs px-2.5 py-1 bg-slate-800 text-slate-300 rounded border border-slate-700 font-mono">
                        {cite}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-500 text-sm">
              Select a trace on the left to inspect specialist decisions.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default TraceExplorer
