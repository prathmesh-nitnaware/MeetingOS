# MeetingOS Data Model

## 1. Core entities

### Meeting
Represents one organizational meeting.

Fields:
- id
- title
- meeting_date
- duration
- source_type
- processing_status
- created_at
- model_pipeline_version

### Participant
Represents a person participating in meetings.

Fields:
- id
- canonical_name
- aliases

### TranscriptSegment
Fields:
- id
- meeting_id
- speaker_id
- start_time
- end_time
- text
- sequence

### Entity
Canonical organizational entity.

Types:
- PERSON
- ORGANIZATION
- PROJECT
- TECHNOLOGY
- DATE
- LOCATION
- PRODUCT
- other domain-specific types as needed

### Topic
A normalized discussion topic.

### Decision
Fields:
- id
- subject
- status
- rationale
- meeting_id
- evidence_segment_id
- created_at
- updated_at

### Commitment / Action
Fields:
- id
- description
- owner_id
- status
- original_deadline
- current_deadline
- meeting_id
- evidence_segment_id

### Issue
Fields:
- id
- description
- owner_id
- status
- first_detected_at
- last_mentioned_at
- resolution_meeting_id
- evidence_segment_id

### Event
Represents change over time.

Examples:
- decision approved
- decision modified
- decision reversed
- deadline changed
- issue detected
- issue resolved
- technology replaced
- project launched

Fields:
- id
- event_type
- occurred_at
- meeting_id
- subject_entity_id
- payload
- evidence_segment_id

### Relationship
Typed connection between entities/facts.

Minimum types:
- ASSIGNED_TO
- WORKS_ON
- OWNS
- DECIDED_IN
- RELATED_TO
- REPLACES
- HAS_DEADLINE
- RESOLVES

### Embedding
Stores vector representation for semantic retrieval.

Fields:
- id
- source_type
- source_id
- chunk_text
- embedding
- model_name
- model_version

### Evidence
Links a fact or answer to its source.

Fields:
- id
- meeting_id
- segment_id
- start_time
- end_time
- text_snapshot
- source_type

## 2. Lifecycle state machines

### Decision

```text
Proposed
   ↓
Discussion
   ↓
Approved
   ↓
Implemented
   ├──→ Modified
   └──→ Reversed
```

### Commitment

```text
Identified → Assigned → In Progress → Completed
                    │
                    └→ Overdue → Reassigned
```

### Issue

```text
Detected → Assigned → Under Investigation → Resolved
    │
    └→ Recurring → Unresolved
```

## 3. Temporal principles

Never overwrite important historical state without recording an event.

Example:

```text
Deadline = Aug 25
        ↓
DEADLINE_CHANGED
        ↓
Deadline = Aug 30
```

The current state and the historical event must both remain queryable.

## 4. Provenance

Every extracted object should carry provenance to the source transcript.

For derived objects, preserve the chain:

```text
Answer
  → retrieved fact
  → relationship/event
  → transcript segment
  → meeting
```

## 5. Entity resolution

Surface variants should map to a canonical entity.

Example:

```text
"Postgres"
"PostgreSQL"
"PostgreSQL DB"
        ↓
Canonical entity: PostgreSQL
```

Resolution should retain aliases and confidence rather than destroying original text.
