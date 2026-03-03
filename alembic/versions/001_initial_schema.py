"""initial_schema

Consolidated initial schema with all tables, indexes, and constraints.
This replaces all previous migrations and provides a clean baseline.

Revision ID: 001
Revises:
Create Date: 2026-02-18 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create all tables, indexes, and constraints."""

    # ========================================
    # Tables
    # ========================================

    # Users table (authentication only)
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # Patients table (patient profiles)
    op.create_table(
        "patients",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patients_user_id", "patients", ["user_id"])

    # Protocol counters table
    op.create_table(
        "protocol_counters",
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("last_sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("year"),
    )

    # Processes table
    op.create_table(
        "processes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("protocol_number", sa.String(length=20), nullable=False),
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column(
            "type",
            sa.Enum("medicamento", "nutricao", "bomba", "outro", name="processtype"),
            nullable=False,
        ),
        sa.Column(
            "request_type",
            sa.Enum("primeira_solicitacao", "renovacao", name="requesttype"),
            nullable=False,
            server_default="primeira_solicitacao",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "rascunho",
                "em_revisao",
                "incompleto",
                "completo",
                "enviado",
                "correcao_solicitada",
                "autorizado",
                "negado",
                "expirado",
                "outro",
                name="processstatus",
            ),
            nullable=False,
            server_default="rascunho",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("original_process_id", sa.UUID(), nullable=True),
        sa.Column("authorization_date", sa.DateTime(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("was_renewed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["original_process_id"], ["processes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_processes_protocol_number", "processes", ["protocol_number"], unique=True
    )
    op.create_index("ix_processes_patient_id", "processes", ["patient_id"])
    op.create_index("ix_processes_status", "processes", ["status"])
    op.create_index("ix_processes_created_at", "processes", ["created_at"])
    op.create_index(
        "ix_processes_original_process_id", "processes", ["original_process_id"]
    )
    op.create_index(
        "ix_processes_authorization_date", "processes", ["authorization_date"]
    )
    op.create_index("ix_processes_sent_at", "processes", ["sent_at"])
    op.create_index(
        "ix_processes_patient_created", "processes", ["patient_id", "created_at"]
    )
    op.create_index(
        "ix_processes_status_created", "processes", ["status", "created_at"]
    )

    # Documents table
    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("process_id", sa.UUID(), nullable=False),
        sa.Column(
            "document_type",
            sa.Enum(
                "formulario",
                "declaracao",
                "receita",
                "relatorio",
                "documento_pessoal",
                "exame",
                "pdf_combinado",
                "outro",
                name="documenttype",
            ),
            nullable=False,
        ),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column(
            "validation_status",
            sa.Enum("pending", "valid", "invalid", name="validationstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("validation_notes", sa.Text(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("validated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["process_id"], ["processes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "file_size > 0 AND file_size <= 10485760", name="check_file_size"
        ),
        sa.CheckConstraint(
            "mime_type IN ('application/pdf', 'image/jpeg', 'image/png')",
            name="check_mime_type",
        ),
    )
    op.create_index("ix_documents_process_id", "documents", ["process_id"])
    op.create_index(
        "ix_documents_validation_status", "documents", ["validation_status"]
    )
    op.create_index(
        "ix_documents_process_status", "documents", ["process_id", "validation_status"]
    )

    # Activity logs table
    op.create_table(
        "activity_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("process_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["process_id"], ["processes.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activity_logs_process_id", "activity_logs", ["process_id"])
    op.create_index("ix_activity_logs_user_id", "activity_logs", ["user_id"])
    op.create_index("ix_activity_logs_created_at", "activity_logs", ["created_at"])
    op.create_index(
        "ix_activity_process_created", "activity_logs", ["process_id", "created_at"]
    )

    # Magic tokens table
    op.create_table(
        "magic_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("expires_at > created_at", name="check_expiry_future"),
    )
    op.create_index("ix_magic_tokens_token", "magic_tokens", ["token"], unique=True)
    op.create_index("ix_magic_tokens_user_id", "magic_tokens", ["user_id"])
    op.create_index("ix_magic_tokens_expires_at", "magic_tokens", ["expires_at"])
    op.create_index("ix_magic_tokens_used", "magic_tokens", ["used"])
    op.create_index(
        "ix_magic_tokens_user_expires", "magic_tokens", ["user_id", "expires_at"]
    )
    op.create_index(
        "ix_magic_tokens_used_expires", "magic_tokens", ["used", "expires_at"]
    )

    # Batch schedules table (scheduled batch sends to DRS)
    op.create_table(
        "batch_schedules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "email_type",
            sa.Enum("renovacao", "solicitacao", name="emailtype"),
            nullable=False,
        ),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("process_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_batch_schedules_scheduled_date", "batch_schedules", ["scheduled_date"]
    )
    op.create_index(
        "ix_batch_schedules_email_type_date",
        "batch_schedules",
        ["email_type", "scheduled_date"],
    )

    # Settings table (runtime configuration)
    op.create_table(
        "settings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_settings_key", "settings", ["key"], unique=True)

    # Seed default scheduler and app settings
    import json

    settings_data = [
        ("SCHEDULER_ENABLED", "true"),
        ("SCHEDULER_TIMEZONE", "America/Sao_Paulo"),
        ("BATCH_SEND_HOUR", "9"),
        ("BATCH_SEND_ENABLED", "true"),
        ("DRS_FOLLOWUP_HOUR", "10"),
        ("DRS_FOLLOWUP_ENABLED", "true"),
        ("AUTO_EXPIRE_HOUR", "8"),
        ("AUTO_EXPIRE_ENABLED", "true"),
        ("BATCH_INTERVAL_DAYS", "14"),
        ("DRS_DEADLINE_DAYS", json.dumps([30, 60])),
        ("AUTH_EXPIRY_DAYS", "180"),
        ("AUTH_EXPIRY_WARNING_DAYS", "30"),
        ("NUTRICAO_EXPIRY_DAYS", "120"),
        ("DATA_RETENTION_YEARS", "5"),
        ("DATA_RETENTION_ENABLED", "true"),
        ("APP_NAME", "SS-54"),
        ("FRONTEND_URL", "http://localhost:8080"),
        ("ALLOWED_ORIGINS", "http://localhost:8080"),
    ]
    for key, value in settings_data:
        op.execute(
            sa.text(
                "INSERT INTO settings (id, key, value, updated_at) VALUES (gen_random_uuid(), :key, :value, NOW()) ON CONFLICT (key) DO NOTHING"
            ).bindparams(key=key, value=value)
        )


def downgrade() -> None:
    """Downgrade schema - drop all tables and enums."""

    # Drop seeded settings
    op.execute(
        sa.text(
            "DELETE FROM settings WHERE key IN ("
            + ", ".join(
                [
                    f"'{k}'"
                    for k in [
                        "SCHEDULER_ENABLED",
                        "SCHEDULER_TIMEZONE",
                        "BATCH_SEND_HOUR",
                        "BATCH_SEND_ENABLED",
                        "DRS_FOLLOWUP_HOUR",
                        "DRS_FOLLOWUP_ENABLED",
                        "AUTO_EXPIRE_HOUR",
                        "AUTO_EXPIRE_ENABLED",
                        "BATCH_INTERVAL_DAYS",
                        "DRS_DEADLINE_DAYS",
                        "AUTH_EXPIRY_DAYS",
                        "AUTH_EXPIRY_WARNING_DAYS",
                        "NUTRICAO_EXPIRY_DAYS",
                        "DATA_RETENTION_YEARS",
                        "DATA_RETENTION_ENABLED",
                        "APP_NAME",
                        "FRONTEND_URL",
                        "ALLOWED_ORIGINS",
                    ]
                ]
            )
            + ")"
        )
    )

    # Drop tables
    op.drop_table("settings")
    op.drop_table("batch_schedules")
    op.drop_table("magic_tokens")
    op.drop_table("activity_logs")
    op.drop_table("documents")
    op.drop_table("processes")
    op.drop_table("protocol_counters")
    op.drop_table("patients")
    op.drop_table("users")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS emailtype")
    op.execute("DROP TYPE IF EXISTS requesttype")
    op.execute("DROP TYPE IF EXISTS processtype")
    op.execute("DROP TYPE IF EXISTS processstatus")
    op.execute("DROP TYPE IF EXISTS documenttype")
    op.execute("DROP TYPE IF EXISTS validationstatus")
