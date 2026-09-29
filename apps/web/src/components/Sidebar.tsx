import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Calendar,
  CheckSquare,
  Target,
  BookOpen,
  Search,
  Users,
  Settings,
  Sparkles,
  Activity,
  Layers
} from "lucide-react";

export const Sidebar: React.FC = () => {
  return (
    <aside className="sidebar">
      {/* Brand Header */}
      <div className="sidebar-brand">
        <div className="brand-icon-wrapper">
          <Sparkles size={18} className="text-brand-accent" />
        </div>
        <div className="brand-text">
          <span className="brand-name">MeetingOS</span>
          <span className="brand-tagline">Meeting Intelligence</span>
        </div>
      </div>

      {/* Navigation Sections */}
      <nav className="nav-menu">
        <div className="nav-section-label">Workspace</div>

        <NavLink
          to="/"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
        >
          <LayoutDashboard size={17} />
          <span>Dashboard</span>
        </NavLink>

        <NavLink
          to="/meetings"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
        >
          <Calendar size={17} />
          <span>Meetings</span>
        </NavLink>

        <NavLink
          to="/projects"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
        >
          <Layers size={17} />
          <span>Projects</span>
        </NavLink>

        <NavLink
          to="/action-items"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
        >
          <CheckSquare size={17} />
          <span>Action Items</span>
        </NavLink>

        <NavLink
          to="/decisions"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
        >
          <Target size={17} />
          <span>Decisions</span>
        </NavLink>

        <div className="nav-section-label">Intelligence</div>

        <NavLink
          to="/knowledge"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
        >
          <BookOpen size={17} />
          <span>Knowledge & Topics</span>
        </NavLink>

        <NavLink
          to="/search"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
        >
          <Search size={17} />
          <span>Search & QA</span>
        </NavLink>

        <NavLink
          to="/team"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
        >
          <Users size={17} />
          <span>Team</span>
        </NavLink>

        <div className="nav-section-label">System</div>

        <NavLink
          to="/settings"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
        >
          <Settings size={17} />
          <span>Settings</span>
        </NavLink>
      </nav>

      {/* Sidebar Footer */}
      <div className="sidebar-footer">
        <div className="sidebar-status-pill">
          <div className="status-indicator-dot online" />
          <span>Text AI Engine Online</span>
        </div>
        <p className="sidebar-version">v2.0 • Text-First Intelligence</p>
      </div>
    </aside>
  );
};

export default Sidebar;
