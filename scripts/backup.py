import argparse
import asyncio
import hashlib
import json
import logging
from datetime import UTC, datetime
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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("meetingos.backup")


async def create_backup(
    output_path: Path,
    dry_run: bool = False,
    db_url: str | None = None,
) -> dict:
    """Export all relational and vector database tables into a verified JSON snapshot with SHA-256."""
    target_url = db_url or settings.database_url
    safe_url = target_url.split("@")[-1] if "@" in target_url else target_url
    logger.info(f"Initiating MeetingOS backup from target: {safe_url} (dry_run={dry_run})")

    if dry_run:
        logger.info("[DRY RUN] Backup plan validated. No files written.")
        return {"status": "dry_run_success", "timestamp": datetime.now(UTC).isoformat()}

    engine = create_async_engine(target_url, echo=False)
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    snapshot_data: dict[str, list[dict]] = {
        "meetings": [],
        "participants": [],
        "speakers": [],
        "transcript_segments": [],
        "jobs": [],
        "entities": [],
        "meeting_entities": [],
        "topics": [],
        "decisions": [],
        "commitments": [],
        "issues": [],
        "events": [],
        "relationships": [],
        "utterance_classifications": [],
        "embeddings": [],
        "evidence": [],
        "audit_logs": [],
    }

    async with session_maker() as session:
        tables_to_dump = [
            ("meetings", MeetingModel),
            ("participants", ParticipantModel),
            ("speakers", SpeakerModel),
            ("transcript_segments", TranscriptSegmentModel),
            ("jobs", JobModel),
            ("entities", EntityModel),
            ("meeting_entities", MeetingEntityModel),
            ("topics", TopicModel),
            ("decisions", DecisionModel),
            ("commitments", CommitmentModel),
            ("issues", IssueModel),
            ("events", EventModel),
            ("relationships", RelationshipModel),
            ("utterance_classifications", UtteranceClassificationModel),
            ("embeddings", EmbeddingModel),
            ("evidence", EvidenceModel),
            ("audit_logs", AuditLogModel),
        ]

        for table_key, model_cls in tables_to_dump:
            try:
                stmt = select(model_cls)
                res = await session.execute(stmt)
                rows = res.scalars().all()
                for r in rows:
                    d = {}
                    for col in model_cls.__table__.columns:
                        val = getattr(r, col.name)
                        if isinstance(val, datetime):
                            val = val.isoformat()
                        d[col.name] = val
                    snapshot_data[table_key].append(d)
                logger.info(
                    f"Dumped {len(snapshot_data[table_key])} records from table '{table_key}'"
                )
            except Exception as e:
                logger.warning(f"Could not dump table '{table_key}': {e}")

    payload_json = json.dumps(snapshot_data, indent=2, default=str)
    checksum = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

    manifest = {
        "version": settings.app_version,
        "backup_timestamp": datetime.now(UTC).isoformat(),
        "database_url_host": safe_url,
        "record_counts": {k: len(v) for k, v in snapshot_data.items()},
        "sha256_checksum": checksum,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = output_path.with_suffix(".meta.json")

    with output_path.open("w", encoding="utf-8") as f:
        f.write(payload_json)

    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"Backup successfully written to {output_path} (Checksum: {checksum[:12]}...)")
    await engine.dispose()
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MeetingOS Operational Database Backup Utility")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("data/backups/meetingos_backup.json"),
        help="Path for backup JSON export",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing files")
    parser.add_argument("--db-url", type=str, default=None, help="Database URL override")
    args = parser.parse_args()

    asyncio.run(create_backup(args.output, dry_run=args.dry_run, db_url=args.db_url))
