"""
Process-related helper functions shared between routes.
"""

from typing import cast

from app.models.process import Process, RequestType
from app.content import DOCUMENT_REQUIREMENTS, RENOVATION_DOCUMENT_REQUIREMENTS
from app.constants.document_types import DOCUMENT_ID_TO_TYPE


def get_document_requirements(process_type: str, is_renovation: bool) -> list:
    """
    Get document requirements for a process type.

    Args:
        process_type: Process type string (medicamento/nutricao/bomba)
        is_renovation: Whether this is a renovation request

    Returns:
        List of document requirement dictionaries
    """
    requirements = (
        RENOVATION_DOCUMENT_REQUIREMENTS if is_renovation else DOCUMENT_REQUIREMENTS
    )
    return requirements.get(process_type, [])


def get_required_doc_types(process: Process) -> list[str]:
    """
    Get required document types for a process based on its type and request type.

    Args:
        process: Process ORM object

    Returns:
        List of document type values (strings)
    """
    requirements = (
        RENOVATION_DOCUMENT_REQUIREMENTS
        if process.request_type == RequestType.RENOVACAO
        else DOCUMENT_REQUIREMENTS
    ).get(process.type.value, [])

    return [
        DOCUMENT_ID_TO_TYPE[cast(int, doc["id"])].value
        for doc in requirements
        if doc["id"] in DOCUMENT_ID_TO_TYPE
    ]


def filter_by_request_type(
    processes: list[Process],
) -> tuple[list[Process], list[Process]]:
    """
    Split processes into renovacao and solicitacao lists.

    Args:
        processes: List of processes to filter

    Returns:
        Tuple of (renovacao_processes, solicitacao_processes)
    """
    renovacao_processes = [
        p for p in processes if p.request_type == RequestType.RENOVACAO
    ]
    solicitacao_processes = [
        p for p in processes if p.request_type != RequestType.RENOVACAO
    ]
    return renovacao_processes, solicitacao_processes
