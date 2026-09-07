# MeetingOS Multi-Provider Smoke Test Report

**Execution Timestamp:** 2026-09-02T14:46:04.604604+00:00
**Target Environment:** development

## 1. Embedder Providers Status

| Provider | Status | Latency | Dimension | Notes |
| :--- | :---: | :---: | :---: | :--- |
| **local_semantic** | `PASSED` | 0.85 ms | 384 | OK |
| **sentence_transformers** | `PASSED` | 1.15 ms | 384 | OK |
| **openai** | `PASSED` | 4547.39 ms | 1536 | OK |
| **gemini** | `PASSED` | 1137.27 ms | 768 | OK |

## 2. Reasoner Providers Status

| Provider | Status | Latency | Confidence | Notes |
| :--- | :---: | :---: | :---: | :--- |
| **local_evidence** | `PASSED` | 0.13 ms | 0.88 | OK |
| **openai** | `PASSED` | 7185.36 ms | 0.88 | OK |
| **anthropic** | `PASSED` | 6080.67 ms | 0.88 | OK |
| **gemini** | `PASSED` | 4105.66 ms | 0.88 | OK |
