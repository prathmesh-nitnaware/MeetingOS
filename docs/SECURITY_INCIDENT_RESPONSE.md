# MeetingOS — Security Incident Response Runbook

## 1. Overview & Purpose

This document defines standard operating procedures (SOPs) for detecting, containing, investigating, mitigating, and recovering from security incidents within the MeetingOS multi-tenant SaaS platform.

---

## 2. Severity Classification

| Severity | Definition | Target Initial Response Time | Escalation |
| :--- | :--- | :--- | :--- |
| **SEV-1 (Critical)** | Active cross-tenant data leak, platform-wide secret exposure, total database compromise. | **< 15 Minutes** | Incident Commander, Lead Architect, Legal/Compliance, Executive Team. |
| **SEV-2 (High)** | Compromised tenant administrator account, single tenant data leakage, active token replay attacks. | **< 30 Minutes** | Security Lead, On-Call Engineer, Tenant Owner. |
| **SEV-3 (Medium)** | Compromised standard user credential, brute-force attempt blocked by rate limit, localized API anomaly. | **< 2 Hours** | On-Call Engineer. |
| **SEV-4 (Low)** | Minor misconfiguration detected in non-production, transient logging anomaly. | **< 24 Hours** | Security Team. |

---

## 3. Incident Scenarios & Standard Operating Procedures

### Scenario 1: Suspected Cross-Tenant Data Leak
* **Trigger**: Alert or report indicating Org A user observed records, transcripts, or audio belonging to Org B.
* **Containment**:
  1. Immediately verify the request parameters and JWT claims in the audit logs (`/api/v1/audit`).
  2. If an active exploit is detected, place affected API endpoints in read-only maintenance mode or revoke active session tokens for the affected tenant(s).
  3. Isolate the affected database tenant partitions or temporarily disable the suspect query endpoint.
* **Investigation**:
  1. Inspect application access logs filtering by `request_id`, `org_id`, and `user_id`.
  2. Identify the exact SQL query, vector search parameters, or storage path involved.
  3. Determine whether the breach occurred due to missing `org_id` WHERE clause, improper join, or storage path traversal.
* **Remediation & Recovery**:
  1. Deploy hotfix with targeted regression tests verifying tenant filtering.
  2. Invalidate compromised session tokens and force re-authentication.
* **Notification**:
  1. Notify the affected tenant owner(s) with an accurate timeline, scope of compromised assets, and remediations applied.

---

### Scenario 2: Compromised User Account
* **Trigger**: Suspicious login from unexpected geolocation/IP, multiple simultaneous active sessions with conflicting user-agent strings.
* **Containment**:
  1. Update `users.is_active = False` or revoke memberships in `organization_memberships`.
  2. Rotate user JWT signing key or invalidate user tokens by timestamp.
* **Investigation**:
  1. Query `audit_logs` where `actor_id = {user_id}` for the last 30 days.
  2. Identify any unauthorized meetings created, exported, or deleted.
* **Recovery**:
  1. Issue a secure password reset link to the verified email address.
  2. Re-enable account upon user identity verification.

---

### Scenario 3: Compromised API Credential / Service Token
* **Trigger**: Static API key or service token discovered in public repository, client bundle, or unauthorized log output.
* **Containment**:
  1. Revoke the API token immediately in the database / environment secrets manager.
  2. Reject all incoming requests bearing the compromised token.
* **Investigation**:
  1. Trace all requests authenticated with the compromised key during the active exposure window.
  2. Determine whether cross-tenant or administrative endpoints were invoked.
* **Recovery**:
  1. Generate and issue a new cryptographically random secret (`secrets.token_urlsafe(32)`).
  2. Update environment configurations in the secret store and restart affected services.

---

### Scenario 4: Compromised OAuth Token / Third-Party Connector
* **Trigger**: Suspicious webhook notifications, token refresh failure alerts from Google Meet / Zoom / Microsoft Teams.
* **Containment**:
  1. Invoke the provider's token revocation endpoint (`POST /oauth2/revoke`).
  2. Mark connector row in `connectors` table as `status = 'disconnected'`.
* **Investigation**:
  1. Audit meeting synchronization logs for unexpected meetings imported or altered.
* **Recovery**:
  1. Require the organization administrator to re-authorize the integration via standard OAuth 2.0 PKCE flow.

---

### Scenario 5: Malicious or Rogue Organization Administrator
* **Trigger**: Admin maliciously attempting bulk deletion of company records or unauthorized member expulsions.
* **Containment**:
  1. Organization Owner downgrades the rogue administrator's role to `viewer` or sets status to `suspended`.
  2. If the rogue actor is the sole Owner, executive escrow intervention is required to freeze the tenant workspace.
* **Investigation**:
  1. Review full audit trail (`GET /api/v1/audit`) for all admin actions within the organization.
* **Recovery**:
  1. Restore soft-deleted meetings via `MeetingRepository.restore_meeting` or database point-in-time recovery.

---

### Scenario 6: Accidental Data Deletion
* **Trigger**: User or automated script mistakenly issues mass deletion requests.
* **Containment & Recovery**:
  1. Because MeetingOS uses **soft deletion** (`deleted_at` timestamp), records remain physically intact in the database.
  2. Execute restorative SQL update:
     ```sql
     UPDATE meetings SET deleted_at = NULL, deleted_by = NULL WHERE org_id = :org_id AND id IN (:meeting_ids);
     ```
  3. If physical hard-deletion was executed, restore from the latest snapshot using `scripts/backup_restore.py restore`.

---

### Scenario 7: Database Corruption / Storage Failure
* **Trigger**: Unhandled SQLite / PostgreSQL I/O errors, storage device read errors, database integrity check failures.
* **Containment**:
  1. Direct API traffic to standby / maintenance page.
* **Recovery**:
  1. Locate the latest validated daily backup tarball in `backups/`.
  2. Run `python scripts/backup_restore.py verify --archive {tarball}`.
  3. Execute `python scripts/backup_restore.py restore --archive {tarball} --restore-db {target_db} --restore-storage {target_storage}`.
  4. Run automated test suite `uv run pytest` to verify database health and API responsiveness.
  5. Restore live traffic.

---

### Scenario 8: Backup Compromise / Ransomware Attempt
* **Trigger**: Backup repository contains unauthorized modifications or failed cryptographic hash checks.
* **Containment**:
  1. Cut off write access to the backup storage bucket.
  2. Switch to immutable WORM (Write Once, Read Many) secondary backup archive (Object Lock).
* **Investigation**:
  1. Verify cryptographic SHA-256 hashes of all stored snapshots against off-site recorded manifests.
* **Recovery**:
  1. Re-seed clean database from verified immutable snapshot.
  2. Rotate all storage access keys and database credentials.

---

## 4. Post-Incident Review & Continuous Improvement

Within 48 hours of any SEV-1 or SEV-2 incident closure:
1. Conduct a blameless post-mortem meeting with engineering and security stakeholders.
2. Produce a Root Cause Analysis (RCA) document including:
   - Root cause and contributing factors.
   - Exact timeline of detection, response, containment, and resolution.
   - Action items with assigned owners and hard deadlines (e.g., adding automated regression tests, updating firewall rules, improving audit alerting).
