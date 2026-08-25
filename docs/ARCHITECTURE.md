# MeetingOS Architecture

## 1. Architectural principle

MeetingOS has two entry paths that converge on a shared organizational memory layer:

1. Meeting ingestion
2. Knowledge query

## 2. High-level flow

```text
                    ┌──────────────────────┐
                    │   Meeting Sources    │
                    │ audio/video/text     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Ingestion + CMF       │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │ Speech Processing     │
                    │ ASR + diarization     │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │ NLP / IE Pipeline     │
                    │ NER/classification/   │
                    │ relations/events/time │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │ Entity Resolution     │
                    └──────────┬───────────┘
                               ▼
              ┌──────────────────────────────────┐
              │     Organizational Memory        │
              │                                  │
              │ Knowledge Graph                  │
              │ Vector Memory                    │
              │ Timeline                         │
              │ Evidence/Provenance              │
              └────────────────┬─────────────────┘
                               ▲
                               │
                    ┌──────────┴───────────┐
                    │ Hybrid Retrieval      │
                    │ lexical + vector +    │
                    │ graph + metadata      │
                    └──────────┬───────────┘
                               ▲
                    ┌──────────┴───────────┐
                    │ Query Planning        │
                    │ person/topic/time/type │
                    └──────────┬───────────┘
                               ▲
                    ┌──────────┴───────────┐
                    │ User Question         │
                    └───────────────────────┘
```

## 3. Ingestion pipeline

1. Validate source.
2. Normalize to Common Meeting Format.
3. Transcribe if needed.
4. Diarize speakers.
5. Preserve timestamps.
6. Segment transcript.
7. Run NLP extraction.
8. Normalize temporal expressions.
9. Resolve entities.
10. Create relationships/events.
11. Generate embeddings.
12. Persist memory and evidence.
13. Emit processing status.

## 4. Query pipeline

1. Receive question.
2. Classify query intent.
3. Extract structured constraints.
4. Build retrieval plan.
5. Run lexical retrieval.
6. Run vector retrieval.
7. Traverse graph where needed.
8. Apply metadata/time filters.
9. Rank and fuse evidence.
10. Reconstruct lifecycle/history.
11. Generate grounded answer.
12. Attach evidence references.

## 5. Common Meeting Format

Every ingestion source should eventually produce:

```text
Meeting
├── meeting_id
├── title
├── date
├── duration
├── source_type
├── participants[]
└── segments[]
    ├── segment_id
    ├── speaker_id
    ├── start_time
    ├── end_time
    └── text
```

Optional source metadata may be retained without leaking connector-specific assumptions into downstream NLP.

## 6. Service boundaries

Recommended logical modules:

- `ingestion`
- `speech`
- `nlp`
- `memory`
- `retrieval`
- `reasoning`
- `api`
- `worker`
- `web`
- `evaluation`

These can begin as modules in one repository and be separated into services only when operational complexity requires it.

## 7. Processing model

Long-running work such as transcription, diarization, extraction and embedding should be asynchronous.

Use durable job states:

`queued → running → succeeded`

Failure path:

`running → failed`

Retries must be idempotent.

## 8. Evidence is a first-class object

Every extracted fact and generated answer should be traceable to:
- meeting
- transcript segment
- timestamp
- extraction/model version where relevant

This prevents the RAG layer from becoming an ungrounded chatbot with a suspiciously confident personality.
