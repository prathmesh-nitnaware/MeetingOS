import React, { useCallback, useEffect, useId, useState } from "react"
import { KeyRound, RefreshCw, ShieldAlert, Trash2 } from "lucide-react"
import { useAuth } from "../auth/AuthContext"
import { Notice } from "../components/Notice"
import { Spinner } from "../components/Spinner"
import { api, type AuditLog, type AuthConfig, type ConnectorStatus, type RetentionResult } from "../services/api"
import { formatDateTime, humanize } from "../utils/format"

const RETENTION_FIELDS = [
  { key: "meeting_days", label: "Delete meetings older than (days)" },
  { key: "transcript_days", label: "Delete transcripts older than (days)" },
  { key: "evidence_days", label: "Delete evidence & search index older than (days)" },
  { key: "audio_days", label: "Delete uploaded audio older than (days)" },
  { key: "audit_log_days", label: "Delete audit logs older than (days)" },
] as const
type RetentionKey = (typeof RETENTION_FIELDS)[number]["key"]

export const Settings: React.FC = () => {
  const ids = useId()
  const { profile, hasPermission, signInWithToken, switchOrganization } = useAuth()
  const isAdmin = profile?.role === "admin" || profile?.role === "owner"

  const [authConfig, setAuthConfig] = useState<AuthConfig | null>(null)
  const [accountMessage, setAccountMessage] = useState<string | null>(null)

  const [connectors, setConnectors] = useState<ConnectorStatus[]>([])
  const [connectorError, setConnectorError] = useState<string | null>(null)
  const [loadingConnectors, setLoadingConnectors] = useState(true)
  const [syncing, setSyncing] = useState<string | null>(null)
  const [syncMessage, setSyncMessage] = useState<{ tone: "success" | "error"; text: string } | null>(null)

  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([])
  const [auditError, setAuditError] = useState<string | null>(null)
  const [loadingLogs, setLoadingLogs] = useState(false)

  const [retention, setRetention] = useState<Record<RetentionKey, string>>({
    meeting_days: "",
    transcript_days: "",
    evidence_days: "",
    audio_days: "",
    audit_log_days: "",
  })
  const [dryRun, setDryRun] = useState(true)
  const [purging, setPurging] = useState(false)
  const [purgeResult, setPurgeResult] = useState<RetentionResult | null>(null)
  const [purgeError, setPurgeError] = useState<string | null>(null)

  const loadConnectors = useCallback(async () => {
    setLoadingConnectors(true)
    setConnectorError(null)
    try {
      setConnectors(await api.getConnectors())
    } catch (err) {
      setConnectorError(err instanceof Error ? err.message : "Failed to load connectors.")
    } finally {
      setLoadingConnectors(false)
    }
  }, [])

  const loadAuditLogs = useCallback(async () => {
    if (!isAdmin) return
    setLoadingLogs(true)
    setAuditError(null)
    try {
      setAuditLogs(await api.getAuditLogs(25, 0))
    } catch (err) {
      setAuditError(err instanceof Error ? err.message : "Failed to load audit logs.")
    } finally {
      setLoadingLogs(false)
    }
  }, [isAdmin])

  useEffect(() => {
    void loadConnectors()
    void loadAuditLogs()
    api.getAuthConfig().then(setAuthConfig).catch(() => setAuthConfig(null))
  }, [loadConnectors, loadAuditLogs])

  const handleSync = async (provider: string) => {
    setSyncing(provider)
    setSyncMessage(null)
    try {
      const res = await api.triggerConnectorSync(provider)
      setSyncMessage({ tone: "success", text: `Sync queued for ${humanize(provider)} (task ${res.task_id}).` })
      void loadAuditLogs()
    } catch (err) {
      setSyncMessage({ tone: "error", text: err instanceof Error ? err.message : "Sync failed." })
    } finally {
      setSyncing(null)
    }
  }

  const handleRetention = async (e: React.FormEvent) => {
    e.preventDefault()
    const params: Record<string, number | boolean> = { dry_run: dryRun }
    for (const { key } of RETENTION_FIELDS) {
      const value = parseInt(retention[key], 10)
      if (retention[key] && (Number.isNaN(value) || value < 1)) {
        setPurgeError("Retention periods must be whole numbers of at least 1 day.")
        return
      }
      if (!Number.isNaN(value)) params[key] = value
    }
    if (Object.keys(params).length === 1) {
      setPurgeError("Enter at least one retention period.")
      return
    }
    if (
      !dryRun &&
      !window.confirm(
        `Permanently delete matching data from "${profile?.organization_name ?? profile?.org_id}"? This cannot be undone.`
      )
    ) {
      return
    }
    setPurging(true)
    setPurgeError(null)
    setPurgeResult(null)
    try {
      setPurgeResult(await api.runRetentionCleanup(params))
      void loadAuditLogs()
    } catch (err) {
      setPurgeError(err instanceof Error ? err.message : "Retention cleanup failed.")
    } finally {
      setPurging(false)
    }
  }

  const switchTo = async (action: () => Promise<void>) => {
    setAccountMessage(null)
    try {
      await action()
    } catch (err) {
      setAccountMessage(err instanceof Error ? err.message : "Could not switch.")
    }
  }

  return (
    <div>
      <header className="page-header">
        <div>
          <h1 className="page-title">System settings</h1>
          <p className="page-subtitle">Your account, connectors, data retention and the audit log.</p>
        </div>
      </header>

      <div className="grid-2">
        <section className="card">
          <h2 className="card-title with-icon">
            <KeyRound size={18} aria-hidden="true" /> Account
          </h2>
          {accountMessage && <Notice tone="error">{accountMessage}</Notice>}
          <dl className="stat-list">
            <div><dt>Signed in as</dt><dd>{profile?.full_name || profile?.email || profile?.user_id}</dd></div>
            <div><dt>Organization</dt><dd>{profile?.organization_name || profile?.org_id}</dd></div>
            <div><dt>Role</dt><dd>{humanize(profile?.role)}</dd></div>
          </dl>

          {profile && profile.organizations.length > 1 && (
            <div className="form-group" style={{ marginTop: 16 }}>
              <label className="form-label" htmlFor={`${ids}-org`}>Switch organization</label>
              <select
                id={`${ids}-org`}
                className="form-select"
                value={profile.org_id}
                onChange={(e) => void switchTo(() => switchOrganization(e.target.value))}
              >
                {profile.organizations.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.name} ({o.role})
                  </option>
                ))}
              </select>
            </div>
          )}

          {authConfig?.dev_auth_enabled && (
            <div className="dev-signin">
              <p className="form-label">Development personas (development mode only)</p>
              <div className="dev-persona-list">
                {authConfig.dev_personas.map((p) => (
                  <button key={p.token} type="button" className="btn btn-secondary" onClick={() => void switchTo(() => signInWithToken(p.token))}>
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </section>

        <section className="card">
          <h2 className="card-title with-icon">
            <RefreshCw size={18} aria-hidden="true" /> Meeting connectors
          </h2>
          {loadingConnectors && <Spinner message="Checking connectors..." />}
          {connectorError && <Notice tone="error">{connectorError}</Notice>}
          {syncMessage && (
            <Notice tone={syncMessage.tone} onDismiss={() => setSyncMessage(null)}>
              {syncMessage.text}
            </Notice>
          )}
          <ul className="connector-list">
            {connectors.map((c) => {
              const canSync = c.enabled && c.authenticated && hasPermission("connectors.manage")
              return (
                <li key={c.provider} className="connector-item">
                  <div>
                    <h3 className="connector-name">{humanize(c.provider)}</h3>
                    <p className="connector-state">
                      <span className={c.enabled ? "text-success" : "muted"}>{c.enabled ? "Enabled" : "Disabled"}</span>
                      {" · "}
                      <span className={c.configured ? "text-success" : "muted"}>{c.configured ? "Credentials set" : "No credentials"}</span>
                      {" · "}
                      <span className={c.authenticated ? "text-success" : "muted"}>
                        {c.authenticated ? (c.demo_mode ? "Demo mode" : "Connected") : "Not connected"}
                      </span>
                    </p>
                    {c.last_error && <p className="muted small">{c.last_error}</p>}
                  </div>
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={!canSync || syncing !== null}
                    title={canSync ? undefined : "Enable the connector and configure working credentials first"}
                    onClick={() => void handleSync(c.provider)}
                  >
                    {syncing === c.provider ? "Syncing…" : "Sync now"}
                  </button>
                </li>
              )
            })}
          </ul>
        </section>
      </div>

      {isAdmin && (
        <div className="grid-2" style={{ marginTop: 24 }}>
          <section className="card">
            <h2 className="card-title with-icon">
              <Trash2 size={18} aria-hidden="true" /> Data retention cleanup
            </h2>
            <p className="muted small" style={{ marginBottom: 16 }}>
              Applies to <strong>{profile?.organization_name || profile?.org_id}</strong> only. Leave a field empty to skip it.
            </p>
            <form onSubmit={handleRetention}>
              <div className="grid-2">
                {RETENTION_FIELDS.map(({ key, label }) => (
                  <div key={key} className="form-group">
                    <label className="form-label" htmlFor={`${ids}-${key}`}>{label}</label>
                    <input
                      id={`${ids}-${key}`}
                      type="number"
                      min={1}
                      className="form-input"
                      value={retention[key]}
                      onChange={(e) => setRetention((r) => ({ ...r, [key]: e.target.value }))}
                    />
                  </div>
                ))}
              </div>
              <div className="checkbox-row">
                <input type="checkbox" id={`${ids}-dry`} checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} />
                <label htmlFor={`${ids}-dry`}>Preview only (count what would be deleted)</label>
              </div>
              {purgeError && <Notice tone="error">{purgeError}</Notice>}
              <div className="form-actions">
                <button type="submit" className={`btn ${dryRun ? "btn-outline" : "btn-danger"}`} disabled={purging}>
                  {purging ? "Working…" : dryRun ? "Preview cleanup" : "Delete permanently"}
                </button>
              </div>
            </form>
            {purgeResult && (
              <Notice tone={purgeResult.dry_run ? "info" : "success"}>
                <strong>{purgeResult.dry_run ? "Would delete:" : "Deleted:"}</strong>{" "}
                {Object.entries(purgeResult.deleted)
                  .map(([k, v]) => `${v} ${humanize(k.replace("_deleted", ""))}`)
                  .join(", ")}
              </Notice>
            )}
          </section>

          <section className="card">
            <h2 className="card-title with-icon">
              <ShieldAlert size={18} aria-hidden="true" /> Audit log
            </h2>
            {loadingLogs && <Spinner message="Loading audit logs..." />}
            {auditError && <Notice tone="error">{auditError}</Notice>}
            {!loadingLogs && !auditError && auditLogs.length === 0 && <p className="muted">No audit entries yet.</p>}
            {auditLogs.length > 0 && (
              <div className="table-container scroll-y">
                <table className="table compact-table">
                  <thead>
                    <tr>
                      <th scope="col">When</th>
                      <th scope="col">Who</th>
                      <th scope="col">Action</th>
                      <th scope="col">Outcome</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditLogs.map((log) => (
                      <tr key={log.id}>
                        <td>{formatDateTime(log.timestamp)}</td>
                        <td>{log.actor_id}</td>
                        <td><code>{log.action}</code></td>
                        <td className={log.outcome === "succeeded" ? "text-success" : "text-danger"}>{log.outcome}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  )
}
export default Settings
