# MeetingOS Multi-Provider Smoke Test Report

**Execution Timestamp:** 2026-09-01T13:31:15.170804+00:00
**Target Environment:** development

## 1. Embedder Providers Status

| Provider | Status | Latency | Dimension | Notes |
| :--- | :---: | :---: | :---: | :--- |
| **local_semantic** | `PASSED` | 0.79 ms | 384 | OK |
| **sentence_transformers** | `PASSED` | 1.09 ms | 384 | OK |
| **openai** | `SKIPPED` | N/A | N/A | No real API key configured |
| **gemini** | `SKIPPED` | N/A | N/A | No real API key configured |

## 2. Reasoner Providers Status

| Provider | Status | Latency | Confidence | Notes |
| :--- | :---: | :---: | :---: | :--- |
| **local_evidence** | `PASSED` | 0.11 ms | 0.88 | OK |
| **openai** | `SKIPPED` | N/A | N/A | No real API key configured |
| **anthropic** | `SKIPPED` | N/A | N/A | No real API key configured |
| **gemini** | `SKIPPED` | N/A | N/A | No real API key configured |
