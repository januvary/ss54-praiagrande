import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, Dict, Any, Tuple, List
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateError
from pathlib import Path
from sqlalchemy.orm import Session
from app.config import settings
from app.utils.file_utils import file_exists
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)


def sanitize_email_header(value: str) -> str:
    """
    Sanitize email header value to prevent header injection attacks.

    Removes newline characters that could be used to inject additional headers.

    Args:
        value: Email header value to sanitize

    Returns:
        Sanitized header value safe for use in email headers
    """
    if not value:
        return value
    return value.replace("\r", "").replace("\n", "")


class EmailService:
    def __init__(self):
        template_dir = Path(__file__).parent.parent / "templates" / "email"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Renderiza um template de email com o contexto dado."""
        return self.env.get_template(template_name).render(**context)

    def send_email(
        self,
        to: str,
        subject: str,
        template_name: str,
        context: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Envia um email usando um template.

        Returns:
            Tuple of (success: bool, error_type: Optional[str])
            error_type can be: 'config', 'connection', 'template', 'delivery'
        """
        reply_to = SettingsService.get_reply_to_email(db) if db else None
        return self.send_email_with_attachments(
            to, subject, template_name, context, db=db, reply_to=reply_to
        )

    def _validate_smtp_config(
        self, db: Optional[Session] = None
    ) -> Tuple[bool, Optional[str]]:
        smtp_host = SettingsService.get_smtp_host()
        smtp_password = SettingsService.get_smtp_password(db)
        smtp_user = SettingsService.get_smtp_user(db)

        if not all(
            [
                smtp_host,
                settings.SMTP_PORT,
                smtp_user,
                smtp_password,
            ]
        ):
            logger.error("Email configuration incomplete")
            return False, "config"
        return True, None

    def _build_email_message(
        self,
        to: str,
        subject: str,
        template_name: str,
        context: Dict[str, Any],
        attachments: List[Dict[str, str]],
        reply_to: Optional[str] = None,
    ) -> Tuple[Optional[MIMEMultipart], Optional[str]]:
        try:
            html_content = self.render_template(template_name, context)
        except TemplateError as e:
            logger.error(f"Email template error: {e}", exc_info=True)
            return None, "template"
        except Exception as e:
            logger.error(f"Unexpected error rendering template: {e}", exc_info=True)
            return None, "delivery"

        msg = MIMEMultipart("mixed")
        msg["Subject"] = sanitize_email_header(subject)
        msg["From"] = f"{settings.APP_NAME} <{SettingsService.get_smtp_user()}>"
        msg["To"] = sanitize_email_header(to)
        if reply_to:
            msg["Reply-To"] = sanitize_email_header(reply_to)

        alt_part = MIMEMultipart("alternative")
        html_part = MIMEText(html_content, "html")
        alt_part.attach(html_part)
        msg.attach(alt_part)

        for attachment in attachments:
            file_path = Path(attachment["path"])
            filename = attachment.get("filename", file_path.name)

            if not file_exists(str(file_path)):
                logger.warning(f"Attachment file not found: {file_path}")
                continue

            try:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(file_path.read_bytes())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", "attachment", filename=filename)
                msg.attach(part)
            except Exception as e:
                logger.error(f"Error attaching file {file_path}: {e}")
                continue

        return msg, None

    def _send_via_smtp(
        self, msg: MIMEMultipart, to: str, db: Optional[Session] = None
    ) -> Tuple[bool, Optional[str]]:
        smtp_host = SettingsService.get_smtp_host()
        smtp_password = SettingsService.get_smtp_password(db)
        smtp_user = SettingsService.get_smtp_user(db)

        try:
            with smtplib.SMTP(smtp_host, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, to, msg.as_string())
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}", exc_info=True)
            return False, "connection"
        except smtplib.SMTPConnectError as e:
            logger.error(f"SMTP connection failed: {e}", exc_info=True)
            return False, "connection"
        except smtplib.SMTPException as e:
            logger.error(f"SMTP delivery failed: {e}", exc_info=True)
            return False, "delivery"
        except Exception as e:
            logger.error(f"Unexpected email error: {e}", exc_info=True)
            return False, "delivery"

        return True, None

    def send_email_with_attachments(
        self,
        to: str,
        subject: str,
        template_name: str,
        context: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Dict[str, str]]] = None,
        db: Optional[Session] = None,
        reply_to: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Envia um email com anexos usando um template.

        Args:
            to: Endereço de email do destinatário
            subject: Assunto do email
            template_name: Nome do template HTML
            context: Contexto para renderizar o template
            attachments: Lista de dicionários com 'path' e 'filename'
            db: Database session for runtime settings
            reply_to: Reply-To email address (optional)

        Returns:
            Tuple of (success: bool, error_type: Optional[str])
        """
        if context is None:
            context = {}
        if attachments is None:
            attachments = []

        success, error_type = self._validate_smtp_config(db)
        if not success:
            return False, error_type

        context["app_name"] = settings.APP_NAME
        context["frontend_url"] = settings.FRONTEND_URL

        msg, error_type = self._build_email_message(
            to, subject, template_name, context, attachments, reply_to
        )
        if msg is None:
            return False, error_type

        return self._send_via_smtp(msg, to, db)


email_service = EmailService()
