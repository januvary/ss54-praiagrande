"""
Document management routes for SS-54 web application.
Handles document download and upload to processes.
"""

import logging
from typing import Tuple
from uuid import UUID

from fastapi import APIRouter, Request, Depends, HTTPException, UploadFile
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user_cookie
from app.dependencies.csrf import validate_csrf_token
from app.models.user import User
from app.models.patient import Patient
from app.models.process import ProcessStatus
from app.repositories.process_repository import get_process_for_owner_update_or_404
from app.repositories.document_repository import get_document_by_id
from app.services.document_service import map_document_id_to_type
from app.services.file_service import (
    FileValidationError,
    prepare_file_upload,
    save_converted_files_atomic,
)
from app.services.activity_service import log_activity
from app.services.process_service import transition_to_em_revisao_if_applicable
from app.utils.file_utils import file_exists

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/documentos/{document_id}/download")
async def download_document(
    document_id: UUID,
    auth: Tuple[User, Patient] = Depends(get_current_user_cookie),
    db: Session = Depends(get_db),
):
    current_user, current_patient = auth

    document = get_document_by_id(db, document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    if document.process.patient_id != current_patient.id:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    if not file_exists(document.file_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return FileResponse(
        path=document.file_path,
        filename=document.original_filename,
        media_type=document.mime_type,
        content_disposition_type="inline",
    )


def _build_error_redirect_url(process_id: UUID, errors: list[str]) -> str:
    """Build redirect URL with error messages as query parameter.

    Args:
        process_id: Process UUID
        errors: List of error messages

    Returns:
        Redirect URL with error query parameter
    """
    error_param = "; ".join(errors)
    return f"/processo/{process_id}?error={error_param}"


@router.post("/processo/{process_id}/documentos")
async def add_documents_to_process(
    request: Request,
    process_id: UUID,
    csrf_protected: None = Depends(validate_csrf_token),
    auth: Tuple[User, Patient] = Depends(get_current_user_cookie),
    db: Session = Depends(get_db),
):
    current_user, current_patient = auth

    process = get_process_for_owner_update_or_404(db, process_id, current_patient.id)

    if process.status not in (
        ProcessStatus.CORRECAO_SOLICITADA,
        ProcessStatus.INCOMPLETO,
        ProcessStatus.RASCUNHO,
    ):
        raise HTTPException(
            status_code=400,
            detail="Não é possível adicionar documentos a este processo",
        )

    form = await request.form()

    staged_files = []
    errors = []

    for doc_id in range(1, 7):
        files = form.getlist(f"doc_{doc_id}")
        for file in files:
            if isinstance(file, UploadFile) and file.filename:
                try:
                    staged = await prepare_file_upload(
                        db,
                        file,
                        process_id,
                        map_document_id_to_type(doc_id),
                        process.patient.name,
                        process.protocol_number,
                    )
                    staged_files.append(staged)
                except FileValidationError as e:
                    errors.append(f"{file.filename}: {e}")

    if errors:
        return RedirectResponse(
            url=_build_error_redirect_url(process_id, errors), status_code=303
        )

    if staged_files:
        try:
            uploaded_count = save_converted_files_atomic(
                db,
                process_id,
                staged_files,
                process.patient.name,
                process.protocol_number,
            )

            transition_to_em_revisao_if_applicable(db, process_id, current_user.id)
            db.flush()

            log_activity(
                db,
                process.id,
                current_user.id,
                "document_uploaded",
                f"{uploaded_count} documento(s) enviado(s)",
                process=process,
            )

        except Exception as e:
            logger.error(f"Failed to save documents atomically: {e}")
            return RedirectResponse(
                url=f"/processo/{process_id}?error=Falha ao salvar documentos: {e}",
                status_code=303,
            )

    return RedirectResponse(url=f"/processo/{process_id}", status_code=303)
