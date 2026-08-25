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
}

export interface MeetingSummary {
  meeting_id: string;
  title: string;
  meeting_date: string;
  duration_seconds?: number;
  source_type: string;
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
  processing_status: string;
  participants: Participant[];
  speakers_count: number;
  segments_count: number;
  metadata: MeetingMetadata;
  created_at: string;
  updated_at: string;
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
  subject: string;
  status: string;
  rationale?: string;
  meeting_id: string;
  evidence_segment_id?: string;
  created_at?: string;
}

export interface ExtractedCommitment {
  commitment_id: string;
  description: string;
  owner_id: string;
  status: string;
  original_deadline?: string;
  current_deadline?: string;
  meeting_id: string;
  evidence_segment_id?: string;
}

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

export interface TimelineEventItem {
  event_id: string;
  event_type: string;
  occurred_at: string;
  meeting_id: string;
  meeting_title?: string;
  subject_entity_id?: string;
  payload?: Record<string, any>;
  evidence_segment_id?: string;
}

export interface DecisionHistoryItem {
  decision: ExtractedDecision;
  status: string;
  meeting_id: string;
  meeting_title: string;
  meeting_date: string;
  events: TimelineEventItem[];
}

export interface CommitmentHistoryItem {
  commitment: ExtractedCommitment;
  status: string;
  original_deadline?: string;
  current_deadline?: string;
  deadline_changes_count: number;
  events: TimelineEventItem[];
}

export interface IssueHistoryItem {
  issue: ExtractedIssue;
  status: string;
  first_detected_at: string;
  last_mentioned_at: string;
  meetings_count: number;
  is_recurring: boolean;
  is_resolved: boolean;
  events: TimelineEventItem[];
}

export interface GraphNode {
  id: string;
  name: string;
  type: string;
  presence_count: number;
}

export interface EntityDetailResponse {
  entity: ExtractedEntity;
  meeting_ids: string[];
  meetings_count: number;
  related_entities: GraphNode[];
  relationships: ExtractedRelation[];
}

export interface EntityTimelineResponse {
  entity_id: string;
  events: TimelineEventItem[];
  decisions: ExtractedDecision[];
  commitments: ExtractedCommitment[];
  issues: ExtractedIssue[];
}

export interface SubgraphResponse {
  nodes: GraphNode[];
  edges: {
    id: string;
    source: string;
    target: string;
    type: string;
  }[];
}

export interface SearchCandidate {
  id: string;
  meeting_id: string;
  meeting_title: string;
  meeting_date: string;
  segment_id?: string;
  start_time?: number;
  end_time?: number;
  text: string;
  source_type: string;
  score: number;
  evidence?: EvidenceItem;
}

export interface SearchResponse {
  query: string;
  total_results: number;
  results: SearchCandidate[];
}

export interface QueryPlan {
  person?: string;
  topic?: string;
  time_range?: string;
  type?: string;
  entities: string[];
  intent: string;
}

export interface EvidenceItem {
  meeting_id: string;
  segment_id: string;
  start_time: number;
  end_time: number;
  text_snapshot: string;
  source_type: string;
}

export interface QueryResponse {
  question: string;
  answer: string;
  evidence: EvidenceItem[];
  query_plan: QueryPlan;
  confidence: number;
  reasoning_path: string[];
}

export interface AgentTraceItem {
  agent: string;
  status: string;
  evidence_count?: number;
  events_count?: number;
  relations_count?: number;
  duration_seconds?: number;
  error?: string;
}

export interface AgenticQueryResponse {
  answer: string;
  confidence: number;
  evidence: EvidenceItem[];
  citations: string[];
  reasoning_summary: string;
  trace: AgentTraceItem[];
  insufficient_evidence: boolean;
}

export interface TemporalReconciliationResult {
  meeting_id: string;
  decision_changes_detected: number;
  deadline_changes_detected: number;
  recurring_issues_detected: number;
  events_created: number;
}

const API_BASE = "/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const token = localStorage.getItem("meetingos_token");
  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const response = await fetch(url, {
    ...options,
    headers,
  });
  if (!response.ok) {
    let errorDetail = "API Request failed";
    try {
      const errBody = await response.json();
      errorDetail = errBody.error?.message || errBody.detail || response.statusText;
    } catch {
      errorDetail = response.statusText;
    }
    throw new Error(errorDetail);
  }
  return response.json() as Promise<T>;
}

export interface ConnectorStatus {
  provider: string;
  enabled: boolean;
  configured: boolean;
  authenticated: boolean;
  last_sync_at: string | null;
  last_error: string | null;
}

export interface AuditLog {
  id: string;
  timestamp: string;
  actor_id: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  outcome: string;
  metadata: any | null;
}

export const api = {
  // Meetings API
  getMeetings: (limit = 50, offset = 0) =>
    request<MeetingSummary[]>(`/meetings?limit=${limit}&offset=${offset}`),

  getMeetingDetail: (meetingId: string) =>
    request<MeetingDetailResponse>(`/meetings/${meetingId}`),

  getMeetingTranscript: (meetingId: string) =>
    request<TranscriptResponse>(`/meetings/${meetingId}/transcript`),

  getMeetingEntities: (meetingId: string) =>
    request<ExtractedEntity[]>(`/meetings/${meetingId}/entities`),

  getMeetingTopics: (meetingId: string) =>
    request<string[]>(`/meetings/${meetingId}/topics`),

  getMeetingDecisions: (meetingId: string) =>
    request<ExtractedDecision[]>(`/meetings/${meetingId}/decisions`),

  getMeetingActions: (meetingId: string) =>
    request<ExtractedCommitment[]>(`/meetings/${meetingId}/actions`),

  getMeetingIssues: (meetingId: string) =>
    request<ExtractedIssue[]>(`/meetings/${meetingId}/issues`),

  getMeetingTimeline: (meetingId: string) =>
    request<ExtractedEvent[]>(`/meetings/${meetingId}/timeline`),

  getMeetingRelations: (meetingId: string) =>
    request<ExtractedRelation[]>(`/meetings/${meetingId}/relations`),

  uploadMeeting: (formData: FormData) =>
    request<{ meeting_id: string; job_id: string; processing_status: string; title: string }>(
      "/meetings",
      {
        method: "POST",
        body: formData,
      }
    ),

  triggerNLPExtraction: (meetingId: string) =>
    request<{ meeting_id: string; entities_count: number; decisions_count: number }>(
      `/meetings/${meetingId}/extract`,
      { method: "POST" }
    ),

  // Dashboard API
  getDashboardMetrics: () => request<DashboardMetrics>("/dashboard"),

  // Temporal API
  getGlobalTimeline: (filters?: {
    entity_id?: string;
    event_type?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
    offset?: number;
  }) => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, val]) => {
        if (val !== undefined && val !== null) params.append(key, String(val));
      });
    }
    return request<TimelineEventItem[]>(`/timeline?${params.toString()}`);
  },

  reconcileLifecycle: (meetingId: string) =>
    request<TemporalReconciliationResult>("/temporal/reconcile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ meeting_id: meetingId }),
    }),

  getDecisionHistory: (decisionId: string) =>
    request<DecisionHistoryItem>(`/decisions/${decisionId}/history`),

  getCommitmentHistory: (commitmentId: string) =>
    request<CommitmentHistoryItem>(`/commitments/${commitmentId}/history`),

  getIssueHistory: (issueId: string) =>
    request<IssueHistoryItem>(`/issues/${issueId}/history`),

  // Entities API
  listCanonicalEntities: (entityType?: string, limit = 50, offset = 0) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (entityType) params.append("entity_type", entityType);
    return request<GraphNode[]>(`/entities?${params.toString()}`);
  },

  getEntityDetail: (entityId: string) =>
    request<EntityDetailResponse>(`/entities/${entityId}`),

  getEntityTimeline: (entityId: string) =>
    request<EntityTimelineResponse>(`/entities/${entityId}/timeline`),

  // Graph API
  getSubgraph: (params?: { entity?: string; depth?: number; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.entity) query.append("entity", params.entity);
    if (params?.depth) query.append("depth", String(params.depth));
    if (params?.limit) query.append("limit", String(params.limit));
    return request<SubgraphResponse>(`/graph/subgraph?${query.toString()}`);
  },

  // Search API
  search: (filters: {
    q?: string;
    meeting_id?: string;
    person?: string;
    topic?: string;
    start_date?: string;
    end_date?: string;
    type?: string;
    limit?: number;
    offset?: number;
  }) => {
    const query = new URLSearchParams();
    Object.entries(filters).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== "") query.append(key, String(val));
    });
    return request<SearchResponse>(`/search?${query.toString()}`);
  },

  // Query/RAG API
  queryRAG: (question: string, planOverride?: QueryPlan, maxEvidence = 10) =>
    request<QueryResponse>("/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        query_plan_override: planOverride,
        max_evidence_items: maxEvidence,
      }),
    }),

  queryAgentic: (question: string) =>
    request<AgenticQueryResponse>("/query/agentic", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    }),

  // Connectors API
  getConnectors: () => request<ConnectorStatus[]>("/connectors"),
  getConnector: (provider: string) => request<ConnectorStatus>(`/connectors/${provider}`),
  triggerConnectorSync: (provider: string) =>
    request<{ status: string; task_id: string }>(`/connectors/${provider}/sync`, {
      method: "POST",
    }),
  listConnectorMeetings: (provider: string) => request<any[]>(`/connectors/${provider}/meetings`),

  // Audit Logs API
  getAuditLogs: (actorId?: string, action?: string, limit = 50, offset = 0) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (actorId) params.append("actor_id", actorId);
    if (action) params.append("action", action);
    return request<AuditLog[]>(`/audit?${params.toString()}`);
  },

  // Admin / Retention Cleanup
  runRetentionCleanup: (params: {
    meeting_days?: number;
    transcript_days?: number;
    evidence_days?: number;
    audit_log_days?: number;
    dry_run?: boolean;
  }) => {
    const query = new URLSearchParams();
    if (params.meeting_days !== undefined) query.append("meeting_days", String(params.meeting_days));
    if (params.transcript_days !== undefined) query.append("transcript_days", String(params.transcript_days));
    if (params.evidence_days !== undefined) query.append("evidence_days", String(params.evidence_days));
    if (params.audit_log_days !== undefined) query.append("audit_log_days", String(params.audit_log_days));
    if (params.dry_run !== undefined) query.append("dry_run", String(params.dry_run));
    return request<{ status: string; dry_run: boolean; deleted: Record<string, number> }>(
      `/admin/retention/cleanup?${query.toString()}`,
      { method: "POST" }
    );
  },
};
