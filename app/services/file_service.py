"""
Serviço de Upload de Arquivos
Gerencia operações de E/S de arquivos: validação, MIME detection e armazenamento.
"""

import filetype  # type: ignore
import logging
from pathlib import Path
from typing import Tuple, Optional
from uuid import UUID
from fastapi import UploadFile
from sqlalchemy.orm import Session
from dataclasses import dataclass

from app.config import settings
from app.models.document import DocumentType
from app.utils.file_sanitization import sanitize_pdf, sanitize_filename
from app.services.image_processing import (
    convert_image_to_pdf,
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
