import React, { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { api, TeamMember } from "../services/api"
import {
  Users,
  UserPlus,
  Mail,
  CheckSquare,
  FileText,
  Clock,
  Shield,
  Search,
  Filter,
  MoreVertical
} from "lucide-react"

export const TeamPage: React.FC = () => {
  const navigate = useNavigate()
  const [members, setMembers] = useState<TeamMember[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")

  useEffect(() => {
    loadTeam()
  }, [])

  const loadTeam = async () => {
    try {
      setLoading(true)
      const data = await api.getTeamMembers()
      setMembers(data)
    } catch (err: any) {
      setError(err.message || "Failed to load team directory")
    } finally {
      setLoading(false)
    }
  }

  const filteredMembers = members.filter(m =>
    m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (m.email && m.email.toLowerCase().includes(searchQuery.toLowerCase())) ||
    m.role.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (m.department && m.department.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map(n => n[0])
      .join("")
      .toUpperCase()
      .substring(0, 2)
  }

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "2rem 1.5rem" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "2rem" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.25rem" }}>
            <span style={{ fontSize: "0.8125rem", color: "var(--color-primary-600)", fontWeight: "600", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Organization Directory
            </span>
          </div>
          <h1 style={{ fontSize: "1.875rem", fontWeight: "700", color: "var(--color-text-main)", margin: 0, letterSpacing: "-0.025em" }}>
            Team & Participants
          </h1>
          <p style={{ color: "var(--color-text-muted)", fontSize: "0.9375rem", margin: "0.25rem 0 0 0" }}>
            Collaborators, meeting participants, and assigned action item owners across your workspace.
          </p>
        </div>

        <button
          onClick={() => alert("Invite link copied to clipboard: https://meetingos.app/join/acme-org")}
          className="btn btn-primary"
          style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.625rem 1.25rem", fontSize: "0.875rem" }}
        >
          <UserPlus size={16} /> Invite Member
        </button>
      </div>

      {/* Search Bar */}
      <div style={{ display: "flex", gap: "1rem", alignItems: "center", background: "white", padding: "1rem", borderRadius: "10px", border: "1px solid var(--color-border)", marginBottom: "1.5rem" }}>
        <div style={{ position: "relative", flex: 1 }}>
          <Search size={16} style={{ position: "absolute", left: "0.875rem", top: "50%", transform: "translateY(-50%)", color: "var(--color-text-muted)" }} />
          <input
            type="text"
            placeholder="Search team members by name, role, department or email..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{
              width: "100%",
              padding: "0.5625rem 0.875rem 0.5625rem 2.25rem",
              borderRadius: "6px",
              border: "1px solid var(--color-border)",
              fontSize: "0.875rem",
              outline: "none"
            }}
          />
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div style={{ padding: "4rem 2rem", textAlign: "center", color: "var(--color-text-muted)" }}>
          <div className="spinner" style={{ margin: "0 auto 1rem auto" }}></div>
          Loading team roster...
        </div>
      ) : error ? (
        <div style={{ padding: "1.25rem 1.5rem", background: "#450a0a", border: "1px solid #7f1d1d", borderRadius: "8px", color: "#fca5a5", fontSize: "13.5px" }}>
          {error}
        </div>
      ) : filteredMembers.length === 0 ? (
        <div style={{ padding: "4rem 2rem", textAlign: "center", background: "white", borderRadius: "10px", border: "1px solid var(--color-border)" }}>
          <Users size={32} style={{ color: "var(--color-text-muted)", margin: "0 auto 1rem auto" }} />
          <h3 style={{ fontSize: "1.125rem", fontWeight: "600", color: "var(--color-text-main)" }}>No members found</h3>
          <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem" }}>Try adjusting your search filter.</p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "1.25rem" }}>
          {filteredMembers.map(member => (
            <div
              key={member.id}
              style={{
                background: "white",
                borderRadius: "10px",
                border: "1px solid var(--color-border)",
                padding: "1.25rem",
                display: "flex",
                flexDirection: "column",
                gap: "1rem",
                transition: "box-shadow 0.15s ease"
              }}
            >
              {/* Member Card Header */}
              <div style={{ display: "flex", alignItems: "flex-start", gap: "0.875rem" }}>
                <div
                  style={{
                    width: "44px",
                    height: "44px",
                    borderRadius: "50%",
                    background: "var(--color-primary-100)",
                    color: "var(--color-primary-700)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontWeight: "700",
                    fontSize: "0.9375rem",
                    flexShrink: 0
                  }}
                >
                  {getInitials(member.name)}
                </div>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div style={{ fontSize: "1rem", fontWeight: "600", color: "var(--color-text-main)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {member.name}
                    </div>
                    {member.role === "Admin" && (
                      <span style={{ display: "inline-flex", alignItems: "center", gap: "0.25rem", padding: "0.15rem 0.45rem", borderRadius: "4px", background: "#fef3c7", color: "#92400e", fontSize: "0.6875rem", fontWeight: "600" }}>
                        <Shield size={10} /> ADMIN
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", marginTop: "0.125rem" }}>
                    {member.role} {member.department ? `· ${member.department}` : ""}
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", marginTop: "0.25rem", display: "flex", alignItems: "center", gap: "0.25rem" }}>
                    <Mail size={12} /> {member.email}
                  </div>
                </div>
              </div>

              {/* Stats Row */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", background: "#f8fafc", padding: "0.75rem", borderRadius: "8px" }}>
                <div>
                  <div style={{ fontSize: "0.6875rem", color: "var(--color-text-muted)", textTransform: "uppercase", fontWeight: "600" }}>Meetings</div>
                  <div style={{ fontSize: "1.125rem", fontWeight: "700", color: "var(--color-text-main)", marginTop: "0.125rem" }}>
                    {member.meetings_count}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "0.6875rem", color: "var(--color-text-muted)", textTransform: "uppercase", fontWeight: "600" }}>Open Actions</div>
                  <div style={{ fontSize: "1.125rem", fontWeight: "700", color: member.open_actions_count > 0 ? "var(--color-primary-600)" : "var(--color-text-muted)", marginTop: "0.125rem" }}>
                    {member.open_actions_count}
                  </div>
                </div>
              </div>

              {/* Action buttons */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: "0.25rem" }}>
                <button
                  onClick={() => navigate(`/action-items?owner=${encodeURIComponent(member.name)}`)}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--color-primary-600)",
                    fontSize: "0.8125rem",
                    fontWeight: "500",
                    cursor: "pointer",
                    padding: 0
                  }}
                >
                  View assigned tasks →
                </button>
                <button
                  onClick={() => navigate(`/meetings?participant=${encodeURIComponent(member.name)}`)}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--color-text-muted)",
                    fontSize: "0.8125rem",
                    cursor: "pointer",
                    padding: 0
                  }}
                >
                  View meetings
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default TeamPage
