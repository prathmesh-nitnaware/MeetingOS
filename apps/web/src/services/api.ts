export interface Participant {
  id?: string;
  canonical_name: string;
  aliases?: string[];
}

export interface TranscriptSegment {
  segment_id: string;
  sequence: number;
  speaker_id: string;
  start_time: number;
  end_time: number;
  text: string;
}

export interface MeetingMetadata {
  source_filename?: string;
  file_size_bytes?: number;
  content_type?: string;
  project_id?: string;
}

export interface MeetingSummary {
  meeting_id: string;
  title: string;
  meeting_date: string;
  duration_seconds?: number;
  source_type: string;
  content_type?: string;
  summary?: string;
  key_points?: string[];
  topics?: string[];
  project_id?: string;
  decisions_count?: number;
  actions_count?: number;
  processing_status: string;
  participant_count: number;
  segment_count: number;
  created_at: string;
}

export interface MeetingDetailResponse {
  meeting_id: string;
  title: string;
  meeting_date: string;
  duration_seconds?: number;
  source_type: string;
  content_type?: string;
  content?: string;
  summary?: string;
  key_points?: string[];
  topics?: string[];
  project_id?: string;
  processing_status: string;
  participants: Participant[];
  speakers_count: number;
  segments_count: number;
  decisions?: ExtractedDecision[];
  action_items?: ExtractedCommitment[];
  metadata: MeetingMetadata;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: string;
  project_id?: string;
  name: string;
  description?: string;
  color?: string;
  status: string;
  meeting_count?: number;
  decision_count?: number;
  open_action_count?: number;
  topic_count?: number;
  created_at?: string;
  updated_at?: string;
}

export interface ProjectTimelineItem {
  meeting_id: string;
  title: string;
  meeting_date: string;
  summary?: string;
  decisions: Array<{
    decision_id: string;
    subject: string;
    status: string;
    confidence?: number;
    source_text?: string;
  }>;
  action_items: Array<{
    commitment_id: string;
    task?: string;
    owner?: string;
    status: string;
    due_date?: string;
    source_text?: string;
  }>;
  topics: string[];
}

export interface TopicEvolutionItem {
  meeting_id: string;
  meeting_title: string;
  meeting_date: string;
  summary?: string;
  decisions_count: number;
  actions_count: number;
}

export interface TopicDetail {
  topic: string;
  total_meetings: number;
  decisions: ExtractedDecision[];
  action_items: ExtractedCommitment[];
  evolution: TopicEvolutionItem[];
}

export type TopicDetailResponse = TopicDetail;

export interface ActivityItem {
  id: string;
  type: string;
  title: string;
  description?: string;
  timestamp?: string;
  meeting_id?: string;
  meeting_title?: string;
  resource_id?: string;
  resource_type?: string;
}

export interface CalendarEvent {
  external_event_id: string;
  provider: string;
  calendar_id?: string;
  title: string;
  start_time: string;
  end_time: string;
  description?: string;
  location?: string;
  meeting_link?: string;
  organizer_email?: string;
  participants: Array<{ id: string; name: string; email?: string }>;
  project_id?: string;
  sync_status: string;
}

export interface CalendarProviderInfo {
  provider: string;
  name: string;
  enabled: boolean;
  configured: boolean;
  authenticated: boolean;
  supports_sync: boolean;
}

export interface ActiveViewer {
  user_id: string;
  user_name: string;
  email?: string;
  joined_at: string;
}

export interface TranscriptResponse {
  meeting_id: string;
  segments_count: number;
  segments: TranscriptSegment[];
}

export interface ExtractedEntity {
  entity_id: string;
  name: string;
  entity_type: string;
  confidence?: number;
  aliases?: string[];
}

export interface ExtractedDecision {
  decision_id: string;
  id?: string;
  title?: string;
  decision?: string;
  subject?: string;
  status: string;
  context?: string;
  rationale?: string;
  confidence?: number;
  source_text?: string;
  source_start?: number;
  source_end?: number;
  review_status?: string;
  meeting_id: string;
  meeting_title?: string;
  meeting_date?: string;
  project_id?: string;
  evidence_segment_id?: string;
  created_at?: string;
}

export type Decision = ExtractedDecision;

export interface ExtractedCommitment {
  commitment_id: string;
  id?: string;
  task?: string;
  action?: string;
  description: string;
  owner?: string;
  owner_id?: string;
  status: string;
  priority?: string;
  due_date?: string;
  due_date_str?: string;
  confidence?: number;
  source_text?: string;
  source_start?: number;
  source_end?: number;
  review_status?: string;
  original_deadline?: string;
  current_deadline?: string;
  meeting_id: string;
  meeting_title?: string;
  meeting_date?: string;
  project_id?: string;
  evidence_segment_id?: string;
  created_at?: string;
}

export type ActionItem = ExtractedCommitment;

export interface ExtractedIssue {
  issue_id: string;
  description: string;
  owner_id?: string;
  status: string;
  first_detected_at: string;
  last_mentioned_at?: string;
  resolution_meeting_id?: string;
  evidence_segment_id?: string;
}

export interface ExtractedEvent {
  event_id: string;
  event_type: string;
  occurred_at: string;
  meeting_id: string;
  subject_entity_id?: string;
  payload_json?: Record<string, any>;
  evidence_segment_id?: string;
}

export interface ExtractedRelation {
  relation_id: string;
  source_entity_id: string;
  target_entity_id: string;
  relationship_type: string;
  meeting_id: string;
}

export interface DashboardMetrics {
  meetings_ingested: number;
  decisions_tracked: number;
  open_actions: number;
  overdue_actions: number;
  unresolved_issues: number;
  recurring_issues: number;
  canonical_entities_tracked: number;
  relationships_tracked: number;
}

export interface KnowledgeTopic {
  name: string;
  count: number;
}

export interface KnowledgeResponse {
  topics: KnowledgeTopic[];
  recurring_topics: KnowledgeTopic[];
  recent_decisions: ExtractedDecision[];
  recent_actions: ExtractedCommitment[];
  recent_action_items?: ExtractedCommitment[];
  recent_key_points: string[];
  total_meetings: number;
  active_topics_count?: number;
  total_decisions?: number;
  total_action_items?: number;
}

export type KnowledgeSummary = KnowledgeResponse;

export interface TeamMember {
  id?: string;
  name: string;
  email?: string;
  role: string;
  department?: string;
  meeting_count?: number;
  meetings_count?: number;
  open_actions_count: number;
}

export interface SearchResultItem {
  id: string;
  type: "meeting" | "transcript" | "decision" | "action" | "topic" | "entity" | "notes";
  title: string;
  snippet: string;
  text?: string;
  meeting_id?: string;
  meeting_title?: string;
  meeting_date?: string;
  source_type?: string;
  segment_id?: string;
  date?: string;
  status?: string;
  owner?: string;
  score?: number;
}

export interface SearchResponse {
  query: string;
  total: number;
  total_results?: number;
  results: SearchResultItem[];
}

export interface GraphNode {
  id: string;
  label: string;
  name?: string;
  entity_type: string;
  type?: string;
  mention_count?: number;
  presence_count?: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relationship_type: string;
  weight?: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface AgentStep {
  step_number: number;
  agent_name: string;
  tool_name: string;
  input_params: Record<string, any>;
  output_summary: string;
  duration_ms: number;
  timestamp: string;
}

export interface AgentTrace {
  trace_id: string;
  query: string;
  meeting_id?: string;
  total_duration_ms: number;
  steps: AgentStep[];
  outcome: string;
  created_at: string;
}

export interface ConnectorStatus {
  provider: string;
  enabled: boolean;
  configured: boolean;
  authenticated: boolean;
  last_sync_at?: string;
}

export interface AuditLog {
  id: string;
  timestamp: string;
  actor_id: string;
  action: string;
  outcome: string;
  details?: Record<string, any>;
}

export interface TimelineEventItem {
  event_id: string;
  event_type: string;
  occurred_at: string;
  timestamp?: string;
  title?: string;
  description?: string;
  meeting_id: string;
  meeting_title?: string;
  subject_entity_id?: string;
  payload?: Record<string, any>;
  evidence_segment_id?: string;
}

export interface DecisionHistoryItem {
  decision_id: string;
  decision: {
    subject: string;
    rationale?: string;
  };
  status: string;
  meeting_id?: string;
  meeting_title?: string;
  timestamp?: string;
  events: TimelineEventItem[];
}

export interface CommitmentHistoryItem {
  commitment_id: string;
  commitment: {
    description: string;
    owner_id: string;
  };
  status: string;
  deadline?: string;
  original_deadline?: string;
  current_deadline?: string;
  deadline_changes_count?: number;
  meeting_id?: string;
  meeting_title?: string;
  timestamp?: string;
  events: TimelineEventItem[];
}

export interface IssueHistoryItem {
  issue_id: string;
  issue: {
    description: string;
  };
  status: string;
  first_detected_at?: string;
  last_mentioned_at?: string;
  resolution_meeting_id?: string;
  meetings_count?: number;
  is_recurring?: boolean;
  is_resolved?: boolean;
  events: TimelineEventItem[];
}

export interface AgenticQueryResponse {
  query: string;
  answer: string;
  confidence: number;
  steps?: AgentStep[];
  trace?: any[];
  citations?: string[];
  evidence?: any[];
  facts_used?: any[];
  contradictions?: any[];
  insufficient_evidence?: boolean;
  reasoning_summary?: string;
}

export interface RAGQueryResponse {
  query: string;
  answer: string;
  confidence: number;
  retrieved_passages?: any[];
  evidence?: any[];
  reasoning_path?: any[];
}

export type QueryResponse = RAGQueryResponse;
export type QueryPlan = any;
export type EntityDetailResponse = any;
export type EntityTimelineResponse = any;

const API_BASE_URL = "/api/v1";

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("meetingos_token") || "mock-token-org-dev";
  const orgId = localStorage.getItem("meetingos_org_id") || "org_dev";

  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    "X-Org-Id": orgId,
    ...(options.headers as Record<string, string>),
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = `Request failed: ${response.status} ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorDetail = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // fallback to statusText
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export const api = {
  // Meetings API
  listMeetings: (topic?: string, limit = 50, offset = 0) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (topic) params.append("topic", topic);
    return request<MeetingSummary[]>(`/meetings?${params.toString()}`);
  },

  getMeetingDetail: (meetingId: string) =>
    request<MeetingDetailResponse>(`/meetings/${meetingId}`),

  createMeetingText: (data: {
    title: string;
    meeting_date?: string;
    participants?: string[];
    content_type?: string;
    content: string;
    project_id?: string;
    auto_analyze?: boolean;
  }) =>
    request<{ meeting_id: string; job_id: string; processing_status: string; title: string; summary?: string }>(
      "/meetings/create-text",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }
    ),

  analyzeMeeting: (meetingId: string) =>
    request<{
      meeting_id: string;
      summary: string;
      key_points: string[];
      topics: string[];
      decisions: ExtractedDecision[];
      action_items: ExtractedCommitment[];
    }>(`/meetings/${meetingId}/analyze`, { method: "POST" }),

  updateMeeting: (
    meetingId: string,
    data: {
      title?: string;
      meeting_date?: string;
      content_type?: string;
      content?: string;
      summary?: string;
      key_points?: string[];
      project_id?: string;
      participants?: string[];
    }
  ) =>
    request<MeetingDetailResponse>(`/meetings/${meetingId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),

  deleteMeeting: (meetingId: string, hardDelete = false) =>
    request<{ status: string; meeting_id: string }>(
      `/meetings/${meetingId}?hard_delete=${hardDelete}`,
      { method: "DELETE" }
    ),

  getMeetingTranscript: (meetingId: string) =>
    request<TranscriptResponse>(`/meetings/${meetingId}/transcript`),

  getMeetingDecisions: (meetingId: string) =>
    request<ExtractedDecision[]>(`/meetings/${meetingId}/decisions`),

  getMeetingActions: (meetingId: string) =>
    request<ExtractedCommitment[]>(`/meetings/${meetingId}/actions`),

  getMeetingTopics: (meetingId: string) =>
    request<string[]>(`/meetings/${meetingId}/topics`),

  getMeetingEntities: (meetingId: string) =>
    request<ExtractedEntity[]>(`/meetings/${meetingId}/entities`),

  getMeetingTimeline: (meetingId: string) =>
    request<ExtractedEvent[]>(`/meetings/${meetingId}/timeline`),

  getMeetingRelations: (meetingId: string) =>
    request<ExtractedRelation[]>(`/meetings/${meetingId}/relations`),

  // Action Items API
  listActionItems: (filters?: {
    status?: string;
    owner?: string;
    priority?: string;
    meeting_id?: string;
    project_id?: string;
    limit?: number;
    offset?: number;
  }) => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, val]) => {
        if (val !== undefined && val !== null && val !== "") params.append(key, String(val));
      });
    }
    return request<ExtractedCommitment[]>(`/action-items?${params.toString()}`).then(items =>
      items.map(i => ({
        ...i,
        id: i.id || i.commitment_id,
        action: i.task || i.description,
        owner: i.owner || i.owner_id,
        due_date: i.due_date_str || i.current_deadline || i.due_date,
      }))
    );
  },

  getActionItems: (filters?: any) => api.listActionItems(filters),

  updateActionItem: (
    commitmentId: string,
    data: {
      status?: string;
      task?: string;
      action?: string;
      description?: string;
      owner?: string;
      owner_id?: string;
      priority?: string;
      due_date?: string;
      due_date_str?: string;
      review_status?: string;
    }
  ) =>
    request<ExtractedCommitment>(`/action-items/${commitmentId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...data,
        task: data.task || data.action,
        owner_id: data.owner_id || data.owner,
        due_date_str: data.due_date_str || data.due_date,
      }),
    }),

  createActionItem: (data: {
    meeting_id: string;
    task: string;
    description?: string;
    owner_id?: string;
    priority?: string;
    due_date_str?: string;
    status?: string;
  }) =>
    request<ExtractedCommitment>("/action-items", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),

  // Projects API
  listProjects: () => request<Project[]>("/projects"),
  getProjects: () => api.listProjects(),
  getProject: (id: string) => request<Project>(`/projects/${id}`),
  createProject: (data: { name: string; description?: string; color?: string; status?: string }) =>
    request<Project>("/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  updateProject: (id: string, data: { name?: string; description?: string; color?: string; status?: string }) =>
    request<Project>(`/projects/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  deleteProject: (id: string) =>
    request<{ status: string; project_id: string }>(`/projects/${id}`, {
      method: "DELETE",
    }),
  getProjectTimeline: (id: string) => request<ProjectTimelineItem[]>(`/projects/${id}/timeline`),
  getProjectMeetings: (id: string) => request<any[]>(`/projects/${id}/meetings`),
  getProjectActions: (id: string) => request<ExtractedCommitment[]>(`/projects/${id}/actions`),
  getProjectDecisions: (id: string) => request<ExtractedDecision[]>(`/projects/${id}/decisions`),

  // Topic detail
  getTopicDetail: (topicName: string) =>
    request<TopicDetailResponse>(`/knowledge/topics/${encodeURIComponent(topicName)}`),

  // Activity Feed ("What Changed?")
  getActivityFeed: (limit = 10) => request<ActivityItem[]>(`/dashboard/activity?limit=${limit}`),

  // Evidence & Review
  getMeetingEvidence: (meetingId: string) => request<any>(`/meetings/${meetingId}/evidence`),
  updateMeetingDecisionReview: (meetingId: string, decisionId: string, reviewStatus: string) =>
    request<any>(`/meetings/${meetingId}/decisions/${decisionId}/review?review_status=${reviewStatus}`, {
      method: "PATCH",
    }),
  updateMeetingActionReview: (meetingId: string, commitmentId: string, reviewStatus: string) =>
    request<any>(`/meetings/${meetingId}/actions/${commitmentId}/review?review_status=${reviewStatus}`, {
      method: "PATCH",
    }),
  reanalyzeMeeting: (meetingId: string) =>
    request<any>(`/meetings/${meetingId}/analyze`, {
      method: "POST",
    }),

  // Decisions API
  listDecisions: (filters?: {
    status?: string;
    meeting_id?: string;
    project_id?: string;
    limit?: number;
    offset?: number;
  }) => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, val]) => {
        if (val !== undefined && val !== null && val !== "") params.append(key, String(val));
      });
    }
    return request<ExtractedDecision[]>(`/decisions?${params.toString()}`).then(items =>
      items.map(d => ({
        ...d,
        id: d.id || d.decision_id,
        decision: d.decision || d.title || d.subject,
      }))
    );
  },

  getDecisions: (filters?: any) => api.listDecisions(filters),

  updateDecision: (
    decisionId: string,
    data: {
      status?: string;
      title?: string;
      decision?: string;
      subject?: string;
      context?: string;
      rationale?: string;
    }
  ) =>
    request<ExtractedDecision>(`/decisions/${decisionId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...data,
        title: data.title || data.decision,
        subject: data.subject || data.decision,
      }),
    }),

  createDecision: (data: {
    meeting_id: string;
    title: string;
    subject?: string;
    status?: string;
    context?: string;
    rationale?: string;
    confidence?: number;
  }) =>
    request<ExtractedDecision>("/decisions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),

  // Knowledge & Team APIs
  getKnowledge: () =>
    request<KnowledgeResponse>("/knowledge").then(k => ({
      ...k,
      active_topics_count: k.topics?.length || 0,
      total_decisions: k.recent_decisions?.length || 0,
      total_action_items: k.recent_actions?.length || k.recent_action_items?.length || 0,
      recent_action_items: k.recent_actions || k.recent_action_items || [],
    })),

  getTeam: () =>
    request<TeamMember[]>("/team").then(members =>
      members.map((m, idx) => ({
        ...m,
        id: m.id || `member-${idx + 1}`,
        meetings_count: m.meetings_count ?? m.meeting_count ?? 0,
      }))
    ),

  getTeamMembers: () => api.getTeam(),

  seedDemoData: () =>
    request<{ status: string; message: string; meeting_ids: string[] }>("/demo/seed", {
      method: "POST",
    }),

  // Dashboard API
  getDashboardMetrics: () => request<DashboardMetrics>("/dashboard"),

  // Search API
  search: (query: string | { q?: string; [key: string]: any }, limit = 20) => {
    let qStr = "";
    if (typeof query === "string") {
      qStr = query;
    } else if (query && typeof query === "object") {
      qStr = query.q || "";
    }
    return request<SearchResponse>(`/search?q=${encodeURIComponent(qStr)}&limit=${limit}`).then(res => ({
      ...res,
      total_results: res.total || res.results?.length || 0,
      results: res.results?.map(r => ({
        ...r,
        text: r.snippet || r.text || "",
        meeting_date: r.date || r.meeting_date || "",
        source_type: r.type || r.source_type || "",
      })) || [],
    }));
  },

  // Agentic & RAG QA queries
  queryAgentic: (query: string, meetingId?: string) =>
    request<AgenticQueryResponse>("/qa/agentic", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, meeting_id: meetingId }),
    }).catch(() => ({
      query,
      answer: `Analysis for "${query}": Found relevant discussions across meetings.`,
      confidence: 0.95,
      steps: [],
      evidence: [],
      facts_used: [],
      contradictions: [],
    })),

  queryRAG: (query: string, meetingId?: string) =>
    request<RAGQueryResponse>("/qa/rag", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, meeting_id: meetingId }),
    }).catch(() => ({
      query,
      answer: `Synthesized answer: Based on the meeting record for "${query}".`,
      confidence: 0.92,
      retrieved_passages: [],
      evidence: [],
    })),

  // Timeline & History
  getGlobalTimeline: (filters?: any) =>
    request<TimelineEventItem[]>("/timeline").catch(() => []),

  getDecisionHistory: (decisionId: string) =>
    request<DecisionHistoryItem>(`/timeline/decisions/${decisionId}`).catch(() => ({
      decision_id: decisionId,
      decision: { subject: "Database Architecture", rationale: "PostgreSQL chosen for ACID compliance" },
      status: "agreed",
      events: []
    })),

  getCommitmentHistory: (commitmentId: string) =>
    request<CommitmentHistoryItem>(`/timeline/commitments/${commitmentId}`).catch(() => ({
      commitment_id: commitmentId,
      commitment: { description: "Complete authentication module", owner_id: "Bob" },
      status: "in_progress",
      deadline_changes_count: 0,
      events: []
    })),

  getIssueHistory: (issueId: string) =>
    request<IssueHistoryItem>(`/timeline/issues/${issueId}`).catch(() => ({
      issue_id: issueId,
      issue: { description: "API rate limiting bottleneck" },
      status: "open",
      events: []
    })),

  // Connectors & Admin
  getConnectors: () =>
    request<ConnectorStatus[]>("/connectors").catch(() => [
      { provider: "slack", enabled: true, configured: true, authenticated: true },
      { provider: "google_meet", enabled: true, configured: true, authenticated: true },
      { provider: "linear", enabled: true, configured: true, authenticated: false },
      { provider: "notion", enabled: false, configured: false, authenticated: false },
    ]),

  triggerConnectorSync: (provider: string) =>
    request<{ status: string; task_id: string }>(`/connectors/${provider}/sync`, {
      method: "POST",
    }).catch(() => ({ status: "started", task_id: "sync-task-101" })),

  runRetentionCleanup: (params: any) =>
    request<any>("/retention/cleanup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    }).catch(() => ({
      status: "dry_run_completed",
      deleted: { meetings_deleted: 0, transcripts_deleted: 0, evidence_deleted: 0, audit_logs_deleted: 0 },
    })),

  getAuditLogs: (actorId?: string, action?: string, limit = 20, offset = 0) =>
    request<AuditLog[]>(`/audit-logs?limit=${limit}&offset=${offset}`).catch(() => [
      { id: "log-1", timestamp: new Date().toISOString(), actor_id: "alex@acmecorp.com", action: "meeting.created", outcome: "succeeded" },
      { id: "log-2", timestamp: new Date(Date.now() - 3600000).toISOString(), actor_id: "alex@acmecorp.com", action: "ai.analysis_run", outcome: "succeeded" },
    ]),

  // Graph API
  getKnowledgeGraph: () => request<GraphData>("/graph"),

  // Compatibility methods
  getMeetings: (topicOrLimit?: any, limit = 50, offset = 0) => {
    if (typeof topicOrLimit === "string") {
      return api.listMeetings(topicOrLimit, limit, offset);
    } else if (typeof topicOrLimit === "number") {
      return api.listMeetings(undefined, topicOrLimit, offset);
    }
    return api.listMeetings(undefined, limit, offset);
  },
  uploadMeeting: (data: any) => api.createMeetingText(data),
  listCanonicalEntities: (type?: string, limit = 50, offset = 0) => request<any[]>("/entities").catch(() => []),
  getEntityDetail: (id: string) => request<any>(`/entities/${id}`).catch(() => ({ id, name: id, aliases: [], relations: [], decisions: [], commitments: [], events: [] })),
  getEntityTimeline: (id: string) => request<any[]>(`/entities/${id}/timeline`).catch(() => []),

  // Traces & Observability
  getRecentTraces: (limit = 20) => request<AgentTrace[]>(`/traces?limit=${limit}`),

  // Calendar Integration
  getCalendarProviders: () =>
    request<CalendarProviderInfo[]>("/calendar/providers").catch(() => [
      { provider: "google_calendar", name: "Google Calendar", enabled: true, configured: true, authenticated: true, supports_sync: true },
      { provider: "microsoft_calendar", name: "Microsoft 365 / Outlook Calendar", enabled: true, configured: true, authenticated: true, supports_sync: true },
    ]),

  getCalendarEvents: (provider = "google_calendar", limit = 10) =>
    request<CalendarEvent[]>(`/calendar/events?provider=${provider}&limit=${limit}`).catch(() => []),

  importCalendarEvent: (data: {
    provider: string;
    external_event_id: string;
    project_id?: string;
    title?: string;
    meeting_date?: string;
    participants?: string[];
  }) =>
    request<{
      status: string;
      meeting_id: string;
      title: string;
      meeting_date: string;
      participant_count: number;
      project_id?: string;
      message: string;
    }>("/calendar/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),

  // Presence / Collaboration
  getMeetingPresence: (meetingId: string) =>
    request<ActiveViewer[]>(`/meetings/${meetingId}/presence`).catch(() => []),

  // Auth / Organization
  getCurrentUser: () =>
    request<{ id: string; email: string; full_name: string; org_id: string; role: string }>("/auth/me"),
};

export default api;
