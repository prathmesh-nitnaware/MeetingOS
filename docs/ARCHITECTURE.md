# MeetingOS Architecture — Production Multi-Tenant Platform

## 1. Architectural Principles

MeetingOS is a multi-tenant enterprise meeting intelligence and organizational memory platform built upon three core tenets:

1. **Strict Tenant Isolation by Default**: Zero cross-organization data leakage across relational storage, vector indices, knowledge graphs, and audio media.
2. **Deterministic Server-Side Authorization**: The authenticated identity's server-resolved `org_id` and RBAC permissions govern all data access—never client-supplied parameters.
3. **Traceable Evidence & Provenance**: Every extracted insight, decision, and entity is anchored to exact transcript timestamps and speaker attribution.

---

## 2. Multi-Tenant Architectural Model

```text
                     ┌─────────────────────────────────────────────────┐
                     │                 User Identity                   │
                     │  (Can hold active memberships in multiple orgs) │
                     └───────────────────────┬─────────────────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
          ┌─────────────────────────┐                 ┌─────────────────────────┐
          │  Organization Tenant A  │                 │  Organization Tenant B  │
          │     (org_acme_corp)     │                 │     (org_beta_labs)     │
          └────────────┬────────────┘                 └────────────┬────────────┘
                       │                                           │
         ┌─────────────┴─────────────┐               ┌─────────────┴─────────────┐
         │ • Relational DB (org_id)  │               │ • Relational DB (org_id)  │
         │ • Vector Memory (org_id)  │               │ • Vector Memory (org_id)  │
         │ • Storage: orgs/acme/...  │               │ • Storage: orgs/beta/...  │
         │ • Knowledge Graph         │               │ • Knowledge Graph         │
         │ • Retention Policies      │               │ • Retention Policies      │
         └───────────────────────────┘               └───────────────────────────┘
```

### A. Organizations & Memberships
- **`organizations`**: Master tenant entity defining workspace name, unique URL slug, status (`active`/`suspended`), and allowed email domains.
- **`users`**: Global user entity representing individuals who can authenticate via password or future SSO identity providers.
- **`organization_memberships`**: Associative join table assigning fine-grained roles (`owner`, `admin`, `member`, `viewer`) and status (`active`, `suspended`) per tenant.

### B. Tenant Context Resolution & RBAC
- **Token Resolution**: The client presents a signed HS256 JWT containing `sub` (user_id), `org_id`, and `role`.
- **Server-Side Enforcement**: `get_current_user` validates the JWT and resolves permissions. Routes declare explicit RBAC dependencies (`require_viewer`, `require_member`, `require_admin`, `require_owner`, `require_permission(...)`).
- **Organization Switching (`POST /api/v1/auth/switch-org`)**: Validates that the user holds an active membership in the target organization before minting a new tenant-scoped access token.

---

## 3. End-to-End Data Isolation Architecture

### 1. Relational Database Isolation
Every core table containing tenant data enforces an indexed `org_id` column:
- `meetings` (`org_id`, `deleted_at`, `deleted_by`)
- `audit_logs` (`org_id`, `actor_id`, `action`, `resource_id`)
- `retention_policies` (`org_id`, `meeting_retention_days`, `auto_delete_enabled`)
- `organization_memberships` (`org_id`, `user_id`, `role`, `status`)
- `organization_invitations` (`org_id`, `email`, `token_hash`, `expires_at`)

All repository methods in `MeetingRepository` require `org_id` and apply mandatory `WHERE org_id = :org_id AND deleted_at IS NULL` filters on all queries, updates, and soft deletes.

### 2. File & Audio Storage Isolation
Tenant media files are physically compartmentalized in the filesystem/object storage:
```text
storage/
  └── orgs/
       └── {org_id}/
            └── meetings/
                 └── {meeting_id}/
                      └── audio.wav
```
- **Path Traversal Defense**: All file access endpoints resolve canonical absolute paths and verify that target paths reside strictly within `storage/orgs/{org_id}/meetings/{meeting_id}/`, rejecting `../` and cross-tenant traversal attempts with `403 Forbidden`.

### 3. Vector & Semantic Search Isolation
- `HybridSearchEngine` and `EmbeddingRepository` execute tenant pre-filtering prior to vector similarity calculation.
- Query: `SELECT * FROM embeddings WHERE org_id = :current_org AND ... ORDER BY embedding <=> query_vector`.
- Cross-tenant semantic overlap is strictly prevented; queries from Org A can never retrieve or compute similarity scores against Org B vector embeddings.

### 4. Knowledge Graph & Temporal Reasoning Isolation
- `GraphService` models entity relationships (`DISCUSSED_WITH`, `DECIDED_IN`, `COMMITTED_TO`) strictly within the active `org_id`.
- `TemporalIntelligenceEngine` scopes meeting timeline reconciliation and state transitions (`PROPOSED` $\rightarrow$ `COMMITTED` $\rightarrow$ `COMPLETED`) exclusively within the tenant boundary.

### 5. Ingestion & Worker Isolation
- Celery worker tasks (`process_meeting_task`) and async pipelines (`run_ingestion_pipeline`) explicitly accept and propagate `org_id`.
- Background tasks operate strictly within the tenant context, preventing cross-tenant factual leakage during NLP entity extraction and temporal reconciliation.

---

## 4. Enterprise Extensibility Points

### A. Enterprise Single Sign-On (SSO / SAML 2.0 / OIDC)
The `UserModel` and `OrganizationMembershipModel` architecture provides a clean extension interface for enterprise identity federation:
```text
Identity Provider (Google Workspace / Azure AD / Okta)
           │ (SAML Assertion / OIDC ID Token)
           ▼
    Verified Email
           │
           ▼
Organization Domain Match or Pre-Configured SSO Mapping
           │
           ▼
Active OrganizationMembership Assignment
```

### B. Customer-Managed Encryption Keys (CMEK)
The compartmentalized `orgs/{org_id}/` storage structure provides seamless extension for tenant-specific encryption keys:
- **AWS KMS**: `arn:aws:kms:region:acct:key/{org_kms_key_id}`
- **GCP Cloud KMS**: `projects/{project}/locations/{region}/keyRings/{ring}/cryptoKeys/{org_key}`
- **Azure Key Vault**: `https://{vault}.vault.azure.net/keys/{org_key}`

### C. Bring Your Own Key (BYOK) for AI Providers
Organization settings can securely hold encrypted API keys for OpenAI / Anthropic / Azure OpenAI, allowing enterprise customers to route LLM requests through their dedicated enterprise billing and data processing agreements.
