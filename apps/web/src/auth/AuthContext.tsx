import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react"
import { api, getToken, SESSION_EXPIRED_EVENT, setToken, type UserProfile } from "../services/api"

interface AuthState {
  profile: UserProfile | null
  loading: boolean
  /** Message shown on the sign-in page (e.g. after the session expired). */
  notice: string | null
  signInWithToken: (token: string) => Promise<void>
  signOut: (notice?: string) => void
  switchOrganization: (orgId: string) => Promise<void>
  hasPermission: (permission: string) => boolean
}

const AuthContext = createContext<AuthState | null>(null)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState<boolean>(() => Boolean(getToken()))
  const [notice, setNotice] = useState<string | null>(null)

  const loadProfile = useCallback(async () => {
    if (!getToken()) {
      setProfile(null)
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      setProfile(await api.getProfile())
      setNotice(null)
    } catch (err) {
      setToken(null)
      setProfile(null)
      setNotice(err instanceof Error ? err.message : "Please sign in again.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadProfile()
  }, [loadProfile])

  useEffect(() => {
    const onExpired = () => {
      setProfile(null)
      setNotice("Your session has expired or your access changed. Please sign in again.")
    }
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired)
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired)
  }, [])

  const signInWithToken = useCallback(
    async (token: string) => {
      setToken(token)
      await loadProfile()
    },
    [loadProfile]
  )

  const signOut = useCallback((message?: string) => {
    setToken(null)
    setProfile(null)
    setNotice(message ?? null)
  }, [])

  const switchOrganization = useCallback(
    async (orgId: string) => {
      const res = await api.switchOrg(orgId)
      await signInWithToken(res.access_token)
    },
    [signInWithToken]
  )

  const hasPermission = useCallback(
    (permission: string) => Boolean(profile?.permissions.includes(permission)),
    [profile]
  )

  const value = useMemo(
    () => ({ profile, loading, notice, signInWithToken, signOut, switchOrganization, hasPermission }),
    [profile, loading, notice, signInWithToken, signOut, switchOrganization, hasPermission]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>")
  return ctx
}
