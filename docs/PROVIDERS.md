# MeetingOS AI Model Providers Specification

MeetingOS is architected to be completely provider-agnostic, supporting both local/offline neural implementations and production cloud providers (OpenAI, Anthropic, Google Gemini).

---

## 1. Provider Architecture Overview

```
Reasoner Abstraction (BaseReasoner)
  ├── LocalEvidenceReasoner      (Offline multi-hop chronological lifecycle reasoning)
  ├── OpenAICompatibleReasoner   (gpt-4o-mini / OpenAI chat completions with structured JSON)
  ├── AnthropicReasoner          (claude-3-5-sonnet Messages API with retry & structured output)
  └── GeminiReasoner             (gemini-1.5-flash generateContent with JSON mode & fallback)

Embedder Abstraction (BaseEmbedder)
  ├── LocalSemanticEmbedder      (Offline 384-dim subword n-gram projections)
  ├── SentenceTransformerEmbedder(HuggingFace all-MiniLM-L6-v2 with local fallback)
  ├── OpenAICompatibleEmbedder   (text-embedding-3-small with SHA-256 caching & fallback)
  └── GeminiEmbedder             (text-embedding-004 batchEmbedContents with SHA-256 caching)
```

---

## 2. Configuration & Environment Variables

| Provider | Reasoner Selector | Embedding Selector | Required API Keys | Default Model |
| :--- | :--- | :--- | :--- | :--- |
| **Local Neural** | `local` / `local_evidence` | `local` / `local_semantic` | None (Offline) | `local-reasoner-v1` / `local-semantic-v1` |
| **OpenAI** | `openai` | `openai` | `MEETINGOS_EMBEDDING_API_KEY`, `MEETINGOS_REASONER_API_KEY` | `gpt-4o-mini` / `text-embedding-3-small` |
| **Anthropic** | `anthropic` | *Uses Local/OpenAI* | `MEETINGOS_ANTHROPIC_API_KEY` | `claude-3-5-sonnet-20241022` |
| **Google Gemini**| `gemini` | `gemini` | `MEETINGOS_GEMINI_API_KEY` | `gemini-1.5-flash` / `text-embedding-004` |

---

## 3. Fallback Mechanics & Resilience

Every cloud provider adapter implements strict resilience guarantees:
1. **Bounded Exponential Backoff:** 3 retry attempts with jitter ($0.5s \times 2^{\text{attempt}}$).
2. **Automatic Local Fallback:** If API keys are missing, network timeouts occur, or rate limits are exceeded, the adapter automatically invokes `LocalEvidenceReasoner` or `LocalSemanticEmbedder`.
3. **Telemetry & Tracking:** All provider calls (including fallbacks, prompt/completion tokens, and latencies) are logged to `UsageTracker` without leaking sensitive secrets.
4. **Secret Sanitization:** All credentials and bearer tokens are automatically scrubbed by `TraceStore` before saving execution traces.
