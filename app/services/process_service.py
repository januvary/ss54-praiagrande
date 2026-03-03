"""
Serviço de Processos
Gerencia criação de processos, controle de status e geração de números de protocolo.
Usa bloqueios em nível de banco de dados para prevenir condições de corrida.
"""

from datetime import datetime
from sqlalchemy.orm import Session
from app.models.process import Process, ProcessType, ProcessStatus, RequestType
from typing import Optional
from uuid import UUID

from app.services.activity_service import log_activity
from app.services.protocol_service import generate_protocol_number
from app.repositories.process_repository import get_process_for_update


def create_process(
    db: Session,
    patient_id,
    process_type: ProcessType,
    status: ProcessStatus = ProcessStatus.RASCUNHO,
    notes: str | None = None,
    request_type: RequestType = RequestType.PRIMEIRA_SOLICITACAO,
    original_process_id: Optional[UUID] = None,
    protocol_suffix: Optional[str] = None,
) -> Process:
    """
    Cria um novo processo com um número de protocolo único.
    Usa bloqueios em nível de banco de dados para thread safety.

    Args:
        db: Sessão do banco de dados
        patient_id: UUID do paciente
        process_type: Tipo de processo (medicamento, nutricao, bomba, outro)
        status: Status inicial (default: RASCUNHO)
        notes: Notas opcionais
        request_type: Tipo de solicitação (primeira_solicitacao ou renovacao)
        original_process_id: ID do processo original para renovações
        protocol_suffix: Sufixo opcional para número de protocolo (ex: "R" para renovações)

    Returns:
        Objeto Process criado
    """
    year = datetime.now().year

    try:
        protocol_number = generate_protocol_number(db, year, protocol_suffix)

        process = Process(
            protocol_number=protocol_number,
            patient_id=patient_id,
            type=process_type,
            status=status,
            notes=notes,
            request_type=request_type,
            original_process_id=original_process_id,
        )

        db.add(process)
        db.flush()  # Flush to get ID and write to transaction
        return process
    except Exception:
        raise


def transition_to_em_revisao_if_applicable(
    db: Session, process_id: UUID, user_id: Optional[UUID] = None
) -> Optional[Process]:
    """Transition process to EM_REVISAO if currently RASCUNHO or INCOMPLETO.

    Used after document uploads to automatically advance process status when
    documents are added to draft/incomplete processes.

    Args:
        db: Database session
        process_id: Process UUID
        user_id: Optional user ID for activity log (None for system actions)

    Returns:
        Updated Process object if transition occurred, None otherwise

    Raises:
        ProcessNotFoundError: If process not found
    """
    process = get_process_for_update(db, process_id)
    if not process:
        raise ProcessNotFoundError(f"Processo não encontrado: {process_id}")

    if process.status not in (ProcessStatus.RASCUNHO, ProcessStatus.INCOMPLETO):
        return None

    return update_process_status(
        db,
        process,
        ProcessStatus.EM_REVISAO,
        note=None,
        extra_data={"trigger": "document_upload"},
        user_id=user_id,
    )


def update_process_status_by_id(
    db: Session,
    process_id: UUID,
    status_str: str,
    note: Optional[str] = None,
    extra_data: Optional[dict] = None,
    user_id: Optional[UUID] = None,
) -> Process:
    """Update process status by ID with validation.

    HTTP-friendly wrapper for routes that accept process_id and status_str.
    Delegates to update_process_status() for the actual update logic.

    Args:
        db: Database session
        process_id: Process UUID
        status_str: New status value as string
        note: Optional note for the status change
        extra_data: Optional extra data for activity log
        user_id: Optional user ID for activity log (None for system actions)

    Returns:
        Updated Process object

    Raises:
        ProcessNotFoundError: If process not found
        ValueError: If status is invalid
    """
    process = get_process_for_update(db, process_id)
    if not process:
        raise ProcessNotFoundError(f"Processo não encontrado: {process_id}")

    try:
        new_status = ProcessStatus(status_str)
    except ValueError as e:
        raise ValueError(f"Status inválido: {status_str}") from e

    return update_process_status(
        db, process, new_status, note=note, extra_data=extra_data, user_id=user_id
    )


class ProcessNotFoundError(Exception):
    """Raised when a process cannot be found."""

    pass


def update_process_status(
    db: Session,
    process: Process,
    new_status: ProcessStatus,
    note: Optional[str] = None,
    extra_data: Optional[dict] = None,
    user_id: Optional[UUID] = None,
) -> Process:
    """
    Update process status with logging.

    Centralizes status change logic to ensure consistent:
    - Status validation
    - Timestamp updates
    - Activity logging

    Args:
        db: Database session
        process: Process object to update
        new_status: New status enum value
        note: Optional note for the status change
        extra_data: Optional extra data for activity log
        user_id: Optional user ID for activity log (None for system actions)

    Returns:
        Updated Process object
    """
    old_status = process.status.value
    process.status = new_status
    process.updated_at = datetime.now()

    if new_status == ProcessStatus.ENVIADO:
        process.sent_at = datetime.now()

    db.flush()

    # Build extra_data with note
    log_extra_data = {"old_status": old_status, "new_status": new_status.value}
    if note:
        log_extra_data["note"] = note.strip()
    if extra_data:
        log_extra_data.update(extra_data)

    log_activity(
        db,
        process.id,
        user_id,
        "status_changed",
        "Status alterado",
        log_extra_data,
        process=process,
    )

    return process
