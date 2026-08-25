# MeetingOS Evaluation Plan

## 1. Evaluation philosophy

Every important layer should be measurable independently.

A visually impressive UI is not evidence that the NLP system works. Humans have unfortunately built entire industries around confusing those two things.

## 2. Component metrics

| Component | Metrics |
|---|---|
| NER | Precision, Recall, F1 |
| Decision extraction | Precision, Recall, F1 |
| Action extraction | Precision, Recall, F1 |
| Commitment classification | Accuracy, F1 |
| Retrieval | Recall@K, MRR |
| QA | Answer correctness, evidence relevance, faithfulness |
| Temporal reasoning | Accuracy of decision changes, deadline changes, issue lifecycles, event ordering |

## 3. Research comparison

Evaluate three systems on the same historical multi-meeting questions.

### System A — Keyword baseline

```text
Transcript
→ keyword search
→ answer
```

### System B — Vector RAG

```text
Transcript
→ embeddings
→ vector retrieval
→ RAG
→ answer
```

### System C — MeetingOS

```text
Transcript
→ NLP extraction
→ knowledge graph
→ temporal memory
→ hybrid retrieval
→ RAG
→ answer
```

## 4. Core hypothesis

Structured temporal memory should improve historical organizational question answering compared with keyword search and standard vector RAG.

This must be tested, not assumed.

## 5. Evaluation dataset

Build a multi-meeting corpus containing:
- repeated topics
- decisions that change
- commitments with changing deadlines
- issues spanning meetings
- aliases/entity variants
- temporal expressions
- cross-meeting dependencies

## 6. Annotation

Each annotated example should support one or more tasks:
- entity spans
- utterance class
- relations
- decisions
- commitments
- actions
- issues
- events
- temporal expressions
- evidence spans

## 7. Ablation studies

Potential ablations:
- no knowledge graph
- no temporal reasoning
- no entity resolution
- no hybrid retrieval
- no graph retrieval
- vector-only retrieval
- keyword-only retrieval

Measure impact on historical QA and evidence quality.

## 8. Error analysis

Categorize errors:
- ASR error
- speaker attribution error
- NER error
- classification error
- relation error
- temporal normalization error
- entity resolution error
- retrieval miss
- graph reasoning error
- generation error
- evidence attribution error

## 9. Reproducibility

Record:
- dataset version
- model versions
- prompts where applicable
- retrieval parameters
- pipeline version
- experiment configuration
- evaluation seed where applicable
