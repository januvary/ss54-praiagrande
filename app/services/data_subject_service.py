"""
Data Subject Service - LGPD Art. 18 Rights Implementation

Provides functions for users to exercise their data subject rights:
- Right to Access (Art. 18, I): View all personal data
- Right to Correction (Art. 18, III): Update personal information
- Right to Portability (Art. 18, V): Export data in machine-readable format
"""

from datetime import datetime, date
from typing import Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from app.models.user import User
from app.models.patient import Patient
from app.models.process import Process, ProcessStatus
from app.models.activity_log import ActivityLog
from app.schemas.process import ProcessResponse
from app.schemas.user import UserResponse
from app.schemas.activity_log import ActivityLogResponse
from app.schemas.patient import PatientResponse
from app.utils.file_sanitization import sanitize_filename
from app.utils.file_utils import file_exists
import zipfile
import io
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def get_user_data_report(
    db: Session, user_id: UUID, include_activities: bool = True
) -> Dict[str, Any] | None:
    """
    Aggregates all personal data stored for a user (LGPD Art. 18, I - Right to Access).

    Returns a comprehensive report including:
    - User account information
    - Associated patients
    - All processes with document counts
    - Recent activity logs (if include_activities=True)
    - Data sharing information

    Args:
        db: Database session
        user_id: UUID of the user
        include_activities: Whether to include activity logs (default True)

    Returns:
        Dictionary containing all user data
    """
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    # Get patients
    patients = (
        db.query(Patient)
        .options(joinedload(Patient.processes).subqueryload(Process.documents))
        .filter(Patient.user_id == user_id)
        .order_by(Patient.name)
        .all()
    )

    # Get all processes for all patients
    all_processes = []
    patient_processes_map = {}

    for patient in patients:
        process_list = [
            ProcessResponse.model_validate(p).model_dump(mode="json")
            for p in patient.processes
        ]
        patient_processes_map[str(patient.id)] = process_list
        all_processes.extend(process_list)

    # Get recent activity logs (only if requested)
    activity_list = []
    if include_activities:
        from app.utils.date_utils import get_days_ago

        cutoff_date = get_days_ago(90)
        activities = (
            db.query(ActivityLog)
            .filter(
                ActivityLog.user_id == user_id, ActivityLog.created_at >= cutoff_date
            )
            .order_by(ActivityLog.created_at.desc())
            .limit(50)
            .all()
        )
        activity_list = [
            ActivityLogResponse.model_validate(a).model_dump(mode="json")
            for a in activities
        ]

    # Build comprehensive report
    report = {
        "user": UserResponse.model_validate(user).model_dump(mode="json"),
        "patients": [
            {
                **PatientResponse.model_validate(p).model_dump(mode="json"),
                "process_count": len(patient_processes_map[str(p.id)]),
            }
            for p in patients
        ],
        "processes": all_processes,
        "processes_by_patient": patient_processes_map,
        "recent_activities": activity_list,
        "data_sharing": {
            "dpo": {
                "name": "Cássio de Castro Navarro",
                "email": "protecaodedados@praiagrande.sp.gov.br",
                "phone": "(13) 3496-2053",
            },
            "ouvidoria": {"phone": "162", "hours": "Segunda a Sexta, 9h às 16h"},
            "sesap": {
                "name": "Assistência Farmacêutica",
                "phone": "(13) 3496-2469",
            },
        },
        "report_generated_at": datetime.now().isoformat(),
    }

    # Note: Logging disabled for user-level activities (activity_logs requires process_id)
    # TODO: Make process_id nullable in activity_logs to enable user-level activity logging

    return report


def _can_process_be_deleted(process: Process) -> bool:
    """
    Determines if a process can be deleted based on legal retention requirements.

    A process CANNOT be deleted if:
    - Status is AUTORIZADO (authorized - must keep for 5 years)
    - Status is EM_REVISAO (under review - active process)
    - Less than 5 years since authorization or creation

    Args:
        process: Process object to check

    Returns:
        True if process can be deleted, False otherwise
    """
    # Active statuses cannot be deleted
    if process.status in (ProcessStatus.AUTORIZADO, ProcessStatus.EM_REVISAO):
        return False

    # Check 5-year retention period
    cutoff_date = datetime.now()
    reference_date = process.authorization_date or process.created_at

    # Must be at least 5 years old
    five_years_ago = datetime(
        reference_date.year + 5, reference_date.month, reference_date.day
    )
    return cutoff_date >= five_years_ago


def can_delete_user_account(db: Session, user_id: UUID) -> Dict[str, Any]:
    """
    Checks if a user account can be deleted based on legal retention requirements.

    Args:
        db: Database session
        user_id: UUID of the user

    Returns:
        Dictionary with:
        - can_delete: boolean
        - blocking_processes: list of processes preventing deletion
        - deletable_processes: count of processes that can be deleted
        - total_processes: count of all processes
    """
    patients = (
        db.query(Patient)
        .options(joinedload(Patient.processes))
        .filter(Patient.user_id == user_id)
        .all()
    )

    blocking_processes = []
    deletable_count = 0
    total_count = 0

    for patient in patients:
        for process in patient.processes:
            total_count += 1
            if not _can_process_be_deleted(process):
                blocking_processes.append(
                    {
                        "protocol_number": process.protocol_number,
                        "status": process.status.value,
                        "reason": _get_blocking_reason(process),
                    }
                )
            else:
                deletable_count += 1

    return {
        "can_delete": len(blocking_processes) == 0,
        "blocking_processes": blocking_processes,
        "deletable_processes": deletable_count,
        "total_processes": total_count,
    }


def _get_blocking_reason(process: Process) -> str:
    """Returns the reason why a process cannot be deleted."""
    if process.status == ProcessStatus.AUTORIZADO:
        return "Processo autorizado - retenção legal de 5 anos"
    if process.status == ProcessStatus.EM_REVISAO:
        return "Processo em análise - não pode ser excluído"
    return "Processo recente - retenção legal de 5 anos"


def export_user_data_zip(db: Session, user_id: UUID) -> bytes | None:
    """
    Exports all user data as ZIP file (LGPD Art. 18, V - Right to Portability).

    ZIP contents:
    - dados_pessoais.txt (formatted text report)
    - documentos/ (folder with all uploaded files organized by patient name)

    Args:
        db: Database session
        user_id: UUID of the user

    Returns:
        ZIP file as bytes
    """
    report = get_user_data_report(db, user_id)
    if not report:
        return None

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        txt_content = _generate_txt_report(report, user)
        zip_file.writestr(
            "dados_pessoais.txt", txt_content, compress_type=zipfile.ZIP_DEFLATED
        )

        # Eager load all data in a single query to avoid N+1
        patients_with_data = (
            db.query(Patient)
            .options(joinedload(Patient.processes).joinedload(Process.documents))
            .filter(Patient.user_id == user_id)
            .all()
        )
        patient_map = {str(p.id): p for p in patients_with_data}

        for patient in report["patients"]:
            patient_obj = patient_map.get(patient["id"])
            if not patient_obj:
                continue

            safe_patient_name = sanitize_filename(patient_obj.name)

            for process in patient_obj.processes:
                for doc in process.documents:
                    if not file_exists(doc.file_path):
                        logger.warning(f"Document file not found: {doc.file_path}")
                        continue

                    folder_path = f"documentos/{safe_patient_name}/"
                    safe_filename = sanitize_filename(doc.original_filename)
                    doc_prefix = f"{doc.document_type.value}_"
                    zip_filename = f"{folder_path}{doc_prefix}{safe_filename}"

                    try:
                        zip_file.writestr(
                            zip_filename,
                            Path(doc.file_path).read_bytes(),
                            compress_type=zipfile.ZIP_DEFLATED,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to read document {doc.file_path}: {e}")

    return zip_buffer.getvalue()


def _generate_txt_report(report: Dict[str, Any], user: User) -> str:
    """Generates a formatted TXT report from user data."""
    lines: list[str] = []
    lines.extend(
        (
            "═" * 60,
            "  EXPORTAÇÃO DE DADOS PESSOAIS - LGPD ART. 18, V",
            "  Sistema: SS-54 - Assistência Farmacêutica Praia Grande",
            f"  Data: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}",
            "═" * 60,
            "",
        )
    )

    # 1. Account Data
    lines.extend(
        (
            "1. DADOS DA CONTA",
            "─" * 60,
            f"Email: {report['user']['email']}",
            f"Telefone: {report['user']['phone'] or 'Não informado'}",
            f"Conta criada em: {report['user']['created_at'][:10]}",
        )
    )
    if report["user"]["last_login"]:
        lines.append(f"Último acesso: {report['user']['last_login'][:10]}")
    else:
        lines.append("Último acesso: Não registrado")
    lines.append("")

    # 2. Patients
    lines.extend(
        (
            "2. PACIENTES CADASTRADOS",
            "─" * 60,
        )
    )
    for i, patient in enumerate(report["patients"], 1):
        lines.extend(
            (
                f"Paciente {i}: {patient['name']}",
                f"  Data de Nascimento: {patient['date_of_birth'][:10] if patient['date_of_birth'] else 'Não informada'}",
                f"  Cadastrado em: {patient['created_at'][:10]}",
                f"  Processos: {patient['process_count']}",
                "",
            )
        )

    # 3. Processes
    lines.extend(
        (
            "3. PROCESSOS",
            "─" * 60,
        )
    )
    for process in report["processes"]:
        lines.extend(
            (
                f"Processo: {process['protocol_number']}",
                f"  Tipo: {process['type'].replace('_', ' ').title()}",
                f"  Status: {process['status'].replace('_', ' ').title()}",
                f"  Data de Criação: {process['created_at'][:10]}",
            )
        )
        if process["authorization_date"]:
            lines.append(f"  Data de Autorização: {process['authorization_date'][:10]}")
        lines.extend(
            (
                f"  Documentos: {process['document_count']} arquivos",
                f"  Solicitação: {process['request_type'].replace('_', ' ').title()}",
                "",
            )
        )

    # 4. Legal Basis
    lines.extend(
        (
            "4. BASE LEGAL",
            "─" * 60,
            "Seus dados são processados com base em:",
            "• Art. 7º, II - Cumprimento de obrigação legal",
            "• Art. 7º, III - Execução de políticas públicas",
            "• Art. 11, II, 'b' e 'f' - Tutela da saúde",
            "",
        )
    )

    # 5. Data Sharing
    lines.extend(
        (
            "5. COMPARTILHAMENTO DE DADOS",
            "─" * 60,
            f"• DPO (Encarregado): {report['data_sharing']['dpo']['email']}",
            f"• Ouvidoria: {report['data_sharing']['ouvidoria']['phone']} ({report['data_sharing']['ouvidoria']['hours']})",
            f"• SESAP: {report['data_sharing']['sesap']['phone']}",
            "",
        )
    )

    # 6. Data Retention
    lines.extend(
        (
            "6. RETENÇÃO DE DADOS",
            "─" * 60,
            "• Processos autorizados: 5 anos após autorização",
            "• Processos negados: 5 anos após indeferimento",
            "• Prontuários eletrônicos: guarda permanente",
            "",
        )
    )

    return "\n".join(lines)


def update_user_phone(db: Session, user: User, phone: str) -> User:
    """
    Updates user's phone number with audit logging.

    Args:
        db: Database session
        user: User object
        phone: New phone number

    Returns:
        Updated User object
    """
    from app.utils.validators import validate_phone

    phone_clean, errors = validate_phone(phone)
    if errors:
        raise ValueError(f"Telefone inválido: {', '.join(errors)}")

    user.phone = phone_clean
    db.flush()

    # Note: Activity logging disabled (requires process_id)
    # TODO: Enable after making process_id nullable in activity_logs

    return user


def update_patient_info(
    db: Session,
    patient: Patient,
    name: str | None = None,
    date_of_birth: date | None = None,
) -> Patient:
    """
    Updates patient information with audit logging.

    Args:
        db: Database session
        patient: Patient object to update
        name: New name (optional)
        date_of_birth: New date of birth (optional)

    Returns:
        Updated Patient object
    """
    from app.utils.validators import validate_name

    changes = []

    if name is not None:
        name_clean, errors = validate_name(name)
        if errors:
            raise ValueError(f"Nome inválido: {', '.join(errors)}")
        if name_clean != patient.name:
            changes.append(f"nome: {patient.name} → {name_clean}")
            patient.name = name_clean

    if date_of_birth is not None:
        if date_of_birth != patient.date_of_birth:
            old_dob = (
                patient.date_of_birth.isoformat()
                if patient.date_of_birth
                else "não informado"
            )
            new_dob = date_of_birth.isoformat()
            changes.append(f"data de nascimento: {old_dob} → {new_dob}")
            patient.date_of_birth = date_of_birth

    if changes:
        db.flush()

        # Note: Activity logging disabled (requires process_id)
        # TODO: Enable after making process_id nullable in activity_logs

    return patient
