import React, { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api, Project } from "../services/api";
import {
  Folder,
  Plus,
  ArrowRight,
  Sparkles,
  Calendar,
  Target,
  CheckSquare,
  Tag,
  Loader2,
  FolderPlus,
  Activity,
} from "lucide-react";

export const ProjectsList: React.FC = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  // New Project Modal
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectDesc, setNewProjectDesc] = useState("");
  const [newProjectColor, setNewProjectColor] = useState("#4f46e5");
  const [creating, setCreating] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const list = await api.getProjects();
      setProjects(list);
    } catch (err: any) {
      console.error("Failed to load projects:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName.trim()) return;

    try {
      setCreating(true);
      const created = await api.createProject({
        name: newProjectName.trim(),
        description: newProjectDesc.trim(),
        color: newProjectColor,
      });
      setIsCreateModalOpen(false);
      setNewProjectName("");
      setNewProjectDesc("");
      navigate(`/projects/${created.id || created.project_id}`);
    } catch (err) {
      console.error("Failed to create project", err);
    } finally {
      setCreating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-600 mb-3" />
        <p className="text-sm text-slate-500 font-medium">Loading projects & workspaces...</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 pb-16">
      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 py-6 border-b border-slate-200 dark:border-slate-800 mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
              Organizational Memory
            </span>
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Projects & Workspaces
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Connected workspaces that aggregate meetings, decisions, action items, and topic timelines.
          </p>
        </div>
        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-semibold shadow-sm transition"
        >
          <Plus className="w-4 h-4" />
          <span>New Project</span>
        </button>
      </div>

      {/* Projects Grid */}
      {projects.length === 0 ? (
        <div className="p-12 text-center bg-white dark:bg-slate-900 border border-dashed border-slate-300 dark:border-slate-800 rounded-2xl">
          <div className="w-14 h-14 bg-indigo-50 dark:bg-indigo-950/50 rounded-2xl flex items-center justify-center mx-auto mb-4 text-indigo-600 dark:text-indigo-400">
            <FolderPlus className="w-7 h-7" />
          </div>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">
            No Projects Created Yet
          </h3>
          <p className="text-sm text-slate-500 max-w-md mx-auto mb-6">
            Create project workspaces (e.g. <em>Product Launch, Engineering Sprints, Customer Research</em>) to connect meetings and organizational knowledge.
          </p>
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-semibold transition"
          >
            <Plus className="w-4 h-4" />
            <span>Create Your First Project</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((proj) => (
            <Link
              key={proj.id || proj.project_id}
              to={`/projects/${proj.id || proj.project_id}`}
              className="group p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm hover:shadow-md hover:border-indigo-300 dark:hover:border-indigo-700 transition flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-3">
                  <div className="flex items-center gap-2.5">
                    <span
                      className="w-3.5 h-3.5 rounded-full flex-shrink-0"
                      style={{ backgroundColor: proj.color || "#4f46e5" }}
                    />
                    <h3 className="text-lg font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 transition">
                      {proj.name}
                    </h3>
                  </div>
                  <span className="px-2 py-0.5 text-[11px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 rounded-full capitalize">
                    {proj.status || "active"}
                  </span>
                </div>

                <p className="text-xs text-slate-500 line-clamp-2 mb-6">
                  {proj.description || "No description provided for this project."}
                </p>
              </div>

              <div>
                {/* Project aggregated metrics */}
                <div className="grid grid-cols-3 gap-2 py-3 border-t border-slate-100 dark:border-slate-800 text-center mb-4">
                  <div className="p-2 bg-slate-50 dark:bg-slate-800/40 rounded-xl">
                    <div className="text-base font-extrabold text-slate-900 dark:text-white">
                      {proj.meeting_count || 0}
                    </div>
                    <div className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">
                      Meetings
                    </div>
                  </div>
                  <div className="p-2 bg-slate-50 dark:bg-slate-800/40 rounded-xl">
                    <div className="text-base font-extrabold text-emerald-600">
                      {proj.decision_count || 0}
                    </div>
                    <div className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">
                      Decisions
                    </div>
                  </div>
                  <div className="p-2 bg-slate-50 dark:bg-slate-800/40 rounded-xl">
                    <div className="text-base font-extrabold text-indigo-600">
                      {proj.open_action_count || 0}
                    </div>
                    <div className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">
                      Actions
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between text-xs font-semibold text-indigo-600 dark:text-indigo-400 group-hover:translate-x-1 transition duration-200">
                  <span>Open Project Workspace</span>
                  <ArrowRight className="w-4 h-4" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Create Project Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 w-full max-w-lg shadow-xl animate-in fade-in zoom-in-95">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-1">
              Create New Project Workspace
            </h2>
            <p className="text-xs text-slate-500 mb-5">
              Group related meetings, track collective decisions, and visualize evolution.
            </p>

            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Project Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Q4 Product Launch, Mobile App V2"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  className="w-full px-3.5 py-2.5 text-sm border border-slate-300 dark:border-slate-700 rounded-xl bg-white dark:bg-slate-800 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Description
                </label>
                <textarea
                  rows={3}
                  placeholder="What is the mission or scope of this project?"
                  value={newProjectDesc}
                  onChange={(e) => setNewProjectDesc(e.target.value)}
                  className="w-full px-3.5 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-xl bg-white dark:bg-slate-800 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Color Tag
                </label>
                <div className="flex items-center gap-3">
                  {["#4f46e5", "#10b981", "#f59e0b", "#ec4899", "#06b6d4", "#8b5cf6"].map((color) => (
                    <button
                      type="button"
                      key={color}
                      onClick={() => setNewProjectColor(color)}
                      className={`w-7 h-7 rounded-full transition ${
                        newProjectColor === color ? "ring-2 ring-offset-2 ring-indigo-500 scale-110" : ""
                      }`}
                      style={{ backgroundColor: color }}
                    />
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-4 py-2 text-sm font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating || !newProjectName.trim()}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl shadow-sm transition disabled:opacity-50"
                >
                  {creating ? "Creating..." : "Create Project"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProjectsList;
