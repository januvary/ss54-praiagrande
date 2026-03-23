"""
Serviço de Upload de Arquivos
Gerencia operações de E/S de arquivos: validação, MIME detection e armazenamento.
"""

import filetype  # type: ignore
import logging
from pathlib import Path
from typing import Tuple, Optional, List
from uuid import UUID
from fastapi import UploadFile
from sqlalchemy.orm import Session
from dataclasses import dataclass

from app.config import settings
from app.models.document import DocumentType, Document, ValidationStatus
from app.utils.file_sanitization import sanitize_pdf, sanitize_filename
from app.services.image_processing import (
    convert_image_to_pdf,
    convert_image_to_pdf_async,
    ImageValidationError,
    ImageConversionError,
)
from app.services.storage_service import retry_file_operation

logger = logging.getLogger(__name__)


# Allowed MIME types for uploads
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}

# MIME type to extension mapping
MIME_TO_EXT = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


class FileValidationError(Exception):
    """Levantada quando a validação de arquivo falha."""

    pass


@dataclass
class ValidationResult:
    """Resultado da validação de arquivo."""

    is_valid: bool
    mime_type: Optional[str]
    error: Optional[str] = None


def _validate_file_content(content: bytes, file_size: int) -> ValidationResult:
    """
    Valida o conteúdo do arquivo em uma única passagem.

    Args:
        content: Bytes do conteúdo do arquivo
        file_size: Tamanho do arquivo em bytes

    Returns:
        ValidationResult com is_valid, mime_type e error
    """
    # Check file size
    if file_size > settings.MAX_FILE_SIZE:
        max_mb = settings.MAX_FILE_SIZE / (1024 * 1024)
        return ValidationResult(
            is_valid=False,
            mime_type=None,
            error=f"Arquivo muito grande. Tamanho máximo: {max_mb:.0f}MB",
        )

    # Detect MIME type (single detection)
    mime_type = detect_mime_type(content)
    if mime_type is None:
        return ValidationResult(
            is_valid=False,
            mime_type=None,
            error="Não foi possível identificar o tipo de arquivo",
        )

    if mime_type not in ALLOWED_MIME_TYPES:
        allowed = ", ".join(["PDF", "JPG", "PNG"])
        return ValidationResult(
            is_valid=False,
            mime_type=mime_type,
            error=f"Tipo de arquivo não permitido. Use: {allowed}",
        )

    return ValidationResult(is_valid=True, mime_type=mime_type)


def get_upload_dir() -> Path:
    """Retorna o caminho do diretório de upload, criando-o se necessário."""
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def get_process_upload_dir(patient_name: str, protocol_number: str) -> Path:
    """
    Retorna o diretório de upload para um processo específico.

    Nova estrutura: uploads/{patient_name}/{protocol_number}/
    """
    sanitized_patient = sanitize_filename(patient_name)
    upload_dir = get_upload_dir() / sanitized_patient / protocol_number
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def detect_mime_type(content: bytes) -> Optional[str]:
    """Detecta o tipo MIME do conteúdo do arquivo usando a biblioteca filetype."""
    kind = filetype.guess(content)
    if kind is None:
        return None
    return kind.mime


def get_file_extension(mime_type: str) -> str:
    """Retorna a extensão de arquivo a partir do tipo MIME."""
    return MIME_TO_EXT.get(mime_type, ".bin")


@retry_file_operation(
    max_retries=settings.STORAGE_RETRY_MAX_ATTEMPTS,
    retry_delay=settings.STORAGE_RETRY_DELAY,
)
def save_file(
    db: Session,
    file: UploadFile,
    process_id: UUID,
    document_type: DocumentType,
    patient_name: str,
    protocol_number: str,
) -> Tuple[str, str, int, str]:
    """
    Salva um arquivo enviado no disco.
    Retorna (stored_filename, file_path, file_size, mime_type).
    Levanta FileValidationError se a validação falhar.

    Nova estrutura: uploads/{patient_name}/{protocol_number}/{document_type}_{count}.pdf
    """
    content = file.file.read()
    file_size = len(content)

    # Single validation pass
    validation = _validate_file_content(content, file_size)
    if not validation.is_valid:
        raise FileValidationError(validation.error)

    mime_type = validation.mime_type

    # Sanitize file content based on type
    if mime_type == "application/pdf":
        content = sanitize_pdf(content)
        # Re-verify MIME type after sanitization
        detected = detect_mime_type(content)
        if detected != "application/pdf":
            raise FileValidationError("PDF inválido após sanitização")
        mime_type = detected

    elif mime_type in ("image/jpeg", "image/png"):
        try:
            # Convert image to PDF
            logger.info(f"Converting {mime_type} image to PDF")
            content = convert_image_to_pdf(content)
            mime_type = "application/pdf"
            logger.info("Image successfully converted to PDF")
        except (ImageValidationError, ImageConversionError) as e:
            # Image processing already provides good error messages
            raise FileValidationError(str(e))
    else:
        raise FileValidationError(f"Tipo MIME não suportado: {mime_type}")

    # Update file size after potential modification
    file_size = len(content)

    # Get document index for naming
    from app.services.document_service import get_document_type_index

    doc_index = get_document_type_index(db, process_id, document_type)

    # Generate filename: {document_type}_{index}.pdf
    stored_filename = (
        f"{document_type.value}_{doc_index}{get_file_extension(mime_type)}"
    )

    # Create process directory with new structure
    process_dir = get_process_upload_dir(patient_name, protocol_number)

    # Save file
    file_path = process_dir / stored_filename
    file_path.write_bytes(content)

    return stored_filename, str(file_path), file_size, mime_type


@retry_file_operation(
    max_retries=settings.STORAGE_RETRY_MAX_ATTEMPTS,
    retry_delay=settings.STORAGE_RETRY_DELAY,
)
def delete_file(file_path: str) -> bool:
    """Deleta um arquivo do disco."""
    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            return True
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(f"Failed to delete file {file_path}: {e}")
    return False


@dataclass
class StagedConversion:
    """Holds converted file in memory before atomic write."""

    document_type: DocumentType
    original_filename: str
    converted_bytes: bytes
    file_size: int
    file_extension: str


async def prepare_file_upload(
    db: Session,
    file: UploadFile,
    process_id: UUID,
    document_type: DocumentType,
    patient_name: str,
    protocol_number: str,
) -> StagedConversion:
    """
    Validate and convert file, but DON'T write to disk yet.

    Args:
        db: Database session
        file: UploadFile to process
        process_id: Process UUID
        document_type: Document type enum
        patient_name: Patient name for directory structure
        protocol_number: Protocol number for directory structure

    Returns:
        StagedConversion with converted bytes in memory

    Raises:
        FileValidationError: If validation or conversion fails
    """
    content = await file.read()
    file_size = len(content)

    validation = _validate_file_content(content, file_size)
    if not validation.is_valid:
        raise FileValidationError(validation.error)

    mime_type = validation.mime_type
    safe_filename = sanitize_filename(file.filename) if file.filename else "unknown"

    if mime_type == "application/pdf":
        content = sanitize_pdf(content)
        detected = detect_mime_type(content)
        if detected != "application/pdf":
            raise FileValidationError("PDF inválido após sanitização")
        mime_type = detected
        converted_bytes = content

    elif mime_type in ("image/jpeg", "image/png"):
        logger.info(f"Converting {mime_type} image to PDF (in memory)")
        converted_bytes = await convert_image_to_pdf_async(content)
        logger.info(f"Image converted to PDF: {len(converted_bytes)} bytes")
        mime_type = "application/pdf"

    else:
        raise FileValidationError(f"Tipo MIME não suportado: {mime_type}")

    return StagedConversion(
        document_type=document_type,
        original_filename=safe_filename,
        converted_bytes=converted_bytes,
        file_size=len(converted_bytes),
        file_extension=get_file_extension(mime_type),
    )


def save_converted_files_atomic(
    db: Session,
    process_id: UUID,
    staged_files: List[StagedConversion],
    patient_name: str,
    protocol_number: str,
) -> int:
    """
    Write all staged files to disk and create DB records atomically.

    ALL-OR-NOTHING: If any file write fails, delete all written files.
    Uses database transaction for DB records (auto-rollback on exception).

    Args:
        db: Database session
        process_id: Process UUID
        staged_files: List of StagedConversion objects
        patient_name: Patient name for directory structure
        protocol_number: Protocol number for directory structure

    Returns:
        Number of files saved

    Raises:
        Exception: If any operation fails (caller handles rollback)
    """
    saved_files = []

    try:
        for staged in staged_files:
            from app.services.document_service import get_document_type_index

            doc_index = get_document_type_index(db, process_id, staged.document_type)

            stored_filename = (
                f"{staged.document_type.value}_{doc_index}{staged.file_extension}"
            )

            process_dir = get_process_upload_dir(patient_name, protocol_number)
            file_path = process_dir / stored_filename
            file_path.write_bytes(staged.converted_bytes)
            saved_files.append(file_path)

            document = Document(
                process_id=process_id,
                document_type=staged.document_type,
                original_filename=staged.original_filename,
                stored_filename=stored_filename,
                file_path=str(file_path),
                file_size=staged.file_size,
                mime_type="application/pdf",
                validation_status=ValidationStatus.PENDING,
            )
            db.add(document)

        db.flush()
        return len(staged_files)

    except Exception as e:
        logger.error(
            f"Failed to save files atomically: {e}, cleaning up {len(saved_files)} files"
        )
        for file_path in saved_files:
            try:
                file_path.unlink()
                logger.info(f"Deleted partial file: {file_path}")
            except Exception as cleanup_error:
                logger.warning(
                    f"Failed to delete partial file {file_path}: {cleanup_error}"
                )
        raise
