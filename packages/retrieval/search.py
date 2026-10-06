import math
from datetime import datetime

from packages.common.enums import SourceType
from packages.common.models import EvidenceItem
from packages.memory.models import (
    CommitmentModel,
    DecisionModel,
    EmbeddingModel,
    IssueModel,
    MeetingModel,
    TopicModel,
    TranscriptSegmentModel,
)
from packages.nlp.interfaces import BaseEmbedder
from packages.nlp.mock import MockEmbedder
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two numeric vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2, strict=False))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm1 * norm2)))


class SearchCandidate(BaseModel):
    id: str
    meeting_id: str
    meeting_title: str
    meeting_date: datetime
    segment_id: str | None = None
    start_time: float | None = None
    end_time: float | None = None
    text: str
    source_type: str
    score: float
    evidence: EvidenceItem | None = None


class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: list[SearchCandidate] = Field(default_factory=list)


STOP_WORDS = {
    "a",
    "an",
    "the",
    "in",
    "on",
    "at",
    "to",
    "for",
    "with",
    "from",
    "into",
    "by",
    "about",
    "what",
    "which",
    "who",
    "whom",
    "whose",
    "when",
    "where",
    "why",
    "how",
    "did",
    "do",
    "does",
    "done",
    "have",
    "has",
    "had",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "our",
    "my",
    "your",
    "their",
    "we",
    "you",
    "they",
    "i",
    "he",
    "she",
    "it",
    "this",
    "that",
    "these",
    "those",
    "will",
    "would",
    "shall",
    "should",
    "can",
    "could",
    "may",
    "might",
    "must",
    "make",
    "made",
    "tell",
    "show",
    "give",
    "find",
    "get",
    "got",
    "all",
    "some",
}

SYNONYMS: dict[str, list[str]] = {
    "decision": [
        "decision",
        "decisions",
        "decide",
        "decided",
        "chose",
        "chosen",
        "adopt",
        "agreed",
    ],
    "decisions": [
        "decision",
        "decisions",
        "decide",
        "decided",
        "chose",
        "chosen",
        "adopt",
        "agreed",
    ],
    "action": [
        "action",
        "actions",
        "commit",
        "commitment",
        "assigned",
        "todo",
        "task",
        "migration",
        "finish",
    ],
    "actions": [
        "action",
        "actions",
        "commit",
        "commitment",
        "assigned",
        "todo",
        "task",
        "migration",
        "finish",
    ],
    "issue": ["issue", "issues", "problem", "bug", "timeout", "error", "failure"],
    "issues": ["issue", "issues", "problem", "bug", "timeout", "error", "failure"],
    "database": ["database", "db", "postgres", "postgresql", "mongodb", "mongo", "pgvector"],
    "redis": ["redis", "cache", "caching", "timeout"],
}


class HybridSearchEngine:
    """Multi-channel hybrid search engine combining lexical search, vector embeddings and facts.

    Must be instantiated with the authenticated user's ``org_id`` so all queries
    are scoped to a single tenant.  Tenants cannot retrieve each other's meetings,
    transcripts, decisions, or embeddings. Soft-deleted meetings are never returned.
    """

    # Minimum cosine similarity for a transcript segment to match on meaning alone
    SEMANTIC_MATCH_THRESHOLD = 0.45

    def __init__(
        self,
        session: AsyncSession,
        embedder: BaseEmbedder | None = None,
        org_id: str = "org_dev",
    ) -> None:
        if isinstance(embedder, str):
            org_id, embedder = embedder, None
        self.session = session
        self.org_id = org_id
        self.embedder = embedder or MockEmbedder()
        # The mock embedder produces arbitrary vectors; never let it match on its own
        self.semantic_matching = not isinstance(self.embedder, MockEmbedder)

    @staticmethod
    def _evidence(
        meeting_id: str, seg: TranscriptSegmentModel, m_info: MeetingModel
    ) -> EvidenceItem:
        return EvidenceItem(
            meeting_id=meeting_id,
            segment_id=seg.id,
            start_time=seg.start_time,
            end_time=seg.end_time,
            text_snapshot=seg.text,
            source_type=SourceType(m_info.source_type),
        )

    async def search(
        self,
        query: str,
        meeting_id: str | None = None,
        person: str | None = None,
        topic: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        result_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> SearchResponse:
        """Perform multi-channel hybrid search across organizational memory."""
        query_clean = query.strip()
        raw_words = [t.lower().strip("?,.!") for t in query_clean.split() if len(t) > 1]
        content_words = [w for w in raw_words if w not in STOP_WORDS]
        query_terms: list[str] = []
        for w in content_words:
            if w in SYNONYMS:
                query_terms.extend(SYNONYMS[w])
            else:
                query_terms.append(w)

        q_vec: list[float] = []
        if query_clean:
            query_embeddings = await self.embedder.embed([query_clean])
            q_vec = query_embeddings[0] if query_embeddings else []

        candidates: list[SearchCandidate] = []

        m_stmt = select(MeetingModel).where(
            MeetingModel.org_id == self.org_id, MeetingModel.deleted_at.is_(None)
        )
        if meeting_id:
            m_stmt = m_stmt.where(MeetingModel.id == meeting_id)
        if start_date:
            m_stmt = m_stmt.where(MeetingModel.meeting_date >= start_date)
        if end_date:
            m_stmt = m_stmt.where(MeetingModel.meeting_date <= end_date)

        meetings_result = await self.session.execute(m_stmt)
        valid_meetings = {m.id: m for m in meetings_result.scalars().all()}

        if topic and valid_meetings:
            top_stmt = select(TopicModel.meeting_id).where(
                TopicModel.name.ilike(f"%{topic}%"),
                TopicModel.meeting_id.in_(list(valid_meetings.keys())),
            )
            topic_meeting_ids = set((await self.session.execute(top_stmt)).scalars().all())
            title_matching_ids = {
                mid for mid, m in valid_meetings.items() if topic.lower() in m.title.lower()
            }
            matching_meeting_ids = topic_meeting_ids | title_matching_ids
            if matching_meeting_ids:
                valid_meetings = {
                    mid: m for mid, m in valid_meetings.items() if mid in matching_meeting_ids
                }

        valid_meeting_ids = set(valid_meetings.keys())

        if not valid_meeting_ids:
            return SearchResponse(query=query, total_results=0, results=[])

        # Transcript segments are needed both for transcript results and for the timestamps /
        # evidence of decision, action and issue results.
        seg_stmt = select(TranscriptSegmentModel).where(
            TranscriptSegmentModel.meeting_id.in_(valid_meeting_ids)
        )
        seg_rows = (await self.session.execute(seg_stmt)).scalars().all()
        all_seg_map: dict[str, TranscriptSegmentModel] = {s.id: s for s in seg_rows}

        if result_type in (None, "all", "transcript"):
            emb_stmt = select(EmbeddingModel.source_id, EmbeddingModel.embedding_json).where(
                EmbeddingModel.meeting_id.in_(valid_meeting_ids),
                EmbeddingModel.source_type == "segment",
            )
            emb_map = dict((await self.session.execute(emb_stmt)).tuples().all())

            for seg in seg_rows:
                m_info = valid_meetings[seg.meeting_id]
                text_lowered = seg.text.lower()

                lexical_score = 0.0
                if query_clean.lower() in text_lowered and len(query_clean) > 3:
                    lexical_score = 1.0
                elif query_terms:
                    matches = sum(1 for t in query_terms if t in text_lowered)
                    if matches > 0:
                        lexical_score = min(1.0, matches / max(1, len(content_words)))

                vector_score = 0.0
                if seg.id in emb_map and q_vec:
                    vector_score = cosine_similarity(q_vec, emb_map[seg.id])

                fused_score = 0.0
                if not query_clean:
                    fused_score = 1.0
                elif lexical_score > 0.0:
                    fused_score = 0.7 * lexical_score + 0.3 * vector_score
                elif self.semantic_matching and vector_score >= self.SEMANTIC_MATCH_THRESHOLD:
                    # Related wording without a shared keyword
                    fused_score = 0.5 * vector_score

                if fused_score > 0.0:
                    candidates.append(
                        SearchCandidate(
                            id=f"cand-{seg.id}",
                            meeting_id=seg.meeting_id,
                            meeting_title=m_info.title,
                            meeting_date=m_info.meeting_date,
                            segment_id=seg.id,
                            start_time=seg.start_time,
                            end_time=seg.end_time,
                            text=seg.text,
                            source_type="transcript",
                            score=round(fused_score, 4),
                            evidence=self._evidence(seg.meeting_id, seg, m_info),
                        )
                    )

        def fact_score(text: str) -> float:
            lowered = text.lower()
            if query_clean.lower() in lowered and len(query_clean) > 3:
                return 0.95
            if query_terms and any(t in lowered for t in query_terms):
                return 0.85
            if not query_clean:
                return 0.50
            return 0.0

        def fact_candidate(
            fact_id: str,
            fact_meeting_id: str,
            evidence_segment_id: str | None,
            text: str,
            kind: str,
            score: float,
        ) -> SearchCandidate:
            m_info = valid_meetings[fact_meeting_id]
            seg = all_seg_map.get(evidence_segment_id or "")
            return SearchCandidate(
                id=f"cand-{fact_id}",
                meeting_id=fact_meeting_id,
                meeting_title=m_info.title,
                meeting_date=m_info.meeting_date,
                segment_id=evidence_segment_id,
                start_time=seg.start_time if seg else None,
                end_time=seg.end_time if seg else None,
                text=text,
                source_type=kind,
                score=round(score, 4),
                evidence=self._evidence(fact_meeting_id, seg, m_info) if seg else None,
            )

        if result_type in (None, "all", "decision"):
            dec_rows = (
                (
                    await self.session.execute(
                        select(DecisionModel).where(DecisionModel.meeting_id.in_(valid_meeting_ids))
                    )
                )
                .scalars()
                .all()
            )
            for dec in dec_rows:
                score = fact_score(dec.subject)
                if score > 0.0:
                    candidates.append(
                        fact_candidate(
                            dec.id,
                            dec.meeting_id,
                            dec.evidence_segment_id,
                            f"Decision: {dec.subject} (Status: {dec.status})",
                            "decision",
                            score,
                        )
                    )

        if result_type in (None, "all", "action", "commitment"):
            com_stmt = select(CommitmentModel).where(
                CommitmentModel.meeting_id.in_(valid_meeting_ids)
            )
            if person:
                com_stmt = com_stmt.where(CommitmentModel.owner_id.ilike(f"%{person}%"))
            for com in (await self.session.execute(com_stmt)).scalars().all():
                score = fact_score(com.description)
                if score > 0.0:
                    candidates.append(
                        fact_candidate(
                            com.id,
                            com.meeting_id,
                            com.evidence_segment_id,
                            f"Action: {com.description} (Owner: {com.owner_id}, Status: {com.status})",
                            "action",
                            score,
                        )
                    )

        if result_type in (None, "all", "issue"):
            iss_rows = (
                (
                    await self.session.execute(
                        select(IssueModel).where(IssueModel.meeting_id.in_(valid_meeting_ids))
                    )
                )
                .scalars()
                .all()
            )
            for iss in iss_rows:
                score = fact_score(iss.description)
                if score > 0.0:
                    candidates.append(
                        fact_candidate(
                            iss.id,
                            iss.meeting_id,
                            iss.evidence_segment_id,
                            f"Issue: {iss.description} (Status: {iss.status})",
                            "issue",
                            score,
                        )
                    )

        candidates.sort(key=lambda c: c.score, reverse=True)
        total_count = len(candidates)
        paginated_results = candidates[offset : offset + limit]

        return SearchResponse(
            query=query,
            total_results=total_count,
            results=paginated_results,
        )
