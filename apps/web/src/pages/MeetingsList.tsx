import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Calendar,
  Search,
  Filter,
  Plus,
  LayoutList,
  LayoutGrid,
  Users,
  CheckSquare,
  Target,
  Sparkles,
  ArrowRight,
  Trash2,
  Tag
} from "lucide-react";
import { api, MeetingSummary } from "../services/api";

export const MeetingsList: React.FC = () => {
  const navigate = useNavigate();
  const [meetings, setMeetings] = useState<MeetingSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTopic, setSelectedTopic] = useState<string>("All");
  const [viewMode, setViewMode] = useState<"list" | "grid">("list");
  const [allTopics, setAllTopics] = useState<string[]>([]);

  useEffect(() => {
    fetchMeetings();
  }, []);

  const fetchMeetings = async () => {
    setLoading(true);
    try {
      const data = await api.listMeetings();
      setMeetings(data || []);

      // Gather unique topics
      const topicsSet = new Set<string>();
      (data || []).forEach((m) => {
        (m.topics || []).forEach((t) => topicsSet.add(t));
      });
      setAllTopics(Array.from(topicsSet));
    } catch (err) {
      console.error("Failed to load meetings", err);
    } finally {
      setLoading(false);
    }
  };

  const filteredMeetings = meetings.filter((m) => {
    const matchesSearch =
      m.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (m.summary && m.summary.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (m.topics && m.topics.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase())));

    const matchesTopic =
      selectedTopic === "All" ||
      (m.topics && m.topics.some((t) => t.toLowerCase() === selectedTopic.toLowerCase()));

    return matchesSearch && matchesTopic;
  });

  const handleDeleteMeeting = async (e: React.MouseEvent, meetingId: string) => {
    e.stopPropagation();
    if (window.confirm("Are you sure you want to remove this meeting?")) {
      try {
        await api.deleteMeeting(meetingId);
        setMeetings((prev) => prev.filter((m) => m.meeting_id !== meetingId));
      } catch (err) {
        console.error("Failed to delete meeting", err);
      }
    }
  };

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header-row">
        <div>
          <h1 className="page-title">Meetings</h1>
          <p className="page-subtitle">
            Capture, understand, and revisit your team's conversations and structured knowledge.
          </p>
        </div>

        <button
          type="button"
          className="btn btn-primary"
          onClick={() => navigate("/meetings/new")}
        >
          <Plus size={16} />
          <span>New Meeting</span>
        </button>
      </div>

      {/* Controls Bar: Search, Topic Filter, View Toggle */}
      <div className="meetings-controls-bar">
        <div className="search-input-box">
          <Search size={16} className="search-box-icon" />
          <input
            type="text"
            className="search-box-input"
            placeholder="Search meetings by title, summary, or topic..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        {/* Topic Filter Pills */}
        <div className="topic-filter-pills">
          <button
            type="button"
            className={`pill-btn ${selectedTopic === "All" ? "active" : ""}`}
            onClick={() => setSelectedTopic("All")}
          >
            All Topics
          </button>
          {allTopics.slice(0, 5).map((t) => (
            <button
              key={t}
              type="button"
              className={`pill-btn ${selectedTopic === t ? "active" : ""}`}
              onClick={() => setSelectedTopic(t)}
            >
              #{t}
            </button>
          ))}
        </div>

        {/* View Mode Toggle */}
        <div className="view-mode-toggle">
          <button
            type="button"
            className={`view-btn ${viewMode === "list" ? "active" : ""}`}
            onClick={() => setViewMode("list")}
            title="List View"
          >
            <LayoutList size={16} />
          </button>
          <button
            type="button"
            className={`view-btn ${viewMode === "grid" ? "active" : ""}`}
            onClick={() => setViewMode("grid")}
            title="Grid View"
          >
            <LayoutGrid size={16} />
          </button>
        </div>
      </div>

      {/* Meeting List / Grid */}
      {loading ? (
        <div className="skeleton-container">
          <div className="skeleton-card" />
          <div className="skeleton-card" />
          <div className="skeleton-card" />
        </div>
      ) : filteredMeetings.length === 0 ? (
        <div className="empty-state-card">
          <Calendar size={36} className="text-muted" />
          <h3>No meetings found</h3>
          <p>
            {searchQuery || selectedTopic !== "All"
              ? "Try adjusting your search or topic filter."
              : "Create your first meeting and turn conversations into structured knowledge."}
          </p>
          <button
            type="button"
            className="btn btn-primary"
            style={{ marginTop: "12px" }}
            onClick={() => navigate("/meetings/new")}
          >
            <Plus size={16} /> + Create Meeting
          </button>
        </div>
      ) : viewMode === "list" ? (
        <div className="meetings-table-container">
          <div className="meetings-list-table">
            {filteredMeetings.map((m) => (
              <div
                key={m.meeting_id}
                className="meeting-list-row"
                onClick={() => navigate(`/meetings/${m.meeting_id}`)}
              >
                <div className="meeting-row-main">
                  <div className="meeting-row-header">
                    <h3 className="meeting-row-title">{m.title}</h3>
                    <span className="meeting-row-date">
                      {new Date(m.meeting_date).toLocaleDateString(undefined, {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </span>
                    <span className="meeting-row-participants">
                      • {m.participant_count} participant{m.participant_count !== 1 ? "s" : ""}
                    </span>
                  </div>

                  <p className="meeting-row-summary">
                    {m.summary
                      ? m.summary.length > 180
                        ? m.summary.slice(0, 177) + "..."
                        : m.summary
                      : "Pasted text / notes meeting ready for AI review."}
                  </p>

                  <div className="meeting-row-tags">
                    <span className="badge badge-subtle">
                      <Target size={12} /> {m.decisions_count || 0} decisions
                    </span>
                    <span className="badge badge-subtle">
                      <CheckSquare size={12} /> {m.actions_count || 0} action items
                    </span>
                    {(m.topics || []).map((top) => (
                      <span key={top} className="badge badge-topic">
                        #{top}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="meeting-row-actions">
                  <button
                    type="button"
                    className="btn-icon text-muted"
                    onClick={(e) => handleDeleteMeeting(e, m.meeting_id)}
                    title="Delete meeting"
                  >
                    <Trash2 size={16} />
                  </button>
                  <ArrowRight size={16} className="text-muted row-arrow" />
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="meetings-grid-layout">
          {filteredMeetings.map((m) => (
            <div
              key={m.meeting_id}
              className="meeting-grid-card"
              onClick={() => navigate(`/meetings/${m.meeting_id}`)}
            >
              <div className="meeting-card-top">
                <span className="meeting-card-date">
                  {new Date(m.meeting_date).toLocaleDateString(undefined, {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })}
                </span>
                <span className="badge badge-subtle">
                  {m.participant_count} participants
                </span>
              </div>

              <h3 className="meeting-card-title">{m.title}</h3>

              <p className="meeting-card-summary">
                {m.summary
                  ? m.summary.length > 130
                    ? m.summary.slice(0, 127) + "..."
                    : m.summary
                  : "Text meeting content and notes."}
              </p>

              <div className="meeting-card-badges">
                <span className="badge badge-subtle">{m.decisions_count || 0} decisions</span>
                <span className="badge badge-subtle">{m.actions_count || 0} actions</span>
              </div>

              {m.topics && m.topics.length > 0 && (
                <div className="meeting-card-topics">
                  {m.topics.slice(0, 2).map((top) => (
                    <span key={top} className="badge badge-topic">
                      #{top}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default MeetingsList;
