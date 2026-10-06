// ---------------------------------------------------------------------------
// Types — these mirror the FastAPI response models field-for-field.
// ---------------------------------------------------------------------------

export interface Participant {
  id?: string
  canonical_name: string
  aliases?: string[]
}

export interface SpeakerInfo {
  speaker_id: string
  name?: string | null
  canonical_entity_id?: string | null
}

export interface TranscriptSegment {
  segment_id: string
  sequence: number
  speaker_id: string
  start_time: number
  end_time: number
  text: string
}

export interface MeetingMetadata {
  source_filename?: string
  file_size_bytes?: number
}

export type ProcessingStatus = "queued" | "running" | "succeeded" | "failed"

export interface MeetingSummary {
  meeting_id: string
  title: string
  meeting_date: string
  duration_seconds?: number | null
  source_type: string
  processing_status: ProcessingStatus
  participant_count: number
  speaker_count: number
  segment_count: number
  created_at: string
}

export interface MeetingDetailResponse {
  meeting_id: string
  title: string
  meeting_date: string
  duration_seconds?: number | null
  source_type: string
  processing_status: ProcessingStatus
  participants: Participant[]
  speakers: SpeakerInfo[]
  speakers_count: number
  segments_count: number
  metadata: MeetingMetadata
  created_at: string
  updated_at: string
  latest_job_id?: string | null
  latest_job_error?: string | null
}

export interface TranscriptResponse {
  meeting_id: string
  segments_count: number
  segments: TranscriptSegment[]
}

export interface ExtractedEntity {
  entity_id: string
  name: string
  entity_type: string
  confidence?: number
  segment_id?: string | null
  aliases?: string[]
}

export interface ExtractedDecision {
  decision_id: string
  subject: string
  status: string
  rationale?: string | null
  meeting_id: string
  evidence_segment_id?: string | null
  created_at?: string
}

export interface ExtractedCommitment {
  commitment_id: string
  description: string
  owner_id?: string | null
  status: string
  original_deadline?: string | null
  current_deadline?: string | null
  meeting_id: string
  evidence_segment_id?: string | null
}

export interface ExtractedIssue {
  issue_id: string
  description: string
  owner_id?: string | null
  status: string
  first_detected_at: string
  last_mentioned_at?: string | null
  resolution_meeting_id?: string | null
  evidence_segment_id?: string | null
}

export type EventPayload = Record<string, unknown>

export interface ExtractedEvent {
  event_id: string
  event_type: string
  occurred_at: string
  meeting_id: string
  subject_entity_id?: string | null
  payload?: EventPayload | null
  evidence_segment_id?: string | null
}

export interface ExtractedRelation {
  relation_id: string
  source_entity_id: string
  target_entity_id: string
  relationship_type: string
  meeting_id: string
  segment_id?: string | null
  confidence?: number
}

export interface DashboardMetrics {
  meetings_ingested: number
  decisions_tracked: number
  open_actions: number
  overdue_actions: number
  unresolved_issues: number
  recurring_issues: number
  canonical_entities_tracked: number
  relationships_tracked: number
}

export interface TimelineEventItem {
  event_id: string
  event_type: string
  occurred_at: string
  meeting_id: string
  meeting_title?: string | null
  subject_entity_id?: string | null
  payload?: EventPayload | null
  evidence_segment_id?: string | null
}

export interface DecisionHistoryItem {
  decision: ExtractedDecision
  status: string
  meeting_id: string
  meeting_title: string
  meeting_date: string
  events: TimelineEventItem[]
}

export interface CommitmentHistoryItem {
  commitment: ExtractedCommitment
  status: string
  original_deadline?: string | null
  current_deadline?: string | null
  deadline_changes_count: number
  events: TimelineEventItem[]
}

export interface IssueHistoryItem {
  issue: ExtractedIssue
  status: string
  first_detected_at: string
  last_mentioned_at: string
  meetings_count: number
  is_recurring: boolean
  is_resolved: boolean
  events: TimelineEventItem[]
}

/** Canonical entity as returned by GET /entities (backend GraphNode). */
export interface GraphNode {
  id: string
  name: string
  entity_type: string
  meeting_count: number
  meetings: string[]
}

export interface EntityDetailResponse {
  entity: ExtractedEntity
  meeting_ids: string[]
  meetings_count: number
  related_entities: GraphNode[]
  relationships: ExtractedRelation[]
}

export interface EntityTimelineResponse {
  entity_id: string
  events: TimelineEventItem[]
  decisions: ExtractedDecision[]
  commitments: ExtractedCommitment[]
  issues: ExtractedIssue[]
}

export interface EvidenceItem {
  meeting_id: string
  segment_id: string
  start_time: number
  end_time: number
  text_snapshot: string
  source_type: string
}

export interface SearchCandidate {
  id: string
  meeting_id: string
  meeting_title: string
  meeting_date: string
  segment_id?: string | null
  start_time?: number | null
  end_time?: number | null
  text: string
  source_type: string
  score: number
  evidence?: EvidenceItem | null
}

export interface SearchResponse {
  query: string
  total_results: number
  results: SearchCandidate[]
}

export interface QueryPlan {
  person?: string | null
  topic?: string | null
  time_range?: string | null
  type?: string | null
  entities: string[]
  intent: string
}

export interface QueryResponse {
  question: string
  answer: string
  evidence: EvidenceItem[]
  query_plan: QueryPlan
  confidence: number
  reasoning_path: string[]
  model_name?: string
}

export interface AgentEvidence {
  meeting_id: string
  meeting_title?: string | null
  meeting_date?: string | null
  segment_id: string
  start_time: number
  end_time: number
  source_type: string
  content: string
  relevance_score?: number
  lifecycle_state?: string
}

export interface AgentTraceItem {
  agent: string
  status: string
  evidence_count?: number | null
  events_count?: number | null
  relations_count?: number | null
  duration_seconds?: number | null
  latency_ms?: number | null
  model_name?: string | null
  output_summary?: string | null
  error?: string | null
}

export interface ConflictItem {
  conflict_type: string
  earlier_meeting_id: string
  later_meeting_id: string
  earlier_claim: string
  latest_claim: string
}

export interface AgenticQueryResponse {
  answer: string
  confidence: number
  evidence: AgentEvidence[]
  citations: string[]
  reasoning_summary: string
  trace: AgentTraceItem[]
  insufficient_evidence: boolean
  trace_id?: string
  conflicts?: ConflictItem[]
}

export interface ExecutionTrace {
  trace_id: string
  query_id: string
  query: string
  answer: string
  confidence: number
  insufficient_evidence: boolean
  total_latency_ms: number
  steps: AgentTraceItem[]
  citations: string[]
  conflicts: ConflictItem[]
  created_at: string
}

export interface UsageSummary {
  total_requests: number
  total_prompt_tokens: number
  total_completion_tokens: number
  total_tokens: number
  total_cost_usd: number
  avg_latency_ms: number
  p50_latency_ms: number
  p95_latency_ms: number
  p99_latency_ms: number
  avg_tokens_per_query: number
  fallback_count: number
  fallback_rate: number
  error_count: number
}

export interface ProviderCapability {
  name: string
  display_name: string
  default_model: string
  supports_reasoning: boolean
  supports_embeddings: boolean
  is_configured: boolean
  description: string
}

export interface ProviderStatus {
  embedding_provider: string
  embedding_model: string
  embedding_configured: boolean
  reasoner_provider: string
  reasoner_model: string
  reasoner_configured: boolean
  has_fallback: boolean
  environment: string
  hardware_device: string
  asr_provider: string
  asr_model: string
  asr_ready: boolean
  diarizer_provider: string
  capabilities: ProviderCapability[]
}

export interface TemporalReconciliationResult {
  meeting_id: string
  decision_changes_detected: number
  deadline_changes_detected: number
  recurring_issues_detected: number
  events_created: number
}

export interface ConnectorStatus {
  provider: string
  enabled: boolean
  configured: boolean
  authenticated: boolean
  demo_mode?: boolean
  last_sync_at: string | null
  last_error: string | null
}

export interface AuditLog {
  id: string
  timestamp: string
  actor_id: string
  action: string
  resource_type: string
  resource_id: string | null
  outcome: string
  metadata: Record<string, unknown> | null
}

export interface JobStatus {
  job_id: string
  meeting_id?: string | null
  status: ProcessingStatus
  stage: string
  progress: number
  error_message?: string | null
  created_at: string
  updated_at: string
}

export interface OrganizationRef {
  id: string
  name: string
  slug?: string
  role: string
}

export interface UserProfile {
  user_id: string
  email?: string | null
  full_name?: string | null
  role: string
  org_id: string
  organization_name?: string | null
  organization_slug?: string | null
  permissions: string[]
  organizations: OrganizationRef[]
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in_seconds: number
  user: { user_id: string; role: string; org_id: string; email?: string; full_name?: string }
  available_organizations: OrganizationRef[]
}

export interface DevPersona {
  token: string
  label: string
  org_id: string
  role: string
}

export interface AuthConfig {
  dev_auth_enabled: boolean
  dev_personas: DevPersona[]
}

export interface HealthInfo {
  status: string
  app_name: string
  version: string
  environment: string
  dependencies: { database: boolean; redis: boolean }
}

export interface RetentionResult {
  status: string
  dry_run: boolean
  org_id?: string
  deleted: Record<string, number>
}

// ---------------------------------------------------------------------------
// Session token handling
// ---------------------------------------------------------------------------

const TOKEN_KEY = "meetingos_token"
export const SESSION_EXPIRED_EVENT = "meetingos:session-expired"

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* storage unavailable (private mode) */
  }
}

// ---------------------------------------------------------------------------
// HTTP helper
// ---------------------------------------------------------------------------

const API_BASE = "/api/v1"

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

type ValidationIssue = { loc?: (string | number)[]; msg?: string }

/** Turns FastAPI error bodies (string detail, validation list, or object) into readable text. */
export function describeErrorBody(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object") return fallback
  const detail = (body as { detail?: unknown }).detail
  if (typeof detail === "string") return detail
  if (Array.isArray(detail)) {
    const parts = (detail as ValidationIssue[]).map((issue) => {
      const field = issue.loc?.filter((p) => p !== "body" && p !== "query" && p !== "path").join(".")
      const msg = (issue.msg || "is invalid").replace(/^Value error, /, "")
      return field ? `${humanField(String(field))}: ${msg}` : msg
    })
    return parts.join("; ") || fallback
  }
  if (detail && typeof detail === "object") {
    const d = detail as Record<string, unknown>
    if (typeof d.message === "string") return d.message
    return JSON.stringify(detail)
  }
  const error = (body as { error?: { message?: string } }).error
  return error?.message || fallback
}

function humanField(field: string): string {
  const name = field.replace(/_/g, " ")
  return name.charAt(0).toUpperCase() + name.slice(1)
}

const AUTH_ENDPOINTS = ["/auth/login", "/auth/register-org", "/auth/invitations/accept", "/auth/config"]

async function send(path: string, options: RequestInit = {}): Promise<Response> {
  const token = getToken()
  const headers: Record<string, string> = { ...(options.headers as Record<string, string>) }
  if (token) headers["Authorization"] = `Bearer ${token}`

  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  } catch {
    throw new ApiError(0, "Cannot reach the MeetingOS API. Check that the backend is running.")
  }

  if (!response.ok) {
    let message = response.statusText || `Request failed (${response.status})`
    try {
      message = describeErrorBody(await response.json(), message)
    } catch {
      /* non-JSON error body */
    }
    if (response.status === 401 && token && !AUTH_ENDPOINTS.some((p) => path.startsWith(p))) {
      setToken(null)
      window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT, { detail: message }))
    }
    throw new ApiError(response.status, message)
  }
  return response
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await send(path, options)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

const json = (body: unknown, method = "POST"): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
})

const qs = (params: Record<string, string | number | boolean | undefined | null>): string => {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== "") search.append(key, String(val))
  })
  const s = search.toString()
  return s ? `?${s}` : ""
}

// ---------------------------------------------------------------------------
// API surface
// ---------------------------------------------------------------------------

export const api = {
  // Health & auth
  getHealth: () => request<HealthInfo>("/health"),
  getAuthConfig: () => request<AuthConfig>("/auth/config"),
  getProfile: () => request<UserProfile>("/auth/me"),
  login: (email: string, password: string, org_slug?: string) =>
    request<LoginResponse>("/auth/login", json({ email, password, org_slug })),
  registerOrg: (data: {
    org_name: string
    org_slug: string
    admin_name: string
    admin_email: string
    admin_password: string
  }) => request<LoginResponse>("/auth/register-org", json(data)),
  acceptInvitation: (data: { token: string; full_name?: string; password?: string }) =>
    request<LoginResponse>("/auth/invitations/accept", json(data)),
  switchOrg: (target_org_id: string) =>
    request<LoginResponse>("/auth/switch-org", json({ target_org_id })),

  // Meetings
  getMeetingsPage: async (limit = 50, offset = 0) => {
    const response = await send(`/meetings${qs({ limit, offset })}`)
    const items = (await response.json()) as MeetingSummary[]
    const total = Number(response.headers.get("X-Total-Count") ?? items.length)
    return { items, total: Number.isNaN(total) ? items.length : total }
  },
  getMeetings: async (limit = 50, offset = 0) => (await api.getMeetingsPage(limit, offset)).items,
  getMeetingDetail: (meetingId: string) =>
    request<MeetingDetailResponse>(`/meetings/${encodeURIComponent(meetingId)}`),
  getMeetingTranscript: (meetingId: string) =>
    request<TranscriptResponse>(`/meetings/${encodeURIComponent(meetingId)}/transcript`),
  getMeetingEntities: (meetingId: string) =>
    request<ExtractedEntity[]>(`/meetings/${encodeURIComponent(meetingId)}/entities`),
  getMeetingTopics: (meetingId: string) =>
    request<string[]>(`/meetings/${encodeURIComponent(meetingId)}/topics`),
  getMeetingDecisions: (meetingId: string) =>
    request<ExtractedDecision[]>(`/meetings/${encodeURIComponent(meetingId)}/decisions`),
  getMeetingActions: (meetingId: string) =>
    request<ExtractedCommitment[]>(`/meetings/${encodeURIComponent(meetingId)}/actions`),
  getMeetingIssues: (meetingId: string) =>
    request<ExtractedIssue[]>(`/meetings/${encodeURIComponent(meetingId)}/issues`),
  getMeetingTimeline: (meetingId: string) =>
    request<ExtractedEvent[]>(`/meetings/${encodeURIComponent(meetingId)}/timeline`),
  getMeetingRelations: (meetingId: string) =>
    request<ExtractedRelation[]>(`/meetings/${encodeURIComponent(meetingId)}/relations`),
  uploadMeeting: (formData: FormData) =>
    request<{ meeting_id: string; job_id: string; processing_status: ProcessingStatus; title: string; message: string }>(
      "/meetings",
      { method: "POST", body: formData }
    ),
  deleteMeeting: (meetingId: string, hardDelete = false) =>
    request<{ status: string }>(
      `/meetings/${encodeURIComponent(meetingId)}${qs({ hard_delete: hardDelete || undefined })}`,
      { method: "DELETE" }
    ),
  triggerNLPExtraction: (meetingId: string) =>
    request<{ meeting_id: string; entities_count: number; decisions_count: number }>(
      `/meetings/${encodeURIComponent(meetingId)}/extract`,
      { method: "POST" }
    ),
  getJob: (jobId: string) => request<JobStatus>(`/jobs/${encodeURIComponent(jobId)}`),

  // Dashboard
  getDashboardMetrics: () => request<DashboardMetrics>("/dashboard"),

  // Temporal
  getGlobalTimeline: (filters: {
    entity_id?: string
    event_type?: string
    start_date?: string
    end_date?: string
    limit?: number
    offset?: number
  } = {}) => request<TimelineEventItem[]>(`/timeline${qs(filters)}`),
  reconcileLifecycle: (meetingId: string) =>
    request<TemporalReconciliationResult>("/temporal/reconcile", json({ meeting_id: meetingId })),
  getDecisionHistory: (decisionId: string) =>
    request<DecisionHistoryItem>(`/decisions/${encodeURIComponent(decisionId)}/history`),
  getCommitmentHistory: (commitmentId: string) =>
    request<CommitmentHistoryItem>(`/commitments/${encodeURIComponent(commitmentId)}/history`),
  getIssueHistory: (issueId: string) =>
    request<IssueHistoryItem>(`/issues/${encodeURIComponent(issueId)}/history`),

  // Entities
  listCanonicalEntities: (entityType?: string, limit = 50, offset = 0) =>
    request<GraphNode[]>(`/entities${qs({ entity_type: entityType, limit, offset })}`),
  getEntityDetail: (entityId: string) =>
    request<EntityDetailResponse>(`/entities/${encodeURIComponent(entityId)}`),
  getEntityTimeline: (entityId: string) =>
    request<EntityTimelineResponse>(`/entities/${encodeURIComponent(entityId)}/timeline`),

  // Search & Q&A
  search: (filters: {
    q?: string
    meeting_id?: string
    person?: string
    topic?: string
    start_date?: string
    end_date?: string
    type?: string
    limit?: number
    offset?: number
  }) => request<SearchResponse>(`/search${qs(filters)}`),
  queryRAG: (question: string, planOverride?: QueryPlan, maxEvidence = 10) =>
    request<QueryResponse>(
      "/query",
      json({ question, query_plan_override: planOverride, max_evidence_items: maxEvidence })
    ),
  queryAgentic: (question: string) =>
    request<AgenticQueryResponse>("/query/agentic", json({ question })),

  // Observability
  getTraces: (limit = 30) => request<ExecutionTrace[]>(`/query/traces${qs({ limit })}`),
  getUsageMetrics: () => request<UsageSummary>("/admin/metrics/usage"),
  getProviderStatus: () => request<ProviderStatus>("/admin/providers/status"),

  // Connectors
  getConnectors: () => request<ConnectorStatus[]>("/connectors"),
  triggerConnectorSync: (provider: string) =>
    request<{ status: string; task_id: string }>(`/connectors/${encodeURIComponent(provider)}/sync`, {
      method: "POST",
    }),

  // Audit & retention
  getAuditLogs: (limit = 50, offset = 0) => request<AuditLog[]>(`/audit${qs({ limit, offset })}`),
  runRetentionCleanup: (params: {
    meeting_days?: number
    transcript_days?: number
    evidence_days?: number
    audio_days?: number
    audit_log_days?: number
    dry_run?: boolean
  }) => request<RetentionResult>(`/admin/retention/cleanup${qs(params)}`, { method: "POST" }),
}
