# MeetingOS Retrieval, Reasoning and RAG

## 1. Objective

Answer historical organizational questions using structured memory plus transcript evidence.

## 2. Query planning

Example:

`What did Rahul decide about authentication last month?`

Expected query plan:

```text
PERSON = Rahul
TOPIC = authentication
TIME = last month
TYPE = decision
```

The planner should distinguish:
- entities
- topics
- time ranges
- fact/event types
- requested relationship
- lifecycle/history intent

## 3. Retrieval channels

### Keyword retrieval
Find exact or lexical matches.

### Vector retrieval
Find semantically related transcript segments.

### Knowledge graph traversal
Follow relationships such as:
person → project → decision → technology → replacement

### Metadata filtering
Filter by:
- meeting
- date
- participant
- entity
- event type
- lifecycle state

## 4. Hybrid retrieval

A query may combine all four channels.

Conceptually:

```text
Final evidence
= lexical candidates
+ semantic candidates
+ graph candidates
+ metadata constraints
→ ranking/fusion
```

The exact weighting must be experimentally evaluated.

## 5. Historical reasoning

The system should reconstruct sequences rather than merely return isolated chunks.

Example:

```text
MongoDB proposed
→ approved
→ implemented
→ production problems
→ decision reversed
→ PostgreSQL adopted
```

Question:
`Why are we using PostgreSQL?`

Expected reasoning:
- identify current decision
- find predecessor decision
- find reversal/change event
- retrieve rationale evidence
- return chronological explanation

## 6. RAG contract

The generation layer receives:
- user question
- retrieved transcript evidence
- relevant graph relationships
- lifecycle/event history
- metadata

The model must not be used as the sole source of organizational facts.

## 7. Evidence attribution

Every substantive claim should map to one or more evidence records.

UI evidence should include:
- meeting
- date
- timestamp
- transcript excerpt
- navigation target

## 8. Faithfulness rules

If evidence is insufficient:
- say that the available meeting memory does not establish the answer
- do not invent rationale
- distinguish explicit statements from inferred relationships

## 9. Retrieval evaluation

Required metrics:
- Recall@K
- MRR
- evidence relevance

For QA:
- answer correctness
- evidence relevance
- faithfulness

## 10. Advanced reasoning

### Contradiction detection

Example:
- Meeting 10: deadline Aug 25
- Meeting 14: deadline Aug 30

Create:

`DEADLINE_CHANGE(task, previous=Aug25, current=Aug30, meeting=14)`

### Unresolved issue detection

Track:
- first detected meeting
- owner
- current status
- last mentioned meeting
- resolution status

Absence of mention alone should not automatically mean resolution.

### Cross-meeting reasoning

Example:

```text
failure detected
→ root cause identified
→ provider changed
→ migration completed
→ issue resolved
```

The reasoning layer should reconstruct this from events and evidence.
