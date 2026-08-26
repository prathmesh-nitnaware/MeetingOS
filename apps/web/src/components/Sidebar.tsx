import React from "react"
import { NavLink } from "react-router-dom"
import {
  LayoutDashboard,
  Video,
  Search,
  Network,
  History,
  Activity,
  GitBranch,
  BarChart3,
  Sliders,
  Settings
} from "lucide-react"

export const Sidebar: React.FC = () => {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <Activity size={24} className="text-accent-indigo" />
        <span>MeetingOS</span>
      </div>
      <nav className="nav-menu">
        <NavLink
          to="/"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
        >
          <LayoutDashboard size={18} />
          <span>Dashboard</span>
        </NavLink>
        <NavLink
          to="/meetings"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
        >
          <Video size={18} />
          <span>Meetings</span>
        </NavLink>
        <NavLink
          to="/search"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
        >
          <Search size={18} />
          <span>Search & QA</span>
        </NavLink>
        <NavLink
          to="/entities"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
        >
          <Network size={18} />
          <span>Entities & Graph</span>
        </NavLink>
        <NavLink
          to="/temporal"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
        >
          <History size={18} />
          <span>Timeline Intelligence</span>
        </NavLink>
        <NavLink
          to="/traces"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
        >
          <GitBranch size={18} />
          <span>Agent Traces</span>
        </NavLink>
        <NavLink
          to="/metrics"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
        >
          <BarChart3 size={18} />
          <span>Observability</span>
        </NavLink>
        <NavLink
          to="/providers"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
        >
          <Sliders size={18} />
          <span>AI Providers</span>
        </NavLink>
        <NavLink
          to="/settings"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
        >
          <Settings size={18} />
          <span>System Settings</span>
        </NavLink>
      </nav>
      <div className="sidebar-footer">
        <p>v0.1.0 • Phase 12 Production</p>
      </div>
    </aside>
  )
}
export default Sidebar
