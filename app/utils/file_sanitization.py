"""
File sanitization utilities for secure file handling.

Provides functions to sanitize:
- Filenames (security-safe, cross-platform)
- PDF content (removing JavaScript, embedded files, auto-execute actions)

Note:
- Image metadata stripping has been moved to app/services/image_processing.py
- Generic filesystem utilities have been moved to app/utils/file_utils.py
"""

import os
import re
import io
import logging

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename for safe cross-platform use.

    Removes dangerous characters and patterns that could be used for:
    - Path traversal attacks (../, ..\\)
    - Null byte injection
    - Cross-platform incompatibility (Windows reserved chars)

    Args:
        filename: Original filename to sanitize

    Returns:
        Sanitized filename safe for filesystem use

    Examples:
        >>> sanitize_filename("../../../etc/passwd")
        'etc_passwd'
        >>> sanitize_filename("file<>name.pdf")
        'file__name.pdf'
        >>> sanitize_filename("")
        'file'
    """
    if not filename:
        return "file"

    # Remove null bytes
    filename = filename.replace("\x00", "")

    # Get just the filename (remove any path components) and remove path traversal attempts
    filename = os.path.basename(filename).replace("..", "")

    # Replace Windows-dangerous characters
    for char in '<>:"|?*':
        filename = filename.replace(char, "_")

    # Keep only safe characters: alphanumeric, dash, underscore, dot, space, and unicode letters
    filename = re.sub(r"[^\w\s\-.]", "_", filename)

    # Collapse multiple consecutive underscores/spaces and remove leading/trailing underscores, spaces, and dots
    filename = re.sub(r"[_\s]+", "_", filename).strip("_. ")

    # Limit length (preserve extension if possible)
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        max_name_len = 255 - len(ext)
        filename = name[:max_name_len] + ext

    # Fallback if empty after sanitization
    if not filename:
        return "file"

    return filename


def _remove_key_if_exists(obj, key):
    """
    Remove a key from an object if it exists.

    Args:
        obj: Object supporting __contains__ and __delitem__
        key: Key to remove

    Returns:
        True if key was removed, False otherwise
    """
    if key in obj:
        del obj[key]
        return True
    return False


def _remove_dangerous_elements(pdf, logger):
    """
    Remove dangerous elements from PDF structure.

    Args:
        pdf: pikepdf.Pdf object
        logger: Logger instance

    Returns:
        bool: True if any modifications were made
    """
    modified = False

    # Remove JavaScript from Names tree
    if "/Names" in pdf.Root:
        names = pdf.Root["/Names"]
        if _remove_key_if_exists(names, "/JavaScript"):
            modified = True
            logger.info("Removed JavaScript from PDF")

        # Remove embedded files
        if _remove_key_if_exists(names, "/EmbeddedFiles"):
            modified = True
            logger.info("Removed embedded files from PDF")

    # Remove OpenAction (auto-execute on document open)
    if _remove_key_if_exists(pdf.Root, "/OpenAction"):
        modified = True
        logger.info("Removed OpenAction from PDF")

    # Remove Additional Actions from document catalog
    if _remove_key_if_exists(pdf.Root, "/AA"):
        modified = True
        logger.info("Removed document-level actions from PDF")

    # Remove Additional Actions from pages
    for i, page in enumerate(pdf.pages):
        if _remove_key_if_exists(page, "/AA"):
            modified = True
            logger.info(f"Removed page actions from page {i}")

    return modified


def sanitize_pdf(content: bytes) -> bytes:
    """
    Sanitize PDF by removing dangerous elements.

    Removes:
    - JavaScript actions
    - Embedded files
    - OpenAction (auto-execute on open)
    - Additional Actions (AA) on pages and document

    Args:
        content: Raw PDF file bytes

    Returns:
        Sanitized PDF bytes, or original bytes on failure

    Raises:
        ValueError: If PDF is password protected or critically invalid
    """
    try:
        import pikepdf
    except ImportError:
        logger.warning("pikepdf not installed, skipping PDF sanitization")
        return content

    try:
        with pikepdf.open(io.BytesIO(content)) as pdf:
            modified = _remove_dangerous_elements(pdf, logger)

            # Only re-encode if we made changes
            if modified:
                output = io.BytesIO()
                pdf.save(output)
                return output.getvalue()
            else:
                # No changes needed, return original
                return content

    except pikepdf.PasswordError:
        logger.warning("PDF is password protected, rejecting")
        raise ValueError("PDF protegido por senha não é permitido")
    except pikepdf.PdfError as e:
        logger.error(f"PDF parsing error: {e}")
        raise ValueError("PDF inválido ou corrompido. Por favor, tente outro arquivo.")
    except Exception as e:
        logger.error(f"Unexpected error during PDF sanitization: {e}")
        # Fail closed - reject file on any unexpected error
        raise ValueError(
            "Não foi possível processar este PDF. Por favor, tente outro arquivo."
        )
