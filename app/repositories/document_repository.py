"""
Document Repository - Centralized document query logic.

Eliminates repeated query patterns and ensures consistent eager loading
to prevent N+1 queries.
"""

from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from datetime import datetime

from app.models.document import Document, DocumentType, ValidationStatus


def get_document_by_id(db: Session, document_id: UUID) -> Optional[Document]:
    """
    Get document by ID with process eagerly loaded.

    Args:
        db: Database session
        document_id: Document UUID

    Returns:
        Document object with process loaded, or None if not found
    """
    return (
        db.query(Document)
        .options(joinedload(Document.process))
        .filter(Document.id == document_id)
        .first()
    )


def get_document_for_download(db: Session, document_id: UUID) -> Optional[Document]:
    """
    Get document by ID without eager loading (for download).
    Only needs file_path, so no eager loading needed.

    Args:
        db: Database session
        document_id: Document UUID

    Returns:
        Document object, or None if not found
    """
    return db.query(Document).filter(Document.id == document_id).first()


def get_combined_pdf_for_process(db: Session, process_id: UUID) -> Optional[Document]:
    """
    Get the combined PDF document for a process (if exists).

    Args:
        db: Database session
        process_id: Process UUID

    Returns:
        Document object if found, None otherwise
    """
    return (
        db.query(Document)
        .filter(
            Document.process_id == process_id,
            Document.document_type == DocumentType.PDF_COMBINADO,
        )
        .first()
    )


def get_combined_pdfs_for_processes(
    db: Session, process_ids: list[UUID]
) -> dict[UUID, Document]:
    """
    Batch fetch combined PDFs for multiple processes.

    Prevents N+1 query pattern when iterating over processes.

    Args:
        db: Database session
        process_ids: List of process UUIDs to fetch PDFs for

    Returns:
        Dict mapping process_id to combined PDF Document
    """
    if not process_ids:
        return {}

    pdfs = (
        db.query(Document)
        .filter(
            Document.process_id.in_(process_ids),
            Document.document_type == DocumentType.PDF_COMBINADO,
        )
        .all()
    )
    return {pdf.process_id: pdf for pdf in pdfs}


def delete_combined_pdfs_for_process(db: Session, process_id: UUID) -> None:
    """
    Delete all existing combined PDF documents for a process.

    Args:
        db: Database session
        process_id: Process UUID
    """
    combined_pdfs = (
        db.query(Document)
        .filter(
            Document.process_id == process_id,
            Document.document_type == DocumentType.PDF_COMBINADO,
        )
        .all()
    )
    for doc in combined_pdfs:
        db.delete(doc)
    db.flush()


def create_combined_pdf_document(
    db: Session,
    process_id: UUID,
    file_path: str,
    filename: str,
    file_size: int,
) -> Document:
    """
    Create a Document record for a combined PDF.

    Args:
        db: Database session
        process_id: Process UUID
        file_path: Path to the generated PDF file
        filename: Filename for the PDF
        file_size: Size of the PDF file in bytes

    Returns:
        The created Document object
    """
    combined_doc = Document(
        process_id=process_id,
        document_type=DocumentType.PDF_COMBINADO,
        original_filename=filename,
        stored_filename=filename,
        file_path=file_path,
        file_size=file_size,
        mime_type="application/pdf",
        validation_status=ValidationStatus.VALID,
        validated_at=datetime.now(),
        uploaded_at=datetime.now(),
    )
    db.add(combined_doc)
    db.flush()
    return combined_doc
