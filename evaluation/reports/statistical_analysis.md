# MeetingOS Phase 11 Statistical Analysis & Uncertainty Report

- **Benchmark Size:** 75 questions (30+ multi-meeting cross-referencing)
- **Methodology:** 1,000-iteration Empirical Bootstrap (95% Confidence Intervals)
- **Embedding Model:** `LocalSemanticEmbedder (384-dim)`
- **Reasoning Provider:** `LocalEvidenceReasoner`

## 1. Primary Systems Comparison (Mean ± 95% CI)

| System | Accuracy (95% CI) | Retrieval Recall (95% CI) | Faithfulness (95% CI) | Avg Latency |
| :--- | :---: | :---: | :---: | :---: |
| **A: Keyword RAG** | 33.33% [22.67%, 44.00%] | 84.33% [77.00%, 91.00%] | 80.67% [75.33%, 85.33%] | 9.10 ms |
| **B: Vector RAG (Real Embeddings)** | 26.67% [17.33%, 37.33%] | 82.11% [75.11%, 88.56%] | 78.67% [72.67%, 84.00%] | 37.40 ms |
| **C: MeetingOS Hybrid RAG** | 18.67% [10.67%, 28.00%] | 63.33% [53.56%, 73.00%] | 74.67% [68.67%, 80.00%] | 62.40 ms |
| **D: Multi-Agent (Mock Reasoner)** | 32.00% [21.33%, 42.67%] | 77.00% [68.00%, 85.56%] | 77.33% [72.00%, 82.67%] | 42.10 ms |
| **E: Multi-Agent (Real Reasoner)** | 41.33% [29.33%, 53.33%] | 77.00% [68.00%, 85.56%] | 84.00% [78.67%, 89.33%] | 40.30 ms |
