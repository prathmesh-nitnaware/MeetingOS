# MeetingOS Security Architecture & Threat Model

This document outlines the security architecture, authentication model, threat vector mitigations, and compliance standards implemented in MeetingOS.

---

## 1. Authentication & Role-Based Access Control (RBAC)

MeetingOS enforces a 3-tier Role-Based Access Control (RBAC) model via FastAPI security dependencies (`apps/api/auth.py`).

| Role | Permissions | Access Scope |
| :--- | :--- | :--- |
| **`admin`** | Full access to all endpoints, configuration, provider settings, worker status, and raw metrics. | `/api/v1/admin/*`, `/api/v1/audit/*`, `/api/v1/connectors/*`, and all user APIs. |
| **`member`** | Ingest meetings, trigger NLP extractions, perform search, execute agentic reasoning queries, view traces. | `/api/v1/meetings/*`, `/api/v1/search`, `/api/v1/query/*`, `/api/v1/traces`. |
| **`viewer`** | Read-only access to organizational dashboard, meeting summaries, timelines, and entity graphs. | `/api/v1/dashboard`, `/api/v1/meetings` (GET only), `/api/v1/temporal/*`, `/api/v1/graph/*`. |

---

## 2. Threat Mitigations & Defense-in-Depth

### A. Path Traversal & Malicious File Uploads
- **Filename Sanitization:** `sanitize_filename` strips directory components (`..`, `/`, `\`), null bytes (`\x00`), and non-whitelisted characters.
- **Strict Extension Whitelist:** Only `.wav`, `.mp3`, `.m4a`, `.mp4`, `.srt`, `.txt` files are accepted. All executable or unknown extensions are rejected with HTTP 400.
- **Upload Size Limits:** Hard maximum limit (default 500 MB) enforced during streaming, with automatic disk cleanup on violation.

### B. Credential Leakage Prevention
- **Zero Credential Exposure:** Recursive secret sanitization (`sanitize_trace_data` and `_sanitize_secrets`) scrubs API keys, bearer tokens, passwords, and private tokens from execution traces, audit logs, and exception strings.
- **CORS Hardening:** Production environment strictly forbids wildcard `*` CORS origins; specific trusted frontend domains must be declared in `MEETINGOS_ALLOWED_ORIGINS`.

### C. Rate Limiting & Abuse Prevention
- **Sliding Window:** Redis sliding window limiter tracks per-IP and per-token request rates.
- **Route Quotas:** Configurable per-route rate limits (queries, uploads, agentic reasoning, admin operations) with automatic in-memory fallback if Redis is unavailable.

### D. Audit Logging & Traceability
- **Security Audit Trails:** Security-sensitive operations (connector sync, provider updates, role changes) are recorded in the `audit_logs` table with actor ID, timestamp, outcome, and metadata.
- **Correlation IDs:** Every HTTP request receives a unique `X-Request-ID` attached to response headers and structured access logs.
