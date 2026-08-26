from packages.agents.context import AgentTraceItem
from packages.agents.traces import AgentExecutionTrace, TraceStore, sanitize_trace_data


def test_trace_sanitization():
    payload = {
        "api_key": "sk-1234567890abcdef1234567890abcdef",
        "auth_header": "Bearer secret_jwt_token_12345",
        "nested": {
            "password": "secret_password",
            "safe_field": "PostgreSQL decision",
        },
        "list_items": [
            "Normal text",
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token",
        ],
    }

    sanitized = sanitize_trace_data(payload)
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["auth_header"] == "[REDACTED]"
    assert sanitized["nested"]["password"] == "[REDACTED]"
    assert sanitized["nested"]["safe_field"] == "PostgreSQL decision"
    assert "secret" not in str(sanitized)


def test_trace_store_operations():
    store = TraceStore(max_traces=5)
    trace = AgentExecutionTrace(
        trace_id="tr-test-1",
        query_id="qry-test-1",
        query="What database was chosen?",
        answer="PostgreSQL with pgvector",
        confidence=0.95,
        steps=[
            AgentTraceItem(
                agent="planner",
                status="completed",
                duration_seconds=0.01,
                latency_ms=10.0,
            )
        ],
        citations=["Meeting 1 (2026-08-20) - 0:00"],
    )

    saved = store.save_trace(trace)
    assert saved.trace_id == "tr-test-1"

    fetched = store.get_trace("tr-test-1")
    assert fetched is not None
    assert fetched.query == "What database was chosen?"

    listed = store.list_traces(limit=10)
    assert len(listed) == 1
