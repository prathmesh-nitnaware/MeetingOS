import React, { useState, useEffect } from "react"
import { HashRouter as Router, Routes, Route } from "react-router-dom"
import Sidebar from "./components/Sidebar"
import Header from "./components/Header"
import GlobalSearchModal from "./components/GlobalSearchModal"
import Dashboard from "./pages/Dashboard"
import MeetingsList from "./pages/MeetingsList"
import MeetingDetail from "./pages/MeetingDetail"
import CreateMeeting from "./pages/CreateMeeting"
import ActionItems from "./pages/ActionItems"
import DecisionsPage from "./pages/DecisionsPage"
import KnowledgePage from "./pages/KnowledgePage"
import SearchQA from "./pages/SearchQA"
import TeamPage from "./pages/TeamPage"
import Settings from "./pages/Settings"
import ProjectsList from "./pages/ProjectsList"
import ProjectDetail from "./pages/ProjectDetail"
import TraceExplorer from "./pages/TraceExplorer"
import MetricsDashboard from "./pages/MetricsDashboard"

export const App: React.FC = () => {
  const [isSearchOpen, setIsSearchOpen] = useState(false)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault()
        setIsSearchOpen(prev => !prev)
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [])

  return (
    <Router>
      <div className="app-container">
        {/* Navigation Sidebar */}
        <Sidebar />

        {/* Global Command Palette Search Modal */}
        <GlobalSearchModal isOpen={isSearchOpen} onClose={() => setIsSearchOpen(false)} />

        {/* Main Application Container */}
        <div className="app-main-wrapper" style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, overflow: "hidden" }}>
          {/* Global Header */}
          <Header onOpenSearch={() => setIsSearchOpen(true)} />

          {/* Page Content Viewport */}
          <main className="main-content" style={{ flex: 1, overflowY: "auto" }}>
            <Routes>
              {/* Primary Text-First MeetingOS Routes */}
              <Route path="/" element={<Dashboard />} />
              <Route path="/meetings" element={<MeetingsList />} />
              <Route path="/meetings/new" element={<CreateMeeting />} />
              <Route path="/meetings/:id" element={<MeetingDetail />} />
              <Route path="/action-items" element={<ActionItems />} />
              <Route path="/decisions" element={<DecisionsPage />} />
              <Route path="/knowledge" element={<KnowledgePage />} />
              <Route path="/search" element={<SearchQA />} />
              <Route path="/team" element={<TeamPage />} />
              <Route path="/settings" element={<Settings />} />

              {/* Projects Workspace */}
              <Route path="/projects" element={<ProjectsList />} />
              <Route path="/projects/:id" element={<ProjectDetail />} />

              {/* Admin & Observability Routes */}
              <Route path="/traces" element={<TraceExplorer />} />
              <Route path="/metrics" element={<MetricsDashboard />} />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  )
}

export default App
