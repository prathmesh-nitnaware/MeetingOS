import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import {
  Calendar,
  Users,
  Sparkles,
  Target,
  CheckSquare,
  FileText,
  Edit3,
  Trash2,
  CheckCircle2,
  Clock,
  Tag,
  ArrowLeft,
  Share2,
  Save,
  X,
  Plus,
  Loader2,
  Folder,
  Eye,
  Check,
  AlertCircle,
  ExternalLink,
  ChevronRight,
} from "lucide-react";
import {
  api,
  MeetingDetailResponse,
  ExtractedDecision,
  ExtractedCommitment,
  Project,
  ActiveViewer,
} from "../services/api";

export const MeetingDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [meeting, setMeeting] = useState<MeetingDetailResponse | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"summary" | "decisions" | "actions" | "content" | "topics">("summary");

  // Highlighted snippet for source traceability
  const [highlightedSnippet, setHighlightedSnippet] = useState<string | null>(null);
  const contentSectionRef = useRef<HTMLDivElement>(null);

  // Editable states
  const [isEditingSummary, setIsEditingSummary] = useState(false);
  const [editableSummary, setEditableSummary] = useState("");
  const [editableKeyPoints, setEditableKeyPoints] = useState<string[]>([]);
  const [newKeyPointText, setNewKeyPointText] = useState("");

  // Re-analyzing state
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState(0);

  // Project selector
  const [isChangingProject, setIsChangingProject] = useState(false);

  // Real-time Collaboration & Presence
  const [activeViewers, setActiveViewers] = useState<ActiveViewer[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!id) return;
    loadMeetingDetail(id);
    loadProjects();

    // Establish WebSocket connection for presence & review sync
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/v1/ws/meetings/${id}?user_name=You&user_id=usr-active`;

    try {
      const socket = new WebSocket(wsUrl);
      wsRef.current = socket;

      socket.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "initial_presence" || msg.type === "presence_update") {
            if (msg.active_viewers) {
              setActiveViewers(msg.active_viewers);
            }
          } else if (msg.type === "review_sync") {
            if (msg.entity_type === "decision") {
              setMeeting((prev) =>
                prev
                  ? {
                      ...prev,
                      decisions: (prev.decisions || []).map((d) =>
                        d.id === msg.entity_id || d.decision_id === msg.entity_id
                          ? { ...d, review_status: msg.review_status }
                          : d
                      ),
                    }
                  : prev
              );
            } else if (msg.entity_type === "action") {
              setMeeting((prev) =>
                prev
                  ? {
                      ...prev,
                      action_items: (prev.action_items || []).map((a) =>
                        a.id === msg.entity_id || a.commitment_id === msg.entity_id
                          ? { ...a, review_status: msg.review_status }
                          : a
                      ),
                    }
                  : prev
              );
            }
          }
        } catch (e) {
          // ignore parsing error
        }
      };

      socket.onerror = () => {
        api.getMeetingPresence(id).then(setActiveViewers).catch(() => {});
      };

      return () => {
        socket.close();
      };
    } catch (err) {
      api.getMeetingPresence(id).then(setActiveViewers).catch(() => {});
    }
  }, [id]);

  const loadProjects = async () => {
    try {
      const data = await api.getProjects();
      setProjects(data);
    } catch (err) {
      console.error("Failed to load projects", err);
    }
  };

  const loadMeetingDetail = async (meetingId: string) => {
    setLoading(true);
    try {
      const data = await api.getMeetingDetail(meetingId);
      setMeeting(data);
      setEditableSummary(data.summary || "");
      setEditableKeyPoints(data.key_points || []);
    } catch (err) {
      console.error("Failed to load meeting details", err);
    } finally {
      setLoading(false);
    }
  };

  const handleRunAIAnalysis = async () => {
    if (!id) return;
    setAnalyzing(true);
    setAnalysisProgress(1);
    const interval = setInterval(() => {
      setAnalysisProgress((prev) => (prev < 4 ? prev + 1 : prev));
    }, 400);

    try {
      await api.reanalyzeMeeting(id);
      clearInterval(interval);
      setAnalysisProgress(5);
      setTimeout(async () => {
        await loadMeetingDetail(id);
        setAnalyzing(false);
        setAnalysisProgress(0);
      }, 500);
    } catch (err) {
      clearInterval(interval);
      console.error("Analysis failed", err);
      setAnalyzing(false);
      setAnalysisProgress(0);
    }
  };

  const handleSaveSummary = async () => {
    if (!id) return;
    try {
      await api.updateMeeting(id, {
        summary: editableSummary,
        key_points: editableKeyPoints,
      });
      if (meeting) {
        setMeeting({
          ...meeting,
          summary: editableSummary,
          key_points: editableKeyPoints,
        });
      }
      setIsEditingSummary(false);
    } catch (err) {
      console.error("Failed to save summary", err);
    }
  };

  const handleAddKeyPoint = () => {
    if (!newKeyPointText.trim()) return;
    setEditableKeyPoints([...editableKeyPoints, newKeyPointText.trim()]);
    setNewKeyPointText("");
  };

  const handleAssignProject = async (projectId: string) => {
    if (!id || !meeting) return;
    try {
      const updated = await api.updateMeeting(id, { project_id: projectId || undefined });
      setMeeting({ ...meeting, project_id: updated.project_id });
      setIsChangingProject(false);
    } catch (err) {
      console.error("Failed to assign project", err);
    }
  };

  const handleToggleActionStatus = async (action: ExtractedCommitment) => {
    const nextStatus = action.status === "Completed" ? "In Progress" : "Completed";
    try {
      await api.updateActionItem(action.id || action.commitment_id, { status: nextStatus });
      if (meeting && meeting.action_items) {
        setMeeting({
          ...meeting,
          action_items: meeting.action_items.map((a) =>
            a.id === action.id || a.commitment_id === action.commitment_id
              ? { ...a, status: nextStatus }
              : a
          ),
        });
      }
    } catch (err) {
      console.error("Failed to update action status", err);
    }
  };

  const handleDecisionReview = async (decision: ExtractedDecision, reviewStatus: string) => {
    if (!id) return;
    const targetId = decision.id || decision.decision_id;
    try {
      await api.updateMeetingDecisionReview(id, targetId, reviewStatus);
      if (meeting && meeting.decisions) {
        setMeeting({
          ...meeting,
          decisions: meeting.decisions.map((d) =>
            d.id === targetId || d.decision_id === targetId
              ? { ...d, review_status: reviewStatus }
              : d
          ),
        });
      }
      // Broadcast to other live reviewers
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({
            type: "review_action",
            entity_type: "decision",
            entity_id: targetId,
            review_status: reviewStatus,
          })
        );
      }
    } catch (err) {
      console.error("Failed to update decision review status", err);
    }
  };

  const handleActionReview = async (action: ExtractedCommitment, reviewStatus: string) => {
    if (!id) return;
    const targetId = action.id || action.commitment_id;
    try {
      await api.updateMeetingActionReview(id, targetId, reviewStatus);
      if (meeting && meeting.action_items) {
        setMeeting({
          ...meeting,
          action_items: meeting.action_items.map((a) =>
            a.id === targetId || a.commitment_id === targetId
              ? { ...a, review_status: reviewStatus }
              : a
          ),
        });
      }
      // Broadcast to other live reviewers
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({
            type: "review_action",
            entity_type: "action",
            entity_id: targetId,
            review_status: reviewStatus,
          })
        );
      }
    } catch (err) {
      console.error("Failed to update action review status", err);
    }
  };

  const handleViewSource = (sourceSnippet?: string) => {
    if (!sourceSnippet) return;
    setHighlightedSnippet(sourceSnippet);
    setActiveTab("content");
    setTimeout(() => {
      contentSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 100);
  };

  const currentProject = projects.find(
    (p) => p.id === meeting?.project_id || p.project_id === meeting?.project_id
  );

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-600 mb-3" />
        <p className="text-sm text-slate-500 font-medium">Loading organizational memory workspace...</p>
      </div>
    );
  }

  if (!meeting) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center">
        <AlertCircle className="w-12 h-12 text-rose-500 mx-auto mb-3" />
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Meeting Not Found</h2>
        <p className="text-slate-500 text-sm mt-1 mb-6">
          The meeting may have been deleted or belongs to a different workspace.
        </p>
        <button
          onClick={() => navigate("/meetings")}
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Meetings
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto pb-16 px-4">
      {/* Top Header Navigation */}
      <div className="flex flex-wrap items-center justify-between gap-4 py-4 mb-6 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/meetings")}
            className="p-2 text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition"
            title="Back to all meetings"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                Meeting Workspace 2.0
              </span>
              <span className="text-slate-300 dark:text-slate-700">•</span>
              <span className="text-xs text-slate-500 capitalize">{meeting.content_type || "Transcript"}</span>
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              {meeting.title}
            </h1>
          </div>
        </div>

        {/* Presence & Action buttons */}
        <div className="flex items-center gap-3">
          {/* Active Presence Pill */}
          <div
            className="flex items-center gap-2 px-3 py-1.5 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 rounded-full text-xs font-semibold text-emerald-700 dark:text-emerald-300"
            title={activeViewers.map((v) => v.user_name).join(", ") || "You are viewing"}
          >
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>
              {activeViewers.length > 1
                ? `${activeViewers.length} Reviewers Active`
                : "Live Workspace"}
            </span>
          </div>

          <button
            onClick={handleRunAIAnalysis}
            disabled={analyzing}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-semibold shadow-sm transition disabled:opacity-50"
          >
            {analyzing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Analyzing ({analysisProgress}/5)...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 text-indigo-200" />
                <span>Re-Analyze Intelligence</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Metadata Strip & Project Pill */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-6">
        {/* Project Card */}
        <div className="p-3.5 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-xl">
          <div className="text-xs font-medium text-slate-500 flex items-center justify-between mb-1">
            <span className="flex items-center gap-1.5">
              <Folder className="w-3.5 h-3.5 text-indigo-500" /> Project
            </span>
            <button
              onClick={() => setIsChangingProject(!isChangingProject)}
              className="text-indigo-600 dark:text-indigo-400 hover:underline text-[11px]"
            >
              {isChangingProject ? "Cancel" : "Change"}
            </button>
          </div>
          {isChangingProject ? (
            <select
              value={meeting.project_id || ""}
              onChange={(e) => handleAssignProject(e.target.value)}
              className="w-full mt-1 text-xs border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 rounded p-1.5"
            >
              <option value="">No Project (Unassigned)</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          ) : currentProject ? (
            <Link
              to={`/projects/${currentProject.id}`}
              className="inline-flex items-center gap-1.5 text-sm font-bold text-slate-900 dark:text-white hover:text-indigo-600 transition"
            >
              <span
                className="w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: currentProject.color || "#4f46e5" }}
              />
              {currentProject.name}
              <ExternalLink className="w-3 h-3 text-slate-400" />
            </Link>
          ) : (
            <span className="text-sm font-medium text-slate-400 italic">No project assigned</span>
          )}
        </div>

        {/* Date Card */}
        <div className="p-3.5 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-xl">
          <div className="text-xs font-medium text-slate-500 flex items-center gap-1.5 mb-1">
            <Calendar className="w-3.5 h-3.5 text-slate-400" /> Date & Time
          </div>
          <p className="text-sm font-bold text-slate-900 dark:text-white">
            {new Date(meeting.meeting_date).toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
              year: "numeric",
            })}
          </p>
        </div>

        {/* Participants Card */}
        <div className="p-3.5 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-xl">
          <div className="text-xs font-medium text-slate-500 flex items-center gap-1.5 mb-1">
            <Users className="w-3.5 h-3.5 text-slate-400" /> Participants
          </div>
          <p className="text-sm font-bold text-slate-900 dark:text-white truncate">
            {meeting.participants && meeting.participants.length > 0
              ? meeting.participants.map((p) => p.canonical_name).join(", ")
              : "Team discussion"}
          </p>
        </div>

        {/* Outcomes Count Card */}
        <div className="p-3.5 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-xl">
          <div className="text-xs font-medium text-slate-500 flex items-center gap-1.5 mb-1">
            <Target className="w-3.5 h-3.5 text-emerald-500" /> Extracted Facts
          </div>
          <p className="text-sm font-bold text-slate-900 dark:text-white">
            {meeting.decisions?.length || 0} Decisions • {meeting.action_items?.length || 0} Actions
          </p>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex border-b border-slate-200 dark:border-slate-800 mb-6 gap-2">
        {[
          { id: "summary", label: "Executive Summary & Key Points", icon: Sparkles },
          {
            id: "decisions",
            label: `Decisions (${meeting.decisions?.length || 0})`,
            icon: Target,
          },
          {
            id: "actions",
            label: `Action Items (${meeting.action_items?.length || 0})`,
            icon: CheckSquare,
          },
          { id: "topics", label: `Topics (${meeting.topics?.length || 0})`, icon: Tag },
          { id: "content", label: "Source Content & Traceability", icon: FileText },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 py-3 px-4 text-sm font-semibold border-b-2 transition ${
                isActive
                  ? "border-indigo-600 text-indigo-600 dark:text-indigo-400 bg-indigo-50/50 dark:bg-indigo-950/20"
                  : "border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        {/* SUMMARY TAB */}
        {activeTab === "summary" && (
          <div className="space-y-6">
            {/* Executive Summary Card */}
            <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-indigo-600" />
                  Executive Summary
                </h3>
                {isEditingSummary ? (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleSaveSummary}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-xs font-semibold hover:bg-emerald-700 transition"
                    >
                      <Save className="w-3.5 h-3.5" /> Save
                    </button>
                    <button
                      onClick={() => setIsEditingSummary(false)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-lg text-xs font-semibold hover:bg-slate-300 transition"
                    >
                      <X className="w-3.5 h-3.5" /> Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setIsEditingSummary(true)}
                    className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-indigo-600 font-medium transition"
                  >
                    <Edit3 className="w-3.5 h-3.5" /> Edit
                  </button>
                )}
              </div>

              {isEditingSummary ? (
                <textarea
                  value={editableSummary}
                  onChange={(e) => setEditableSummary(e.target.value)}
                  rows={4}
                  className="w-full p-3 text-sm border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              ) : (
                <p className="text-slate-700 dark:text-slate-300 text-sm leading-relaxed whitespace-pre-line font-normal">
                  {meeting.summary || "No executive summary generated yet. Click Re-Analyze to generate."}
                </p>
              )}
            </div>

            {/* Key Points */}
            <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-indigo-600" />
                  Key Takeaways
                </h3>
              </div>

              {editableKeyPoints && editableKeyPoints.length > 0 ? (
                <ul className="space-y-2.5">
                  {editableKeyPoints.map((point, index) => (
                    <li
                      key={index}
                      className="flex items-start gap-3 text-sm text-slate-700 dark:text-slate-300"
                    >
                      <span className="w-2 h-2 rounded-full bg-indigo-500 mt-2 flex-shrink-0" />
                      <span className="flex-1 leading-relaxed">{point}</span>
                      {isEditingSummary && (
                        <button
                          onClick={() =>
                            setEditableKeyPoints(editableKeyPoints.filter((_, i) => i !== index))
                          }
                          className="text-rose-500 hover:text-rose-700 p-1"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-slate-400 text-sm italic">No key points extracted yet.</p>
              )}

              {isEditingSummary && (
                <div className="flex gap-2 mt-4 pt-3 border-t border-slate-100 dark:border-slate-800">
                  <input
                    type="text"
                    placeholder="Add a new takeaway..."
                    value={newKeyPointText}
                    onChange={(e) => setNewKeyPointText(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleAddKeyPoint()}
                    className="flex-1 px-3 py-1.5 text-xs border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800"
                  />
                  <button
                    onClick={handleAddKeyPoint}
                    className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700"
                  >
                    Add
                  </button>
                </div>
              )}
            </div>

            {/* Quick Highlights of Decisions and Actions */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Recent Decisions Preview */}
              <div className="p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <Target className="w-4 h-4 text-emerald-600" />
                    Decisions Summary
                  </h4>
                  <button
                    onClick={() => setActiveTab("decisions")}
                    className="text-xs text-indigo-600 dark:text-indigo-400 font-semibold hover:underline"
                  >
                    View all ({meeting.decisions?.length || 0})
                  </button>
                </div>
                {meeting.decisions && meeting.decisions.length > 0 ? (
                  <div className="space-y-2">
                    {meeting.decisions.slice(0, 3).map((dec, idx) => (
                      <div
                        key={idx}
                        className="p-2.5 bg-slate-50 dark:bg-slate-800/50 rounded-lg text-xs border border-slate-100 dark:border-slate-800"
                      >
                        <p className="font-semibold text-slate-800 dark:text-slate-200">{dec.subject}</p>
                        <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-500">
                          <span className="px-1.5 py-0.5 bg-emerald-100 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 rounded font-medium">
                            {dec.status}
                          </span>
                          {dec.source_text && (
                            <button
                              onClick={() => handleViewSource(dec.source_text)}
                              className="text-indigo-600 dark:text-indigo-400 hover:underline inline-flex items-center gap-0.5"
                            >
                              <Eye className="w-3 h-3" /> View source
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-slate-400 text-xs italic">No decisions recorded in this meeting.</p>
                )}
              </div>

              {/* Recent Action Items Preview */}
              <div className="p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <CheckSquare className="w-4 h-4 text-indigo-600" />
                    Action Items Summary
                  </h4>
                  <button
                    onClick={() => setActiveTab("actions")}
                    className="text-xs text-indigo-600 dark:text-indigo-400 font-semibold hover:underline"
                  >
                    View all ({meeting.action_items?.length || 0})
                  </button>
                </div>
                {meeting.action_items && meeting.action_items.length > 0 ? (
                  <div className="space-y-2">
                    {meeting.action_items.slice(0, 3).map((act, idx) => (
                      <div
                        key={idx}
                        className="p-2.5 bg-slate-50 dark:bg-slate-800/50 rounded-lg text-xs border border-slate-100 dark:border-slate-800 flex items-start gap-2"
                      >
                        <input
                          type="checkbox"
                          checked={act.status === "Completed"}
                          onChange={() => handleToggleActionStatus(act)}
                          className="mt-0.5 rounded text-indigo-600 focus:ring-indigo-500"
                        />
                        <div className="flex-1">
                          <p
                            className={`font-semibold ${
                              act.status === "Completed"
                                ? "line-through text-slate-400"
                                : "text-slate-800 dark:text-slate-200"
                            }`}
                          >
                            {act.task || act.description}
                          </p>
                          <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-500">
                            <span className="font-medium text-slate-700 dark:text-slate-300">
                              Assignee: {act.owner_id || "Unassigned"}
                            </span>
                            <span>•</span>
                            <span>Due: {act.due_date_str || "Not specified"}</span>
                            {act.source_text && (
                              <button
                                onClick={() => handleViewSource(act.source_text)}
                                className="text-indigo-600 dark:text-indigo-400 hover:underline inline-flex items-center gap-0.5 ml-auto"
                              >
                                <Eye className="w-3 h-3" /> View source
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-slate-400 text-xs italic">No action items created yet.</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* DECISIONS TAB */}
        {activeTab === "decisions" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                  Organizational Decisions
                </h3>
                <p className="text-xs text-slate-500">
                  Decisions extracted from this meeting with rationale, confidence scores, and source evidence.
                </p>
              </div>
            </div>

            {meeting.decisions && meeting.decisions.length > 0 ? (
              <div className="grid grid-cols-1 gap-4">
                {meeting.decisions.map((dec) => (
                  <div
                    key={dec.decision_id || dec.id}
                    className="p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm hover:border-indigo-200 transition"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="flex-1 min-w-[280px]">
                        <div className="flex items-center gap-2 mb-1.5">
                          <span
                            className={`px-2 py-0.5 rounded text-xs font-bold ${
                              dec.status === "Approved" || dec.status === "Confirmed"
                                ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                                : dec.status === "Modified"
                                ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                                : "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300"
                            }`}
                          >
                            {dec.status}
                          </span>

                          {/* Review status badge */}
                          {dec.review_status === "confirmed" ? (
                            <span className="px-2 py-0.5 bg-emerald-50 text-emerald-600 border border-emerald-200 rounded text-xs font-medium inline-flex items-center gap-1">
                              <Check className="w-3 h-3" /> Confirmed
                            </span>
                          ) : dec.review_status === "rejected" ? (
                            <span className="px-2 py-0.5 bg-rose-50 text-rose-600 border border-rose-200 rounded text-xs font-medium">
                              Rejected
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 bg-amber-50 text-amber-700 border border-amber-200 rounded text-xs font-medium inline-flex items-center gap-1">
                              <Sparkles className="w-3 h-3 text-amber-500" /> Needs Review
                            </span>
                          )}

                          <span className="text-xs text-slate-400">
                            Confidence: {Math.round((dec.confidence || 0.95) * 100)}%
                          </span>
                        </div>

                        <h4 className="text-base font-bold text-slate-900 dark:text-white leading-snug">
                          {dec.subject}
                        </h4>

                        {dec.rationale && (
                          <p className="text-xs text-slate-600 dark:text-slate-400 mt-2 bg-slate-50 dark:bg-slate-800/40 p-2.5 rounded-lg border border-slate-100 dark:border-slate-800">
                            <span className="font-semibold text-slate-700 dark:text-slate-300">
                              Rationale:
                            </span>{" "}
                            {dec.rationale}
                          </p>
                        )}
                      </div>

                      {/* Review Buttons & Source Button */}
                      <div className="flex flex-col sm:flex-row items-end sm:items-center gap-2">
                        {dec.source_text && (
                          <button
                            onClick={() => handleViewSource(dec.source_text)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-950/50 dark:hover:bg-indigo-900 text-indigo-700 dark:text-indigo-300 rounded-lg text-xs font-semibold transition"
                          >
                            <Eye className="w-3.5 h-3.5" /> View source
                          </button>
                        )}

                        {dec.review_status !== "confirmed" && (
                          <button
                            onClick={() => handleDecisionReview(dec, "confirmed")}
                            className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold transition"
                            title="Confirm this decision"
                          >
                            <Check className="w-3.5 h-3.5" /> Confirm
                          </button>
                        )}

                        {dec.review_status !== "rejected" && (
                          <button
                            onClick={() => handleDecisionReview(dec, "rejected")}
                            className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-slate-100 hover:bg-rose-50 hover:text-rose-600 dark:bg-slate-800 text-slate-600 rounded-lg text-xs font-semibold transition"
                            title="Reject this decision"
                          >
                            <X className="w-3.5 h-3.5" /> Reject
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl">
                <Target className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                  No decisions found
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  Decisions agreed upon in this meeting will be listed here.
                </p>
              </div>
            )}
          </div>
        )}

        {/* ACTIONS TAB */}
        {activeTab === "actions" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                  Action Items & Follow-ups
                </h3>
                <p className="text-xs text-slate-500">
                  Assigned commitments with deadlines, zero-hallucination verification, and source links.
                </p>
              </div>
            </div>

            {meeting.action_items && meeting.action_items.length > 0 ? (
              <div className="grid grid-cols-1 gap-3">
                {meeting.action_items.map((act) => (
                  <div
                    key={act.commitment_id || act.id}
                    className={`p-4 bg-white dark:bg-slate-900 border rounded-2xl shadow-sm transition ${
                      act.status === "Completed"
                        ? "border-emerald-200 dark:border-emerald-950/60 bg-emerald-50/20"
                        : "border-slate-200 dark:border-slate-800 hover:border-indigo-200"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-3 flex-1">
                        <button
                          onClick={() => handleToggleActionStatus(act)}
                          className={`mt-1 w-5 h-5 rounded-md border flex items-center justify-center transition ${
                            act.status === "Completed"
                              ? "bg-emerald-600 border-emerald-600 text-white"
                              : "border-slate-300 dark:border-slate-600 hover:border-indigo-600"
                          }`}
                        >
                          {act.status === "Completed" && <Check className="w-3.5 h-3.5" />}
                        </button>

                        <div className="flex-1 min-w-[240px]">
                          <p
                            className={`text-sm font-bold leading-tight ${
                              act.status === "Completed"
                                ? "line-through text-slate-400"
                                : "text-slate-900 dark:text-white"
                            }`}
                          >
                            {act.task || act.description}
                          </p>

                          <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-slate-500">
                            <span className="font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-1">
                              <Users className="w-3 h-3 text-slate-400" />
                              {act.owner_id || "Unassigned"}
                            </span>
                            <span className="text-slate-300">•</span>
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3 text-slate-400" />
                              Due: {act.due_date_str || "Not specified"}
                            </span>
                            <span className="text-slate-300">•</span>
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                                act.priority === "high"
                                  ? "bg-rose-100 text-rose-700"
                                  : act.priority === "low"
                                  ? "bg-slate-100 text-slate-700"
                                  : "bg-indigo-100 text-indigo-700"
                              }`}
                            >
                              {act.priority || "medium"}
                            </span>

                            {act.review_status === "confirmed" ? (
                              <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-600 border border-emerald-200 rounded text-[10px] font-semibold">
                                Confirmed
                              </span>
                            ) : act.review_status === "rejected" ? (
                              <span className="px-1.5 py-0.5 bg-rose-50 text-rose-600 border border-rose-200 rounded text-[10px] font-semibold">
                                Rejected
                              </span>
                            ) : (
                              <span className="px-1.5 py-0.5 bg-amber-50 text-amber-700 border border-amber-200 rounded text-[10px] font-semibold">
                                Needs Review
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Source & Actions */}
                      <div className="flex items-center gap-2">
                        {act.source_text && (
                          <button
                            onClick={() => handleViewSource(act.source_text)}
                            className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 rounded-lg text-xs font-semibold"
                          >
                            <Eye className="w-3.5 h-3.5" /> Source
                          </button>
                        )}
                        {act.review_status !== "confirmed" && (
                          <button
                            onClick={() => handleActionReview(act, "confirmed")}
                            className="p-1.5 bg-emerald-100 text-emerald-700 rounded-lg hover:bg-emerald-200 transition"
                            title="Confirm action"
                          >
                            <Check className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl">
                <CheckSquare className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                  No action items assigned
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  Deliverables and follow-ups will appear here.
                </p>
              </div>
            )}
          </div>
        )}

        {/* TOPICS TAB */}
        {activeTab === "topics" && (
          <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm">
            <h3 className="text-base font-bold text-slate-900 dark:text-white mb-2 flex items-center gap-2">
              <Tag className="w-4 h-4 text-indigo-600" /> Discussion Topics
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Categorized tags and thematic topics identified in this meeting.
            </p>

            {meeting.topics && meeting.topics.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {meeting.topics.map((top, idx) => (
                  <Link
                    key={idx}
                    to={`/knowledge?topic=${encodeURIComponent(top)}`}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 border border-indigo-100 dark:border-indigo-800 rounded-xl text-xs font-semibold hover:bg-indigo-100 transition"
                  >
                    <Tag className="w-3 h-3" />
                    {top}
                    <ChevronRight className="w-3 h-3 text-indigo-400" />
                  </Link>
                ))}
              </div>
            ) : (
              <p className="text-slate-400 text-xs italic">No topics extracted.</p>
            )}
          </div>
        )}

        {/* SOURCE CONTENT TAB */}
        {activeTab === "content" && (
          <div
            ref={contentSectionRef}
            className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm"
          >
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <FileText className="w-4 h-4 text-indigo-600" />
                  Source Meeting Content & Evidence
                </h3>
                <p className="text-xs text-slate-500">
                  Full transcript and notes recorded for this meeting.
                </p>
              </div>
              {highlightedSnippet && (
                <button
                  onClick={() => setHighlightedSnippet(null)}
                  className="text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 font-medium"
                >
                  Clear Highlight
                </button>
              )}
            </div>

            {meeting.content ? (
              <div className="p-4 bg-slate-50 dark:bg-slate-950 font-mono text-xs leading-relaxed rounded-xl border border-slate-200 dark:border-slate-800 max-h-[500px] overflow-y-auto whitespace-pre-wrap">
                {highlightedSnippet ? (
                  <div>
                    {meeting.content.split(highlightedSnippet).map((part, index, arr) => (
                      <React.Fragment key={index}>
                        <span>{part}</span>
                        {index < arr.length - 1 && (
                          <mark className="bg-amber-200 text-amber-950 dark:bg-amber-900/60 dark:text-amber-200 font-bold px-1.5 py-0.5 rounded shadow-sm border border-amber-300 dark:border-amber-700 animate-pulse">
                            {highlightedSnippet}
                          </mark>
                        )}
                      </React.Fragment>
                    ))}
                  </div>
                ) : (
                  meeting.content
                )}
              </div>
            ) : (
              <p className="text-slate-400 text-xs italic">No raw content attached to this meeting.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default MeetingDetail;
