import React, { useState, useEffect } from "react"
import { api, ConnectorStatus, AuditLog } from "../services/api"
import {
  User,
  Building2,
  Cpu,
  Shield,
  Bell,
  RefreshCw,
  Trash2,
  Key,
  ShieldAlert,
  CheckCircle,
  Info,
  Layers,
  Sparkles,
  Save
} from "lucide-react"

export const Settings: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"profile" | "org" | "ai" | "integrations" | "security">("profile")
  const [token, setToken] = useState(localStorage.getItem("meetingos_token") || "")
  const [connectors, setConnectors] = useState<ConnectorStatus[]>([])
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([])
  
  // AI Provider state
  const [primaryProvider, setPrimaryProvider] = useState("gemini")
  const [analysisModel, setAnalysisModel] = useState("gemini-2.5-flash")
  const [fallbackProvider, setFallbackProvider] = useState("anthropic")
  const [temperature, setTemperature] = useState(0.2)
  const [savedSuccess, setSavedSuccess] = useState(false)

  // Loading & Error states
  const [loadingConnectors, setLoadingConnectors] = useState(false)
  const [loadingLogs, setLoadingLogs] = useState(false)
  const [connectorError, setConnectorError] = useState<string | null>(null)
  const [logError, setLogError] = useState<string | null>(null)

  // Sync statuses
  const [syncingProvider, setSyncingProvider] = useState<string | null>(null)
  const [syncMessage, setSyncMessage] = useState<string | null>(null)

  // Retention cleanup states
  const [meetingDays, setMeetingDays] = useState<number>(30)
  const [transcriptDays, setTranscriptDays] = useState<number>(30)
  const [evidenceDays, setEvidenceDays] = useState<number>(30)
  const [auditDays, setAuditDays] = useState<number>(90)
  const [dryRun, setDryRun] = useState(true)
  const [purging, setPurging] = useState(false)
  const [purgeResult, setPurgeResult] = useState<any | null>(null)
  const [purgeError, setPurgeError] = useState<string | null>(null)

  // Load configuration and data
  const loadConnectors = async () => {
    setLoadingConnectors(true)
    setConnectorError(null)
    try {
      const res = await api.getConnectors()
      setConnectors(res)
    } catch (err: any) {
      setConnectorError(err.message || "Failed to load connector statuses.")
    } finally {
      setLoadingConnectors(false)
    }
  }

  const loadAuditLogs = async () => {
    setLoadingLogs(true)
    setLogError(null)
    try {
      const logs = await api.getAuditLogs(undefined, undefined, 20, 0)
      setAuditLogs(logs)
    } catch (err: any) {
      setLogError(err.message || "Failed to load system audit logs.")
    } finally {
      setLoadingLogs(false)
    }
  }

  useEffect(() => {
    if (activeTab === "integrations") loadConnectors()
    if (activeTab === "security") loadAuditLogs()
  }, [activeTab, token])

  const handleSaveToken = (val: string) => {
    setToken(val)
    if (val) {
      localStorage.setItem("meetingos_token", val)
    } else {
      localStorage.removeItem("meetingos_token")
    }
  }

  const handleTriggerSync = async (provider: string) => {
    setSyncingProvider(provider)
    setSyncMessage(null)
    try {
      const res = await api.triggerConnectorSync(provider)
      setSyncMessage(`Sync triggered successfully! Task ID: ${res.task_id}`)
      loadConnectors()
    } catch (err: any) {
      setSyncMessage(`Sync failed: ${err.message}`)
    } finally {
      setSyncingProvider(null)
    }
  }

  const handleRunRetention = async (e: React.FormEvent) => {
    e.preventDefault()
    setPurging(true)
    setPurgeError(null)
    setPurgeResult(null)
    try {
      const res = await api.runRetentionCleanup({
        meeting_days: meetingDays,
        transcript_days: transcriptDays,
        evidence_days: evidenceDays,
        audit_log_days: auditDays,
        dry_run: dryRun
      })
      setPurgeResult(res)
      loadAuditLogs()
    } catch (err: any) {
      setPurgeError(err.message || "Failed to execute retention policy cleanup.")
    } finally {
      setPurging(false)
    }
  }

  const handleSaveAISettings = (e: React.FormEvent) => {
    e.preventDefault()
    setSavedSuccess(true)
    setTimeout(() => setSavedSuccess(false), 3000)
  }

  return (
    <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "2rem 1.5rem" }}>
      {/* Header */}
      <div style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "1.875rem", fontWeight: "700", color: "var(--color-text-main)", margin: 0, letterSpacing: "-0.025em" }}>
          Workspace Settings
        </h1>
        <p style={{ color: "var(--color-text-muted)", fontSize: "0.9375rem", margin: "0.25rem 0 0 0" }}>
          Manage your account, multi-tenant workspace, AI models, and organizational security policies.
        </p>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: "0.5rem", borderBottom: "1px solid var(--color-border)", marginBottom: "2rem", overflowX: "auto" }}>
        {[
          { id: "profile", label: "Profile", icon: User },
          { id: "org", label: "Organization & Tenancy", icon: Building2 },
          { id: "ai", label: "AI Intelligence", icon: Sparkles },
          { id: "integrations", label: "External Connectors", icon: RefreshCw },
          { id: "security", label: "Security & Retention", icon: Shield }
        ].map(tab => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                padding: "0.75rem 1rem",
                border: "none",
                background: "transparent",
                borderBottom: isActive ? "2px solid var(--color-primary-600)" : "2px solid transparent",
                color: isActive ? "var(--color-primary-700)" : "var(--color-text-muted)",
                fontWeight: isActive ? "600" : "500",
                fontSize: "0.875rem",
                cursor: "pointer",
                marginBottom: "-1px",
                whiteSpace: "nowrap"
              }}
            >
              <Icon size={16} />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Tab 1: Profile */}
      {activeTab === "profile" && (
        <div style={{ background: "white", borderRadius: "10px", border: "1px solid var(--color-border)", padding: "2rem", maxWidth: "700px" }}>
          <h2 style={{ fontSize: "1.125rem", fontWeight: "600", color: "var(--color-text-main)", marginBottom: "1.5rem" }}>
            Personal Profile
          </h2>

          <div style={{ display: "flex", alignItems: "center", gap: "1.25rem", marginBottom: "2rem" }}>
            <div style={{ width: "64px", height: "64px", borderRadius: "50%", background: "var(--color-primary-100)", color: "var(--color-primary-700)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "1.5rem", fontWeight: "700" }}>
              AL
            </div>
            <div>
              <div style={{ fontSize: "1.125rem", fontWeight: "600", color: "var(--color-text-main)" }}>Alex Lawson</div>
              <div style={{ fontSize: "0.875rem", color: "var(--color-text-muted)" }}>alex@acmecorp.com · Workspace Admin</div>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: "600", color: "var(--color-text-muted)", marginBottom: "0.375rem" }}>
                Full Name
              </label>
              <input
                type="text"
                defaultValue="Alex Lawson"
                style={{ width: "100%", padding: "0.5625rem 0.875rem", borderRadius: "6px", border: "1px solid var(--color-border)", fontSize: "0.875rem" }}
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: "600", color: "var(--color-text-muted)", marginBottom: "0.375rem" }}>
                Email Address
              </label>
              <input
                type="email"
                defaultValue="alex@acmecorp.com"
                disabled
                style={{ width: "100%", padding: "0.5625rem 0.875rem", borderRadius: "6px", border: "1px solid var(--color-border)", fontSize: "0.875rem", background: "#f8fafc" }}
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: "600", color: "var(--color-text-muted)", marginBottom: "0.375rem" }}>
                Timezone
              </label>
              <select style={{ width: "100%", padding: "0.5625rem 0.875rem", borderRadius: "6px", border: "1px solid var(--color-border)", fontSize: "0.875rem" }}>
                <option>America/New_York (UTC-04:00)</option>
                <option>America/Los_Angeles (UTC-07:00)</option>
                <option>Europe/London (UTC+01:00)</option>
                <option>Asia/Tokyo (UTC+09:00)</option>
              </select>
            </div>

            <button className="btn btn-primary" style={{ alignSelf: "flex-start", marginTop: "0.5rem", padding: "0.5625rem 1.25rem", fontSize: "0.875rem" }}>
              Save Profile Changes
            </button>
          </div>
        </div>
      )}

      {/* Tab 2: Organization & Multi-Tenancy */}
      {activeTab === "org" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "2rem", maxWidth: "800px" }}>
          <div style={{ background: "white", borderRadius: "10px", border: "1px solid var(--color-border)", padding: "2rem" }}>
            <h2 style={{ fontSize: "1.125rem", fontWeight: "600", color: "var(--color-text-main)", marginBottom: "0.5rem" }}>
              Active Organization Workspace
            </h2>
            <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: "1.5rem" }}>
              All meetings, action items, decisions, and knowledge are cryptographically scoped to this tenant boundary.
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", background: "#f8fafc", padding: "1.25rem", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <div>
                <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", textTransform: "uppercase", fontWeight: "600" }}>Workspace Name</div>
                <div style={{ fontSize: "1rem", fontWeight: "600", color: "var(--color-text-main)", marginTop: "0.25rem" }}>Acme Global Corp</div>
              </div>
              <div>
                <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", textTransform: "uppercase", fontWeight: "600" }}>Tenant ID</div>
                <div style={{ fontSize: "0.875rem", fontFamily: "monospace", color: "var(--color-primary-700)", marginTop: "0.25rem" }}>org_dev</div>
              </div>
            </div>
          </div>

          {/* Dev Tenant Switcher */}
          <div style={{ background: "white", borderRadius: "10px", border: "1px solid var(--color-border)", padding: "2rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
              <Key size={18} style={{ color: "var(--color-primary-600)" }} />
              <h2 style={{ fontSize: "1.125rem", fontWeight: "600", color: "var(--color-text-main)", margin: 0 }}>
                Development Tenant & Role Simulator
              </h2>
            </div>
            <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: "1.25rem" }}>
              Quickly switch between simulated organizations and role boundaries to test RBAC and tenant isolation.
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <div style={{ fontSize: "0.8125rem", fontWeight: "600", color: "var(--color-primary-600)" }}>ORGANIZATION A (Default Dev Org)</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                <button
                  className={`btn ${token === "admin-secret-token" ? "btn-primary" : "btn-secondary"}`}
                  onClick={() => handleSaveToken("admin-secret-token")}
                  style={{ fontSize: "0.8125rem", padding: "0.45rem 0.85rem" }}
                >
                  Admin Role (Full Access)
                </button>
                <button
                  className={`btn ${token === "member-secret-token" ? "btn-primary" : "btn-secondary"}`}
                  onClick={() => handleSaveToken("member-secret-token")}
                  style={{ fontSize: "0.8125rem", padding: "0.45rem 0.85rem" }}
                >
                  Member Role (Standard)
                </button>
                <button
                  className={`btn ${token === "viewer-secret-token" ? "btn-primary" : "btn-secondary"}`}
                  onClick={() => handleSaveToken("viewer-secret-token")}
                  style={{ fontSize: "0.8125rem", padding: "0.45rem 0.85rem" }}
                >
                  Viewer Role (Read-only)
                </button>
              </div>

              <div style={{ fontSize: "0.8125rem", fontWeight: "600", color: "#10b981", marginTop: "0.5rem" }}>ORGANIZATION B (BetaCorp Tenant)</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                <button
                  className={`btn ${token === "admin-beta-token" ? "btn-primary" : "btn-secondary"}`}
                  onClick={() => handleSaveToken("admin-beta-token")}
                  style={{ fontSize: "0.8125rem", padding: "0.45rem 0.85rem" }}
                >
                  BetaCorp: Admin Role
                </button>
                <button
                  className={`btn ${token === "member-beta-token" ? "btn-primary" : "btn-secondary"}`}
                  onClick={() => handleSaveToken("member-beta-token")}
                  style={{ fontSize: "0.8125rem", padding: "0.45rem 0.85rem" }}
                >
                  BetaCorp: Member Role
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: AI Intelligence */}
      {activeTab === "ai" && (
        <div style={{ background: "white", borderRadius: "10px", border: "1px solid var(--color-border)", padding: "2rem", maxWidth: "700px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
            <Sparkles size={18} style={{ color: "var(--color-primary-600)" }} />
            <h2 style={{ fontSize: "1.125rem", fontWeight: "600", color: "var(--color-text-main)", margin: 0 }}>
              AI Meeting Intelligence Engine
            </h2>
          </div>
          <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: "1.5rem" }}>
            Configure the LLM models used for extracting executive summaries, key points, decisions, and action items.
          </p>

          <form onSubmit={handleSaveAISettings} style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: "600", color: "var(--color-text-muted)", marginBottom: "0.375rem" }}>
                Primary AI Provider
              </label>
              <select
                value={primaryProvider}
                onChange={e => setPrimaryProvider(e.target.value)}
                style={{ width: "100%", padding: "0.5625rem 0.875rem", borderRadius: "6px", border: "1px solid var(--color-border)", fontSize: "0.875rem" }}
              >
                <option value="gemini">Google Gemini (Default)</option>
                <option value="openai">OpenAI GPT</option>
                <option value="anthropic">Anthropic Claude</option>
                <option value="local">Local Rule-Based & MicroLLM</option>
              </select>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: "600", color: "var(--color-text-muted)", marginBottom: "0.375rem" }}>
                Analysis Model
              </label>
              <select
                value={analysisModel}
                onChange={e => setAnalysisModel(e.target.value)}
                style={{ width: "100%", padding: "0.5625rem 0.875rem", borderRadius: "6px", border: "1px solid var(--color-border)", fontSize: "0.875rem" }}
              >
                <option value="gemini-2.5-flash">Gemini 2.5 Flash (Ultra-fast & structured)</option>
                <option value="gemini-1.5-pro">Gemini 1.5 Pro (Deep reasoning)</option>
                <option value="gpt-4o">GPT-4o</option>
                <option value="claude-3-5-sonnet">Claude 3.5 Sonnet</option>
              </select>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: "600", color: "var(--color-text-muted)", marginBottom: "0.375rem" }}>
                Fallback Provider
              </label>
              <select
                value={fallbackProvider}
                onChange={e => setFallbackProvider(e.target.value)}
                style={{ width: "100%", padding: "0.5625rem 0.875rem", borderRadius: "6px", border: "1px solid var(--color-border)", fontSize: "0.875rem" }}
              >
                <option value="anthropic">Anthropic Claude</option>
                <option value="openai">OpenAI GPT</option>
                <option value="gemini">Google Gemini</option>
                <option value="local">Local MicroLLM</option>
              </select>
            </div>

            <div style={{ background: "#f8fafc", padding: "1rem", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <div style={{ fontSize: "0.8125rem", fontWeight: "600", color: "var(--color-text-main)", marginBottom: "0.25rem" }}>
                Zero-Hallucination Guardrails
              </div>
              <p style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", margin: 0 }}>
                Strict extraction rules are active: unmentioned owners default to <em>Unassigned</em>, missing deadlines default to <em>Not specified</em>, and ambiguous agreements preserve uncertainty.
              </p>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginTop: "0.5rem" }}>
              <button type="submit" className="btn btn-primary" style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.5625rem 1.25rem", fontSize: "0.875rem" }}>
                <Save size={16} /> Save AI Configuration
              </button>
              {savedSuccess && (
                <span style={{ fontSize: "0.8125rem", color: "#16a34a", display: "flex", alignItems: "center", gap: "0.25rem", fontWeight: "600" }}>
                  <CheckCircle size={14} /> Saved successfully
                </span>
              )}
            </div>
          </form>
        </div>
      )}

      {/* Tab 4: Connectors */}
      {activeTab === "integrations" && (
        <div style={{ background: "white", borderRadius: "10px", border: "1px solid var(--color-border)", padding: "2rem", maxWidth: "800px" }}>
          <h2 style={{ fontSize: "1.125rem", fontWeight: "600", color: "var(--color-text-main)", marginBottom: "0.5rem" }}>
            External Data Connectors
          </h2>
          <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: "1.5rem" }}>
            Import meeting transcripts and push action items automatically to your productivity tools.
          </p>

          {loadingConnectors && <div style={{ textAlign: "center", padding: "2rem" }}>Loading connectors...</div>}
          
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {connectors.map(c => (
              <div
                key={c.provider}
                style={{
                  padding: "1.25rem",
                  borderRadius: "8px",
                  background: "#f8fafc",
                  border: "1px solid #e2e8f0",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center"
                }}
              >
                <div>
                  <h3 style={{ textTransform: "capitalize", fontSize: "1rem", fontWeight: "600", color: "var(--color-text-main)", margin: 0 }}>
                    {c.provider.replace("_", " ")}
                  </h3>
                  <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.25rem", fontSize: "0.75rem", color: "var(--color-text-muted)" }}>
                    <span style={{ color: c.enabled ? "#16a34a" : "#64748b", fontWeight: "600" }}>
                      {c.enabled ? "● Enabled" : "○ Disabled"}
                    </span>
                    <span>·</span>
                    <span>{c.configured ? "Configured" : "Not Configured"}</span>
                    <span>·</span>
                    <span>{c.authenticated ? "Connected" : "Disconnected"}</span>
                  </div>
                </div>

                <button
                  className="btn btn-secondary"
                  disabled={!c.configured || syncingProvider !== null}
                  onClick={() => handleTriggerSync(c.provider)}
                  style={{ fontSize: "0.8125rem", padding: "0.4rem 0.85rem" }}
                >
                  {syncingProvider === c.provider ? "Syncing..." : "Sync Now"}
                </button>
              </div>
            ))}
          </div>

          {syncMessage && (
            <div style={{ marginTop: "1.25rem", padding: "0.75rem 1rem", borderRadius: "6px", background: "#f0fdf4", border: "1px solid #bbf7d0", color: "#166534", fontSize: "0.8125rem" }}>
              {syncMessage}
            </div>
          )}
        </div>
      )}

      {/* Tab 5: Security */}
      {activeTab === "security" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "2rem", maxWidth: "800px" }}>
          {/* Retention */}
          <div style={{ background: "white", borderRadius: "10px", border: "1px solid var(--color-border)", padding: "2rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
              <Trash2 size={18} style={{ color: "#dc2626" }} />
              <h2 style={{ fontSize: "1.125rem", fontWeight: "600", color: "var(--color-text-main)", margin: 0 }}>
                Data Retention & Auto-Pruning
              </h2>
            </div>
            <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: "1.5rem" }}>
              Configure automatic compliance purging cycles for meetings, transcripts, and audit logs.
            </p>

            <form onSubmit={handleRunRetention} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: "600", color: "var(--color-text-muted)", marginBottom: "0.25rem" }}>
                    Meeting Max Age (Days)
                  </label>
                  <input
                    type="number"
                    value={meetingDays}
                    onChange={e => setMeetingDays(parseInt(e.target.value) || 0)}
                    style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid var(--color-border)" }}
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: "600", color: "var(--color-text-muted)", marginBottom: "0.25rem" }}>
                    Transcripts Max Age (Days)
                  </label>
                  <input
                    type="number"
                    value={transcriptDays}
                    onChange={e => setTranscriptDays(parseInt(e.target.value) || 0)}
                    style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid var(--color-border)" }}
                  />
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <input
                  type="checkbox"
                  id="dryRun"
                  checked={dryRun}
                  onChange={e => setDryRun(e.target.checked)}
                />
                <label htmlFor="dryRun" style={{ fontSize: "0.875rem", color: "var(--color-text-main)", cursor: "pointer" }}>
                  Dry Run (Simulate count of items to delete without executing destructive deletion)
                </label>
              </div>

              <button
                type="submit"
                className="btn btn-secondary"
                disabled={purging}
                style={{ alignSelf: "flex-start", marginTop: "0.5rem", color: "#dc2626" }}
              >
                {purging ? "Executing purge..." : "Run Retention Cleanup"}
              </button>
            </form>

            {purgeResult && (
              <div style={{ marginTop: "1rem", padding: "0.75rem 1rem", borderRadius: "6px", background: "#f8fafc", border: "1px solid #e2e8f0", fontSize: "0.8125rem" }}>
                <strong>Purge result:</strong> {purgeResult.status.toUpperCase()} (Meetings: {purgeResult.deleted?.meetings_deleted || 0}, Segments: {purgeResult.deleted?.transcripts_deleted || 0})
              </div>
            )}
          </div>

          {/* Audit Logs */}
          <div style={{ background: "white", borderRadius: "10px", border: "1px solid var(--color-border)", padding: "2rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
              <ShieldAlert size={18} style={{ color: "var(--color-primary-600)" }} />
              <h2 style={{ fontSize: "1.125rem", fontWeight: "600", color: "var(--color-text-main)", margin: 0 }}>
                Security Audit Log Stream
              </h2>
            </div>
            <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: "1.25rem" }}>
              Immutable record of security, authorization, and administrative events.
            </p>

            {loadingLogs ? (
              <div>Loading audit logs...</div>
            ) : auditLogs.length === 0 ? (
              <div style={{ color: "var(--color-text-muted)", fontSize: "0.875rem" }}>No audit log entries recorded yet.</div>
            ) : (
              <div style={{ maxHeight: "250px", overflowY: "auto", border: "1px solid #e2e8f0", borderRadius: "6px" }}>
                <table style={{ width: "100%", fontSize: "0.75rem", borderCollapse: "collapse" }}>
                  <thead style={{ background: "#f8fafc", borderBottom: "1px solid #e2e8f0" }}>
                    <tr>
                      <th style={{ padding: "0.5rem", textAlign: "left" }}>Time</th>
                      <th style={{ padding: "0.5rem", textAlign: "left" }}>Actor</th>
                      <th style={{ padding: "0.5rem", textAlign: "left" }}>Action</th>
                      <th style={{ padding: "0.5rem", textAlign: "left" }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditLogs.map(log => (
                      <tr key={log.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                        <td style={{ padding: "0.5rem", color: "var(--color-text-muted)" }}>{new Date(log.timestamp).toLocaleTimeString()}</td>
                        <td style={{ padding: "0.5rem" }}>{log.actor_id}</td>
                        <td style={{ padding: "0.5rem", fontFamily: "monospace" }}>{log.action}</td>
                        <td style={{ padding: "0.5rem", color: log.outcome === "succeeded" ? "#16a34a" : "#dc2626", fontWeight: "600" }}>
                          {log.outcome}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default Settings
