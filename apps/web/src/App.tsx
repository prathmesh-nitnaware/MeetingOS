import React from "react"
import { HashRouter as Router, Routes, Route } from "react-router-dom"
import Sidebar from "./components/Sidebar"
import Dashboard from "./pages/Dashboard"
import MeetingsList from "./pages/MeetingsList"
import MeetingDetail from "./pages/MeetingDetail"
import SearchQA from "./pages/SearchQA"
import EntitiesList from "./pages/EntitiesList"
import TemporalTimeline from "./pages/TemporalTimeline"

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
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
