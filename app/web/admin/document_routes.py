"""
Admin Document Routes - Document validation, upload, download
"""

from pathlib import Path
from typing import Optional, cast
from uuid import UUID
import logging

from fastapi import (
    APIRouter,
    Request,
    Depends,
    Form,
    UploadFile,  # noqa: F401
    HTTPException,
)
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.csrf import validate_csrf_token
from app.models.document import DocumentType
from app.schemas.document import DocumentResponse
from app.utils.template_config import templates
from app.services.document_service import (
    create_document,
    update_document_validation,
    DocumentNotFoundError,
)
from app.services.file_service import FileValidationError
from app.services.activity_service import log_activity
from app.utils.file_utils import file_exists
from app.repositories.document_repository import (
    get_document_by_id,
    get_document_for_download,
)
from app.repositories.process_repository import get_process_for_update
from app.content import (
    DOCUMENT_TYPE_TITLES,
    VALIDATION_COLORS,
    VALIDATION_LABELS,
    COLOR_CLASSES,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Documents"])


@router.post("/documents/{document_id}/validate")
async def admin_validate_document(
    request: Request,
    document_id: UUID,
    csrf_protected: None = Depends(validate_csrf_token),
    validation_status: str = Form(...),
    validation_notes: str = Form(default=""),
    db: Session = Depends(get_db),
):
    """Valida ou rejeita um documento."""
    try:
        document = update_document_validation(
            db,
            document_id,
            validation_status,
            notes=validation_notes,
        )
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return RedirectResponse(
        url=f"/admin/processes/{document.process_id}", status_code=303
    )


def _update_document_status(
    db: Session, document, status_str: str, old_status: str
) -> None:
    """Update document validation status and log activity."""
    try:
        activity_desc = (
            f"Documento {document.document_type.value} marcado como {status_str}"
        )
        update_document_validation(
            db, document.id, status_str, activity_description=activity_desc
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Status de validação inválido")


def _update_document_notes(
    db: Session, document, notes_str: Optional[str], old_notes: Optional[str]
) -> None:
    """Update document validation notes and log activity if changed."""
    if notes_str == "":
        document.validation_notes = None
    elif notes_str != document.validation_notes:
        document.validation_notes = notes_str

    if notes_str != old_notes:
        log_activity(
            db,
            document.process_id,
            None,
            "document_note_updated",
            f"Nota atualizada para documento {document.document_type.value}",
            {"old_notes": old_notes, "new_notes": notes_str},
            process=document.process,
        )


def _build_template_context(doc_data: dict, csrf_token: str, partial_type: str) -> dict:
    """Build template context for document row rendering."""
    context = {
        "doc": doc_data,
        "csrf_token": csrf_token,
        "validation_colors": VALIDATION_COLORS,
        "validation_labels": VALIDATION_LABELS,
        "color_classes": COLOR_CLASSES,
    }

    if partial_type == "validation_only":
        context["partial"] = "validation_only"
    else:
        context["partial"] = "full"
        context["doc_type_titles"] = DOCUMENT_TYPE_TITLES

    return context


def _render_document_row(
    request: Request, doc_data: dict, csrf_token: str, partial_type: str
):
    """Render document row HTML fragment."""
    context = _build_template_context(doc_data, csrf_token, partial_type)
    return templates.TemplateResponse(
        request, "components/document_row_wrapper.html", context
    )


@router.post("/documents/{document_id}/validate-quick")
async def admin_validate_document_quick(
    request: Request,
    document_id: UUID,
    csrf_protected: None = Depends(validate_csrf_token),
    status: str = Form(default=""),
    notes: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
):
    """Valida rapidamente documento via HTMX - retorna HTML atualizado da linha do documento."""
    document = get_document_by_id(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    old_status = document.validation_status.value
    old_notes = document.validation_notes

    try:
        if status:
            _update_document_status(db, document, status, old_status)

        if notes is not None:
            _update_document_notes(db, document, notes, old_notes)

        doc_schema = DocumentResponse.model_validate(document)
        doc_data = doc_schema.model_dump()

        csrf_token = request.cookies.get("csrf_token") or ""

        partial_type = "validation_only" if status and not notes else "full"
        return _render_document_row(request, doc_data, csrf_token, partial_type)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in validate-quick: {e}")
        raise


@router.get("/documents/{document_id}/download")
async def admin_download_document(document_id: UUID, db: Session = Depends(get_db)):
    """Baixa um arquivo de documento."""
    document = get_document_for_download(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    if not file_exists(document.file_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return FileResponse(
        path=document.file_path,
        filename=document.original_filename,
        media_type=document.mime_type,
        content_disposition_type="inline",
    )


@router.post("/processes/{process_id}/documentos")
async def admin_upload_document(
    request: Request,
    process_id: UUID,
    csrf_protected: None = Depends(validate_csrf_token),
    db: Session = Depends(get_db),
):
    """Faz upload de um documento (tipo='outro') para um processo como admin."""
    process = get_process_for_update(db, process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    form = await request.form()
    file = form.get("documento")

    if not file or not hasattr(file, "filename") or not file.filename:  # type: ignore
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado")

    try:
        create_document(db, cast(UUID, process.id), DocumentType.OUTRO, file)  # type: ignore

        db.flush()

        log_activity(
            db,
            process.id,
            None,
            "document_uploaded",
            "Documento enviado pela equipe",
            process=process,
        )

    except FileValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return RedirectResponse(url=f"/admin/processes/{process_id}", status_code=303)
