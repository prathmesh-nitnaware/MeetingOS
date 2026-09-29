import React, { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import {
  api,
  Project,
  ProjectTimelineItem,
  ExtractedCommitment,
  ExtractedDecision,
} from "../services/api";
import {
  Folder,
  ArrowLeft,
  Calendar,
  Target,
  CheckSquare,
  Tag,
  Clock,
  Check,
  Plus,
  Loader2,
  FileText,
  Users,
  ChevronRight,
  ExternalLink,
  Sparkles,
} from "lucide-react";

export const ProjectDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [project, setProject] = useState<Project | null>(null);
  const [timeline, setTimeline] = useState<ProjectTimelineItem[]>([]);
  const [meetings, setMeetings] = useState<any[]>([]);
  const [decisions, setDecisions] = useState<ExtractedDecision[]>([]);
  const [actions, setActions] = useState<ExtractedCommitment[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"timeline" | "meetings" | "decisions" | "actions">("timeline");

  useEffect(() => {
    if (id) {
      loadProjectData(id);
    }
  }, [id]);

  const loadProjectData = async (projectId: string) => {
    setLoading(true);
    try {
      const [projData, timelineData, meetingsData, decisionsData, actionsData] = await Promise.all([
        api.getProject(projectId),
        api.getProjectTimeline(projectId),
        api.getProjectMeetings(projectId),
        api.getProjectDecisions(projectId),
        api.getProjectActions(projectId),
      ]);

      setProject(projData);
      setTimeline(timelineData);
      setMeetings(meetingsData);
      setDecisions(decisionsData);
      setActions(actionsData);
    } catch (err) {
      console.error("Failed to load project workspace", err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleActionStatus = async (action: ExtractedCommitment) => {
    const nextStatus = action.status === "Completed" ? "In Progress" : "Completed";
    try {
      await api.updateActionItem(action.id || action.commitment_id, { status: nextStatus });
      setActions((prev) =>
        prev.map((a) =>
          a.id === action.id || a.commitment_id === action.commitment_id
            ? { ...a, status: nextStatus }
            : a
        )
      );
    } catch (err) {
      console.error("Failed to toggle action status", err);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-600 mb-3" />
        <p className="text-sm text-slate-500 font-medium">Loading project workspace 2.0...</p>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">Project Not Found</h2>
        <p className="text-sm text-slate-500 mb-6">The project workspace could not be located.</p>
        <button
          onClick={() => navigate("/projects")}
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Projects
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 pb-16">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 py-4 mb-6 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/projects")}
            className="p-2 text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition"
            title="Back to all projects"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                Project Workspace 2.0
              </span>
              <span className="text-slate-300 dark:text-slate-700">•</span>
              <span className="text-xs font-medium text-slate-500 capitalize">{project.status}</span>
            </div>
            <div className="flex items-center gap-2.5 mt-0.5">
              <span
                className="w-3.5 h-3.5 rounded-full flex-shrink-0"
                style={{ backgroundColor: project.color || "#4f46e5" }}
              />
              <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
                {project.name}
              </h1>
            </div>
          </div>
        </div>

        <Link
          to={`/create-meeting?project_id=${project.id || project.project_id}`}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-semibold shadow-sm transition"
        >
          <Plus className="w-4 h-4" />
          <span>Add Meeting to Project</span>
        </Link>
      </div>

      {/* Description */}
      {project.description && (
        <p className="text-sm text-slate-600 dark:text-slate-300 max-w-3xl mb-6 leading-relaxed">
          {project.description}
        </p>
      )}

      {/* Overview Aggregation Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="p-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 mb-1">
            <Calendar className="w-4 h-4 text-indigo-500" /> Meetings
          </div>
          <div className="text-2xl font-black text-slate-900 dark:text-white">
            {meetings.length}
          </div>
        </div>

        <div className="p-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 mb-1">
            <Target className="w-4 h-4 text-emerald-500" /> Decisions
          </div>
          <div className="text-2xl font-black text-emerald-600">
            {decisions.length}
          </div>
        </div>

        <div className="p-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 mb-1">
            <CheckSquare className="w-4 h-4 text-indigo-500" /> Action Items
          </div>
          <div className="text-2xl font-black text-indigo-600">
            {actions.filter((a) => a.status !== "Completed").length}{" "}
            <span className="text-xs font-medium text-slate-400">/ {actions.length}</span>
          </div>
        </div>

        <div className="p-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 mb-1">
            <Sparkles className="w-4 h-4 text-amber-500" /> Intelligence
          </div>
          <div className="text-2xl font-black text-slate-900 dark:text-white">
            {timeline.length} <span className="text-xs font-medium text-slate-400">Milestones</span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 dark:border-slate-800 mb-6 gap-2">
        {[
          { id: "timeline", label: "Chronological Timeline", icon: Clock },
          { id: "meetings", label: `Meetings (${meetings.length})`, icon: Calendar },
          { id: "decisions", label: `Decisions (${decisions.length})`, icon: Target },
          { id: "actions", label: `Action Items (${actions.length})`, icon: CheckSquare },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 py-3 px-4 text-sm font-semibold border-b-2 transition ${
                isActive
                  ? "border-indigo-600 text-indigo-600 dark:text-indigo-400 bg-indigo-50/40 dark:bg-indigo-950/20"
                  : "border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* TAB 1: CHRONOLOGICAL TIMELINE */}
      {activeTab === "timeline" && (
        <div className="space-y-6">
          {timeline.length === 0 ? (
            <div className="p-8 text-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl">
              <Clock className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                No timeline events yet
              </p>
              <p className="text-xs text-slate-400 mt-1">
                Meetings added to this project will form a chronological memory timeline.
              </p>
            </div>
          ) : (
            <div className="relative pl-6 border-l-2 border-indigo-200 dark:border-indigo-900/60 space-y-8 ml-3">
              {timeline.map((item, idx) => (
                <div key={item.meeting_id} className="relative group">
                  {/* Timeline dot */}
                  <div className="absolute -left-[31px] top-1.5 w-4 h-4 rounded-full bg-white dark:bg-slate-950 border-4 border-indigo-600 group-hover:scale-125 transition" />

                  <div className="p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm hover:border-indigo-300 dark:hover:border-indigo-700 transition">
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                      <div className="text-xs font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">
                        {new Date(item.meeting_date).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                          year: "numeric",
                        })}
                      </div>
                      <Link
                        to={`/meetings/${item.meeting_id}`}
                        className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-indigo-600 font-semibold transition"
                      >
                        <span>Open Workspace</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </Link>
                    </div>

                    <h3 className="text-base font-bold text-slate-900 dark:text-white mb-2">
                      {item.title}
                    </h3>

                    {item.summary && (
                      <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed mb-4">
                        {item.summary}
                      </p>
                    )}

                    {/* Timeline Decisions & Actions */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-3 border-t border-slate-100 dark:border-slate-800">
                      {/* Decisions in this meeting */}
                      <div>
                        <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1">
                          <Target className="w-3 h-3 text-emerald-500" /> Decisions
                        </div>
                        {item.decisions.length > 0 ? (
                          <div className="space-y-1.5">
                            {item.decisions.map((d, dIdx) => (
                              <div
                                key={dIdx}
                                className="p-2 bg-slate-50 dark:bg-slate-800/40 rounded-lg text-xs border border-slate-100 dark:border-slate-800 text-slate-800 dark:text-slate-200 font-medium"
                              >
                                {d.subject}
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-xs text-slate-400 italic">None recorded</p>
                        )}
                      </div>

                      {/* Actions in this meeting */}
                      <div>
                        <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1">
                          <CheckSquare className="w-3 h-3 text-indigo-500" /> Actions
                        </div>
                        {item.action_items.length > 0 ? (
                          <div className="space-y-1.5">
                            {item.action_items.map((a, aIdx) => (
                              <div
                                key={aIdx}
                                className="p-2 bg-slate-50 dark:bg-slate-800/40 rounded-lg text-xs border border-slate-100 dark:border-slate-800 flex items-center justify-between text-slate-800 dark:text-slate-200 font-medium"
                              >
                                <span>{a.task}</span>
                                <span className="text-[10px] text-slate-400 ml-2">
                                  {a.owner || "Unassigned"}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-xs text-slate-400 italic">None assigned</p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: MEETINGS */}
      {activeTab === "meetings" && (
        <div className="space-y-4">
          {meetings.length === 0 ? (
            <div className="p-8 text-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl">
              <Calendar className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                No meetings assigned to this project
              </p>
              <Link
                to={`/create-meeting?project_id=${project.id || project.project_id}`}
                className="inline-flex items-center gap-2 mt-3 px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold"
              >
                <Plus className="w-3.5 h-3.5" /> Add Meeting
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {meetings.map((m) => (
                <Link
                  key={m.id || m.meeting_id}
                  to={`/meetings/${m.id || m.meeting_id}`}
                  className="p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm hover:border-indigo-300 dark:hover:border-indigo-700 transition group flex flex-col justify-between"
                >
                  <div>
                    <div className="text-xs font-semibold text-slate-400 mb-1">
                      {new Date(m.meeting_date).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </div>
                    <h4 className="text-base font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 transition mb-2">
                      {m.title}
                    </h4>
                    {m.summary && (
                      <p className="text-xs text-slate-500 line-clamp-2 mb-4">{m.summary}</p>
                    )}
                  </div>

                  <div className="flex items-center justify-between text-xs font-semibold pt-3 border-t border-slate-100 dark:border-slate-800 text-slate-500">
                    <span>
                      {m.decisions_count || 0} Decisions • {m.actions_count || 0} Actions
                    </span>
                    <span className="text-indigo-600 group-hover:translate-x-1 transition">
                      View Workspace →
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: DECISIONS */}
      {activeTab === "decisions" && (
        <div className="space-y-4">
          {decisions.length === 0 ? (
            <div className="p-8 text-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl">
              <Target className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                No decisions recorded for this project
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {decisions.map((dec) => (
                <div
                  key={dec.id || dec.decision_id}
                  className="p-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm"
                >
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <span className="px-2 py-0.5 bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 text-xs font-bold rounded">
                      {dec.status}
                    </span>
                    <Link
                      to={`/meetings/${dec.meeting_id}`}
                      className="text-xs text-slate-400 hover:text-indigo-600 font-medium"
                    >
                      {dec.meeting_title || "Source Meeting"} →
                    </Link>
                  </div>
                  <h4 className="text-sm font-bold text-slate-900 dark:text-white">{dec.subject}</h4>
                  {dec.rationale && (
                    <p className="text-xs text-slate-500 mt-1">Rationale: {dec.rationale}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 4: ACTION ITEMS */}
      {activeTab === "actions" && (
        <div className="space-y-3">
          {actions.length === 0 ? (
            <div className="p-8 text-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl">
              <CheckSquare className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                No action items tracked in this project
              </p>
            </div>
          ) : (
            actions.map((act) => (
              <div
                key={act.id || act.commitment_id}
                className={`p-4 bg-white dark:bg-slate-900 border rounded-2xl shadow-sm flex items-start gap-3 ${
                  act.status === "Completed"
                    ? "border-emerald-200 dark:border-emerald-950 bg-emerald-50/10"
                    : "border-slate-200 dark:border-slate-800"
                }`}
              >
                <button
                  onClick={() => handleToggleActionStatus(act)}
                  className={`mt-0.5 w-5 h-5 rounded-md border flex items-center justify-center transition ${
                    act.status === "Completed"
                      ? "bg-emerald-600 border-emerald-600 text-white"
                      : "border-slate-300 dark:border-slate-600 hover:border-indigo-600"
                  }`}
                >
                  {act.status === "Completed" && <Check className="w-3.5 h-3.5" />}
                </button>

                <div className="flex-1">
                  <p
                    className={`text-sm font-bold ${
                      act.status === "Completed"
                        ? "line-through text-slate-400"
                        : "text-slate-900 dark:text-white"
                    }`}
                  >
                    {act.task || act.description}
                  </p>
                  <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
                    <span>Assignee: {act.owner_id || "Unassigned"}</span>
                    <span>•</span>
                    <span>Due: {act.due_date_str || "Not specified"}</span>
                    <Link
                      to={`/meetings/${act.meeting_id}`}
                      className="ml-auto text-indigo-600 dark:text-indigo-400 hover:underline"
                    >
                      {act.meeting_title || "Meeting"} →
                    </Link>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default ProjectDetail;
