"""
Serviço de Geração de PDF
Gerencia geração de PDFs combinados para processos completos.

Architecture:
- PDFValidator: Validates source PDF files before merging
- PDFMerger: Handles PDF merging operations using pikepdf
- Module-level functions: Public API for PDF generation

Module-level aliases are provided for backward compatibility:
- generate_combined_pdf = generate_for_process
- ensure_combined_pdf = ensure_for_process
"""

import os
import logging
import operator
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.models.document import Document, ValidationStatus, DocumentType
from app.models.process import Process
from app.services.activity_service import log_activity
from app.services.file_service import delete_file
from app.services.storage_service import retry_file_operation
from app.utils.file_sanitization import sanitize_filename
from app.utils.file_utils import file_exists
from app.repositories.process_repository import (
    get_process_with_patient_and_documents,
    get_processes_by_statuses,
)
from app.repositories.document_repository import (
    get_combined_pdf_for_process,
    delete_combined_pdfs_for_process,
    create_combined_pdf_document,
)
from app.content import PROCESS_TYPE_TITLES

logger = logging.getLogger(__name__)


class PDFGenerationError(Exception):
    """Base exception for PDF generation failures."""

    pass


class PDFMergeError(PDFGenerationError):
    """Raised when PDF merging fails."""

    pass


class PDFFileNotFoundError(PDFGenerationError):
    """Raised when source PDF file is missing."""

    pass


class PDFNoDocumentsError(PDFGenerationError):
    """Raised when no valid documents are available for PDF generation."""

    pass


DOCUMENT_TYPE_ORDER = [
    "formulario",
    "declaracao",
    "receita",
    "relatorio",
    "documento_pessoal",
    "exame",
]


@dataclass
class PDFEnsureResult:
    """
    Result of ensuring a combined PDF exists for a process.

    Attributes:
        pdf: The PDF Document object if available, None if skipped/failed
        generated: True if PDF was just created (didn't exist before)
        skipped: True if process was skipped (e.g., no valid documents)
        skip_reason: Reason for skipping if skipped=True
        error: Exception that occurred during processing, if any
    """

    pdf: Optional[Document] = None
    generated: bool = False
    skipped: bool = False
    skip_reason: Optional[str] = None
    error: Optional[Exception] = None

    @property
    def exists(self) -> bool:
        """True if PDF is available (existed or was generated)."""
        return self.pdf is not None


class PDFValidator:
    """
    Validates PDF files and document collections before merging.

    Checks:
    - Document validation status
    - File existence
    - Document type ordering
    """

    @staticmethod
    def get_doc_order(doc: Document) -> int:
        """Get sort order for document by type."""
        try:
            return DOCUMENT_TYPE_ORDER.index(doc.document_type.value)
        except ValueError:
            return len(DOCUMENT_TYPE_ORDER)

    @staticmethod
    def get_valid_documents(process: Process) -> Optional[List[Document]]:
        """
        Get and sort valid documents for PDF generation.

        Returns:
            List of valid documents sorted by type, or None if no valid documents found
        """
        valid_documents = [
            doc
            for doc in process.documents
            if doc.validation_status == ValidationStatus.VALID
            and doc.document_type.value in DOCUMENT_TYPE_ORDER
        ]

        admin_documents = [
            doc
            for doc in process.documents
            if doc.document_type == DocumentType.OUTRO
            and doc.validation_status == ValidationStatus.VALID
        ]

        valid_documents.extend(admin_documents)

        if not valid_documents:
            return None

        valid_documents.sort(key=PDFValidator.get_doc_order)
        return valid_documents


class PDFMerger:
    """
    Handles PDF merging operations using pikepdf.

    Provides methods to merge multiple PDF documents into a single file
    with retry logic for resilience on remote storage.
    """

    @staticmethod
    @retry_file_operation(
        max_retries=settings.STORAGE_RETRY_MAX_ATTEMPTS,
        retry_delay=settings.STORAGE_RETRY_DELAY,
    )
    def merge_documents(documents: List[Document], output_path: Path) -> bool:
        """
        Merge multiple document PDFs into a single PDF file.

        Uses retry_file_operation decorator for resilience on remote storage.

        Args:
            documents: List of Document objects to merge
            output_path: Path where the combined PDF will be saved

        Returns:
            True if successful, False otherwise

        Raises:
            StorageRetryableError: After max retries exceeded (from decorator)
        """
        try:
            import pikepdf
        except ImportError:
            logger.error("Biblioteca pikepdf não disponível")
            return False

        try:
            with pikepdf.new() as combined_pdf:
                for doc in documents:
                    doc_path = Path(doc.file_path)
                    if not doc_path.exists():
                        logger.warning(
                            f"Arquivo de documento não encontrado: {doc.file_path}"
                        )
                        continue

                    try:
                        with pikepdf.open(doc.file_path) as src_pdf:
                            for page in src_pdf.pages:
                                combined_pdf.pages.append(page)
                            doc_type_label = doc.document_type.value
                            logger.info(f"Added {doc_type_label} to combined PDF")
                    except Exception as e:
                        logger.error(f"Erro ao adicionar documento {doc.id}: {e}")
                        continue

                combined_pdf.save(str(output_path))
                logger.info(f"PDF successfully saved to {output_path}")

            if not output_path.exists():
                logger.error(
                    f"Arquivo PDF não criado em {output_path} após pikepdf.save()"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Erro ao mesclar documentos em PDF: {e}")
            return False


def _delete_old_combined_pdfs(process: Process, combined_pdfs: List[Document]) -> None:
    """
    Delete physical files and database records for old combined PDFs.

    Uses delete_file from file_service which has built-in retry logic.

    Args:
        process: Process object
        combined_pdfs: List of combined PDF documents to delete
    """
    for old_doc in combined_pdfs:
        logger.info(
            f"Deleting old combined PDF (ID: {old_doc.id}) for process {process.id}"
        )
        if delete_file(old_doc.file_path):
            logger.info(f"Deleted old PDF file: {old_doc.file_path}")
        else:
            logger.warning(f"Failed to delete old PDF file: {old_doc.file_path}")


def _generate_pdf_filename(process: Process) -> str:
    """
    Generate filename for combined PDF.

    Args:
        process: Process object

    Returns:
        Generated filename
    """
    patient_name = (
        sanitize_filename(process.patient.name)
        if process.patient.name
        else "Desconhecido"
    )
    process_type_label = PROCESS_TYPE_TITLES.get(process.type.value, process.type.value)
    return f"{patient_name} - {process_type_label}.pdf"


def get_generated_pdfs_dir() -> Path:
    """Retorna o diretório para PDFs combinados gerados."""
    upload_dir = Path(settings.UPLOAD_DIR)
    generated_dir = upload_dir / "generated_pdfs"
    generated_dir.mkdir(parents=True, exist_ok=True)
    return generated_dir


def generate_combined_pdf(db: Session, process_id: UUID) -> Optional[str]:
    """
    Gera um PDF combinado para um processo contendo todos os documentos válidos.

    Esta função:
    1. Busca o processo com documentos
    2. Remove PDFs combinados existentes
    3. Filtra e ordena documentos válidos
    4. Mescla documentos em um único PDF
    5. Cria registro no banco de dados
    6. Registra atividade

    Args:
        db: Sessão do banco de dados
        process_id: UUID do processo

    Returns:
        Caminho para o arquivo PDF gerado, ou None se a geração falhou
    """
    process = get_process_with_patient_and_documents(db, process_id)
    if not process:
        logger.error(f"Processo {process_id} não encontrado")
        return None

    existing_combined_pdfs = [
        doc
        for doc in process.documents
        if doc.document_type == DocumentType.PDF_COMBINADO
    ]
    _delete_old_combined_pdfs(process, existing_combined_pdfs)

    if existing_combined_pdfs:
        delete_combined_pdfs_for_process(db, process_id)

    valid_documents = PDFValidator.get_valid_documents(process)
    if not valid_documents:
        logger.warning(
            f"Nenhum documento válido encontrado para o processo {process_id}"
        )
        return None

    filename = _generate_pdf_filename(process)
    output_path = get_generated_pdfs_dir() / filename

    admin_count = len(
        [doc for doc in valid_documents if doc.document_type == DocumentType.OUTRO]
    )

    if not PDFMerger.merge_documents(valid_documents, output_path):
        return None

    file_size = output_path.stat().st_size
    combined_doc = create_combined_pdf_document(
        db, process.id, str(output_path), filename, file_size
    )

    log_message = f"PDF combinado gerado com {len(valid_documents)} documentos (documento ID: {combined_doc.id})"
    if admin_count > 0:
        log_message += (
            f" ({admin_count} documento{'s' if admin_count > 1 else ''} da equipe)"
        )
    log_activity(
        db,
        process_id,
        None,
        "pdf_generated",
        log_message,
        process=process,
    )

    logger.info(f"Successfully generated combined PDF: {output_path}")
    return str(output_path)


def ensure_combined_pdf(db: Session, process_id: UUID) -> PDFEnsureResult:
    """
    Ensure a combined PDF exists for a process.

    Handles:
    - Checking for existing PDF record
    - Verifying file exists (handles stale data by letting generate_combined_pdf delete old records)
    - Generating PDF if missing
    - Skipping if no valid documents

    Note: This function only flushes the database. Caller is responsible for committing.

    Args:
        db: Database session
        process_id: Process UUID

    Returns:
        PDFEnsureResult with status information
    """
    combined_pdf = get_combined_pdf_for_process(db, process_id)

    if combined_pdf:
        if not file_exists(combined_pdf.file_path):
            logger.info(
                f"PDF file missing for process {process_id}, marking for regeneration"
            )
            combined_pdf = None
        else:
            logger.info(f"PDF already exists for process {process_id}")
            return PDFEnsureResult(pdf=combined_pdf, generated=False, skipped=False)

    logger.info(f"Generating combined PDF for process {process_id}")
    pdf_path = generate_combined_pdf(db, process_id)

    if pdf_path:
        combined_pdf = get_combined_pdf_for_process(db, process_id)
        if combined_pdf:
            logger.info(f"Successfully generated PDF for process {process_id}")
            return PDFEnsureResult(pdf=combined_pdf, generated=True, skipped=False)

    logger.warning(
        f"Could not generate PDF for process {process_id} "
        f"(no valid documents or generation error)"
    )
    return PDFEnsureResult(
        pdf=None, generated=False, skipped=True, skip_reason="no_valid_docs"
    )


def ensure_combined_pdfs_batch(
    db: Session, process_ids: List[UUID]
) -> Dict[UUID, PDFEnsureResult]:
    """
    Ensure combined PDFs exist for multiple processes.

    Efficiently batch-processes PDF generation with shared logic.

    Note: This function only flushes the database. Caller is responsible for committing.

    Args:
        db: Database session
        process_ids: List of process UUIDs

    Returns:
        Dict mapping process_id to PDFEnsureResult
    """
    results: Dict[UUID, PDFEnsureResult] = {}

    for process_id in process_ids:
        results[process_id] = ensure_combined_pdf(db, process_id)

    generated_count = sum(1 for r in results.values() if r.generated)
    skipped_count = sum(1 for r in results.values() if r.skipped)
    existing_count = sum(1 for r in results.values() if r.exists and not r.generated)

    logger.info(
        f"PDF ensure batch complete: {existing_count} existing, "
        f"{generated_count} generated, {skipped_count} skipped"
    )

    return results


def batch_generate_pdfs(db: Session, force_regenerate: bool = False) -> List[Dict]:
    """
    Gera PDFs combinados para todos os processos com status "completo".

    Args:
        db: Sessão do banco de dados
        force_regenerate: Se True, regera todos os PDFs mesmo que já existam.
                          Se False (padrão), apenas gera PDFs que não existem
                          ou que têm arquivos corrompidos (stale data).

    Returns:
        Lista de dicionários com informações dos PDFs gerados:
        [{
            'process_id': UUID,
            'protocol': str,
            'patient_name': str,
            'filename': str,
            'pdf_path': str,
            'file_size': int,
            'generated_at': datetime
        }]
    """
    from datetime import datetime

    processes = get_processes_by_statuses(db, ["completo"])
    results = []

    for process in processes:
        logger.info(f"Generating PDF for process {process.protocol_number}")

        if force_regenerate:
            pdf_path = generate_combined_pdf(db, process.id)
        else:
            result = ensure_combined_pdf(db, process.id)
            pdf_path = (
                result.pdf.file_path
                if result and result.exists and result.pdf
                else None
            )

        if pdf_path:
            file_size = os.path.getsize(pdf_path)
            results.append(
                {
                    "process_id": str(process.id),
                    "protocol": process.protocol_number,
                    "patient_name": (
                        process.patient.name if process.patient else "Unknown"
                    ),
                    "filename": Path(pdf_path).name,
                    "pdf_path": pdf_path,
                    "file_size": file_size,
                    "generated_at": datetime.now(),
                }
            )
        else:
            logger.warning(
                f"Falha ao gerar PDF para o processo {process.protocol_number}"
            )

    logger.info(f"Generated {len(results)} combined PDFs")
    return results


def list_generated_pdfs() -> List[Dict]:
    """
    Lista todos os arquivos PDF gerados com metadados.

    Returns:
        Lista de dicionários com informações dos PDFs:
        [{
            'filename': str,
            'file_size': int,
            'created_at': datetime
        }]
    """
    generated_dir = get_generated_pdfs_dir()

    if not generated_dir.exists():
        return []

    pdfs = []

    for pdf_path in generated_dir.glob("*.pdf"):
        stat = pdf_path.stat()
        pdfs.append(
            {
                "filename": pdf_path.name,
                "file_size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime),
            }
        )

    pdfs.sort(key=operator.itemgetter("created_at"), reverse=True)

    return pdfs
