# MeetingOS Dataset Strategy

## 1. Purpose

The dataset must support both engineering validation and the research comparison.

## 2. Data sources

Initial MVP:
- project-created synthetic/sample meetings
- manually curated meeting transcripts
- user-provided meeting files where permission exists

Do not use meeting content without appropriate rights or consent.

## 3. Common Meeting Format

All datasets should normalize to:

```text
meeting_id
meeting_date
participants
segments:
  segment_id
  speaker_id
  start_time
  end_time
  text
```

## 4. Annotation layers

### Layer 1: NER
Span + entity type.

### Layer 2: utterance classification
Decision, Action, Commitment, Question, Suggestion, Problem, Information.

### Layer 3: relations
Typed entity-to-entity or entity-to-fact relationships.

### Layer 4: organizational facts
Decisions, commitments, actions, issues.

### Layer 5: events
Changes and lifecycle transitions.

### Layer 6: temporal labels
Normalized dates/ranges and relation to meeting date.

### Layer 7: evidence
Source segments supporting each fact.

## 5. Train/validation/test split

Splits should preferably be meeting-level, not random utterance-level.

This prevents nearly identical statements from the same meeting leaking across train and test sets.

For temporal-memory evaluation, reserve complete meeting sequences so the system must generalize across meetings.

## 6. Quality control

Use:
- annotation guidelines
- double annotation for a subset
- adjudication
- inter-annotator agreement
- documented disagreement cases

## 7. Dataset versioning

Every dataset release should have:
- version
- source manifest
- annotation schema version
- preprocessing version
- license/permission notes
- known limitations
