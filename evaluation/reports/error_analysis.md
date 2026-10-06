# MeetingOS Evaluation Failure & Error Analysis Report

- **Total Questions Evaluated:** 42
- **Total Inaccuracies:** 25

## Detailed Failure Log

| ID | Category | Failed Component | Likely Cause |
| :--- | :--- | :--- | :--- |
| `eq-03` | `factual_lookup` | `retrieval_failure` | Hybrid retrieval engine returned zero matching ground-truth segments |
| `eq-07` | `entity_lookup` | `answer_synthesis_failure` | Answer synthesis failed to include exact expected keyphrases |
| `eq-10` | `decision_history` | `retrieval_failure` | Hybrid retrieval engine returned zero matching ground-truth segments |
| `eq-13` | `decision_history` | `answer_synthesis_failure` | Answer synthesis failed to include exact expected keyphrases |
| `eq-15` | `decision_reversal` | `retrieval_failure` | Hybrid retrieval engine returned zero matching ground-truth segments |
| `eq-16` | `decision_reversal` | `answer_synthesis_failure` | Answer synthesis failed to include exact expected keyphrases |
| `eq-17` | `decision_reversal` | `answer_synthesis_failure` | Answer synthesis failed to include exact expected keyphrases |
| `eq-18` | `commitment_ownership` | `answer_synthesis_failure` | Answer synthesis failed to include exact expected keyphrases |
| `eq-19` | `commitment_ownership` | `retrieval_failure` | Hybrid retrieval engine returned zero matching ground-truth segments |
| `eq-20` | `commitment_ownership` | `answer_synthesis_failure` | Answer synthesis failed to include exact expected keyphrases |
| `eq-22` | `deadline_tracking` | `temporal_reasoning_failure` | Temporal lifecycle reconciliation failed to order events |
| `eq-23` | `deadline_tracking` | `retrieval_failure` | Hybrid retrieval engine returned zero matching ground-truth segments |
| `eq-24` | `deadline_tracking` | `retrieval_failure` | Hybrid retrieval engine returned zero matching ground-truth segments |
| `eq-25` | `deadline_tracking` | `retrieval_failure` | Hybrid retrieval engine returned zero matching ground-truth segments |
| `eq-26` | `issue_recurrence` | `answer_synthesis_failure` | Answer synthesis failed to include exact expected keyphrases |
| `eq-27` | `issue_recurrence` | `answer_synthesis_failure` | Answer synthesis failed to include exact expected keyphrases |
| `eq-29` | `issue_resolution` | `answer_synthesis_failure` | Answer synthesis failed to include exact expected keyphrases |
| `eq-30` | `issue_resolution` | `answer_synthesis_failure` | Answer synthesis failed to include exact expected keyphrases |
| `eq-31` | `issue_resolution` | `answer_synthesis_failure` | Answer synthesis failed to include exact expected keyphrases |
| `eq-32` | `temporal_reasoning` | `retrieval_failure` | Hybrid retrieval engine returned zero matching ground-truth segments |
| `eq-33` | `temporal_reasoning` | `temporal_reasoning_failure` | Temporal lifecycle reconciliation failed to order events |
| `eq-34` | `temporal_reasoning` | `retrieval_failure` | Hybrid retrieval engine returned zero matching ground-truth segments |
| `eq-36` | `cross_meeting_reasoning` | `retrieval_failure` | Hybrid retrieval engine returned zero matching ground-truth segments |
| `eq-37` | `graph_relationship` | `graph_reasoning_failure` | Graph service failed to bridge multi-hop entity relationships |
| `eq-38` | `graph_relationship` | `graph_reasoning_failure` | Graph service failed to bridge multi-hop entity relationships |


### Per-Question Diagnostic Breakdown

#### Question eq-03: "What NLP backbone library was selected for entity extraction?"
- **Expected Answer:** `spaCy`
- **Generated Answer:** `According to the retrieved evidence: Action: Nisha Patel: I will own the NLP pipeline integration task. I commit to delivering the entity extractor prototype by end of sprint, which is September 5th. (Owner: spk_nisha, Status: In Progres...`
- **Failed Component:** `retrieval_failure`
- **Cause:** Hybrid retrieval engine returned zero matching ground-truth segments

#### Question eq-07: "Who owns the Kubernetes cluster setup?"
- **Expected Answer:** `Kiran Das`
- **Generated Answer:** `According to the retrieved evidence: Decision: We decided to use Docker Compose for local development environments. The decision was made to avoid Kubernetes complexity at this stage. (Status: Approved) Decision: We need an API rate limi...`
- **Failed Component:** `answer_synthesis_failure`
- **Cause:** Answer synthesis failed to include exact expected keyphrases

#### Question eq-10: "Why did we adopt PostgreSQL instead of MongoDB?"
- **Expected Answer:** `PostgreSQL with pgvector supports vector embedding lookups`
- **Generated Answer:** `Based on the meeting records, the team evaluated MongoDB and PostgreSQL, and decided to adopt PostgreSQL with pgvector as the official database.`
- **Failed Component:** `retrieval_failure`
- **Cause:** Hybrid retrieval engine returned zero matching ground-truth segments

#### Question eq-13: "What is the required retention period for data access audit logs?"
- **Expected Answer:** `90 days`
- **Generated Answer:** `According to the retrieved evidence: Decision: Let's finalize the database. We decided to adopt PostgreSQL for MeetingOS since pgvector fits our needs better than MongoDB. (Status: Reversed) Decision: We have decided to adopt PostgreSQL ...`
- **Failed Component:** `answer_synthesis_failure`
- **Cause:** Answer synthesis failed to include exact expected keyphrases

#### Question eq-15: "What was the initial orchestration choice and why was it reversed?"
- **Expected Answer:** `Docker Compose`
- **Generated Answer:** `According to the retrieved evidence: Decision: We have decided to adopt PostgreSQL as our primary database. The decision is final and replaces the earlier MongoDB evaluation. (Status: Approved) Decision: Rahul Verma and Priya Sharma are ...`
- **Failed Component:** `retrieval_failure`
- **Cause:** Hybrid retrieval engine returned zero matching ground-truth segments

#### Question eq-16: "Did the team stick with Docker Compose or migrate to Kubernetes for production?"
- **Expected Answer:** `Kubernetes`
- **Generated Answer:** `According to the retrieved evidence: Decision: Let's finalize the database. We decided to adopt PostgreSQL for MeetingOS since pgvector fits our needs better than MongoDB. (Status: Reversed) Decision: We decided to use Docker Compose for...`
- **Failed Component:** `answer_synthesis_failure`
- **Cause:** Answer synthesis failed to include exact expected keyphrases

#### Question eq-17: "Which NLP library was replaced in favor of spaCy?"
- **Expected Answer:** `NLTK`
- **Generated Answer:** `According to the retrieved evidence: Decision: We decided to switch our NLP caching strategy from write-through to write-behind to reduce latency. This modifies the original Redis caching decision from the kickoff meeting. (Status: Appro...`
- **Failed Component:** `answer_synthesis_failure`
- **Cause:** Answer synthesis failed to include exact expected keyphrases

#### Question eq-18: "Who was assigned to the database schema migration task?"
- **Expected Answer:** `Priya Sharma`
- **Generated Answer:** `Based on the meeting records, the team evaluated MongoDB and PostgreSQL, and decided to adopt PostgreSQL with pgvector as the official database.`
- **Failed Component:** `answer_synthesis_failure`
- **Cause:** Answer synthesis failed to include exact expected keyphrases

#### Question eq-19: "Who is responsible for the Redis rate limiter task?"
- **Expected Answer:** `Rahul Verma`
- **Generated Answer:** `According to the retrieved evidence: Action: Priya Sharma: I will own the database schema migration task. The deadline is set for next Friday, which is August 29th. (Owner: spk_priya, Status: In Progress) Action: Nisha Patel: I will own ...`
- **Failed Component:** `retrieval_failure`
- **Cause:** Hybrid retrieval engine returned zero matching ground-truth segments

#### Question eq-20: "Who was assigned to optimize Docker container image sizes?"
- **Expected Answer:** `Kiran Das`
- **Generated Answer:** `According to the retrieved evidence: Action: Rahul Verma: The Redis timeout issue has recurred despite our connection pool fix. We are escalating this to a P1 incident. Alex Rivera is assigned to resolve it completely. (Owner: spk_resolv...`
- **Failed Component:** `answer_synthesis_failure`
- **Cause:** Answer synthesis failed to include exact expected keyphrases

#### Question eq-22: "What was the original deadline for the database schema migration?"
- **Expected Answer:** `August 29th`
- **Generated Answer:** `Based on the meeting records, the team evaluated MongoDB and PostgreSQL, and decided to adopt PostgreSQL with pgvector as the official database.`
- **Failed Component:** `temporal_reasoning_failure`
- **Cause:** Temporal lifecycle reconciliation failed to order events

#### Question eq-23: "To what date was the schema migration deadline moved?"
- **Expected Answer:** `September 1st`
- **Generated Answer:** `The available meeting memory does not establish an answer to this question.`
- **Failed Component:** `retrieval_failure`
- **Cause:** Hybrid retrieval engine returned zero matching ground-truth segments

#### Question eq-24: "When was the Kubernetes cluster setup deadline scheduled for?"
- **Expected Answer:** `September 15th`
- **Generated Answer:** `The available meeting memory does not establish an answer to this question.`
- **Failed Component:** `retrieval_failure`
- **Cause:** Hybrid retrieval engine returned zero matching ground-truth segments

#### Question eq-25: "What was the final extended deadline for the NLP pipeline integration?"
- **Expected Answer:** `September 10th`
- **Generated Answer:** `According to the retrieved evidence: Action: Priya Sharma: I will own the database schema migration task. The deadline is set for next Friday, which is August 29th. (Owner: spk_priya, Status: In Progress) Action: Nisha Patel: I will own ...`
- **Failed Component:** `retrieval_failure`
- **Cause:** Hybrid retrieval engine returned zero matching ground-truth segments

#### Question eq-26: "How many times did the Redis timeout issue recur across sprints?"
- **Expected Answer:** `recurred`
- **Generated Answer:** `According to the retrieved evidence: Issue: Alex Rivera: We have a timeout issue in Redis cache that is causing connection failures. (Status: Resolved) Issue: Alex Rivera: I am tracking the Redis timeout issue, but it is still ongoing. (...`
- **Failed Component:** `answer_synthesis_failure`
- **Cause:** Answer synthesis failed to include exact expected keyphrases

#### Question eq-27: "Which authentication issue recurred twice during testing?"
- **Expected Answer:** `token expiry`
- **Generated Answer:** `According to the retrieved evidence: Issue: Alex Rivera: The pgvector extension for PostgreSQL has an open issue — embedding dimensions must match exactly. We encountered a dimension mismatch bug in staging and it caused a silent query f...`
- **Failed Component:** `answer_synthesis_failure`
- **Cause:** Answer synthesis failed to include exact expected keyphrases

#### Question eq-29: "How was the Redis timeout issue finally resolved?"
- **Expected Answer:** `circuit breaker`
- **Generated Answer:** `According to the retrieved evidence: Issue: Alex Rivera: We have a timeout issue in Redis cache that is causing connection failures. (Status: Resolved) Issue: Alex Rivera: I am tracking the Redis timeout issue, but it is still ongoing. (...`
- **Failed Component:** `answer_synthesis_failure`
- **Cause:** Answer synthesis failed to include exact expected keyphrases

#### Question eq-30: "How was the Kubernetes pod startup issue resolved?"
- **Expected Answer:** `multi-stage builds`
- **Generated Answer:** `According to the retrieved evidence: Issue: Alex Rivera: We have a timeout issue in Redis cache that is causing connection failures. (Status: Resolved) Issue: Alex Rivera: I am tracking the Redis timeout issue, but it is still ongoing. (...`
- **Failed Component:** `answer_synthesis_failure`
- **Cause:** Answer synthesis failed to include exact expected keyphrases

#### Question eq-31: "What was the cause of the JWT token expiry bug and how was it fixed?"
- **Expected Answer:** `milliseconds`
- **Generated Answer:** `According to the retrieved evidence: Issue: Rahul Verma: Agreed. Rahul Verma will investigate the Redis timeout root cause and report by Tuesday. (Status: Recurring) Issue: Rahul Verma: I investigated the Redis timeout issue. The root ca...`
- **Failed Component:** `answer_synthesis_failure`
- **Cause:** Answer synthesis failed to include exact expected keyphrases

#### Question eq-32: "On what date was the database schema migration completed and marked done?"
- **Expected Answer:** `August 29th`
- **Generated Answer:** `Based on the meeting records, the team evaluated MongoDB and PostgreSQL, and decided to adopt PostgreSQL with pgvector as the official database.`
- **Failed Component:** `retrieval_failure`
- **Cause:** Hybrid retrieval engine returned zero matching ground-truth segments

#### Question eq-33: "When was the Redis fix officially deployed?"
- **Expected Answer:** `September 3rd`
- **Generated Answer:** `According to the retrieved evidence: Decision: We need an API rate limiter. We decided to implement Redis-based rate limiting using the token bucket algorithm. Rahul Verma owns this task, due by September 8th. (Status: Approved) Decision...`
- **Failed Component:** `temporal_reasoning_failure`
- **Cause:** Temporal lifecycle reconciliation failed to order events

#### Question eq-34: "Was the Google Meet connector finished before or after September 20th?"
- **Expected Answer:** `September 18th`
- **Generated Answer:** `According to the retrieved evidence: Decision: Let's finalize the database. We decided to adopt PostgreSQL for MeetingOS since pgvector fits our needs better than MongoDB. (Status: Reversed) Decision: We decided to use Docker Compose for...`
- **Failed Component:** `retrieval_failure`
- **Cause:** Hybrid retrieval engine returned zero matching ground-truth segments

#### Question eq-36: "What connects the NLP entity extractor task to the spaCy adoption decision?"
- **Expected Answer:** `spaCy`
- **Generated Answer:** `According to the retrieved evidence: Decision: Let's finalize the database. We decided to adopt PostgreSQL for MeetingOS since pgvector fits our needs better than MongoDB. (Status: Reversed) Decision: We have decided to adopt PostgreSQL ...`
- **Failed Component:** `retrieval_failure`
- **Cause:** Hybrid retrieval engine returned zero matching ground-truth segments

#### Question eq-37: "Who worked across both Redis caching and rate limiting implementations?"
- **Expected Answer:** `Rahul Verma`
- **Generated Answer:** `According to the retrieved evidence: Decision: We have decided to adopt PostgreSQL as our primary database. The decision is final and replaces the earlier MongoDB evaluation. (Status: Approved) Decision: We need an API rate limiter. We d...`
- **Failed Component:** `graph_reasoning_failure`
- **Cause:** Graph service failed to bridge multi-hop entity relationships

#### Question eq-38: "Who are the joint owners of the data retention policy?"
- **Expected Answer:** `Rahul Verma and Priya Sharma`
- **Generated Answer:** `According to the retrieved evidence: Decision: Let's finalize the database. We decided to adopt PostgreSQL for MeetingOS since pgvector fits our needs better than MongoDB. (Status: Reversed) Decision: We have decided to adopt PostgreSQL ...`
- **Failed Component:** `graph_reasoning_failure`
- **Cause:** Graph service failed to bridge multi-hop entity relationships

