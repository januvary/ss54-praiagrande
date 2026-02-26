"""
Document management routes for SS-54 web application.
Handles document download and upload to processes.
"""

from typing import Tuple, cast
from uuid import UUID
from pathlib import Path

from fastapi import APIRouter, Request, Depends, HTTPException
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
from app.services.document_service import (
    create_document,
    map_document_id_to_type,
)
from app.services.file_service import FileValidationError
from app.services.activity_service import log_activity
from app.services.process_service import transition_to_em_revisao_if_applicable
from app.utils.file_utils import file_exists

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


def _process_document_upload_loop(
    db: Session, process_id: UUID, form_data, file_count: int = 6
) -> tuple[int, list[str]]:
    """Process document upload loop for all document fields.

    Iterates through doc_1 to doc_6 (or file_count) and attempts to
    upload all files, collecting any validation errors.

    Args:
        db: Database session
        process_id: Process UUID
        form_data: Form data from request
        file_count: Number of document fields to process (default: 6)

    Returns:
        Tuple of (uploaded_count, errors_list)
    """
    from fastapi import UploadFile

    errors = []
    uploaded_count = 0

    for doc_id in range(1, file_count + 1):
        field_name = f"doc_{doc_id}"
        files = form_data.getlist(field_name)

        if files:
            for file in files:
                if getattr(file, "filename", None):
                    try:
                        doc_type = map_document_id_to_type(doc_id)
                        create_document(
                            db, cast(UUID, process_id), doc_type, cast(UploadFile, file)
                        )
                        uploaded_count += 1
                    except FileValidationError as e:
                        errors.append(
                            f"Arquivo {getattr(file, 'filename', 'unknown')}: {e}"
                        )

    return uploaded_count, errors


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

    uploaded_count, errors = _process_document_upload_loop(db, process_id, form)

    if errors:
        return RedirectResponse(
            url=_build_error_redirect_url(process_id, errors), status_code=303
        )

    if uploaded_count > 0:
        transition_to_em_revisao_if_applicable(db, process_id, current_user.id)
        db.flush()

        log_activity(
            db,
            process.id,
            current_user.id,
            "document_uploaded",
            "Documento enviado",
            process=process,
        )

    return RedirectResponse(url=f"/processo/{process_id}", status_code=303)
