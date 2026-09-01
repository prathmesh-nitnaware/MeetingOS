import argparse
import asyncio
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path

from apps.api.config import settings
from packages.memory.models import (
    AuditLogModel,
    CommitmentModel,
    DecisionModel,
    EmbeddingModel,
    EntityModel,
    EventModel,
    EvidenceModel,
    IssueModel,
    JobModel,
    MeetingEntityModel,
    MeetingModel,
    ParticipantModel,
    RelationshipModel,
    SpeakerModel,
    TopicModel,
    TranscriptSegmentModel,
    UtteranceClassificationModel,
)
from packages.memory.repository import init_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("meetingos.restore")


async def restore_backup(
    input_path: Path,
    dry_run: bool = False,
    db_url: str | None = None,
) -> dict:
    """Validate snapshot checksum and safely restore tables into database."""
    if not input_path.exists():
        raise FileNotFoundError(f"Backup file not found: {input_path}")

    target_url = db_url or settings.database_url
    safe_url = target_url.split("@")[-1] if "@" in target_url else target_url

    # Checksum validation
    with input_path.open("r", encoding="utf-8") as f:
        content = f.read()

    calculated_checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
    manifest_path = input_path.with_suffix(".meta.json")
    if manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8") as f:
            manifest = json.load(f)
        expected_checksum = manifest.get("sha256_checksum")
        if expected_checksum and expected_checksum != calculated_checksum:
            raise ValueError(
                f"Backup checksum mismatch! Expected: {expected_checksum}, Calculated: {calculated_checksum}"
            )
        logger.info(f"Verified backup checksum: {calculated_checksum[:12]}...")

    data = json.loads(content)
    counts = {k: len(v) for k, v in data.items()}
    logger.info(f"Loaded backup archive with records: {counts}")

    if dry_run:
        logger.info(
            f"[DRY RUN] Verified backup integrity for {safe_url}. No database writes executed."
        )
        return {"status": "dry_run_success", "records": counts}

    engine = create_async_engine(target_url, echo=False)
    await init_db(engine)
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as session:
        # Ingest meetings
        for m_data in data.get("meetings", []):
            if "meeting_date" in m_data and isinstance(m_data["meeting_date"], str):
                m_data["meeting_date"] = datetime.fromisoformat(m_data["meeting_date"])
            if "created_at" in m_data and isinstance(m_data["created_at"], str):
                m_data["created_at"] = datetime.fromisoformat(m_data["created_at"])
            if "updated_at" in m_data and isinstance(m_data["updated_at"], str):
                m_data["updated_at"] = datetime.fromisoformat(m_data["updated_at"])
            session.add(MeetingModel(**m_data))

        # Ingest participants
        for p_data in data.get("participants", []):
            session.add(ParticipantModel(**p_data))

        # Ingest speakers
        for s_data in data.get("speakers", []):
            session.add(SpeakerModel(**s_data))

        # Ingest segments
        for seg_data in data.get("transcript_segments", []):
            if "created_at" in seg_data and isinstance(seg_data["created_at"], str):
                seg_data["created_at"] = datetime.fromisoformat(seg_data["created_at"])
            session.add(TranscriptSegmentModel(**seg_data))

        # Ingest jobs
        for j_data in data.get("jobs", []):
            if "created_at" in j_data and isinstance(j_data["created_at"], str):
                j_data["created_at"] = datetime.fromisoformat(j_data["created_at"])
            if "updated_at" in j_data and isinstance(j_data["updated_at"], str):
                j_data["updated_at"] = datetime.fromisoformat(j_data["updated_at"])
            session.add(JobModel(**j_data))

        # Ingest entities
        for ent_data in data.get("entities", []):
            if "created_at" in ent_data and isinstance(ent_data["created_at"], str):
                ent_data["created_at"] = datetime.fromisoformat(ent_data["created_at"])
            session.add(EntityModel(**ent_data))

        # Ingest meeting entities
        for me_data in data.get("meeting_entities", []):
            if "created_at" in me_data and isinstance(me_data["created_at"], str):
                me_data["created_at"] = datetime.fromisoformat(me_data["created_at"])
            session.add(MeetingEntityModel(**me_data))

        # Ingest topics
        for top_data in data.get("topics", []):
            if "created_at" in top_data and isinstance(top_data["created_at"], str):
                top_data["created_at"] = datetime.fromisoformat(top_data["created_at"])
            session.add(TopicModel(**top_data))

        # Ingest decisions
        for dec_data in data.get("decisions", []):
            if "created_at" in dec_data and isinstance(dec_data["created_at"], str):
                dec_data["created_at"] = datetime.fromisoformat(dec_data["created_at"])
            if "updated_at" in dec_data and isinstance(dec_data["updated_at"], str):
                dec_data["updated_at"] = datetime.fromisoformat(dec_data["updated_at"])
            session.add(DecisionModel(**dec_data))

        # Ingest commitments
        for com_data in data.get("commitments", []):
            if "original_deadline" in com_data and isinstance(com_data["original_deadline"], str):
                com_data["original_deadline"] = datetime.fromisoformat(
                    com_data["original_deadline"]
                )
            if "current_deadline" in com_data and isinstance(com_data["current_deadline"], str):
                com_data["current_deadline"] = datetime.fromisoformat(com_data["current_deadline"])
            if "created_at" in com_data and isinstance(com_data["created_at"], str):
                com_data["created_at"] = datetime.fromisoformat(com_data["created_at"])
            session.add(CommitmentModel(**com_data))

        # Ingest issues
        for iss_data in data.get("issues", []):
            if "first_detected_at" in iss_data and isinstance(iss_data["first_detected_at"], str):
                iss_data["first_detected_at"] = datetime.fromisoformat(
                    iss_data["first_detected_at"]
                )
            if "last_mentioned_at" in iss_data and isinstance(iss_data["last_mentioned_at"], str):
                iss_data["last_mentioned_at"] = datetime.fromisoformat(
                    iss_data["last_mentioned_at"]
                )
            if "created_at" in iss_data and isinstance(iss_data["created_at"], str):
                iss_data["created_at"] = datetime.fromisoformat(iss_data["created_at"])
            session.add(IssueModel(**iss_data))

        # Ingest events
        for ev_data in data.get("events", []):
            if "occurred_at" in ev_data and isinstance(ev_data["occurred_at"], str):
                ev_data["occurred_at"] = datetime.fromisoformat(ev_data["occurred_at"])
            if "created_at" in ev_data and isinstance(ev_data["created_at"], str):
                ev_data["created_at"] = datetime.fromisoformat(ev_data["created_at"])
            session.add(EventModel(**ev_data))

        # Ingest relationships
        for rel_data in data.get("relationships", []):
            if "created_at" in rel_data and isinstance(rel_data["created_at"], str):
                rel_data["created_at"] = datetime.fromisoformat(rel_data["created_at"])
            session.add(RelationshipModel(**rel_data))

        # Ingest utterance classifications
        for uc_data in data.get("utterance_classifications", []):
            if "created_at" in uc_data and isinstance(uc_data["created_at"], str):
                uc_data["created_at"] = datetime.fromisoformat(uc_data["created_at"])
            session.add(UtteranceClassificationModel(**uc_data))

        # Ingest embeddings
        for emb_data in data.get("embeddings", []):
            if "created_at" in emb_data and isinstance(emb_data["created_at"], str):
                emb_data["created_at"] = datetime.fromisoformat(emb_data["created_at"])
            session.add(EmbeddingModel(**emb_data))

        # Ingest evidence
        for ev_item in data.get("evidence", []):
            if "created_at" in ev_item and isinstance(ev_item["created_at"], str):
                ev_item["created_at"] = datetime.fromisoformat(ev_item["created_at"])
            session.add(EvidenceModel(**ev_item))

        # Ingest audit logs
        for al_data in data.get("audit_logs", []):
            if "timestamp" in al_data and isinstance(al_data["timestamp"], str):
                al_data["timestamp"] = datetime.fromisoformat(al_data["timestamp"])
            session.add(AuditLogModel(**al_data))

        await session.commit()

    logger.info(f"Database successfully restored from {input_path}")
    await engine.dispose()
    return {"status": "restore_success", "records_restored": counts}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MeetingOS Operational Database Restore Utility")
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        required=True,
        help="Path of backup JSON file to restore",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate without restoring database"
    )
    parser.add_argument("--db-url", type=str, default=None, help="Database URL override")
    args = parser.parse_args()

    asyncio.run(restore_backup(args.input, dry_run=args.dry_run, db_url=args.db_url))
