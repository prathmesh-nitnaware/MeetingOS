import React, { useCallback, useEffect, useState } from "react"
import { Mic, Sliders, Sparkles, Waypoints } from "lucide-react"
import { Notice } from "../components/Notice"
import { Spinner } from "../components/Spinner"
import { api, type ProviderStatus } from "../services/api"

const LOCAL = new Set(["local", "local_evidence", "local_semantic", "real", "mock", "sentence_transformers", "st"])

const Ready: React.FC<{ ok: boolean; okText: string; badText: string }> = ({ ok, okText, badText }) => (
  <span className={`badge ${ok ? "badge-succeeded" : "badge-failed"}`}>{ok ? okText : badText}</span>
)

export const ProvidersSettings: React.FC = () => {
  const [status, setStatus] = useState<ProviderStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setStatus(await api.getProviderStatus())
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load provider status.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <div>
      <header className="page-header">
        <div>
          <h1 className="page-title with-icon">
            <Sliders aria-hidden="true" /> AI Providers
          </h1>
          <p className="page-subtitle">
            Which models answer questions, index meetings and transcribe audio. Configured in the server's .env file.
          </p>
        </div>
      </header>

      {error && <Notice tone="error">{error}</Notice>}
      {loading && !status && <Spinner message="Loading provider status..." />}

      {status && (
        <>
          {status.reasoner_provider === "mock" && (
            <Notice tone="info">
              The reasoner is set to <code>mock</code>, which only quotes evidence. Set MEETINGOS_REASONER_PROVIDER to
              <code> local</code>, <code>anthropic</code>, <code>openai</code> or <code>gemini</code> for real answers.
            </Notice>
          )}
          {status.asr_provider === "mock" && (
            <Notice tone="info">
              Speech-to-text is set to <code>mock</code>: uploaded audio gets a canned demo transcript. Set ASR_PROVIDER=whisper.
            </Notice>
          )}

          <div className="grid-3">
            <section className="card">
              <h2 className="card-title with-icon">
                <Sparkles size={18} aria-hidden="true" /> Question answering
              </h2>
              <dl className="stat-list">
                <div><dt>Provider</dt><dd><code>{status.reasoner_provider}</code></dd></div>
                <div><dt>Model</dt><dd><code>{status.reasoner_model}</code></dd></div>
                <div>
                  <dt>Status</dt>
                  <dd>
                    <Ready ok={status.reasoner_configured} okText={LOCAL.has(status.reasoner_provider) ? "Runs locally" : "API key set"} badText="API key missing" />
                  </dd>
                </div>
                {status.has_fallback && <div><dt>If the API fails</dt><dd>Falls back to the local evidence reasoner</dd></div>}
              </dl>
            </section>

            <section className="card">
              <h2 className="card-title with-icon">
                <Waypoints size={18} aria-hidden="true" /> Search embeddings
              </h2>
              <dl className="stat-list">
                <div><dt>Provider</dt><dd><code>{status.embedding_provider}</code></dd></div>
                <div><dt>Model</dt><dd><code>{status.embedding_model}</code></dd></div>
                <div>
                  <dt>Status</dt>
                  <dd>
                    <Ready ok={status.embedding_configured} okText={LOCAL.has(status.embedding_provider) ? "Runs locally" : "API key set"} badText="API key missing" />
                  </dd>
                </div>
              </dl>
            </section>

            <section className="card">
              <h2 className="card-title with-icon">
                <Mic size={18} aria-hidden="true" /> Speech-to-text
              </h2>
              <dl className="stat-list">
                <div><dt>Provider</dt><dd><code>{status.asr_provider}</code></dd></div>
                <div><dt>Model</dt><dd><code>{status.asr_model}</code></dd></div>
                <div><dt>Device</dt><dd>{status.hardware_device}</dd></div>
                <div><dt>Speaker separation</dt><dd>{status.diarizer_provider === "mock" ? "Demo names (mock)" : "Not available — one speaker"}</dd></div>
                <div>
                  <dt>Status</dt>
                  <dd>
                    <Ready ok={status.asr_ready} okText="Ready" badText="Not installed (uv sync --extra asr)" />
                  </dd>
                </div>
              </dl>
            </section>
          </div>

          <section className="card" style={{ marginTop: 24 }}>
            <h2 className="card-title">Supported providers</h2>
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th scope="col">Provider</th>
                    <th scope="col">Default model</th>
                    <th scope="col">Answers</th>
                    <th scope="col">Embeddings</th>
                    <th scope="col">Credentials</th>
                  </tr>
                </thead>
                <tbody>
                  {status.capabilities.map((c) => (
                    <tr key={c.name}>
                      <td>{c.display_name}</td>
                      <td><code>{c.default_model}</code></td>
                      <td>{c.supports_reasoning ? "Yes" : "—"}</td>
                      <td>{c.supports_embeddings ? "Yes" : "—"}</td>
                      <td>{c.is_configured ? "Available" : "Not configured"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  )
}
export default ProvidersSettings
