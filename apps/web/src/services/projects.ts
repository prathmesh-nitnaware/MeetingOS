export interface Project {
  id: string
  name: string
  description: string
  color: string
  iconType: string
  customInstructions?: string
  createdAt: string
  updatedAt: string
}

const STORAGE_PROJECTS_KEY = "meetingos_projects"
const STORAGE_MEETING_PROJECTS_KEY = "meetingos_meeting_projects"

export const projectService = {
  getProjects: (): Project[] => {
    try {
      const raw = localStorage.getItem(STORAGE_PROJECTS_KEY)
      if (!raw) {
        return []
      }
      return JSON.parse(raw)
    } catch {
      return []
    }
  },

  getProject: (id: string): Project | undefined => {
    const list = projectService.getProjects()
    return list.find((p) => p.id === id)
  },

  createProject: (data: {
    name: string
    description?: string
    color?: string
    iconType?: string
    customInstructions?: string
  }): Project => {
    const projects = projectService.getProjects()
    const id = data.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || `proj-${Date.now()}`
    
    // Avoid collision
    const existing = projects.find((p) => p.id === id)
    const finalId = existing ? `${id}-${Math.floor(Math.random() * 1000)}` : id

    const newProject: Project = {
      id: finalId,
      name: data.name,
      description: data.description || "Project workspace for categorized meetings and contextual AI reasoning.",
      color: data.color || "#3b82f6",
      iconType: data.iconType || "folder",
      customInstructions: data.customInstructions || "",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }

    const updated = [...projects, newProject]
    localStorage.setItem(STORAGE_PROJECTS_KEY, JSON.stringify(updated))
    return newProject
  },

  updateProject: (id: string, data: Partial<Project>): Project | undefined => {
    const projects = projectService.getProjects()
    const index = projects.findIndex((p) => p.id === id)
    if (index === -1) return undefined

    const updatedProject = {
      ...projects[index],
      ...data,
      updatedAt: new Date().toISOString(),
    }
    projects[index] = updatedProject
    localStorage.setItem(STORAGE_PROJECTS_KEY, JSON.stringify(projects))
    return updatedProject
  },

  deleteProject: (id: string): boolean => {
    const projects = projectService.getProjects()
    const filtered = projects.filter((p) => p.id !== id)
    if (filtered.length === projects.length) return false

    localStorage.setItem(STORAGE_PROJECTS_KEY, JSON.stringify(filtered))
    return true
  },

  // Meeting to Project Mapping
  getMeetingProjectMapping: (): Record<string, string> => {
    try {
      const raw = localStorage.getItem(STORAGE_MEETING_PROJECTS_KEY)
      return raw ? JSON.parse(raw) : {}
    } catch {
      return {}
    }
  },

  getMeetingProjectId: (meeting: { meeting_id: string; title?: string }): string => {
    const map = projectService.getMeetingProjectMapping()
    return map[meeting.meeting_id] || ""
  },

  setMeetingProject: (meetingId: string, projectId: string) => {
    const map = projectService.getMeetingProjectMapping()
    if (!projectId) {
      delete map[meetingId]
    } else {
      map[meetingId] = projectId
    }
    localStorage.setItem(STORAGE_MEETING_PROJECTS_KEY, JSON.stringify(map))
  },
}
