# MeetingOS Research & Evaluation Framework

MeetingOS provides a quantitative evaluation harness measuring question-answering accuracy, retrieval recall, faithfulness, confidence calibration (Brier score), audio pipeline real-time factor, and human assessment.

---

## 1. Evaluation Datasets

| Dataset | Meetings | Questions | Scope | Format |
| :--- | :---: | :---: | :--- | :--- |
| `compositional_dataset.json` | 13 | 75 | 12 query categories, decision reversals, deadline slippages | Labeled JSON |
| `manifest.json` | 3 | N/A | Real & synthetic audio recordings for ASR/Diarization RTF | Audio CMF Manifest |
| `human_eval_template.json` | 13 | 75 | 8-dimension qualitative human assessment template | Rubric JSON |

---

## 2. Evaluation Metrics

1. **Answer Accuracy:** Strict factual agreement on compositional queries.
2. **Retrieval Recall:** Recall over target transcript segments ($Recall = |S_{\text{retrieved}} \cap S_{\text{target}}| / |S_{\text{target}}|$).
3. **Faithfulness:** Verification that synthesized answers do not contain claims unsupported by evidence.
4. **Real-Time Factor (RTF):** $RTF = \text{total\_processing\_time} / \text{audio\_duration}$.
5. **Confidence Calibration (Brier Score):** Mean squared error between confidence scores and binary correctness ($BS = \frac{1}{N} \sum (f_t - o_t)^2$).
6. **Human Evaluation:** 8 standard Likert dimensions (Correctness, Evidence Support, Citation Quality, Temporal Correctness, Completeness, Hallucination, Helpfulness, Calibration).

---

## 3. Reproduction Commands

```bash
# Execute local deterministic research benchmark
python -m evaluation.phase14 --mode local

# Execute benchmark with configured cloud providers (OpenAI, Anthropic, Gemini)
python -m evaluation.phase14 --mode configured

# Aggregate completed human evaluation annotations
python -m evaluation.human_eval evaluation/reports/human_eval_phase14.json
```
