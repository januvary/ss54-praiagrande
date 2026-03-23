"""
Patient Repository - Lógica centralizada de consultas de pacientes.

Gerencia operações de banco de dados para a entidade Patient.
"""

from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_

from app.models.patient import Patient
from app.models.process import Process
from app.models.user import User


def get_patients_for_user(db: Session, user_id: UUID) -> List[Patient]:
    """
    Obtém todos os pacientes associados a um usuário.

    Args:
        db: Sessão do banco de dados
        user_id: UUID do usuário

    Returns:
        Lista de objetos Patient, ordenados por nome
    """
    return (
        db.query(Patient)
        .filter(Patient.user_id == user_id)
        .order_by(Patient.name)
        .all()
    )


def get_patient_for_owner(
    db: Session, patient_id: UUID, user_id: UUID
) -> Optional[Patient]:
    """
    Obtém um paciente por ID verificando se pertence ao usuário.

    Args:
        db: Sessão do banco de dados
        patient_id: UUID do paciente
        user_id: UUID do usuário para verificar propriedade

    Returns:
        Objeto Patient ou None se não encontrado ou não pertencer ao usuário
    """
    return (
        db.query(Patient)
        .filter(Patient.id == patient_id, Patient.user_id == user_id)
        .first()
    )


def get_patient_by_id(db: Session, patient_id: UUID) -> Optional[Patient]:
    """
    Obtém um paciente por ID com usuário carregado.

    Args:
        db: Sessão do banco de dados
        patient_id: UUID do paciente

    Returns:
        Objeto Patient com usuário carregado ou None se não encontrado
    """
    return (
        db.query(Patient)
        .options(joinedload(Patient.user))
        .filter(Patient.id == patient_id)
        .first()
    )


def create_patient(
    db: Session, user_id: UUID, name: str, date_of_birth=None
) -> Patient:
    """
    Cria um novo paciente para um usuário.

    Args:
        db: Sessão do banco de dados
        user_id: UUID do usuário proprietário
        name: Nome do paciente
        date_of_birth: Data de nascimento opcional

    Returns:
        Objeto Patient criado
    """
    patient = Patient(user_id=user_id, name=name, date_of_birth=date_of_birth)
    db.add(patient)
    db.flush()

    return patient


def get_patient_process_info(db: Session, patient_ids: List[UUID]) -> dict[UUID, dict]:
    """
    Obtém informações de processos para múltiplos pacientes de uma vez.

    Args:
        db: Sessão do banco de dados
        patient_ids: Lista de IDs de pacientes

    Returns:
        Dicionário mapeando patient_id -> {count, last_date}
    """
    if not patient_ids:
        return {}

    process_info = (
        db.query(
            Process.patient_id,
            func.count(Process.id).label("process_count"),
            func.max(Process.created_at).label("last_process_date"),
        )
        .filter(Process.patient_id.in_(patient_ids))
        .group_by(Process.patient_id)
        .all()
    )

    return {
        info.patient_id: {
            "process_count": info.process_count or 0,
            "last_process_date": info.last_process_date,
        }
        for info in process_info
    }


def get_all_patients_paginated(
    db: Session,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
) -> Tuple[List[Patient], int]:
    """
    Obtém todos os pacientes com filtragem e paginação opcionais.

    Args:
        db: Sessão do banco de dados
        search: Termo de busca opcional (busca nome, email, telefone)
        page: Número da página (indexado a partir de 1)
        per_page: Resultados por página

    Returns:
        Tupla de (lista de pacientes, total de registros)
    """
    query = db.query(Patient).join(User, Patient.user_id == User.id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Patient.name.ilike(search_term),
                User.email.ilike(search_term),
                User.phone.ilike(search_term),
            )
        )

    total = query.count()

    offset = (page - 1) * per_page

    patients = (
        query.options(
            joinedload(Patient.user),
        )
        .order_by(Patient.updated_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    patient_ids = [p.id for p in patients]
    process_info_map = get_patient_process_info(db, patient_ids)

    for patient in patients:
        info = process_info_map.get(patient.id, {})
        patient.process_count = info.get("process_count", 0)
        patient.last_process_date = info.get("last_process_date")

    return patients, total
