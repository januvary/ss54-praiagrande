"""
Admin PDF Routes - PDF generation, viewing, downloading
"""

import logging

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.csrf import validate_csrf_token
from app.utils.template_helpers import render_template
from app.utils.file_sanitization import sanitize_filename
from app.utils.file_utils import file_exists
from app.services.pdf_generation_service import (
    batch_generate_pdfs,
    get_generated_pdfs_dir,
    list_generated_pdfs,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin PDF"])


@router.post("/generate-pdfs", response_class=HTMLResponse)
async def generate_pdfs(
    request: Request,
    csrf_protected: None = Depends(validate_csrf_token),
    db: Session = Depends(get_db),
):
    """
    Generate combined PDFs for all processes with 'completo' status.
    Returns HTML fragment with list of generated PDFs.
    """
    try:
        generated_pdfs = batch_generate_pdfs(db)

        context = {
            "generated_pdfs": generated_pdfs,
            "success": True,
            "message": f"{len(generated_pdfs)} PDF(s) gerado(s) com sucesso",
        }

        return render_template(
            request, "admin/partials/generated_pdfs_list.html", context, is_admin=True
        )

    except Exception as e:
        logger.error(f"Error generating PDFs: {e}")
        context = {
            "generated_pdfs": [],
            "success": False,
            "error": "Erro ao gerar PDFs",
        }
        return render_template(
            request, "admin/partials/generated_pdfs_list.html", context, is_admin=True
        )


@router.get("/generated-pdfs", response_class=HTMLResponse)
async def render_generated_pdfs_list(request: Request, db: Session = Depends(get_db)):
    """
    List all generated PDF files.
    Returns HTML fragment with list of PDFs.
    """
    try:
        pdfs = list_generated_pdfs()

        context = {"generated_pdfs": pdfs, "success": True}

        return render_template(
            request, "admin/partials/generated_pdfs_list.html", context, is_admin=True
        )

    except Exception as e:
        logger.error(f"Error listing PDFs: {e}")
        context = {
            "generated_pdfs": [],
            "success": False,
            "error": "Erro ao listar PDFs",
        }
        return render_template(
            request, "admin/partials/generated_pdfs_list.html", context, is_admin=True
        )


@router.get("/generated-pdfs/{filename}")
async def download_generated_pdf(filename: str, db: Session = Depends(get_db)):
    """
    Download a generated combined PDF file.
    """
    safe_filename = sanitize_filename(filename)

    if not safe_filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid filename")

    pdf_path = get_generated_pdfs_dir() / safe_filename

    if not file_exists(str(pdf_path)):
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(
        path=str(pdf_path),
        filename=safe_filename,
        media_type="application/pdf",
        content_disposition_type="inline",
    )
