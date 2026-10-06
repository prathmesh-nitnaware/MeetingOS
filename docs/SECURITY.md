# MeetingOS Security Architecture & Threat Model

## 1. Executive Summary

MeetingOS employs a defense-in-depth security model engineered for multi-tenant enterprise software-as-a-service (SaaS) environments. Security controls are enforced at every architectural tier: edge routing, API gateway, application business logic, relational persistence, vector indices, and object storage.

---

## 2. Multi-Tenant Role-Based Access Control (RBAC)

MeetingOS enforces a 4-tier Role-Based Access Control model via FastAPI security dependencies (`apps/api/auth.py`).

| Role | Description | Core Permissions |
| :--- | :--- | :--- |
| **`owner`** | Primary tenant administrator with billing and organizational governance authority. | Full access including tenant deletion, member removal, retention policy configuration, role assignment. |
| **`admin`** | Operational administrator managing workspaces and integrations. | Member invitations, connector configurations, retention configuration, audit log viewing. |
| **`member`** | Standard organizational user with full analytical capabilities. | Meeting uploads, NLP extraction triggers, semantic search, AI agent queries, timeline analysis. |
| **`viewer`** | Read-only stakeholder with inspection access. | Read-only access to meeting transcripts, summaries, timelines, and organizational dashboards. |

### Fine-Grained Permission Matrix
MeetingOS maps 17 granular permission scopes:
- **Meetings**: `meetings.read`, `meetings.write`, `meetings.delete`
- **Analytics & AI**: `transcripts.read`, `search.execute`, `query.execute`, `nlp.extract`, `temporal.read`, `graph.read`
- **Integrations**: `connectors.read`, `connectors.write`
- **Governance & Admin**: `members.read`, `members.invite`, `members.remove`, `organization.read`, `organization.update`, `audit.read`

---

## 3. Cryptographic Standards & Password Security

### A. Password Hashing
- Passwords are encrypted using **PBKDF2-HMAC-SHA256** with a cryptographically secure 128-bit random salt (`secrets.token_hex(16)`) and **100,000 iterations**.
- Format: `pbkdf2_sha256${salt}${hash}`.
- Prevents rainbow table attacks, dictionary attacks, and pre-computation exploits.
- Legacy password hash fallback supported for non-destructive migration.

### B. JWT Token Lifecycle & Signing
- JWT tokens signed with **HMAC-SHA256 (HS256)** using a 256-bit cryptographically secure secret key configured via environment variable `MEETINGOS_JWT_SECRET`.
- Payload includes:
  - `sub`: Unique user ID.
  - `org_id`: Active tenant identifier.
  - `role`: User role within the active tenant.
  - `email`: Authenticated email address.
  - `exp`: Expiration timestamp (default: 24 hours).
- Switching organizations (`POST /api/v1/auth/switch-org`) requires verification of active tenant membership before minting a new tenant-scoped JWT.

### C. Invitation Token Security
- Invitation tokens generated using `secrets.token_hex(32)`.
- Only the **SHA-256 hash** of the token is persisted in `organization_invitations.token_hash`.
- Enforces single-use consumption (`accepted_at` timestamp check) and strict 7-day expiration (`expires_at > utc_now()`).

---

## 4. Threat Vector Mitigations & Defense-in-Depth

### A. Broken Object Level Authorization (BOLA / IDOR) Defense
- No endpoint relies solely on a client-provided `org_id` or resource UUID.
- All database queries filter on `WHERE org_id = :authenticated_user_org_id AND deleted_at IS NULL`.
- Inquiries targeting foreign tenant resources safely return `404 Not Found`, denying attackers confirmation of resource existence.

### B. Storage Isolation & Path Traversal Protection
- Storage structure: `storage/orgs/{org_id}/meetings/{meeting_id}/audio.wav`.
- File download handlers resolve canonical absolute paths (`Path.resolve()`) and enforce strict boundary checks (`target.relative_to(tenant_dir)`).
- Malicious traversal attempts (`../../etc/passwd`, `%2e%2e%2f`) are immediately caught and rejected with `403 Forbidden`.

### C. Vector & AI Retrieval Isolation
- `HybridSearchEngine` and `EmbeddingRepository` mandate tenant pre-filtering prior to vector similarity calculation (`WHERE org_id = :current_org`).
- Queries from Org A can never retrieve or compute similarity scores against Org B vector embeddings.

### D. Accidental Data Loss Protection & Soft Deletion
- Meeting deletions execute non-destructive soft deletes by setting `deleted_at` and `deleted_by`.
- Soft-deleted meetings are excluded from standard API responses and vector queries while remaining fully recoverable by organization Owners.

### E. Rate Limiting & Abuse Prevention
- Sliding-window rate limiter protects sensitive endpoints:
  - `/api/v1/auth/login`: 10 requests / minute per IP.
  - `/api/v1/auth/register-org`: 5 requests / hour per IP.
  - `/api/v1/meetings` (upload): 20 uploads / hour per tenant.
  - `/api/v1/query/*`: 100 queries / minute per tenant.

### F. Audit Logging & Credential Sanitization
- All security-sensitive actions (registration, invitation, role alteration, policy updates, deletions) record immutable audit entries in `audit_logs`.
- All logs and traces pass through automated secret scrubbing filters (`_sanitize_secrets`), ensuring passwords, JWTs, and API keys are never logged.
