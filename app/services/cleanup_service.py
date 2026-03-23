"""
Cleanup Service - Manages deletion of synced files from VM

Features:
- Only delete files from terminal-status processes
- Only delete if successfully synced
- Full audit trail
"""

import logging
import os

from pathlib import Path
from typing import List, Dict, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.process import Process
from app.models.sync_state import DocumentSyncState, SyncStatus
from app.services.sync_service import TERMINAL_STATUSES

logger = logging.getLogger(__name__)


class CleanupService:
    @staticmethod
    def get_cleanup_candidates(db: Session) -> List[Dict[str, Any]]:
        results = db.execute(
            select(
                Document.id,
                Document.file_path,
                Document.original_filename,
                Process.id.label("process_id"),
                Process.protocol_number,
                Process.terminal_status_since,
                DocumentSyncState.synced_at,
                DocumentSyncState.remote_path,
            )
            .select_from(Document)
            .join(Process, Document.process_id == Process.id)
            .join(DocumentSyncState, Document.id == DocumentSyncState.document_id)
            .where(Process.status.in_(TERMINAL_STATUSES))
            .where(DocumentSyncState.sync_status == SyncStatus.SYNCED)
            .where(Process.files_cleaned_up.is_(False))
        ).all()

        candidates = [
            {
                "document_id": row.id,
                "file_path": row.file_path,
                "original_filename": row.original_filename,
                "process_id": row.process_id,
                "protocol_number": row.protocol_number,
                "terminal_status_since": row.terminal_status_since,
                "synced_at": row.synced_at,
                "remote_path": row.remote_path,
            }
            for row in results
        ]

        return candidates

    @staticmethod
    def cleanup_document(db: Session, document_id: UUID) -> Dict[str, Any]:
        doc = db.execute(
            select(Document).where(Document.id == document_id)
        ).scalar_one_or_none()
        if not doc:
            return {"success": False, "error": "Document not found"}
        sync_state = db.execute(
            select(DocumentSyncState).where(
                DocumentSyncState.document_id == document_id
            )
        ).scalar_one_or_none()
        if not sync_state or sync_state.sync_status != SyncStatus.SYNCED:
            return {"success": False, "error": "Document not synced"}
        file_path = Path(doc.file_path)
        deleted = False
        error = None
        try:
            if file_path.exists():
                file_path.unlink()
                deleted = True
                logger.info(f"Deleted file: {file_path}")
            else:
                logger.warning(f"File already deleted: {file_path}")
                deleted = True
        except Exception as e:
            error = str(e)
            logger.error(f"Failed to delete file {file_path}: {e}")
        return {
            "success": deleted,
            "document_id": str(document_id),
            "file_path": str(file_path),
            "remote_path": sync_state.remote_path,
            "error": error,
        }

    @staticmethod
    def cleanup_process_files(db: Session, process_id: UUID) -> Dict[str, Any]:
        process = db.execute(
            select(Process).where(Process.id == process_id)
        ).scalar_one_or_none()
        if not process:
            return {"success": False, "error": "Process not found"}
        documents = (
            db.execute(
                select(Document)
                .where(Document.process_id == process_id)
                .join(DocumentSyncState)
            )
            .scalars()
            .all()
        )
        results = []
        directories_to_clean = set()
        for doc in documents:
            sync_state = db.execute(
                select(DocumentSyncState).where(DocumentSyncState.document_id == doc.id)
            ).scalar_one_or_none()

            if sync_state and sync_state.sync_status == SyncStatus.SYNCED:
                result = CleanupService.cleanup_document(db, doc.id)
                results.append(result)
                if doc.file_path:
                    directories_to_clean.add(Path(doc.file_path).parent)
            elif sync_state and sync_state.sync_status == SyncStatus.FAILED:
                sync_state.sync_status = SyncStatus.PENDING
                sync_state.last_error = None
                logger.info(f"Reset failed sync state for document {doc.id}")

        process.files_cleaned_up = True
        db.commit()

        for directory in directories_to_clean:
            if directory.exists() and not any(directory.iterdir()):
                try:
                    directory.rmdir()
                    logger.info(f"Removed empty directory: {directory}")
                except Exception as e:
                    logger.warning(f"Failed to remove directory {directory}: {e}")

        success_count = sum(1 for r in results if r.get("success"))
        return {
            "success": True,
            "process_id": str(process_id),
            "total_documents": len(documents),
            "cleaned": success_count,
            "results": results,
        }

    @staticmethod
    def run_scheduled_cleanup(db: Session) -> Dict[str, Any]:
        """Triggered automatically when processes reach terminal status and all docs synced"""
        candidates = CleanupService.get_cleanup_candidates(db)
        if not candidates:
            logger.info("No documents eligible for cleanup")
            return {
                "success": True,
                "candidates_found": 0,
                "cleaned": 0,
                "results": [],
            }
        logger.info(f"Found {len(candidates)} documents eligible for cleanup")
        results = []
        cleaned_count = 0
        errors = []
        cleaned_processes = set()
        for candidate in candidates:
            result = CleanupService.cleanup_document(db, candidate["document_id"])
            results.append(
                result
                | {
                    "protocol_number": candidate["protocol_number"],
                    "original_filename": candidate["original_filename"],
                }
            )
            if result.get("success"):
                cleaned_count += 1
                cleaned_processes.add(candidate["process_id"])
            else:
                errors.append(result.get("error"))
        for process_id in cleaned_processes:
            process = db.execute(
                select(Process).where(Process.id == process_id)
            ).scalar_one_or_none()
            if process:
                process.files_cleaned_up = True
        db.commit()
        logger.info(
            f"Cleanup complete: {cleaned_count}/{len(candidates)} files deleted"
        )
        return {
            "success": True,
            "candidates_found": len(candidates),
            "cleaned": cleaned_count,
            "errors": errors,
            "results": results,
        }

    @staticmethod
    def get_cleanup_stats(db: Session) -> Dict[str, Any]:
        pending_cleanup = (
            db.execute(
                select(Document)
                .join(Process)
                .join(DocumentSyncState)
                .where(Process.status.in_(TERMINAL_STATUSES))
                .where(DocumentSyncState.sync_status == SyncStatus.SYNCED)
                .where(Process.files_cleaned_up.is_(False))
            )
            .scalars()
            .all()
        )

        total_storage_bytes = 0
        for doc in pending_cleanup:
            if doc.file_path and Path(doc.file_path).exists():
                total_storage_bytes += os.path.getsize(doc.file_path)

        return {
            "pending_cleanup_count": len(pending_cleanup) if pending_cleanup else 0,
            "storage_reclaimable_bytes": total_storage_bytes,
            "storage_reclaimable_mb": round(total_storage_bytes / (1024 * 1024), 2),
        }
