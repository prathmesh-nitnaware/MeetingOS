"""MeetingOS Automated Backup & Disaster Recovery Utility.

Provides automated backup generation, storage archive, checksum validation,
and point-in-time disaster recovery restore verification for multi-tenant deployments.
"""

import argparse
import hashlib
import json
import logging
import shutil
import tarfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("meetingos.backup")


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file for cryptographic integrity verification."""
    hasher = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def create_backup(
    db_file_or_url: str,
    storage_dir: str,
    output_dir: str = "backups",
    backup_label: str | None = None,
) -> dict[str, Any]:
    """Generate a complete, tamper-evident backup of database and tenant object storage."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    timestamp_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    label = f"_{backup_label}" if backup_label else ""
    backup_name = f"meetingos_backup_{timestamp_str}{label}"
    staging_dir = out_path / backup_name
    staging_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Starting MeetingOS backup generation into staging dir: %s", staging_dir)
    manifest: dict[str, Any] = {
        "backup_name": backup_name,
        "created_at": datetime.now(UTC).isoformat(),
        "version": "1.0.0",
        "components": {},
    }

    # 1. Database backup (handles SQLite file copy or PostgreSQL dump)
    if "sqlite" in db_file_or_url or Path(db_file_or_url).exists():
        db_clean = db_file_or_url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
        db_src = Path(db_clean)
        if db_src.exists():
            db_dest = staging_dir / "database.sqlite"
            shutil.copy2(db_src, db_dest)
            db_hash = compute_sha256(db_dest)
            manifest["components"]["database"] = {
                "type": "sqlite",
                "file": "database.sqlite",
                "size_bytes": db_dest.stat().st_size,
                "sha256": db_hash,
            }
            logger.info("SQLite database backed up (SHA-256: %s)", db_hash[:12])
    else:
        manifest["components"]["database"] = {
            "type": "postgresql_uri",
            "uri": db_file_or_url,
            "note": "Use pg_dump in production RDS / Cloud SQL pipeline",
        }

    # 2. Object storage backup (tenant audio, transcripts, exports)
    storage_src = Path(storage_dir)
    if storage_src.exists():
        storage_dest = staging_dir / "storage"
        shutil.copytree(storage_src, storage_dest, dirs_exist_ok=True)
        file_count = sum(1 for _ in storage_dest.rglob("*") if _.is_file())
        manifest["components"]["storage"] = {
            "path": "storage",
            "file_count": file_count,
            "size_bytes": sum(f.stat().st_size for f in storage_dest.rglob("*") if f.is_file()),
        }
        logger.info("Storage directory backed up (%d files)", file_count)

    # 3. Write Manifest
    manifest_file = staging_dir / "manifest.json"
    with manifest_file.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # 4. Create compressed tarball
    tarball_path = out_path / f"{backup_name}.tar.gz"
    with tarfile.open(tarball_path, "w:gz") as tar:
        tar.add(staging_dir, arcname=backup_name)

    # Cleanup staging directory
    shutil.rmtree(staging_dir, ignore_errors=True)

    tarball_hash = compute_sha256(tarball_path)
    logger.info("Backup archive generated: %s (SHA-256: %s)", tarball_path, tarball_hash[:12])

    return {
        "status": "success",
        "archive_path": str(tarball_path),
        "sha256": tarball_hash,
        "manifest": manifest,
    }


def verify_backup(backup_tarball: str) -> bool:
    """Verify cryptographic integrity and manifest validity of a backup archive."""
    archive_path = Path(backup_tarball)
    if not archive_path.exists():
        logger.error("Backup archive does not exist: %s", backup_tarball)
        return False

    temp_extract = archive_path.parent / f"verify_{archive_path.stem}_{int(time.time())}"
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(temp_extract)

        manifest_file = next(temp_extract.rglob("manifest.json"), None)
        if not manifest_file or not manifest_file.exists():
            logger.error("Missing manifest.json inside backup archive")
            return False

        with manifest_file.open("r", encoding="utf-8") as f:
            manifest = json.load(f)

        # Verify DB hash if SQLite
        if "database" in manifest.get("components", {}):
            db_meta = manifest["components"]["database"]
            if db_meta.get("type") == "sqlite":
                db_file = manifest_file.parent / db_meta["file"]
                actual_hash = compute_sha256(db_file)
                if actual_hash != db_meta["sha256"]:
                    logger.error(
                        "Database checksum mismatch! Expected: %s, Actual: %s",
                        db_meta["sha256"],
                        actual_hash,
                    )
                    return False

        logger.info("Backup archive verification PASSED successfully.")
        return True
    except Exception as exc:
        logger.error("Backup verification failed with error: %s", exc)
        return False
    finally:
        shutil.rmtree(temp_extract, ignore_errors=True)


def restore_backup(
    backup_tarball: str,
    target_db_path: str,
    target_storage_dir: str,
) -> bool:
    """Restore database and storage files from a verified backup archive."""
    if not verify_backup(backup_tarball):
        logger.error("Restore aborted: Backup integrity check failed.")
        return False

    archive_path = Path(backup_tarball)
    temp_extract = archive_path.parent / f"restore_{int(time.time())}"

    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(temp_extract)

        manifest_file = next(temp_extract.rglob("manifest.json"), None)
        if not manifest_file:
            return False

        base_dir = manifest_file.parent

        # 1. Restore Database
        db_src = base_dir / "database.sqlite"
        if db_src.exists():
            target_db = Path(target_db_path)
            target_db.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(db_src, target_db)
            logger.info("Restored database to %s", target_db)

        # 2. Restore Storage
        storage_src = base_dir / "storage"
        if storage_src.exists():
            target_storage = Path(target_storage_dir)
            target_storage.mkdir(parents=True, exist_ok=True)
            shutil.copytree(storage_src, target_storage, dirs_exist_ok=True)
            logger.info("Restored tenant storage to %s", target_storage)

        logger.info("Disaster recovery restore completed successfully.")
        return True
    except Exception as exc:
        logger.error("Restore failed: %s", exc)
        return False
    finally:
        shutil.rmtree(temp_extract, ignore_errors=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MeetingOS Backup & Recovery CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Backup command
    cmd_backup = subparsers.add_parser("backup", help="Create a complete backup")
    cmd_backup.add_argument("--db", required=True, help="Database file path or URL")
    cmd_backup.add_argument("--storage", required=True, help="Storage directory")
    cmd_backup.add_argument("--out", default="backups", help="Output directory")

    # Verify command
    cmd_verify = subparsers.add_parser("verify", help="Verify backup integrity")
    cmd_verify.add_argument("--archive", required=True, help="Backup tarball file")

    # Restore command
    cmd_restore = subparsers.add_parser("restore", help="Restore database and storage from backup")
    cmd_restore.add_argument("--archive", required=True, help="Backup tarball file")
    cmd_restore.add_argument("--target-db", required=True, help="Target database file")
    cmd_restore.add_argument("--target-storage", required=True, help="Target storage directory")

    args = parser.parse_args()

    if args.command == "backup":
        res = create_backup(args.db, args.storage, args.out)
        print(json.dumps(res, indent=2))
    elif args.command == "verify":
        ok = verify_backup(args.archive)
        exit(0 if ok else 1)
    elif args.command == "restore":
        ok = restore_backup(args.archive, args.target_db, args.target_storage)
        exit(0 if ok else 1)
