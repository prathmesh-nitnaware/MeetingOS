import React from "react"
import { HashRouter as Router, Routes, Route } from "react-router-dom"
import Sidebar from "./components/Sidebar"
import Dashboard from "./pages/Dashboard"
import MeetingsList from "./pages/MeetingsList"
import MeetingDetail from "./pages/MeetingDetail"
import SearchQA from "./pages/SearchQA"
import EntitiesList from "./pages/EntitiesList"
import TemporalTimeline from "./pages/TemporalTimeline"
import Settings from "./pages/Settings"
import TraceExplorer from "./pages/TraceExplorer"
import MetricsDashboard from "./pages/MetricsDashboard"
import ProvidersSettings from "./pages/ProvidersSettings"

export const App: React.FC = () => {
  return (
    <Router>
      <div className="app-container">
        {/* Sidebar Shell */}
        <Sidebar />

        {/* Main Content Area */}
        <main className="main-content">
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
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
