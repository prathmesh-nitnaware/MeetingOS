# MeetingOS NLP and Deep Learning Specification

## 1. Principle

MeetingOS must remain a genuine NLP/deep-learning system. The LLM is not the entire intelligence layer.

Each extraction component must be independently testable.

## 2. Speech recognition

Input:
- wav
- mp3
- m4a
- mp4

Output:
- timestamped transcript
- speaker-attributed segments when diarization succeeds

Candidate models:
- Whisper
- WhisperX
- faster-whisper

## 3. Speaker diarization

Candidate:
- pyannote.audio

Output:
- anonymous speaker IDs initially
- optional mapping to known participants

The system must not assume that `Speaker 1` is a particular person without evidence.

## 4. NER

Required labels:
- PERSON
- ORGANIZATION
- PROJECT
- TECHNOLOGY
- DATE
- LOCATION

Example:

`Rahul will migrate the backend to PostgreSQL by Friday.`

Expected:
- Rahul → PERSON
- PostgreSQL → TECHNOLOGY
- Friday → DATE

Metrics:
- precision
- recall
- F1

## 5. Utterance classification

Required classes:
- Decision
- Action
- Commitment
- Question
- Suggestion
- Problem
- Information

The classifier should support multi-label extension later because natural meeting utterances can contain more than one semantic role.

## 6. Relation extraction

Required relations:
- ASSIGNED_TO
- WORKS_ON
- OWNS
- DECIDED_IN
- RELATED_TO
- REPLACES
- HAS_DEADLINE
- RESOLVES

Example:

`Rahul will implement OAuth.`

Potential relation:

`Rahul --ASSIGNED_TO--> OAuth implementation`

## 7. Event extraction

Detect:
- decision change
- decision reversal
- deadline change
- issue resolution
- technology replacement
- project launch
- migration
- other domain-specific events

## 8. Temporal information extraction

Normalize:
- tomorrow
- next Friday
- before release
- two weeks later
- by the end of the week

Relative expressions must be resolved using the meeting date and, when needed, surrounding temporal context.

## 9. Coreference resolution

Example:

`Rahul will implement the API. He will finish it tomorrow.`

Expected:
- He → Rahul
- it → API implementation

## 10. Entity resolution

Normalize variants into canonical entities while retaining:
- original surface form
- canonical ID
- alias
- resolution confidence

## 11. Embeddings

Sentence-transformer style embeddings are proposed for transcript semantic retrieval.

Embedding model selection must be benchmarked rather than treated as permanent.

## 12. Model versioning

Every production extraction result should be associated with:
- model name
- model version
- pipeline version
- extraction timestamp

This is required for reproducibility and reprocessing.

## 13. NLP pipeline output

The extraction pipeline should produce structured objects rather than free-form prose.

```json
{
  "entities": [],
  "topics": [],
  "decisions": [],
  "actions": [],
  "commitments": [],
  "issues": [],
  "events": [],
  "relations": [],
  "temporal_expressions": [],
  "evidence": []
}
```

## 14. Error handling

Never silently discard uncertain extraction.

Use confidence and provenance fields so downstream reasoning can distinguish:
- high-confidence fact
- uncertain extraction
- conflicting extraction
