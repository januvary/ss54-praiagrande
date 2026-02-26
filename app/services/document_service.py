"""
Serviço de Documentos
Gerencia lógica de negócio de documentos: criação, deleção e validação.
"""

import logging
from typing import Union, Optional
from uuid import UUID
from datetime import datetime

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentType, ValidationStatus
from app.utils.uuid_utils import ensure_uuid
from app.utils.file_sanitization import sanitize_filename
from app.services.file_service import (
    save_file,
    delete_file,
)
from app.services.activity_service import log_activity
from app.repositories.process_repository import get_process_for_update
from app.repositories.document_repository import get_document_by_id
from app.constants.document_types import DOCUMENT_ID_TO_TYPE

logger = logging.getLogger(__name__)


def get_document_type_index(
    db: Session, process_id: UUID, document_type: DocumentType
) -> int:
    """
    Conta quantos documentos do mesmo tipo já existem para este processo.
    Retorna o próximo índice a ser usado (1-based).
    """
    from app.models.document import Document

    count = (
        db.query(Document)
        .filter(
            Document.process_id == process_id, Document.document_type == document_type
        )
        .count()
    )

    return count + 1


def create_document(
    db: Session,
    process_id: Union[str, UUID],
    document_type: DocumentType,
    file: UploadFile,
) -> Document:
    """
    Cria um registro de documento e salva o arquivo.
    """
    process_id = ensure_uuid(process_id)

    process = get_process_for_update(db, process_id)
    if not process:
        raise ValueError(f"Processo {process_id} não encontrado")

    patient_name = process.patient.name if process.patient else "unknown"
    protocol_number = process.protocol_number

    stored_filename, file_path, file_size, mime_type = save_file(
        db, file, process_id, document_type, patient_name, protocol_number
    )

    safe_filename = sanitize_filename(file.filename) if file.filename else "unknown"

    document = Document(
        process_id=process_id,
        document_type=document_type,
        original_filename=safe_filename,
        stored_filename=stored_filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type,
        validation_status=ValidationStatus.PENDING,
    )

    db.add(document)
    db.flush()
    return document


def delete_document(db: Session, document: Document) -> bool:
    """Deleta um registro de documento e seu arquivo."""
    delete_file(document.file_path)

    db.delete(document)
    db.flush()
    return True


def map_document_id_to_type(doc_id: int) -> DocumentType:
    """
    Mapeia o ID do documento do frontend para o enum DocumentType.

    Veja app/constants/document_types.py para mapeamento completo e documentação.
    """
    return DOCUMENT_ID_TO_TYPE.get(doc_id, DocumentType.OUTRO)


def update_document_validation(
    db: Session,
    document_id: UUID,
    status_str: str,
    notes: Optional[str] = None,
    activity_description: str = "Documento validado",
) -> Document:
    """Update document validation status with logging.

    Centralizes document validation logic to ensure consistent:
    - Status validation
    - Timestamp updates
    - Notes handling
    - Activity logging

    Args:
        db: Database session
        document_id: Document UUID
        status_str: New validation status as string
        notes: Optional validation notes
        activity_description: Custom description for activity log

    Returns:
        Updated Document object

    Raises:
        DocumentNotFoundError: If document not found
        ValueError: If status is invalid
    """
    document = get_document_by_id(db, document_id)
    if not document:
        raise DocumentNotFoundError(f"Documento não encontrado: {document_id}")

    try:
        new_status = ValidationStatus(status_str)
    except ValueError as e:
        raise ValueError(f"Status de validação inválido: {status_str}") from e

    old_status = document.validation_status.value
    document.validation_status = new_status
    document.validated_at = datetime.now()

    if notes is not None:
        document.validation_notes = notes if notes else None

    db.flush()

    log_activity(
        db,
        document.process_id,
        None,
        "document_validated",
        activity_description,
        {"old_status": old_status, "new_status": status_str},
        process=document.process,
    )

    return document


class DocumentNotFoundError(Exception):
    """Raised when a document cannot be found."""

    pass
