# MeetingOS Phase 14 Empirical Research & Provider Evaluation Report

**Date:** 2026-08-27  
**Execution Mode:** LOCAL  
**Compositional Questions:** 75  

## 1. Multi-System Performance Matrix

| System | Accuracy | Retrieval Recall | Faithfulness | Latency |
| :--- | :---: | :---: | :---: | :---: |
| **A: Keyword RAG (BM25)** | 33.33% | 84.33% | 80.67% | 6.67 ms |
| **B: Vector RAG (Dense)** | 26.67% | 82.11% | 78.67% | 26.56 ms |
| **C: MeetingOS Hybrid RAG** | 21.33% | 63.78% | 77.33% | 38.34 ms |
| **D: Multi-Agent (Local Reasoner)** | **40.00%** | **89.00%** | **86.67%** | 44.52 ms |
| **E: Multi-Agent (OpenAI gpt-4o-mini)** | *CONTRACT TESTED (KEY NOT CONFIGURED)* | N/A | N/A | N/A |
| **F: Multi-Agent (Anthropic Claude 3.5)** | *CONTRACT TESTED (KEY NOT CONFIGURED)* | N/A | N/A | N/A |
| **G: Multi-Agent (Google Gemini 1.5)** | *CONTRACT TESTED (KEY NOT CONFIGURED)* | N/A | N/A | N/A |

## 2. Audio Processing Benchmark & Hardware Real-Time Factor

- **Total Audio Items Evaluated:** 3
- **Mean Real-Time Factor (RTF):** 0.0004 (Lower is better)
- **Audio Processing Throughput:** 2391.42x real-time
- **Median Latency (p50):** 8.34 ms
- **95th Percentile Latency (p95):** 20.94 ms
