# MeetingOS API Specification

This is the initial logical API contract. Exact framework and authentication implementation are implementation decisions.

## 1. API conventions

Base path:

`/api/v1`

Use JSON for application payloads.

Long-running processing should return a job/process identifier rather than block the HTTP request.

## 2. Meetings

### POST `/meetings`

Create/upload a meeting.

Inputs:
- file
- title
- meeting date
- optional participant metadata

Returns:
- meeting_id
- processing_status

### GET `/meetings/{meeting_id}`

Returns:
- metadata
- processing status
- participants
- summary metadata
- available artifacts

### GET `/meetings/{meeting_id}/transcript`

Returns timestamped transcript segments.

### GET `/meetings/{meeting_id}/timeline`

Returns meeting-level extracted events chronologically.

### GET `/meetings/{meeting_id}/entities`

Returns entities associated with the meeting.

### GET `/meetings/{meeting_id}/decisions`

Returns decisions extracted from the meeting.

### GET `/meetings/{meeting_id}/actions`

Returns actions/commitments.

### GET `/meetings/{meeting_id}/issues`

Returns issues.

## 3. Query

### POST `/query`

Request:

```json
{
  "question": "What decisions have we made about the database?"
}
```

Response concept:

```json
{
  "answer": "...",
  "evidence": [
    {
      "meeting_id": "...",
      "segment_id": "...",
      "start_time": 123.4,
      "end_time": 140.2,
      "text": "..."
    }
  ],
  "query_plan": {
    "person": null,
    "topic": "database",
    "time_range": null,
    "type": "decision"
  }
}
```

Whether `query_plan` is exposed publicly or only in debug mode is a product decision.

## 4. Search

### GET `/search`

Parameters:
- q
- meeting_id
- person
- topic
- start_date
- end_date
- type

Returns ranked evidence candidates.

## 5. Graph

### GET `/graph/entities/{entity_id}`

Returns connected entities and typed relationships.

### GET `/graph/subgraph`

Parameters:
- entity
- depth
- relationship types

## 6. Dashboard

### GET `/dashboard`

Potential metrics:
- meetings ingested
- decisions tracked
- open actions
- unresolved issues
- overdue actions

## 7. Processing status

### GET `/jobs/{job_id}`

Returns:
- status
- stage
- progress
- error
- created_at
- updated_at

## 8. Error contract

Use consistent structure:

```json
{
  "error": {
    "code": "PROCESSING_FAILED",
    "message": "Human-readable explanation",
    "request_id": "..."
  }
}
```

Do not expose stack traces or sensitive transcript content in production error responses.
