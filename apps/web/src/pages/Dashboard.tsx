import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Calendar,
  CheckSquare,
  Target,
  BookOpen,
  Plus,
  ArrowRight,
  Sparkles,
  Users,
  CheckCircle2,
  Clock,
  Tag,
  AlertCircle,
  FileText,
  MessageSquare,
  Activity,
  FolderGit2
} from "lucide-react";
import { api, MeetingSummary, ExtractedCommitment, ExtractedDecision, ActivityItem } from "../services/api";

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [meetings, setMeetings] = useState<MeetingSummary[]>([]);
  const [actionItems, setActionItems] = useState<ExtractedCommitment[]>([]);
  const [decisions, setDecisions] = useState<ExtractedDecision[]>([]);
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [topicsCount, setTopicsCount] = useState<number>(0);
  const [projectsCount, setProjectsCount] = useState<number>(0);
  const [seedSuccess, setSeedSuccess] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      const [meetingsData, actionsData, decisionsData, knowledgeData, activityData, projectsData] = await Promise.all([
        api.listMeetings(undefined, 6),
        api.listActionItems({ status: "open", limit: 6 }),
        api.listDecisions({ limit: 5 }),
        api.getKnowledge().catch(() => ({ topics: [], recurring_topics: [] })),
        api.getActivityFeed(8).catch(() => []),
        api.getProjects().catch(() => [])
      ]);

      setMeetings(meetingsData || []);
      setActionItems(actionsData || []);
      setDecisions(decisionsData || []);
      setActivities(activityData || []);
      setProjectsCount((projectsData || []).length);
      setTopicsCount((knowledgeData?.topics || []).length);
    } catch (err) {
      console.error("Failed to load dashboard data", err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleActionStatus = async (item: ExtractedCommitment) => {
    const newStatus = item.status === "Completed" ? "In Progress" : "Completed";
    try {
      await api.updateActionItem(item.id || item.commitment_id, { status: newStatus });
      setActionItems((prev) =>
        prev.map((a) =>
          (a.id === item.id || a.commitment_id === item.commitment_id)
            ? { ...a, status: newStatus }
            : a
        )
      );
    } catch (err) {
      console.error("Failed to update action item status", err);
    }
  };

  const handleSeedDemo = async () => {
    try {
      const res = await api.seedDemoData();
      setSeedSuccess(res.message);
      await loadDashboardData();
      setTimeout(() => setSeedSuccess(null), 4000);
    } catch (err: any) {
      console.error("Failed to seed demo data", err);
    }
  };

  const openActionsCount = actionItems.filter(
    (a) => a.status !== "Completed" && a.status !== "Cancelled"
  ).length;

  return (
    <div className="page-container dashboard-page">
      {seedSuccess && (
        <div className="alert-banner success">
          <CheckCircle2 size={16} />
          <span>{seedSuccess}</span>
        </div>
      )}

      {/* Hero / Quick Actions Row */}
      <div className="dashboard-hero-card">
        <div className="hero-content">
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--color-primary-600)", background: "var(--color-primary-50)", padding: "0.2rem 0.6rem", borderRadius: "9999px" }}>
              Organizational Memory 2.0
            </span>
          </div>
          <h1 className="hero-title">MeetingOS Workspace</h1>
          <p className="hero-description">
            Turning meetings into lasting organizational memory. Capture transcripts and notes to extract
            source-traceable decisions, action deliverables, project timelines, and evolving knowledge.
          </p>

          <div className="hero-actions">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => navigate("/meetings/new")}
            >
              <Plus size={16} />
              <span>+ New Meeting</span>
            </button>

            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => navigate("/projects")}
            >
              <FolderGit2 size={15} />
              <span>Projects Workspace</span>
            </button>

            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => navigate("/knowledge")}
            >
              <BookOpen size={15} />
              <span>Explore Knowledge</span>
            </button>

            {meetings.length === 0 && (
              <button
                type="button"
                className="btn btn-ghost text-brand-accent"
                onClick={handleSeedDemo}
              >
                <Sparkles size={15} />
                <span>Load Sample Product Launch Project</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Overview Metric Cards */}
      <div className="metrics-grid">
        <div className="metric-card" onClick={() => navigate("/projects")} style={{ cursor: "pointer" }}>
          <div className="metric-header">
            <span className="metric-label">Active Projects</span>
            <div className="metric-icon-badge blue">
              <FolderGit2 size={16} />
            </div>
          </div>
          <div className="metric-value">{projectsCount || 1}</div>
          <span className="metric-subtext">Organizational initiatives</span>
        </div>

        <div className="metric-card" onClick={() => navigate("/meetings")} style={{ cursor: "pointer" }}>
          <div className="metric-header">
            <span className="metric-label">Meetings</span>
            <div className="metric-icon-badge indigo">
              <Calendar size={16} />
            </div>
          </div>
          <div className="metric-value">{meetings.length}</div>
          <span className="metric-subtext">Total meetings recorded</span>
        </div>

        <div className="metric-card" onClick={() => navigate("/action-items")} style={{ cursor: "pointer" }}>
          <div className="metric-header">
            <span className="metric-label">Open Action Items</span>
            <div className="metric-icon-badge amber">
              <CheckSquare size={16} />
            </div>
          </div>
          <div className="metric-value">{openActionsCount}</div>
          <span className="metric-subtext">Pending deliverables</span>
        </div>

        <div className="metric-card" onClick={() => navigate("/decisions")} style={{ cursor: "pointer" }}>
          <div className="metric-header">
            <span className="metric-label">Decisions Recorded</span>
            <div className="metric-icon-badge emerald">
              <Target size={16} />
            </div>
          </div>
          <div className="metric-value">{decisions.length}</div>
          <span className="metric-subtext">Organizational agreements</span>
        </div>
      </div>

      {/* What Changed? Activity Feed Banner */}
      {activities.length > 0 && (
        <div style={{ background: "white", padding: "1.5rem", borderRadius: "10px", border: "1px solid var(--color-border)", marginBottom: "1.5rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <div>
              <h2 style={{ fontSize: "1.125rem", fontWeight: "700", color: "var(--color-text-main)", margin: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Activity size={18} style={{ color: "var(--color-primary-600)" }} />
                What Changed?
              </h2>
              <p style={{ color: "var(--color-text-muted)", fontSize: "0.8125rem", margin: "0.25rem 0 0 0" }}>
                Recent activity across your organization's meetings, decisions, and action items
              </p>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "0.75rem" }}>
            {activities.slice(0, 4).map((act, i) => (
              <div
                key={i}
                onClick={() => act.meeting_id && navigate(`/meetings/${act.meeting_id}`)}
                style={{
                  padding: "0.875rem 1rem",
                  borderRadius: "8px",
                  background: "#f8fafc",
                  border: "1px solid #e2e8f0",
                  cursor: act.meeting_id ? "pointer" : "default",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  gap: "0.5rem",
                  transition: "all 0.15s ease"
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem" }}>
                  <span
                    style={{
                      fontSize: "0.7rem",
                      fontWeight: "700",
                      textTransform: "uppercase",
                      padding: "0.15rem 0.45rem",
                      borderRadius: "4px",
                      background: act.type === "meeting_analyzed" ? "#e0e7ff" : act.type === "decision_added" ? "#dcfce7" : "#fef3c7",
                      color: act.type === "meeting_analyzed" ? "#4338ca" : act.type === "decision_added" ? "#15803d" : "#b45309"
                    }}
                  >
                    {act.type === "meeting_analyzed" ? "Meeting Analyzed" : act.type === "decision_added" ? "Decision Recorded" : "Action Created"}
                  </span>
                  <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)" }}>
                    {act.timestamp ? new Date(act.timestamp).toLocaleDateString() : "Recent"}
                  </span>
                </div>

                <div style={{ fontSize: "0.875rem", fontWeight: "600", color: "var(--color-text-main)", lineHeight: 1.4 }}>
                  {act.title}
                </div>

                <div style={{ fontSize: "0.75rem", color: "var(--color-primary-600)", fontWeight: "500", display: "flex", alignItems: "center", gap: "0.25rem" }}>
                  {act.meeting_title || "View Source"} →
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main Two-Column Dashboard Content */}
      <div className="dashboard-grid-two">
        {/* Left Column: Recent Meetings */}
        <div className="dashboard-section">
          <div className="section-header">
            <div>
              <h2 className="section-title">Recent Meetings</h2>
              <p className="section-subtitle">Conversations and structured summaries</p>
            </div>
            <Link to="/meetings" className="section-view-all">
              <span>View all</span> <ArrowRight size={14} />
            </Link>
          </div>

          {loading ? (
            <div className="skeleton-container">
              <div className="skeleton-row" />
              <div className="skeleton-row" />
              <div className="skeleton-row" />
            </div>
          ) : meetings.length === 0 ? (
            <div className="empty-state-card">
              <Calendar size={32} className="text-muted" />
              <h3>No meetings yet</h3>
              <p>Turn your team's conversations and notes into structured intelligence.</p>
              <div style={{ display: "flex", gap: "10px", marginTop: "12px" }}>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => navigate("/meetings/new")}
                >
                  <Plus size={14} /> Create First Meeting
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={handleSeedDemo}
                >
                  <Sparkles size={14} /> Load Realistic Demo
                </button>
              </div>
            </div>
          ) : (
            <div className="meetings-cards-list">
              {meetings.map((m) => (
                <div
                  key={m.meeting_id}
                  className="dashboard-meeting-card"
                  onClick={() => navigate(`/meetings/${m.meeting_id}`)}
                >
                  <div className="meeting-card-header">
                    <h3 className="meeting-card-title">{m.title}</h3>
                    <span className="meeting-card-date">
                      {new Date(m.meeting_date).toLocaleDateString(undefined, {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </span>
                  </div>

                  {m.summary ? (
                    <p className="meeting-card-summary">
                      {m.summary.length > 140 ? m.summary.slice(0, 137) + "..." : m.summary}
                    </p>
                  ) : (
                    <p className="meeting-card-summary text-muted">
                      Text meeting with {m.participant_count} participants. Click to view intelligence.
                    </p>
                  )}

                  <div className="meeting-card-footer">
                    <div className="meeting-badges-row">
                      <span className="badge badge-subtle">
                        {m.decisions_count || 0} decisions
                      </span>
                      <span className="badge badge-subtle">
                        {m.actions_count || 0} action items
                      </span>
                      {m.topics && m.topics.length > 0 && (
                        <span className="badge badge-topic">
                          #{m.topics[0]}
                        </span>
                      )}
                    </div>
                    <span className="view-link">Open Workspace →</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Outstanding Action Items & Decisions */}
        <div className="dashboard-sidebar-column">
          {/* Outstanding Action Items */}
          <div className="dashboard-section">
            <div className="section-header">
              <div>
                <h2 className="section-title">Open Action Items</h2>
                <p className="section-subtitle">Key deliverables and commitments</p>
              </div>
              <Link to="/action-items" className="section-view-all">
                <span>View all</span> <ArrowRight size={14} />
              </Link>
            </div>

            {loading ? (
              <div className="skeleton-container">
                <div className="skeleton-row" />
                <div className="skeleton-row" />
              </div>
            ) : actionItems.length === 0 ? (
              <div className="empty-state-compact">
                <CheckCircle2 size={24} className="text-emerald" />
                <p>You're all caught up! No open action items.</p>
              </div>
            ) : (
              <div className="action-items-list-compact">
                {actionItems.slice(0, 5).map((item) => (
                  <div
                    key={item.id || item.commitment_id}
                    className={`action-item-row ${item.status === "Completed" ? "completed" : ""}`}
                  >
                    <button
                      type="button"
                      className={`action-checkbox ${item.status === "Completed" ? "checked" : ""}`}
                      onClick={() => handleToggleActionStatus(item)}
                      title="Toggle completed"
                    >
                      {item.status === "Completed" && <CheckCircle2 size={14} />}
                    </button>

                    <div className="action-item-body">
                      <span className="action-task-title">{item.task || item.description}</span>
                      <div className="action-item-meta">
                        <span className="action-owner">{item.owner_id || "Unassigned"}</span>
                        {item.due_date_str && (
                          <>
                            <span className="dot-separator">•</span>
                            <span className="action-due">Due {item.due_date_str}</span>
                          </>
                        )}
                        {item.meeting_title && (
                          <>
                            <span className="dot-separator">•</span>
                            <span
                              onClick={() => item.meeting_id && navigate(`/meetings/${item.meeting_id}`)}
                              className="action-source text-muted"
                              style={{ cursor: item.meeting_id ? "pointer" : "default" }}
                            >
                              {item.meeting_title}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recent Decisions */}
          <div className="dashboard-section" style={{ marginTop: "24px" }}>
            <div className="section-header">
              <div>
                <h2 className="section-title">Recent Decisions</h2>
                <p className="section-subtitle">Confirmed organizational direction</p>
              </div>
              <Link to="/decisions" className="section-view-all">
                <span>View all</span> <ArrowRight size={14} />
              </Link>
            </div>

            {decisions.length === 0 ? (
              <div className="empty-state-compact">
                <Target size={24} className="text-muted" />
                <p>No decisions recorded yet.</p>
              </div>
            ) : (
              <div className="decisions-list-compact">
                {decisions.slice(0, 4).map((dec) => (
                  <div
                    key={dec.id || dec.decision_id}
                    className="decision-row-compact"
                    onClick={() => dec.meeting_id && navigate(`/meetings/${dec.meeting_id}`)}
                  >
                    <div className="decision-status-indicator">
                      <Target size={14} className="text-emerald" />
                    </div>
                    <div className="decision-content-compact">
                      <span className="decision-title-text">{dec.title || dec.subject || dec.decision}</span>
                      {dec.meeting_title && (
                        <span className="decision-source-text">From: {dec.meeting_title}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;

