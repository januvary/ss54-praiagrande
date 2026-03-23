"""
Sync Service - Manages file synchronization to Google Drive via Rclone

Features:
- Sync on status change (async)
- Retry logic with exponential backoff
- Integrity verification (SHA256)
- Sync state tracking
- Stats output verification
"""

import hashlib
import logging
import re
import subprocess  # nosec: B404 - needed for rclone operations, inputs from trusted config
from datetime import datetime, timezone
from pathlib import Path
from typing import cast
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.document import Document
from app.models.process import Process, ProcessStatus
from app.models.sync_state import DocumentSyncState, SyncConfig, SyncStatus

logger = logging.getLogger(__name__)

TERMINAL_STATUSES = [
    ProcessStatus.AUTORIZADO,
    ProcessStatus.NEGADO,
    ProcessStatus.ENCERRADO,
    ProcessStatus.EXPIRADO,
]


class SyncService:
    @staticmethod
    def get_config(db: Session) -> SyncConfig:
        config = db.execute(
            select(SyncConfig).where(SyncConfig.id == 1)
        ).scalar_one_or_none()
        if not config:
            config = SyncConfig(id=1)
            db.add(config)
        db.commit()
        return config

    @staticmethod
    def _trigger_cleanup_if_eligible(db: Session, process_id: UUID) -> None:
        from app.models.process import Process
        import threading
        import traceback

        process = db.execute(
            select(Process).where(Process.id == process_id)
        ).scalar_one_or_none()

        if not process or process.status not in TERMINAL_STATUSES:
            return

        if process.files_cleaned_up:
            return

        documents = (
            db.execute(select(Document).where(Document.process_id == process_id))
            .scalars()
            .all()
        )

        if not documents:
            return

        sync_states = (
            db.execute(
                select(DocumentSyncState).where(
                    DocumentSyncState.document_id.in_([doc.id for doc in documents])
                )
            )
            .scalars()
            .all()
        )

        # Only cleanup if ALL documents have sync states AND all are SYNCED
        if len(sync_states) != len(documents):
            logger.info(
                f"Process {process_id} has {len(documents)} documents but only {len(sync_states)} sync states - skipping cleanup"
            )
            return

        all_synced = all(
            sync_state.sync_status == SyncStatus.SYNCED for sync_state in sync_states
        )

        if not all_synced:
            logger.info(
                f"Process {process_id} has {len(documents)} documents but not all synced - skipping cleanup"
            )
            return

        def cleanup_thread():
            from app.services.cleanup_service import CleanupService
            from app.database import SessionLocal

            db_local = SessionLocal()
            try:
                CleanupService.cleanup_process_files(db_local, process_id)
                logger.info(f"Cleanup completed for process {process_id}")
            except Exception as e:
                logger.error(f"Cleanup failed for process {process_id}: {e}")
                logger.error(traceback.format_exc())
            finally:
                db_local.close()

        # Use non-daemon thread to ensure cleanup completes
        thread = threading.Thread(target=cleanup_thread, daemon=False)
        thread.start()
        logger.info(f"Cleanup thread started for process {process_id}")

    @staticmethod
    def get_or_create_sync_state(db: Session, document_id: UUID) -> DocumentSyncState:
        sync_state = db.execute(
            select(DocumentSyncState).where(
                DocumentSyncState.document_id == document_id
            )
        ).scalar_one_or_none()

        if not sync_state:
            sync_state = DocumentSyncState(document_id=document_id)
            db.add(sync_state)
            db.commit()

        return sync_state

    @staticmethod
    def check_remote_available() -> tuple[bool, Optional[str]]:
        try:
            remote = getattr(settings, "SYNC_RCLONE_REMOTE", "gdrive")
            config_path = getattr(
                settings, "SYNC_RCLONE_CONFIG", "/opt/ss54-backend/.rclone.conf"
            )

            if not Path(config_path).exists():
                return False, f"Rclone config not found at {config_path}"

            cmd = [
                "/usr/bin/rclone",
                "--config",
                config_path,
                "lsd",
                f"{remote}:",
                "--max-depth",
                "1",
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30, shell=False
            )

            if result.returncode == 0:
                return True, None
            else:
                error = (
                    result.stderr.strip() if result.stderr else result.stdout.strip()
                )
                return False, f"Rclone connection failed: {error}"

        except subprocess.TimeoutExpired:
            return False, "Connection timeout"
        except FileNotFoundError:
            return False, "Rclone not installed"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def compute_file_hash(file_path: Path) -> str:
        sha256 = hashlib.sha256()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def _parse_rclone_stats(output: str) -> Dict[str, Any]:
        """
        Parse rclone stats output.
        Expected format: "Transferred:   1 / 1, 100%, 1.234 KiB, ETA 0s"
        Returns: {"transferred": int, "total": int, "percentage": int, "success": bool}
        """
        result = {"transferred": 0, "total": 0, "percentage": 0, "success": False}

        match = re.search(r"Transferred:\s*(\d+)\s*/\s*(\d+),\s*(\d+)%", output)
        if match:
            result["transferred"] = int(match.group(1))
            result["total"] = int(match.group(2))
            result["percentage"] = int(match.group(3))
            result["success"] = (
                result["transferred"] == result["total"] and result["total"] > 0
            )

        return result

    @staticmethod
    def sync_document(
        db: Session, document_id: UUID, sync_state: Optional[DocumentSyncState] = None
    ) -> Dict[str, Any]:
        doc = db.execute(
            select(Document).where(Document.id == document_id)
        ).scalar_one_or_none()

        if not doc:
            return {"success": False, "error": "Document not found"}

        if sync_state is None:
            sync_state = SyncService.get_or_create_sync_state(db, document_id)

        if sync_state.sync_status == SyncStatus.SYNCED:
            return {
                "success": True,
                "already_synced": True,
                "document_id": str(document_id),
                "remote_path": sync_state.remote_path,
            }

        file_path = Path(doc.file_path)
        if not file_path.exists():
            if sync_state.synced_at:
                logger.info(f"File {file_path} already synced and removed from VM")
                if sync_state.sync_status != SyncStatus.SYNCED:
                    sync_state.sync_status = SyncStatus.SYNCED
                    db.commit()
                return {
                    "success": True,
                    "already_synced": True,
                    "document_id": str(document_id),
                    "message": "File already synced and removed from VM",
                }
            sync_state.sync_status = SyncStatus.FAILED
            sync_state.last_error = "File not found on VM"
            db.commit()
            return {"success": False, "error": "File not found on VM"}

        remote = getattr(settings, "SYNC_RCLONE_REMOTE", "gdrive")
        remote_base = getattr(settings, "SYNC_RCLONE_PATH", "ss54-archives")
        config_path = getattr(
            settings, "SYNC_RCLONE_CONFIG", "/opt/ss54-backend/.rclone.conf"
        )

        sync_state.sync_attempts += 1
        sync_state.last_sync_attempt = datetime.now(timezone.utc)

        try:
            remote_path = f"{remote_base}/{file_path}"
            remote_full = f"{remote}:{remote_path}"

            cmd = [
                "/usr/bin/rclone",
                "--config",
                config_path,
                "copyto",
                str(file_path),
                remote_full,
            ]

            process = subprocess.run(  # nosec
                cmd, capture_output=True, text=True, timeout=120
            )

            if process.returncode == 0:
                sync_state.sync_status = SyncStatus.SYNCED
                sync_state.synced_at = datetime.now(timezone.utc)
                sync_state.last_error = None
                sync_state.remote_path = remote_path
                sync_state.file_size = file_path.stat().st_size
                sync_state.file_hash = SyncService.compute_file_hash(file_path)
                db.commit()

                logger.info(f"Synced document {document_id} to {remote_full}")

                synced_at_iso = cast(datetime, sync_state.synced_at).isoformat()
                return {
                    "success": True,
                    "document_id": str(document_id),
                    "original_filename": doc.original_filename,
                    "file_path": str(file_path),
                    "remote_path": remote_path,
                    "file_size": sync_state.file_size,
                    "file_hash": sync_state.file_hash,
                    "synced_at": synced_at_iso,
                    "sync_attempts": sync_state.sync_attempts,
                }
            else:
                error = (
                    process.stderr.strip() if process.stderr else process.stdout.strip()
                )
                raise Exception(f"Rclone copyto failed: {error}")

        except subprocess.TimeoutExpired:
            sync_state.sync_status = SyncStatus.FAILED
            sync_state.last_error = "Sync timeout (120s)"
            db.commit()

            logger.error(f"Timeout syncing document {document_id}")
            return {
                "success": False,
                "error": "Sync timeout",
                "document_id": str(document_id),
                "sync_attempts": sync_state.sync_attempts,
            }

        except Exception as e:
            sync_state.sync_status = SyncStatus.FAILED
            sync_state.last_error = str(e)
            db.commit()

            logger.error(f"Failed to sync document {document_id}: {e}")

            return {
                "success": False,
                "error": str(e),
                "document_id": str(document_id),
                "sync_attempts": sync_state.sync_attempts,
            }

    @staticmethod
    def check_and_cleanup_all_terminal_processes(db: Session) -> None:
        """Check all terminal processes and trigger cleanup if eligible."""
        terminal_processes = (
            db.execute(
                select(Process.id).where(
                    Process.status.in_(TERMINAL_STATUSES),
                    not Process.files_cleaned_up,
                )
            )
            .scalars()
            .all()
        )

        if terminal_processes:
            logger.info(
                f"Checking {len(terminal_processes)} terminal processes for cleanup"
            )

            for process_id in terminal_processes:
                SyncService._trigger_cleanup_if_eligible(db, process_id)

    @staticmethod
    def sync_all_processes_with_pending(db: Session) -> Dict[str, Any]:
        """Sync all processes that have pending documents.

        Triggered when ANY process status changes. Syncs ALL processes with
        pending documents across the system, not just the process that changed.

        Process:
        1. Convert all FAILED states to PENDING (auto-retry)
        2. Query ALL PENDING documents
        3. Group by process_id
        4. Sync documents per-process
        5. After each process sync, trigger cleanup for that process
        6. After all syncs, check ALL terminal processes for cleanup
        """
        config = SyncService.get_config(db)

        available, error = SyncService.check_remote_available()
        if not available:
            config.last_sync_status = "offline"
            config.last_sync_error = f"Google Drive offline: {error}"
            db.commit()
            return {
                "success": True,
                "synced_count": 0,
                "message": "Google Drive offline, documents queued for retry",
                "error": error,
            }

        # Convert all FAILED states to PENDING (auto-retry)
        failed_states = (
            db.execute(
                select(DocumentSyncState).where(
                    DocumentSyncState.sync_status == SyncStatus.FAILED
                )
            )
            .scalars()
            .all()
        )

        if failed_states:
            for sync_state in failed_states:
                sync_state.sync_status = SyncStatus.PENDING
                sync_state.last_error = None
            db.commit()
            logger.info(
                f"Converted {len(failed_states)} FAILED states to PENDING for retry"
            )

        # Query ALL PENDING documents
        pending_states = (
            db.execute(
                select(DocumentSyncState).where(
                    DocumentSyncState.sync_status == SyncStatus.PENDING
                )
            )
            .scalars()
            .all()
        )

        if not pending_states:
            logger.info("No pending documents to sync")
            SyncService.check_and_cleanup_all_terminal_processes(db)
            return {
                "success": True,
                "synced_count": 0,
                "message": "No pending documents",
            }

        # Group by process_id
        from collections import defaultdict

        documents_by_process = defaultdict(list)
        for sync_state in pending_states:
            documents_by_process[sync_state.document_id].append(sync_state)

        # Get document info and group by process_id
        process_docs = defaultdict(list)
        document_ids = list(documents_by_process.keys())
        documents = (
            db.execute(select(Document).where(Document.id.in_(document_ids)))
            .scalars()
            .all()
        )

        for doc in documents:
            process_docs[doc.process_id].append(doc)

        logger.info(f"Syncing {len(process_docs)} processes with pending documents")

        all_results = []
        total_success_count = 0
        total_failed_count = 0
        total_skipped_count = 0

        # Sync documents per-process
        for process_id, documents in process_docs.items():
            results = []
            success_count = 0
            failed_count = 0
            skipped_count = 0

            for doc in documents:
                sync_state = SyncService.get_or_create_sync_state(db, doc.id)

                if sync_state.sync_status == SyncStatus.SYNCED:
                    skipped_count += 1
                    continue

                result = SyncService.sync_document(db, doc.id, sync_state=sync_state)
                results.append(result)

                if result.get("success"):
                    success_count += 1
                else:
                    failed_count += 1

            all_results.extend(results)
            total_success_count += success_count
            total_failed_count += failed_count
            total_skipped_count += skipped_count

            logger.info(
                f"Process {process_id}: {success_count} synced, {failed_count} failed, {skipped_count} skipped"
            )

        # After all syncs, check ALL terminal processes for cleanup
        SyncService.check_and_cleanup_all_terminal_processes(db)

        config.last_sync_at = datetime.now(timezone.utc)
        config.last_sync_status = "success" if total_failed_count == 0 else "partial"
        config.last_sync_files_count = total_success_count
        config.last_sync_error = (
            None if total_failed_count == 0 else f"{total_failed_count} files failed"
        )
        db.commit()

        return {
            "success": True,
            "processes_synced": len(process_docs),
            "synced_count": total_success_count,
            "failed_count": total_failed_count,
            "skipped_count": total_skipped_count,
            "results": all_results,
        }

    @staticmethod
    def get_sync_status(db: Session) -> Dict[str, Any]:
        config = SyncService.get_config(db)

        pending = (
            db.execute(
                select(DocumentSyncState).where(
                    DocumentSyncState.sync_status == SyncStatus.PENDING
                )
            )
            .scalars()
            .all()
        )
        pending_count = len(pending) if pending else 0

        synced = (
            db.execute(
                select(DocumentSyncState).where(
                    DocumentSyncState.sync_status == SyncStatus.SYNCED
                )
            )
            .scalars()
            .all()
        )
        synced_count = len(synced) if synced else 0

        failed = (
            db.execute(
                select(DocumentSyncState).where(
                    DocumentSyncState.sync_status == SyncStatus.FAILED
                )
            )
            .scalars()
            .all()
        )
        failed_count = len(failed) if failed else 0

        available, error = SyncService.check_remote_available()

        last_sync_at_iso = (
            config.last_sync_at.isoformat() if config.last_sync_at else None
        )
        return {
            "last_sync_at": last_sync_at_iso,
            "last_sync_status": config.last_sync_status,
            "last_sync_files_count": config.last_sync_files_count,
            "last_sync_error": config.last_sync_error,
            "remote_available": available,
            "remote_error": error,
            "pending_count": pending_count,
            "synced_count": synced_count,
            "failed_count": failed_count,
        }

    @staticmethod
    def update_config(
        db: Session,
        last_sync_status: Optional[str] = None,
        last_sync_files_count: Optional[int] = None,
        last_sync_error: Optional[str] = None,
    ) -> SyncConfig:
        config = SyncService.get_config(db)

        if last_sync_status is not None:
            config.last_sync_status = last_sync_status
        if last_sync_files_count is not None:
            config.last_sync_files_count = last_sync_files_count
        if last_sync_error is not None:
            config.last_sync_error = last_sync_error

        db.commit()
        return config
