import React, { useState } from "react"
import { HashRouter as Router, Link, Route, Routes, useLocation } from "react-router-dom"
import { Menu } from "lucide-react"
import { AuthProvider, useAuth } from "./auth/AuthContext"
import ErrorBoundary from "./components/ErrorBoundary"
import Sidebar from "./components/Sidebar"
import { Spinner } from "./components/Spinner"
import Dashboard from "./pages/Dashboard"
import EntitiesList from "./pages/EntitiesList"
import Login from "./pages/Login"
import MeetingDetail from "./pages/MeetingDetail"
import MeetingsList from "./pages/MeetingsList"
import MetricsDashboard from "./pages/MetricsDashboard"
import ProvidersSettings from "./pages/ProvidersSettings"
import SearchQA from "./pages/SearchQA"
import Settings from "./pages/Settings"
import TemporalTimeline from "./pages/TemporalTimeline"
import TraceExplorer from "./pages/TraceExplorer"

const NotFound: React.FC = () => (
  <div className="card empty-state">
    <h1 className="page-title">Page not found</h1>
    <p className="muted" style={{ marginTop: 8 }}>
      There is nothing at this address.
    </p>
    <Link to="/" className="btn btn-primary" style={{ marginTop: 16 }}>
      Go to the dashboard
    </Link>
  </div>
)

const Shell: React.FC = () => {
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="app-container">
      <header className="mobile-topbar">
        <button
          type="button"
          className="btn btn-outline icon-btn"
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((v) => !v)}
        >
          <Menu size={18} aria-hidden="true" />
        </button>
        <span className="mobile-title">MeetingOS</span>
      </header>
      {menuOpen && <div className="sidebar-backdrop" onClick={() => setMenuOpen(false)} />}
      <Sidebar open={menuOpen} onNavigate={() => setMenuOpen(false)} />

      <main className="main-content">
        <ErrorBoundary key={location.pathname}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/meetings" element={<MeetingsList />} />
            <Route path="/meetings/:id" element={<MeetingDetail />} />
            <Route path="/search" element={<SearchQA />} />
            <Route path="/entities" element={<EntitiesList />} />
            <Route path="/temporal" element={<TemporalTimeline />} />
            <Route path="/traces" element={<TraceExplorer />} />
            <Route path="/metrics" element={<MetricsDashboard />} />
            <Route path="/providers" element={<ProvidersSettings />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </ErrorBoundary>
      </main>
    </div>
  )
}

const Gate: React.FC = () => {
  const { profile, loading } = useAuth()
  if (loading) return <Spinner message="Checking your session…" />
  if (!profile) return <Login />
  return (
    <Router>
      <Shell />
    </Router>
  )
}

export const App: React.FC = () => (
  <AuthProvider>
    <Gate />
  </AuthProvider>
)

export default App
