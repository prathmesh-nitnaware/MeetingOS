# Source Notes

These planning documents are derived from the uploaded `MeetingOS_Project_Document.docx`.

The source specification defines:
- MeetingOS as organizational memory rather than a meeting summarizer.
- Two pipelines: meeting ingestion and knowledge query.
- Three central memory forms: knowledge graph, vector memory and timeline.
- Seven extraction categories and lifecycle/state machines.
- NLP tasks including NER, classification, relation/event/temporal extraction, coreference and entity resolution.
- Deep-learning components for ASR, diarization, transformers and embeddings.
- Hybrid retrieval, RAG, evidence attribution, contradiction detection, unresolved issue detection and cross-meeting reasoning.
- Dashboard, meeting explorer, knowledge graph explorer and connectors.
- Evaluation metrics and comparison of keyword search, vector RAG and MeetingOS.
- A seven-stage development strategy.

Where the source lists candidate technologies rather than mandatory decisions, this documentation keeps them as candidates/proposals. In particular, PostgreSQL + pgvector is treated as the proposed vector-memory option, and Whisper-family/pyannote components remain candidate model/tool choices until benchmarked.
