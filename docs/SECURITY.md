# MeetingOS Security and Privacy Requirements

Meeting data can contain confidential organizational information. Security is part of the architecture, not a future decorative sticker.

## 1. Data principles

- Minimize collected data.
- Preserve provenance.
- Restrict access by organization/user where multi-user support exists.
- Never log raw transcripts by default.
- Never expose secrets in model prompts or logs unless explicitly required.
- Define retention/deletion behavior.

## 2. File ingestion security

Validate:
- file type
- file size
- filename
- content
- processing limits

Treat uploaded files as untrusted input.

## 3. Access control

Future production system should support:
- authentication
- authorization
- organization/tenant boundaries
- meeting-level access controls where needed

## 4. Model security

External model providers must be treated as data processors.

Before sending transcript content externally, define:
- what data leaves the system
- retention behavior
- provider terms
- redaction requirements

## 5. Prompt injection

Meeting transcripts may contain malicious or misleading instructions.

Transcript content is **data**, not system instructions.

The RAG pipeline must separate:
- system instructions
- user question
- retrieved evidence

Retrieved text must never be allowed to override system behavior.

## 6. Evidence security

Evidence shown to a user must respect the same authorization rules as the underlying meeting.

## 7. Auditability

Record security-relevant events such as:
- authentication
- authorization failures
- data deletion
- exports
- administrative actions

Avoid putting transcript contents into audit logs.

## 8. Deletion

Deletion must cover:
- meeting metadata
- transcripts
- embeddings
- extracted facts
- graph relationships
- evidence
- derived caches

Derived memory must not survive deletion accidentally.
