from datetime import datetime
from typing import Any

from packages.common.enums import SourceType
from packages.common.models import EvidenceItem
from packages.memory.models import (
    EmbeddingModel,
    MeetingModel,
    TranscriptSegmentModel,
)
from packages.nlp.interfaces import BaseEmbedder
from packages.nlp.mock import MockEmbedder
from packages.retrieval.search import (
    STOP_WORDS,
    SYNONYMS,
    SearchCandidate,
    SearchResponse,
    cosine_similarity,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class KeywordSearchEngine:
    """Baseline A: Keyword/Lexical retrieval engine."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search(
        self,
        query: str,
        meeting_id: str | None = None,
        person: str | None = None,
        topic: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        result_type: str | None = None,
        limit: int = 10,
        offset: int = 0,
        **kwargs: Any,
    ) -> SearchResponse:
        query_clean = query.strip()
        _ = (person, topic, result_type, kwargs)
        raw_words = [t.lower().strip("?,.!") for t in query_clean.split() if len(t) > 1]
        content_words = [w for w in raw_words if w not in STOP_WORDS]
        query_terms: list[str] = []
        for w in content_words:
            if w in SYNONYMS:
                query_terms.extend(SYNONYMS[w])
            else:
                query_terms.append(w)

        m_stmt = select(MeetingModel)
        if meeting_id:
            m_stmt = m_stmt.where(MeetingModel.id == meeting_id)
        if start_date:
            m_stmt = m_stmt.where(MeetingModel.meeting_date >= start_date)
        if end_date:
            m_stmt = m_stmt.where(MeetingModel.meeting_date <= end_date)

        meetings_result = await self.session.execute(m_stmt)
        valid_meetings = {m.id: m for m in meetings_result.scalars().all()}
        valid_meeting_ids = set(valid_meetings.keys())

        if not valid_meeting_ids:
            return SearchResponse(query=query, total_results=0, results=[])

        seg_stmt = select(TranscriptSegmentModel).where(
            TranscriptSegmentModel.meeting_id.in_(valid_meeting_ids)
        )
        seg_rows = (await self.session.execute(seg_stmt)).scalars().all()

        candidates: list[SearchCandidate] = []
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

            if lexical_score > 0.0 or not query_clean:
                ev = EvidenceItem(
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
                        score=round(lexical_score, 4),
                        evidence=ev,
                    )
                )

        candidates.sort(key=lambda c: c.score, reverse=True)
        return SearchResponse(
            query=query,
            total_results=len(candidates),
            results=candidates[offset : offset + limit],
        )


class VectorSearchEngine:
    """Baseline B: Vector/Semantic retrieval engine."""

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
        limit: int = 10,
        offset: int = 0,
        **kwargs: Any,
    ) -> SearchResponse:
        query_clean = query.strip()
        _ = (person, topic, result_type, kwargs)
        query_embeddings = await self.embedder.embed([query_clean])
        q_vec = query_embeddings[0] if query_embeddings else []

        m_stmt = select(MeetingModel)
        if meeting_id:
            m_stmt = m_stmt.where(MeetingModel.id == meeting_id)
        if start_date:
            m_stmt = m_stmt.where(MeetingModel.meeting_date >= start_date)
        if end_date:
            m_stmt = m_stmt.where(MeetingModel.meeting_date <= end_date)

        meetings_result = await self.session.execute(m_stmt)
        valid_meetings = {m.id: m for m in meetings_result.scalars().all()}
        valid_meeting_ids = set(valid_meetings.keys())

        if not valid_meeting_ids:
            return SearchResponse(query=query, total_results=0, results=[])

        seg_stmt = select(TranscriptSegmentModel).where(
            TranscriptSegmentModel.meeting_id.in_(valid_meeting_ids)
        )
        seg_rows = (await self.session.execute(seg_stmt)).scalars().all()

        emb_stmt = select(EmbeddingModel).where(
            EmbeddingModel.meeting_id.in_(valid_meeting_ids),
            EmbeddingModel.source_type == "segment",
        )
        emb_rows = (await self.session.execute(emb_stmt)).scalars().all()
        emb_map = {e.source_id: e.embedding_json for e in emb_rows}

        candidates: list[SearchCandidate] = []
        for seg in seg_rows:
            m_info = valid_meetings[seg.meeting_id]
            vector_score = 0.0
            if seg.id in emb_map and q_vec:
                vector_score = cosine_similarity(q_vec, emb_map[seg.id])

            if vector_score > 0.0 or not query_clean:
                ev = EvidenceItem(
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
                        score=round(vector_score, 4),
                        evidence=ev,
                    )
                )

        candidates.sort(key=lambda c: c.score, reverse=True)
        return SearchResponse(
            query=query,
            total_results=len(candidates),
            results=candidates[offset : offset + limit],
        )
