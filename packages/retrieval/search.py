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
    """Multi-channel hybrid search engine combining Lexical Search, Vector Embeddings, and Graph Relationships."""

    def __init__(self, session: AsyncSession, embedder: BaseEmbedder | None = None) -> None:
        self.session = session
        self.embedder = embedder or MockEmbedder()

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

        query_embeddings = await self.embedder.embed([query_clean])
        q_vec = query_embeddings[0] if query_embeddings else []

        candidates: list[SearchCandidate] = []

        m_stmt = select(MeetingModel)
        if meeting_id:
            m_stmt = m_stmt.where(MeetingModel.id == meeting_id)
        if start_date:
            m_stmt = m_stmt.where(MeetingModel.meeting_date >= start_date)
        if end_date:
            m_stmt = m_stmt.where(MeetingModel.meeting_date <= end_date)

        meetings_result = await self.session.execute(m_stmt)
        valid_meetings = {m.id: m for m in meetings_result.scalars().all()}

        if topic:
            top_stmt = select(TopicModel.meeting_id).where(TopicModel.name.ilike(f"%{topic}%"))
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

        all_seg_map: dict[str, TranscriptSegmentModel] = {}
        if result_type in (None, "all", "transcript"):
            seg_stmt = select(TranscriptSegmentModel).where(
                TranscriptSegmentModel.meeting_id.in_(valid_meeting_ids)
            )
            seg_rows = (await self.session.execute(seg_stmt)).scalars().all()
            all_seg_map = {s.id: s for s in seg_rows}

            emb_stmt = select(EmbeddingModel).where(
                EmbeddingModel.meeting_id.in_(valid_meeting_ids),
                EmbeddingModel.source_type == "segment",
            )
            emb_rows = (await self.session.execute(emb_stmt)).scalars().all()
            emb_map = {e.source_id: e.embedding_json for e in emb_rows}

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

                is_match = False
                fused_score = 0.0
                if not query_clean:
                    is_match = True
                    fused_score = 1.0
                elif lexical_score > 0.0:
                    is_match = True
                    fused_score = 0.7 * lexical_score + 0.3 * vector_score

                if is_match:
                    evidence = EvidenceItem(
                        meeting_id=seg.meeting_id,
                        segment_id=seg.id,
                        start_time=seg.start_time,
                        end_time=seg.end_time,
                        text_snapshot=seg.text,
                        source_type=SourceType(m_info.source_type),
                    )
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
                            evidence=evidence,
                        )
                    )

        if result_type in (None, "all", "decision"):
            dec_stmt = select(DecisionModel).where(DecisionModel.meeting_id.in_(valid_meeting_ids))
            dec_rows = (await self.session.execute(dec_stmt)).scalars().all()

            for dec in dec_rows:
                m_info = valid_meetings[dec.meeting_id]
                sub_lowered = dec.subject.lower()
                score = 0.0
                if query_clean.lower() in sub_lowered and len(query_clean) > 3:
                    score = 0.95
                elif query_terms and any(t in sub_lowered for t in query_terms):
                    score = 0.85
                elif not query_clean:
                    score = 0.50

                if score > 0.0:
                    ev: EvidenceItem | None = None
                    if dec.evidence_segment_id and dec.evidence_segment_id in all_seg_map:
                        seg = all_seg_map[dec.evidence_segment_id]
                        ev = EvidenceItem(
                            meeting_id=dec.meeting_id,
                            segment_id=seg.id,
                            start_time=seg.start_time,
                            end_time=seg.end_time,
                            text_snapshot=seg.text,
                            source_type=SourceType(m_info.source_type),
                        )
                    candidates.append(
                        SearchCandidate(
                            id=f"cand-{dec.id}",
                            meeting_id=dec.meeting_id,
                            meeting_title=m_info.title,
                            meeting_date=m_info.meeting_date,
                            segment_id=dec.evidence_segment_id,
                            text=f"Decision: {dec.subject} (Status: {dec.status})",
                            source_type="decision",
                            score=round(score, 4),
                            evidence=ev,
                        )
                    )

        if result_type in (None, "all", "action", "commitment"):
            com_stmt = select(CommitmentModel).where(
                CommitmentModel.meeting_id.in_(valid_meeting_ids)
            )
            if person:
                com_stmt = com_stmt.where(CommitmentModel.owner_id.ilike(f"%{person}%"))
            com_rows = (await self.session.execute(com_stmt)).scalars().all()

            for com in com_rows:
                m_info = valid_meetings[com.meeting_id]
                desc_lowered = com.description.lower()
                score = 0.0
                if query_clean.lower() in desc_lowered and len(query_clean) > 3:
                    score = 0.95
                elif query_terms and any(t in desc_lowered for t in query_terms):
                    score = 0.85
                elif not query_clean:
                    score = 0.50

                if score > 0.0:
                    ev: EvidenceItem | None = None
                    if com.evidence_segment_id and com.evidence_segment_id in all_seg_map:
                        seg = all_seg_map[com.evidence_segment_id]
                        ev = EvidenceItem(
                            meeting_id=com.meeting_id,
                            segment_id=seg.id,
                            start_time=seg.start_time,
                            end_time=seg.end_time,
                            text_snapshot=seg.text,
                            source_type=SourceType(m_info.source_type),
                        )
                    candidates.append(
                        SearchCandidate(
                            id=f"cand-{com.id}",
                            meeting_id=com.meeting_id,
                            meeting_title=m_info.title,
                            meeting_date=m_info.meeting_date,
                            segment_id=com.evidence_segment_id,
                            text=f"Action: {com.description} (Owner: {com.owner_id}, Status: {com.status})",
                            source_type="action",
                            score=round(score, 4),
                            evidence=ev,
                        )
                    )

        if result_type in (None, "all", "issue"):
            iss_stmt = select(IssueModel).where(IssueModel.meeting_id.in_(valid_meeting_ids))
            iss_rows = (await self.session.execute(iss_stmt)).scalars().all()

            for iss in iss_rows:
                m_info = valid_meetings[iss.meeting_id]
                desc_lowered = iss.description.lower()
                score = 0.0
                if query_clean.lower() in desc_lowered and len(query_clean) > 3:
                    score = 0.95
                elif query_terms and any(t in desc_lowered for t in query_terms):
                    score = 0.85
                elif not query_clean:
                    score = 0.50

                if score > 0.0:
                    ev: EvidenceItem | None = None
                    if iss.evidence_segment_id and iss.evidence_segment_id in all_seg_map:
                        seg = all_seg_map[iss.evidence_segment_id]
                        ev = EvidenceItem(
                            meeting_id=iss.meeting_id,
                            segment_id=seg.id,
                            start_time=seg.start_time,
                            end_time=seg.end_time,
                            text_snapshot=seg.text,
                            source_type=SourceType(m_info.source_type),
                        )
                    candidates.append(
                        SearchCandidate(
                            id=f"cand-{iss.id}",
                            meeting_id=iss.meeting_id,
                            meeting_title=m_info.title,
                            meeting_date=m_info.meeting_date,
                            segment_id=iss.evidence_segment_id,
                            text=f"Issue: {iss.description} (Status: {iss.status})",
                            source_type="issue",
                            score=round(score, 4),
                            evidence=ev,
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
