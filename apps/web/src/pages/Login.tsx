import React, { useEffect, useId, useState } from "react"
import { Activity } from "lucide-react"
import { useAuth } from "../auth/AuthContext"
import { Notice } from "../components/Notice"
import { api, type AuthConfig } from "../services/api"

type Mode = "signin" | "register"

export const Login: React.FC = () => {
  const ids = useId()
  const { signInWithToken, notice } = useAuth()
  const [mode, setMode] = useState<Mode>("signin")
  const [config, setConfig] = useState<AuthConfig | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [orgName, setOrgName] = useState("")
  const [orgSlug, setOrgSlug] = useState("")
  const [fullName, setFullName] = useState("")

  useEffect(() => {
    api.getAuthConfig().then(setConfig).catch(() => setConfig({ dev_auth_enabled: false, dev_personas: [] }))
  }, [])

  const run = async (action: () => Promise<void>) => {
    setBusy(true)
    setError(null)
    try {
      await action()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.")
    } finally {
      setBusy(false)
    }
  }

  const handleSignIn = (e: React.FormEvent) => {
    e.preventDefault()
    void run(async () => {
      const res = await api.login(email.trim(), password)
      await signInWithToken(res.access_token)
    })
  }

  const handleRegister = (e: React.FormEvent) => {
    e.preventDefault()
    void run(async () => {
      const res = await api.registerOrg({
        org_name: orgName.trim(),
        org_slug: (orgSlug || orgName).trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""),
        admin_name: fullName.trim(),
        admin_email: email.trim(),
        admin_password: password,
      })
      await signInWithToken(res.access_token)
    })
  }

  return (
    <div className="login-page">
      <div className="card login-card">
        <div className="sidebar-logo login-logo">
          <Activity size={26} className="text-accent-indigo" aria-hidden="true" />
          <span>MeetingOS</span>
        </div>

        <div className="segmented" role="tablist" aria-label="Sign in or create an organization">
          <button
            type="button"
            role="tab"
            aria-selected={mode === "signin"}
            className={`btn ${mode === "signin" ? "btn-primary" : "btn-outline"}`}
            onClick={() => setMode("signin")}
          >
            Sign in
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "register"}
            className={`btn ${mode === "register" ? "btn-primary" : "btn-outline"}`}
            onClick={() => setMode("register")}
          >
            Create organization
          </button>
        </div>

        {notice && <Notice tone="info">{notice}</Notice>}
        {error && <Notice tone="error">{error}</Notice>}

        {mode === "signin" ? (
          <form onSubmit={handleSignIn}>
            <div className="form-group">
              <label className="form-label" htmlFor={`${ids}-email`}>Email</label>
              <input id={`${ids}-email`} className="form-input" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor={`${ids}-password`}>Password</label>
              <input id={`${ids}-password`} className="form-input" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </div>
            <button type="submit" className="btn btn-primary full-width" disabled={busy}>
              {busy ? "Signing in…" : "Sign in"}
            </button>
          </form>
        ) : (
          <form onSubmit={handleRegister}>
            <div className="form-group">
              <label className="form-label" htmlFor={`${ids}-org`}>Organization name</label>
              <input id={`${ids}-org`} className="form-input" value={orgName} onChange={(e) => setOrgName(e.target.value)} required />
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor={`${ids}-slug`}>Workspace URL name</label>
              <input id={`${ids}-slug`} className="form-input" value={orgSlug} placeholder="acme-corp" onChange={(e) => setOrgSlug(e.target.value)} />
              <span className="field-hint">Lowercase letters, digits and hyphens. Defaults to the organization name.</span>
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor={`${ids}-name`}>Your name</label>
              <input id={`${ids}-name`} className="form-input" autoComplete="name" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor={`${ids}-remail`}>Email</label>
              <input id={`${ids}-remail`} className="form-input" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor={`${ids}-rpassword`}>Password (at least 8 characters)</label>
              <input id={`${ids}-rpassword`} className="form-input" type="password" autoComplete="new-password" minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} required />
            </div>
            <button type="submit" className="btn btn-primary full-width" disabled={busy}>
              {busy ? "Creating…" : "Create organization"}
            </button>
          </form>
        )}

        {config?.dev_auth_enabled && config.dev_personas.length > 0 && (
          <div className="dev-signin">
            <p className="form-label">Development sign-in (only available in development mode)</p>
            <div className="dev-persona-list">
              {config.dev_personas.map((p) => (
                <button key={p.token} type="button" className="btn btn-secondary" disabled={busy} onClick={() => void run(() => signInWithToken(p.token))}>
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
export default Login
