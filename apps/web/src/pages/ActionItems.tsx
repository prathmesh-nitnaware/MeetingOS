import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  CheckSquare,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  Users,
  AlertCircle,
  Plus,
  ArrowRight,
  Sparkles,
  ExternalLink,
  ShieldCheck,
  XCircle,
  FileText
} from "lucide-react";
import { api, ExtractedCommitment, MeetingSummary } from "../services/api";

export const ActionItems: React.FC = () => {
  const navigate = useNavigate();
  const [items, setItems] = useState<ExtractedCommitment[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<string>("Open");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPriority, setSelectedPriority] = useState<string>("All");

  useEffect(() => {
    fetchActionItems();
  }, [filterStatus]);

  const fetchActionItems = async () => {
    setLoading(true);
    try {
      const statusParam = filterStatus === "All" ? undefined : filterStatus;
      const data = await api.listActionItems({ status: statusParam });
      setItems(data || []);
    } catch (err) {
      console.error("Failed to load action items", err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleStatus = async (item: ExtractedCommitment) => {
    const nextStatus = item.status === "Completed" ? "In Progress" : "Completed";
    try {
      await api.updateActionItem(item.id || item.commitment_id, { status: nextStatus });
      setItems((prev) =>
        prev.map((a) =>
          (a.id === item.id || a.commitment_id === item.commitment_id)
            ? { ...a, status: nextStatus }
            : a
        )
      );
    } catch (err) {
      console.error("Failed to update status", err);
    }
  };

  const handleReviewAction = async (item: ExtractedCommitment, newReviewStatus: string) => {
    if (!item.meeting_id) return;
    try {
      await api.updateMeetingActionReview(item.meeting_id, item.id || item.commitment_id, newReviewStatus);
      setItems((prev) =>
        prev.map((a) =>
          (a.id === item.id || a.commitment_id === item.commitment_id)
            ? { ...a, review_status: newReviewStatus }
            : a
        )
      );
    } catch (err: any) {
      alert("Failed to update review status: " + err.message);
    }
  };

  const isItemOverdue = (item: ExtractedCommitment): boolean => {
    if (item.status === "Completed" || item.status === "Cancelled") return false;
    const dateCandidate = item.due_date || item.due_date_str;
    if (!dateCandidate) return false;
    const parsed = Date.parse(dateCandidate);
    if (isNaN(parsed)) return false;
    return new Date(parsed) < new Date(new Date().setHours(0, 0, 0, 0));
  };

  const isItemUnassigned = (item: ExtractedCommitment): boolean => {
    return !item.owner_id || item.owner_id.trim().toLowerCase() === "unassigned";
  };

  const filteredItems = items.filter((item) => {
    // Custom filter tabs
    if (filterStatus === "Overdue" && !isItemOverdue(item)) return false;
    if (filterStatus === "Unassigned" && !isItemUnassigned(item)) return false;

    const matchesSearch =
      (item.task && item.task.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (item.description && item.description.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (item.owner_id && item.owner_id.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (item.meeting_title && item.meeting_title.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesPriority =
      selectedPriority === "All" ||
      (item.priority && item.priority.toLowerCase() === selectedPriority.toLowerCase());

    return matchesSearch && matchesPriority;
  });

  return (
    <div className="page-container">
      <div className="page-header-row">
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.25rem" }}>
            <span style={{ fontSize: "0.8125rem", color: "var(--color-primary-600)", fontWeight: "600", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Organizational Deliverables
            </span>
          </div>
          <h1 className="page-title">Action Items</h1>
          <p className="page-subtitle">
            Track commitments, tasks, and deliverables with verifiable source evidence extracted from meetings.
          </p>
        </div>
      </div>

      {/* Filter Tabs & Search Bar */}
      <div className="action-items-filter-bar">
        <div className="filter-tabs-row">
          {["Open", "In Progress", "Completed", "Overdue", "Unassigned", "All"].map((st) => (
            <button
              key={st}
              type="button"
              className={`filter-tab-btn ${filterStatus === st ? "active" : ""}`}
              onClick={() => setFilterStatus(st)}
            >
              {st}
            </button>
          ))}
        </div>

        <div className="filter-controls-right">
          <div className="search-input-box small">
            <Search size={14} className="search-box-icon" />
            <input
              type="text"
              className="search-box-input"
              placeholder="Filter tasks, owners, meetings..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <select
            className="form-select-sm"
            value={selectedPriority}
            onChange={(e) => setSelectedPriority(e.target.value)}
          >
            <option value="All">All Priorities</option>
            <option value="high">High Priority</option>
            <option value="medium">Medium Priority</option>
            <option value="low">Low Priority</option>
          </select>
        </div>
      </div>

      {/* Action Items List Table */}
      {loading ? (
        <div className="skeleton-container">
          <div className="skeleton-row" />
          <div className="skeleton-row" />
          <div className="skeleton-row" />
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="empty-state-card">
          <CheckCircle2 size={36} className="text-emerald" />
          <h3>No action items found</h3>
          <p>
            {searchQuery
              ? "No action items matching your search."
              : "All caught up for this filter."}
          </p>
        </div>
      ) : (
        <div className="action-items-table-card">
          <div className="action-table-header">
            <div className="col-check" />
            <div className="col-task">Task & Evidence</div>
            <div className="col-owner">Owner</div>
            <div className="col-source">Source Meeting</div>
            <div className="col-due">Due Date</div>
            <div className="col-priority">Priority</div>
            <div className="col-status">Review / Status</div>
          </div>

          <div className="action-table-body">
            {filteredItems.map((item) => (
              <div
                key={item.id || item.commitment_id}
                className={`action-table-row ${item.status === "Completed" ? "completed" : ""}`}
              >
                <div className="col-check">
                  <button
                    type="button"
                    className={`action-checkbox ${item.status === "Completed" ? "checked" : ""}`}
                    onClick={() => handleToggleStatus(item)}
                  >
                    {item.status === "Completed" && <CheckCircle2 size={13} />}
                  </button>
                </div>

                <div className="col-task">
                  <span className="task-title-text">{item.task || item.description}</span>
                  {item.source_text && (
                    <div style={{ marginTop: "0.25rem", fontSize: "0.75rem", color: "#64748b", fontStyle: "italic", background: "#f8fafc", padding: "0.25rem 0.5rem", borderRadius: "4px", border: "1px solid #e2e8f0", display: "inline-block", maxWidth: "100%" }}>
                      Evidence: "{item.source_text}"
                    </div>
                  )}
                </div>

                <div className="col-owner">
                  <span className="badge badge-owner">
                    <Users size={11} />
                    <span>{item.owner_id || "Unassigned"}</span>
                  </span>
                </div>

                <div className="col-source">
                  {item.meeting_id ? (
                    <Link to={`/meetings/${item.meeting_id}`} className="meeting-source-link" style={{ display: "inline-flex", alignItems: "center", gap: "0.25rem" }}>
                      <span>{item.meeting_title || "Meeting"}</span>
                      <ExternalLink size={11} />
                    </Link>
                  ) : (
                    <span className="text-muted">—</span>
                  )}
                </div>

                <div className="col-due">
                  <span className="due-date-text">
                    <Clock size={12} className={isItemOverdue(item) ? "text-danger" : "text-muted"} />
                    <span style={{ color: isItemOverdue(item) ? "#ef4444" : "inherit", fontWeight: isItemOverdue(item) ? "600" : "normal" }}>
                      {item.due_date_str || "Not specified"}
                    </span>
                  </span>
                  {isItemOverdue(item) && (
                    <span style={{ fontSize: "0.65rem", background: "#fee2e2", color: "#b91c1c", padding: "0.1rem 0.35rem", borderRadius: "3px", fontWeight: "700", marginLeft: "0.35rem" }}>
                      OVERDUE
                    </span>
                  )}
                </div>

                <div className="col-priority">
                  <span className={`badge badge-priority ${item.priority || "medium"}`}>
                    {item.priority || "medium"}
                  </span>
                </div>

                <div className="col-status" style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
                  <select
                    className="status-dropdown-select"
                    value={item.status}
                    onChange={(e) => {
                      const newStatus = e.target.value;
                      api.updateActionItem(item.id || item.commitment_id, { status: newStatus });
                      setItems((prev) =>
                        prev.map((a) =>
                          (a.id === item.id || a.commitment_id === item.commitment_id)
                            ? { ...a, status: newStatus }
                            : a
                        )
                      );
                    }}
                  >
                    <option value="In Progress">In Progress</option>
                    <option value="Completed">Completed</option>
                    <option value="Open">Open</option>
                    <option value="Cancelled">Cancelled</option>
                  </select>

                  {/* Review Status indicator */}
                  <div style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
                    <span
                      style={{
                        fontSize: "0.65rem",
                        fontWeight: "700",
                        textTransform: "uppercase",
                        padding: "0.1rem 0.35rem",
                        borderRadius: "3px",
                        background: item.review_status === "confirmed" ? "#dcfce7" : item.review_status === "rejected" ? "#fee2e2" : "#fef3c7",
                        color: item.review_status === "confirmed" ? "#15803d" : item.review_status === "rejected" ? "#b91c1c" : "#b45309"
                      }}
                    >
                      {item.review_status || "Needs Review"}
                    </span>
                    {item.review_status !== "confirmed" && item.meeting_id && (
                      <button
                        onClick={() => handleReviewAction(item, "confirmed")}
                        style={{ border: "none", background: "transparent", color: "#16a34a", cursor: "pointer", padding: "1px" }}
                        title="Confirm action"
                      >
                        <ShieldCheck size={13} />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ActionItems;

