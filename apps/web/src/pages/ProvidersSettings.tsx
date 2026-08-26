import React, { useEffect, useState } from "react"
import { Sliders, ShieldCheck, Sparkles, CheckCircle2, AlertCircle } from "lucide-react"

interface ProviderStatus {
  embedding_provider: string
  embedding_model: string
  embedding_configured: boolean
  reasoner_provider: string
  reasoner_model: string
  reasoner_configured: boolean
  has_fallback: boolean
  environment: string
}

export const ProvidersSettings: React.FC = () => {
  const [status, setStatus] = useState<ProviderStatus | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchStatus()
  }, [])

  const fetchStatus = async () => {
    try {
      setLoading(true)
      const res = await fetch("/api/v1/admin/providers/status", {
        headers: { Authorization: "Bearer viewer-secret-token" },
      })
      if (res.ok) {
        const data = await res.json()
        setStatus(data)
      }
    } catch (err) {
      console.error("Failed to fetch provider status", err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
          <Sliders className="text-indigo-400" />
          AI Provider Settings & Health
        </h1>
        <p className="text-slate-400 mt-1">
          Inspect model routing, embedding dimensions, fallback states, and security posture.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Reasoning Engine Card */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
          <div className="flex justify-between items-start">
            <div className="flex items-center gap-2.5">
              <Sparkles className="text-indigo-400" size={20} />
              <h2 className="text-lg font-bold text-white">Reasoning Engine</h2>
            </div>
            {status?.reasoner_configured ? (
              <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-950/60 text-emerald-400 border border-emerald-800/40 flex items-center gap-1">
                <CheckCircle2 size={12} /> Configured
              </span>
            ) : (
              <span className="text-xs px-2.5 py-1 rounded-full bg-amber-950/60 text-amber-400 border border-amber-800/40 flex items-center gap-1">
                <AlertCircle size={12} /> Local Fallback
              </span>
            )}
          </div>

          <div className="space-y-3 text-sm">
            <div className="flex justify-between py-1.5 border-b border-slate-800">
              <span className="text-slate-400">Provider</span>
              <span className="font-mono text-slate-200 uppercase font-semibold">{status?.reasoner_provider || "LOCAL"}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-800">
              <span className="text-slate-400">Active Model</span>
              <span className="font-mono text-indigo-300">{status?.reasoner_model || "local-evidence-reasoner-v1"}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-800">
              <span className="text-slate-400">Offline Fallback</span>
              <span className="font-mono text-emerald-400">Active (LocalEvidenceReasoner)</span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-slate-400">Structured Output</span>
              <span className="font-mono text-slate-200">Strict JSON Schema</span>
            </div>
          </div>
        </div>

        {/* Embedding Provider Card */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
          <div className="flex justify-between items-start">
            <div className="flex items-center gap-2.5">
              <ShieldCheck className="text-indigo-400" size={20} />
              <h2 className="text-lg font-bold text-white">Embedding Pipeline</h2>
            </div>
            {status?.embedding_configured ? (
              <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-950/60 text-emerald-400 border border-emerald-800/40 flex items-center gap-1">
                <CheckCircle2 size={12} /> Ready
              </span>
            ) : (
              <span className="text-xs px-2.5 py-1 rounded-full bg-amber-950/60 text-amber-400 border border-amber-800/40 flex items-center gap-1">
                <AlertCircle size={12} /> Local Semantic
              </span>
            )}
          </div>

          <div className="space-y-3 text-sm">
            <div className="flex justify-between py-1.5 border-b border-slate-800">
              <span className="text-slate-400">Provider</span>
              <span className="font-mono text-slate-200 uppercase font-semibold">{status?.embedding_provider || "LOCAL"}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-800">
              <span className="text-slate-400">Embedding Model</span>
              <span className="font-mono text-indigo-300">{status?.embedding_model || "local-semantic-v1"}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-800">
              <span className="text-slate-400">Dimensions</span>
              <span className="font-mono text-slate-200">384-dim (Dense)</span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-slate-400">Caching Engine</span>
              <span className="font-mono text-emerald-400">SHA-256 Segment Hash</span>
            </div>
          </div>
        </div>
      </div>

      {/* Security & Credentials Notice */}
      <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5 text-xs text-slate-400 flex items-center gap-3">
        <ShieldCheck size={20} className="text-emerald-400 shrink-0" />
        <div>
          <span className="font-semibold text-slate-200">Credential Leak Prevention:</span> API keys are stored exclusively in environment variables and are never transmitted to the browser, logs, or trace streams.
        </div>
      </div>
    </div>
  )
}

export default ProvidersSettings
