import React, { useState, useEffect } from "react"
import { api, ConnectorStatus, AuditLog } from "../services/api"
import { Spinner } from "../components/Spinner"
import { Key, RefreshCw, Trash2, ShieldAlert, CheckCircle, XCircle, Info } from "lucide-react"

export const Settings: React.FC = () => {
  const [token, setToken] = useState(localStorage.getItem("meetingos_token") || "")
  const [connectors, setConnectors] = useState<ConnectorStatus[]>([])
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([])
  
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
      setLogError(err.message || "Failed to load system audit logs. Ensure you are authenticated as Admin.")
    } finally {
      setLoadingLogs(false)
    }
  }

  useEffect(() => {
    loadConnectors()
    loadAuditLogs()
  }, [token])

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
      loadAuditLogs()
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

  return (
    <div className="temporal-timeline-container" style={{ padding: "2rem" }}>
      <div className="timeline-header" style={{ marginBottom: "2rem" }}>
        <h1>System Administration & Hardening</h1>
        <p className="timeline-subtitle">
          Configure connectors, manage retention policy schedules, inspect system audit logs, and test access authorization roles.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem", marginBottom: "2rem" }}>
        {/* Developer Token / Auth Role Panel */}
        <div className="timeline-card">
          <div className="card-header" style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Key className="text-primary" size={20} />
            <h2>Developer Authentication Boundary</h2>
          </div>
          <div className="card-content" style={{ marginTop: "1rem" }}>
            <p style={{ fontSize: "0.9rem", color: "var(--text-secondary)", marginBottom: "1rem" }}>
              Select a development token to configure your current authorization role.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.8rem" }}>
              <button
                className={`timeline-btn ${token === "admin-secret-token" ? "btn-primary" : "btn-secondary"}`}
                onClick={() => handleSaveToken("admin-secret-token")}
                style={{ textAlign: "left", justifyContent: "flex-start" }}
              >
                Administrator Role (Full access)
              </button>
              <button
                className={`timeline-btn ${token === "member-secret-token" ? "btn-primary" : "btn-secondary"}`}
                onClick={() => handleSaveToken("member-secret-token")}
                style={{ textAlign: "left", justifyContent: "flex-start" }}
              >
                Member Role (Upload, Query, Read)
              </button>
              <button
                className={`timeline-btn ${token === "viewer-secret-token" ? "btn-primary" : "btn-secondary"}`}
                onClick={() => handleSaveToken("viewer-secret-token")}
                style={{ textAlign: "left", justifyContent: "flex-start" }}
              >
                Viewer Role (Read-only views)
              </button>
              <button
                className={`timeline-btn ${!token ? "btn-primary" : "btn-secondary"}`}
                onClick={() => handleSaveToken("")}
                style={{ textAlign: "left", justifyContent: "flex-start" }}
              >
                Anonymous Role (Unauthorized)
              </button>
            </div>
            
            <div style={{ marginTop: "1.5rem" }}>
              <label style={{ fontSize: "0.85rem", display: "block", marginBottom: "0.4rem" }}>Active Header Token:</label>
              <input
                type="text"
                className="filter-input"
                style={{ width: "100%", fontFamily: "monospace" }}
                value={token}
                onChange={(e) => handleSaveToken(e.target.value)}
                placeholder="No token set"
              />
            </div>
          </div>
        </div>

        {/* Connectors Sync Status Panel */}
        <div className="timeline-card">
          <div className="card-header" style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <RefreshCw className="text-primary" size={20} />
            <h2>External Connectors Sync status</h2>
          </div>
          <div className="card-content" style={{ marginTop: "1rem" }}>
            {loadingConnectors && <Spinner message="Querying connectors..." />}
            {connectorError && (
              <div style={{ color: "#ef4444", display: "flex", gap: "0.5rem", alignItems: "center", marginBottom: "1rem" }}>
                <ShieldAlert size={18} />
                <span>{connectorError}</span>
              </div>
            )}
            
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              {connectors.map((c) => (
                <div
                  key={c.provider}
                  style={{
                    padding: "1rem",
                    borderRadius: "8px",
                    background: "rgba(255,255,255,0.02)",
                    border: "1px solid rgba(255,255,255,0.05)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center"
                  }}
                >
                  <div>
                    <h3 style={{ textTransform: "capitalize", fontSize: "1.1rem" }}>{c.provider.replace("_", " ")}</h3>
                    <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.4rem", fontSize: "0.8rem" }}>
                      <span style={{ color: c.enabled ? "#10b981" : "#6b7280" }}>
                        {c.enabled ? "● Enabled" : "○ Disabled"}
                      </span>
                      <span style={{ color: "#6b7280" }}>|</span>
                      <span style={{ color: c.configured ? "#10b981" : "#ef4444" }}>
                        {c.configured ? "Configured" : "Not Configured"}
                      </span>
                      <span style={{ color: "#6b7280" }}>|</span>
                      <span style={{ color: c.authenticated ? "#10b981" : "#ef4444" }}>
                        {c.authenticated ? "Authenticated" : "Not Authenticated"}
                      </span>
                    </div>
                  </div>
                  
                  <button
                    className="timeline-btn btn-primary"
                    disabled={!c.configured || syncingProvider !== null}
                    onClick={() => handleTriggerSync(c.provider)}
                    style={{ fontSize: "0.85rem", padding: "0.4rem 0.8rem" }}
                  >
                    {syncingProvider === c.provider ? "Syncing..." : "Sync Now"}
                  </button>
                </div>
              ))}
            </div>

            {syncMessage && (
              <div style={{ marginTop: "1rem", padding: "0.8rem", borderRadius: "6px", background: "rgba(255,255,255,0.05)", fontSize: "0.85rem" }}>
                {syncMessage}
              </div>
            )}
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem" }}>
        {/* Retention Policy Panel */}
        <div className="timeline-card">
          <div className="card-header" style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Trash2 className="text-primary" size={20} />
            <h2>Retention Policies Cleanup</h2>
          </div>
          <div className="card-content" style={{ marginTop: "1rem" }}>
            <p style={{ fontSize: "0.9rem", color: "var(--text-secondary)", marginBottom: "1.5rem" }}>
              Configure and run transient data pruning cycles. (Admin required)
            </p>
            <form onSubmit={handleRunRetention} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.8rem", marginBottom: "0.3rem" }}>Meetings Max Age (days):</label>
                  <input
                    type="number"
                    className="filter-input"
                    value={meetingDays}
                    onChange={(e) => setMeetingDays(parseInt(e.target.value) || 0)}
                    style={{ width: "100%" }}
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "0.8rem", marginBottom: "0.3rem" }}>Transcripts Max Age (days):</label>
                  <input
                    type="number"
                    className="filter-input"
                    value={transcriptDays}
                    onChange={(e) => setTranscriptDays(parseInt(e.target.value) || 0)}
                    style={{ width: "100%" }}
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "0.8rem", marginBottom: "0.3rem" }}>Evidence Max Age (days):</label>
                  <input
                    type="number"
                    className="filter-input"
                    value={evidenceDays}
                    onChange={(e) => setEvidenceDays(parseInt(e.target.value) || 0)}
                    style={{ width: "100%" }}
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "0.8rem", marginBottom: "0.3rem" }}>Audit Logs Max Age (days):</label>
                  <input
                    type="number"
                    className="filter-input"
                    value={auditDays}
                    onChange={(e) => setAuditDays(parseInt(e.target.value) || 0)}
                    style={{ width: "100%" }}
                  />
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: "0.5rem" }}>
                <input
                  type="checkbox"
                  id="dryRun"
                  checked={dryRun}
                  onChange={(e) => setDryRun(e.target.checked)}
                />
                <label htmlFor="dryRun" style={{ fontSize: "0.9rem", cursor: "pointer" }}>
                  Dry Run (List items to delete without actually deleting them)
                </label>
              </div>

              <button
                type="submit"
                className="timeline-btn btn-danger"
                disabled={purging}
                style={{ width: "100%", marginTop: "1rem" }}
              >
                {purging ? "Purging records..." : "Trigger Retention Purge"}
              </button>
            </form>

            {purgeError && (
              <div style={{ color: "#ef4444", marginTop: "1rem", fontSize: "0.85rem", display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <ShieldAlert size={16} />
                <span>{purgeError}</span>
              </div>
            )}

            {purgeResult && (
              <div style={{ marginTop: "1rem", padding: "1rem", borderRadius: "6px", background: "rgba(255,255,255,0.05)", fontSize: "0.85rem" }}>
                <h4 style={{ marginBottom: "0.5rem", fontWeight: "bold" }}>
                  Status: {purgeResult.status.toUpperCase()}
                </h4>
                <ul style={{ paddingLeft: "1.2rem", listStyleType: "disc" }}>
                  <li>Meetings matching: {purgeResult.deleted?.meetings_deleted || 0}</li>
                  <li>Segments matching: {purgeResult.deleted?.transcripts_deleted || 0}</li>
                  <li>Evidence matching: {purgeResult.deleted?.evidence_deleted || 0}</li>
                  <li>Audit Logs matching: {purgeResult.deleted?.audit_logs_deleted || 0}</li>
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* Audit Log Table Panel */}
        <div className="timeline-card">
          <div className="card-header" style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <ShieldAlert className="text-primary" size={20} />
            <h2>Security Audit Logs</h2>
          </div>
          <div className="card-content" style={{ marginTop: "1rem" }}>
            {loadingLogs && <Spinner message="Loading audit logs..." />}
            {logError && (
              <div style={{ color: "#ef4444", display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <Info size={18} />
                <span>{logError}</span>
              </div>
            )}
            
            {!loadingLogs && !logError && (
              <div style={{ maxHeight: "300px", overflowY: "auto" }}>
                {auditLogs.length === 0 ? (
                  <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem" }}>No audit log entries found.</p>
                ) : (
                  <table style={{ width: "100%", fontSize: "0.8rem", borderCollapse: "collapse" }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)", textAlign: "left" }}>
                        <th style={{ padding: "0.4rem" }}>Time</th>
                        <th style={{ padding: "0.4rem" }}>Actor</th>
                        <th style={{ padding: "0.4rem" }}>Action</th>
                        <th style={{ padding: "0.4rem" }}>Outcome</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditLogs.map((log) => (
                        <tr key={log.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                          <td style={{ padding: "0.4rem", color: "var(--text-secondary)" }}>
                            {new Date(log.timestamp).toLocaleTimeString()}
                          </td>
                          <td style={{ padding: "0.4rem" }}>{log.actor_id}</td>
                          <td style={{ padding: "0.4rem", fontFamily: "monospace" }}>{log.action}</td>
                          <td style={{ padding: "0.4rem", color: log.outcome === "succeeded" ? "#10b981" : "#ef4444" }}>
                            {log.outcome}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Settings

