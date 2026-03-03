"""
Patient Repository - Lógica centralizada de consultas de pacientes.

Gerencia operações de banco de dados para a entidade Patient.
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.patient import Patient


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
