"""
Document Type Constants

Centralized mapping between frontend document IDs and backend DocumentType enum.
This file should be kept in sync with app/content.py
"""

from app.models.document import DocumentType

# Document ID mappings from frontend content.py
# These MUST match the IDs in DOCUMENT_REQUIREMENTS
DOCUMENT_ID_TO_TYPE = {
    1: DocumentType.FORMULARIO,
    2: DocumentType.DECLARACAO,
    3: DocumentType.RECEITA,
    4: DocumentType.RELATORIO,
    5: DocumentType.DOCUMENTO_PESSOAL,
    6: DocumentType.EXAME,
}

# Human-readable names for logging and display
DOCUMENT_TYPE_NAMES = {
    DocumentType.FORMULARIO: "Formulário de Avaliação",
    DocumentType.DECLARACAO: "Declaração de Conflito de Interesses",
    DocumentType.RECEITA: "Receita Médica",
    DocumentType.RELATORIO: "Relatório Médico",
    DocumentType.DOCUMENTO_PESSOAL: "Documentos Pessoais",
    DocumentType.EXAME: "Exames Complementares",
    DocumentType.PDF_COMBINADO: "PDF Combinado",
    DocumentType.OUTRO: "Outro",
}
