"""
Patient Service - Business logic for patient management.

Handles patient onboarding, validation, and management operations.
"""

from datetime import date
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.repositories.patient_repository import (
    get_patients_for_user,
    get_patient_for_owner,
    create_patient,
)
from app.utils.uuid_utils import ensure_uuid


def needs_patient_setup(db: Session, user_id: UUID) -> bool:
    """
    Check if user needs patient setup (has no patients).

    Args:
        db: Database session
        user_id: UUID of the user

    Returns:
        True if user has no patients, False otherwise
    """
    patients = get_patients_for_user(db, user_id)
    return len(patients) == 0


def create_patient_profile(
    db: Session, user_id: UUID, name: str, date_of_birth: Optional[date] = None
) -> Patient:
    """
    Create a new patient profile for a user.

    Args:
        db: Database session
        user_id: UUID of the user
        name: Name of the patient
        date_of_birth: Optional date of birth

    Returns:
        Created Patient object
    """
    user_id = ensure_uuid(user_id)
    return create_patient(db, user_id, name, date_of_birth)


def get_patients_for_user_safe(db: Session, user_id: UUID) -> List[Patient]:
    """
    Get all patients for a user (safe wrapper for repository).

    Args:
        db: Database session
        user_id: UUID of the user

    Returns:
        List of Patient objects
    """
    return get_patients_for_user(db, user_id)


def get_patient_for_owner_safe(
    db: Session, patient_id: UUID, user_id: UUID
) -> Optional[Patient]:
    """
    Get a patient by ID verifying ownership (safe wrapper for repository).

    Args:
        db: Database session
        patient_id: UUID of the patient
        user_id: UUID of the user for ownership verification

    Returns:
        Patient object if found and owned by user, None otherwise
    """
    return get_patient_for_owner(db, patient_id, user_id)
