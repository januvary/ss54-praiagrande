"""
Process Repository - Lógica centralizada de consultas de processos.

Elimina padrões de consulta repetitivos e garante carregamento consistente
para prevenir consultas N+1.
"""

from contextlib import suppress

from typing import Optional, List, TypedDict
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from app.models.patient import Patient
from sqlalchemy import func, or_, case

from app.models.process import Process, ProcessStatus
from app.models.user import User
from app.models.document import Document, DocumentType
from fastapi import HTTPException


class DashboardStatistics(TypedDict):
    """Resumo de estatísticas do painel."""

    status_counts: dict[str, int]
    total_processes: int
    total_patients: int
    total_documents: int
    processes_this_week: int
    processes_this_month: int


def get_process_with_documents(db: Session, process_id: UUID) -> Optional[Process]:
    """
    Obtém processo por ID com documentos carregados ansiosamente.

    Args:
        db: Sessão do banco de dados
        process_id: UUID do processo

    Returns:
        Objeto Process com documentos carregados, ou None se não encontrado
    """
    return (
        db.query(Process)
        .options(joinedload(Process.documents))
        .filter(Process.id == process_id)
        .first()
    )


def get_process_with_patient_and_documents(
    db: Session, process_id: UUID
) -> Optional[Process]:
    """
    Obtém processo por ID com paciente e documentos carregados ansiosamente.

    Args:
        db: Sessão do banco de dados
        process_id: UUID do processo

    Returns:
        Objeto Process com paciente e documentos carregados, ou None se não encontrado
    """
    return (
        db.query(Process)
        .options(
            joinedload(Process.documents),
            joinedload(Process.patient).joinedload(Patient.user),
        )
        .filter(Process.id == process_id)
        .first()
    )


def get_processes_for_patient(db: Session, patient_id: UUID) -> List[Process]:
    """
    Obtém todos os processos de um paciente com documentos carregados ansiosamente.

    Args:
        db: Sessão do banco de dados
        patient_id: UUID do paciente

    Returns:
        Lista de objetos Process com documentos carregados, ordenados por data de criação
    """
    return (
        db.query(Process)
        .options(joinedload(Process.documents))
        .filter(Process.patient_id == patient_id)
        .order_by(Process.created_at.desc())
        .all()
    )


def get_all_processes_paginated(
    db: Session,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[List[Process], int]:
    """
    Obtém todos os processos com filtragem e paginação opcionais.

    Args:
        db: Sessão do banco de dados
        status: Filtro de status opcional
        search: Termo de busca opcional (busca protocolo, email, nome)
        page: Número da página (indexado a partir de 1)
        per_page: Resultados por página

    Returns:
        Tupla de (lista de processos, total de registros)
    """
    query = db.query(Process)

    # Filter by status
    if status:
        with suppress(ValueError):
            status_enum = ProcessStatus(status)
            query = query.filter(Process.status == status_enum)

    # Search by protocol number or patient info
    if search:
        search_term = f"%{search}%"
        query = (
            query.join(Patient, Process.patient_id == Patient.id)
            .join(User, Patient.user_id == User.id)
            .filter(
                or_(
                    Process.protocol_number.ilike(search_term),
                    Patient.name.ilike(search_term),
                    User.email.ilike(search_term),
                )
            )
        )

    # Get total count before pagination
    total = query.count()

    # Calculate pagination
    offset = (page - 1) * per_page

    # Order by most recent first with eager loading
    processes = (
        query.options(
            joinedload(Process.patient).joinedload(Patient.user),
            joinedload(Process.documents),
        )
        .order_by(Process.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    return processes, total


def get_recent_processes(db: Session, limit: int = 10) -> List[Process]:
    """
    Obtém processos recentes com carregamento básico.

    Args:
        db: Sessão do banco de dados
        limit: Número máximo de processos a retornar

    Returns:
        Lista de objetos Process recentes
    """
    return (
        db.query(Process)
        .options(joinedload(Process.patient).joinedload(Patient.user))
        .order_by(Process.created_at.desc())
        .limit(limit)
        .all()
    )


def get_process_for_update(db: Session, process_id: UUID) -> Optional[Process]:
    """
    Obtém processo por ID com paciente carregado ansiosamente (para atualizações).
    NÃO carrega documentos - use get_process_with_patient_and_documents() para operações de leitura.

    Args:
        db: Sessão do banco de dados
        process_id: UUID do processo

    Returns:
        Objeto Process com paciente carregado, ou None se não encontrado
    """
    return (
        db.query(Process)
        .options(joinedload(Process.patient).joinedload(Patient.user))
        .filter(Process.id == process_id)
        .first()
    )


def get_dashboard_statistics(db: Session) -> DashboardStatistics:
    """
    Obtém todas as estatísticas do painel de admin em consultas otimizadas.

    Args:
        db: Sessão do banco de dados

    Returns:
        Dicionário com todas as métricas do painel incluindo contagens de status,
        contagens totais e contagens baseadas em tempo.
    """
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # Single query with conditional counts for Process
    process_stats = db.query(
        func.count(Process.id).label("total"),
        func.sum(case((Process.created_at >= week_ago, 1), else_=0)).label("this_week"),
        func.sum(case((Process.created_at >= month_ago, 1), else_=0)).label(
            "this_month"
        ),
    ).first()

    # process_stats is always returned by func.count() even if empty table
    if process_stats is None:  # pragma: no cover
        raise RuntimeError("Unexpected: count query returned no rows")

    # Status counts (separate query needed for GROUP BY)
    status_results = (
        db.query(Process.status, func.count(Process.id)).group_by(Process.status).all()
    )

    # Convert to dict with all statuses (including zeros)
    status_counts = {status.value: 0 for status in ProcessStatus}
    for status, count in status_results:
        status_counts[status.value] = count

    # Cross-table counts (cannot combine with Process queries)
    total_patients = db.query(func.count(Patient.id)).scalar()
    total_documents = (
        db.query(func.count(Document.id))
        .filter(Document.document_type != DocumentType.PDF_COMBINADO)
        .scalar()
    )

    return {
        "status_counts": status_counts,
        "total_processes": process_stats.total or 0,
        "total_patients": total_patients or 0,
        "total_documents": total_documents or 0,
        "processes_this_week": int(process_stats.this_week or 0),
        "processes_this_month": int(process_stats.this_month or 0),
    }


def get_processes_by_statuses(db: Session, statuses: List[str]) -> List[Process]:
    """
    Obtém processos com status especificados, ordenados alfabeticamente por nome do paciente.
    Usado na página Envios para exibir processos no fluxo de envio.

    Args:
        db: Sessão do banco de dados
        statuses: Lista de valores de status para buscar

    Returns:
        Lista de objetos Process com paciente carregado ansiosamente, ordenados por nome do paciente
    """
    # Convert status strings to enums
    status_enums = []
    for status in statuses:
        try:
            status_enums.append(ProcessStatus(status))
        except ValueError:
            continue  # Skip invalid statuses

    if not status_enums:
        return []

    # Query processes with eager loading, ordered by patient name
    processes = (
        db.query(Process)
        .options(
            joinedload(Process.patient).joinedload(Patient.user),
            joinedload(Process.documents),
        )
        .filter(Process.status.in_(status_enums))
        .all()
    )

    processes.sort(
        key=lambda p: (p.patient.name.lower() if p.patient and p.patient.name else "")
    )

    return processes


def get_process_for_owner_update_or_404(
    db: Session, process_id: UUID, patient_id: UUID
) -> Process:
    """
    Obtém processo por ID verificando propriedade.
    Levanta HTTPException(404) se não encontrado ou não pertencer ao paciente.

    Args:
        db: Sessão do banco de dados
        process_id: UUID do processo
        patient_id: UUID do paciente para verificar propriedade

    Returns:
        Objeto Process com documentos carregados

    Raises:
        HTTPException: 404 se processo não encontrado ou não pertencer ao paciente
    """
    process = (
        db.query(Process)
        .options(
            joinedload(Process.documents),
            joinedload(Process.patient).joinedload(Patient.user),
        )
        .filter(Process.id == process_id, Process.patient_id == patient_id)
        .first()
    )

    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    return process


def get_expired_processes_for_patient(db: Session, patient_id: UUID) -> List[Process]:
    return (
        db.query(Process)
        .filter(
            Process.patient_id == patient_id,
            Process.status == ProcessStatus.EXPIRADO,
        )
        .order_by(Process.created_at.desc())
        .all()
    )
