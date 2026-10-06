import React, { useEffect, useState } from "react"
import { NavLink } from "react-router-dom"
import {
  Activity,
  BarChart3,
  GitBranch,
  History,
  LayoutDashboard,
  LogOut,
  Network,
  Search,
  Settings,
  Sliders,
  Video,
} from "lucide-react"
import { useAuth } from "../auth/AuthContext"
import { api } from "../services/api"

const LINKS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/meetings", label: "Meetings", icon: Video },
  { to: "/search", label: "Search & QA", icon: Search },
  { to: "/entities", label: "Entities & Graph", icon: Network },
  { to: "/temporal", label: "Timeline Intelligence", icon: History },
  { to: "/traces", label: "Agent Traces", icon: GitBranch },
  { to: "/metrics", label: "Observability", icon: BarChart3 },
  { to: "/providers", label: "AI Providers", icon: Sliders },
  { to: "/settings", label: "System Settings", icon: Settings },
]

interface SidebarProps {
  open: boolean
  onNavigate: () => void
}

export const Sidebar: React.FC<SidebarProps> = ({ open, onNavigate }) => {
  const { profile, signOut } = useAuth()
  const [version, setVersion] = useState<string | null>(null)

  useEffect(() => {
    api
      .getHealth()
      .then((h) => setVersion(h.version))
      .catch(() => setVersion(null))
  }, [])

  return (
    <aside className={`sidebar${open ? " open" : ""}`} aria-label="Main navigation">
      <div className="sidebar-logo">
        <Activity size={24} className="text-accent-indigo" aria-hidden="true" />
        <span>MeetingOS</span>
      </div>
      <nav className="nav-menu">
        {LINKS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
          >
            <Icon size={18} aria-hidden="true" />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      {profile && (
        <div className="sidebar-user">
          <div className="sidebar-user-name">{profile.full_name || profile.email || profile.user_id}</div>
          <div className="sidebar-user-meta">
            {profile.organization_name || profile.org_id} · {profile.role}
          </div>
          <button type="button" className="btn btn-outline sidebar-signout" onClick={() => signOut()}>
            <LogOut size={14} aria-hidden="true" />
            <span>Sign out</span>
          </button>
        </div>
      )}
      <div className="sidebar-footer">
        <p>{version ? `MeetingOS v${version}` : "MeetingOS"}</p>
      </div>
    </aside>
  )
}
export default Sidebar
