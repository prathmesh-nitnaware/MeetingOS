# Contributing to MeetingOS

## 1. Engineering principles

- Prefer simple architecture until complexity is justified.
- Keep ML components independently evaluable.
- Preserve evidence and provenance.
- Do not silently mutate historical facts.
- Treat uncertainty explicitly.
- Write tests around lifecycle transitions.
- Document architecture changes.

## 2. Branching

Use short-lived feature branches.

Examples:

```text
feature/transcript-ingestion
feature/decision-extraction
feature/hybrid-retrieval
fix/entity-resolution
```

## 3. Pull requests

A PR should explain:
- what changed
- why it changed
- affected modules
- tests
- evaluation impact
- schema/API changes
- documentation changes

## 4. ML changes

For model/pipeline changes, record:
- model version
- dataset version
- metrics before/after
- known regressions
- inference cost/latency where relevant

## 5. Database changes

Schema changes must include:
- migration
- backward compatibility consideration
- data migration plan if needed
- rollback consideration

## 6. Definition of done

- implementation complete
- tests passing
- documentation updated
- observability considered
- security/privacy considered
- evaluation updated for ML changes
- no unexplained breaking changes
