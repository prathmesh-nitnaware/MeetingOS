# MeetingOS Product Requirements Document

## 1. Product overview

MeetingOS transforms organizational conversations into persistent memory and enables evidence-backed reasoning over that memory.

It is explicitly **not** positioned as a conventional AI meeting summarizer.

## 2. Problem

Meeting information becomes fragmented across recordings, transcripts and independent meeting notes. Important decisions, ownership, deadlines, unresolved issues and changes disappear into historical records.

MeetingOS must connect information across meetings so that organizational history can be queried as a coherent timeline.

## 3. Goals

### Primary goals

- Convert meeting audio/video/transcripts into structured organizational knowledge.
- Preserve source evidence and timestamps.
- Connect knowledge across meetings.
- Track decision, commitment and issue lifecycles.
- Support semantic and relationship-heavy historical questions.
- Detect important changes such as deadline changes and decision reversals.
- Produce answers grounded in retrieved evidence.

### Non-goals for the initial MVP

- Real-time meeting assistant
- Automatic meeting participation
- Full Teams/Zoom/Google Meet integrations
- Fully autonomous project management
- Unbounded general-purpose enterprise knowledge management

## 4. Users

### Software teams
Need architecture decisions, assignments, bugs, releases and technical history.

### Corporate management
Need strategic decisions, action items, project status and recurring issues.

### Consulting teams
Need client requirements, decisions, commitments and unresolved questions.

### Research teams
Need hypotheses, experiments, decisions and research tasks.

## 5. Core user journeys

### Journey A: ingest meeting

User uploads `.wav`, `.mp3`, `.m4a`, `.mp4`, `.txt` or `.srt`.

System:
1. validates the file
2. creates a meeting record
3. transcribes audio/video when needed
4. identifies speakers
5. runs NLP extraction
6. resolves entities
7. creates structured events/relationships
8. stores transcript embeddings
9. builds/updates organizational memory
10. marks processing status

### Journey B: ask a historical question

User asks:
- What decisions have we made about the database?
- What tasks has Rahul committed to?
- Which issues are still unresolved?
- What changed between the last three meetings?
- Why did we reject Firebase?
- When did we first discuss payment failures?

System:
1. parses intent
2. extracts filters such as person/topic/time/type
3. retrieves lexical, semantic, graph and metadata evidence
4. reconstructs relevant history
5. generates an answer
6. attaches evidence to meetings and timestamps

## 6. Functional requirements

### FR-01 Meeting ingestion
Support initial file-based ingestion and normalize all sources into a Common Meeting Format.

### FR-02 Speech processing
Provide speech-to-text and speaker diarization for supported audio/video inputs.

Candidate models/libraries from the specification include Whisper/WhisperX/faster-whisper and pyannote.audio.

### FR-03 Entity extraction
Extract PERSON, ORGANIZATION, PROJECT, TECHNOLOGY, DATE and LOCATION.

### FR-04 Utterance classification
Classify utterances into Decision, Action, Commitment, Question, Suggestion, Problem and Information.

### FR-05 Relation extraction
Support at minimum:
ASSIGNED_TO, WORKS_ON, OWNS, DECIDED_IN, RELATED_TO, REPLACES, HAS_DEADLINE, RESOLVES.

### FR-06 Event extraction
Detect events including decision reversal, deadline change, issue resolution, technology replacement, database migration and project launch.

### FR-07 Temporal normalization
Normalize relative expressions against meeting date.

### FR-08 Coreference resolution
Resolve references such as pronouns and references to previously mentioned entities/tasks.

### FR-09 Entity resolution
Merge variants such as Postgres, PostgreSQL and PostgreSQL DB.

### FR-10 Organizational memory
Store knowledge graph relationships, semantic transcript memory and chronological timeline events.

### FR-11 Lifecycle tracking
Track decision, commitment and issue state transitions.

### FR-12 Hybrid retrieval
Combine keyword search, vector search, knowledge-graph traversal and metadata filtering.

### FR-13 RAG
Generate answers only after assembling retrieved evidence and relevant structured memory.

### FR-14 Evidence attribution
Every substantive answer must identify source meeting and timestamp.

### FR-15 Contradiction detection
Detect changes such as deadline 25 Aug becoming 30 Aug.

### FR-16 Unresolved issue detection
Surface issues that remain unresolved across meetings.

### FR-17 Cross-meeting reasoning
Reconstruct topic evolution over multiple meetings.

### FR-18 UI
Provide dashboard, meeting explorer, knowledge graph explorer, timeline and search/query experience.

## 7. Non-functional requirements

- Evidence traceability for substantive answers.
- Reproducible NLP evaluation.
- Modular ingestion.
- Model components must be independently testable.
- Processing jobs should be observable.
- Structured memory must survive model changes.
- APIs should be versioned.
- Sensitive meeting data must not be exposed in logs.

## 8. MVP acceptance criteria

A meeting can be uploaded, processed and inspected.

The system can answer a basic question using extracted memory and provide source meeting/timestamp evidence.

At minimum the MVP demonstrates:
- transcription
- speaker identification where available
- NER
- decision/action extraction
- topic extraction
- persistent storage
- semantic retrieval
- evidence-backed QA

## 9. Success metrics

Model-level:
- NER precision/recall/F1
- decision extraction precision/recall/F1
- action extraction precision/recall/F1
- commitment classification accuracy/F1
- retrieval Recall@K and MRR
- answer correctness
- evidence relevance
- answer faithfulness
- temporal reasoning accuracy

Research-level:
Compare:
A. keyword search
B. vector RAG
C. MeetingOS structured temporal memory + hybrid retrieval + RAG

The central experimental question is whether structured temporal memory improves historical multi-meeting QA over conventional approaches.
