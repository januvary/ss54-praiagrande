from contextlib import suppress

from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional, Tuple
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.models.patient import Patient
from app.services.auth_service import verify_jwt_token
from app.utils.uuid_utils import ensure_uuid
from app.repositories.patient_repository import get_patients_for_user


def _get_user_uuid(user_id: str) -> Optional[UUID]:
    """Converte com segurança string user_id para UUID, retorna None em caso de falha."""
    try:
        return ensure_uuid(user_id)
    except ValueError:
        return None


def _validate_token_and_get_user(request: Request, db: Session) -> Optional[User]:
    """
    Extracts and validates JWT token from auth cookie.

    Shared helper for all auth dependencies that need user validation.

    Args:
        request: FastAPI request object (contains cookies)
        db: Database session

    Returns:
        User object if valid, None otherwise
    """
    token = request.cookies.get("auth_token")
    if not token:
        return None

    user_id = verify_jwt_token(token)
    if user_id is None:
        return None

    user_uuid = _get_user_uuid(user_id)
    if user_uuid is None:
        return None

    user = db.query(User).filter(User.id == user_uuid).first()
    return user


def _get_selected_patient(
    request: Request, user: User, db: Session
) -> Optional[Patient]:
    """
    Gets the selected patient for a user, handling cookie-based selection.

    Selection logic:
    1. If user has no patients, returns None
    2. If cookie has valid patient ID belonging to user, returns that patient
    3. Otherwise returns the first patient

    Args:
        request: FastAPI request object (contains cookies)
        user: Authenticated user
        db: Database session

    Returns:
        Selected Patient or None if user has no patients
    """
    patients = get_patients_for_user(db, user.id)

    if not patients:
        return None

    selected_patient_id_str = request.cookies.get("selected_patient_id")
    selected_patient = None

    if selected_patient_id_str:
        with suppress(ValueError):
            selected_patient_id = ensure_uuid(selected_patient_id_str)
            for p in patients:
                if p.id == selected_patient_id:
                    selected_patient = p
                    break

    if not selected_patient:
        selected_patient = patients[0]

    return selected_patient


def get_current_user_cookie(
    request: Request, db: Session = Depends(get_db)
) -> Tuple[User, Patient]:
    """
    Dependency that extracts and validates JWT token from auth cookie.

    Used for web routes (HTML pages).
    Raises HTTPException if not authenticated.
    Redirects to /select-patient if user has no patients.

    Returns:
        Tuple of (User, Patient)
    """
    user = _validate_token_and_get_user(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND, headers={"Location": "/login"}
        )

    patient = _get_selected_patient(request, user, db)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND, headers={"Location": "/select-patient"}
        )

    return user, patient


def get_current_user_optional(
    request: Request, db: Session = Depends(get_db)
) -> Optional[Tuple[User, Optional[Patient]]]:
    """
    Dependency that extracts and validates JWT token from auth cookie.

    Returns None if not authenticated (no exception).
    Used for pages that work for both logged-in and anonymous users.

    Returns:
        Tuple of (User, Patient or None) or None if not authenticated
    """
    user = _validate_token_and_get_user(request, db)
    if not user:
        return None

    patient = _get_selected_patient(request, user, db)
    return user, patient


def get_current_user_cookie_no_registration_check(
    request: Request, db: Session = Depends(get_db)
) -> User:
    """
    Dependency that extracts and validates JWT token from auth cookie.

    Like get_current_user_cookie but does NOT check for patients.
    Used for routes that handle patient selection/creation.
    Raises HTTPException if not authenticated.

    Returns:
        User object
    """
    user = _validate_token_and_get_user(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND, headers={"Location": "/login"}
        )

    return user
