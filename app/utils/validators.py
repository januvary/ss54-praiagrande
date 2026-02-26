"""
Utilitários de validação para o SS-54.

Este módulo contém:

1. **Validadores de Formulário**: Validação de campos de entrada do usuário
2. **Validadores de Domínio**: Validação específica de Process

Para validação de UUIDs, use app.utils.uuid_utils.validate_uuid()

Para segurança de redirecionamento, use app.utils.security_utils
(is_safe_redirect, sanitize_redirect)

Para utilitários de resposta HTTP, use app.utils.response_utils
(set_cookie)

Padrões de Validação:
---------------------
Este módulo usa diferentes padrões dependendo do contexto:

- **Padrão de Exceção**: Lança HTTPException (para validação de rota)
  Uso: validate_process_type(), validate_process_expired()

- **Padrão de Tupla**: Retorna (valor, erros) (para validação de formulário)
  Uso: validate_name(), validate_phone()

- **Padrão de Erros Apenas**: Retorna lista de erros (quando valor já está disponível)
  Uso: validate_date_of_birth()
"""

import re
from datetime import date
from typing import Optional

from fastapi import HTTPException

from app.content import PROCESS_TYPES
from app.models.process import Process, ProcessStatus

# ============================================================
# SEÇÃO 1: Validadores de Campos de Formulário
# ============================================================
# Validação de entradas do usuário em formulários.
# Padrão: Retornam tupla (valor_sanitizado, lista_de_erros)
# ou apenas lista_de_erros quando o valor já está disponível.


def validate_name(name: Optional[str]) -> tuple[str, list[str]]:
    """
    Valida e sanitiza um campo de nome.

    Padrão: Tupla (valor, erros)

    Regras de validação:
    - Obrigatório (não pode estar vazio)
    - Mínimo 2 caracteres
    - Máximo 255 caracteres
    - Apenas letras (incluindo acentuadas), espaços, apóstrofos e hífens

    Args:
        name: A string de nome para validar

    Returns:
        Tupla de (nome_sanitizado, lista_de_erros)
        - nome_sanitizado: Nome com espaços removidos das extremidades
        - lista_de_erros: Lista vazia se válido, ou mensagens de erro
    """
    errors = []
    name = (name or "").strip()

    if not name:
        errors.append("Nome é obrigatório")
    elif len(name) < 2:
        errors.append("Nome deve ter pelo menos 2 caracteres")
    elif len(name) > 255:
        errors.append("Nome muito longo (máximo 255 caracteres)")
    else:
        if not re.match(r"^[a-zA-ZÀ-ÿ\s'\-]+$", name):
            errors.append(
                "Nome deve conter apenas letras, espaços, apóstrofos ou hífens"
            )

    return name, errors


def validate_phone(phone: Optional[str]) -> tuple[str, list[str]]:
    """
    Valida um número de telefone brasileiro.

    Padrão: Tupla (valor, erros)

    Aceita formatos de entrada:
    - (XX) XXXXX-XXXX (celular com máscara)
    - (XX) XXXX-XXXX (fixo com máscara)
    - XXXXXXXXXXX (dígitos brutos, 10 ou 11 dígitos)

    Regras de validação:
    - 10 dígitos (fixo): DDD (11-99) + número de 8 dígitos
    - 11 dígitos (celular): DDD (11-99) + 9 + número de 8 dígitos

    Args:
        phone: A string de telefone para validar

    Returns:
        Tupla de (telefone_original, lista_de_erros)
        - telefone_original: Valor de entrada sem modificação
        - lista_de_erros: Lista vazia se válido, ou mensagens de erro

    Note:
        A validação extrai dígitos internamente mas retorna o valor original.
        Para obter apenas dígitos, processe externamente com re.sub(r"\\D", "", phone).
    """
    errors = []
    phone = phone or ""

    digits = re.sub(r"\D", "", phone)

    if not digits:
        errors.append("Telefone é obrigatório")
    elif len(digits) not in (10, 11):
        errors.append("Telefone deve ter 10 ou 11 dígitos (DDD + número)")
    else:
        ddd = int(digits[:2])
        if ddd < 11 or ddd > 99:
            errors.append("DDD inválido")

        if len(digits) == 11 and digits[2] != "9":
            errors.append("Número de celular deve começar com 9")

    return phone, errors


def validate_date_of_birth(dob: date) -> list[str]:
    """
    Valida uma data de nascimento.

    Padrão: Apenas erros (valor já disponível como parâmetro tipado)

    Regras de validação:
    - Não pode ser no futuro
    - Ano deve ser >= 1900

    Args:
        dob: A data de nascimento para validar (objeto date)

    Returns:
        Lista de mensagens de erro (vazia se válido)
    """
    errors = []
    today = date.today()

    if dob > today:
        errors.append("Data de nascimento não pode ser no futuro")
    elif dob.year < 1900:
        errors.append("Data de nascimento inválida (ano muito antigo)")

    return errors


# ============================================================
# SEÇÃO 2: Validadores de Domínio (Process)
# ============================================================
# Validação específica da entidade Process.
# Padrão: Lançam HTTPException para interromper fluxo de rota.


def validate_process_type(process_type: str) -> str:
    """
    Valida se um tipo de processo é válido.

    Padrão: Exceção (lança HTTPException 404 se inválido)

    Tipos válidos são definidos em app.content.PROCESS_TYPES:
    - "medicamento"
    - "nutricao"
    - "bomba"

    Args:
        process_type: String do tipo de processo

    Returns:
        O mesmo process_type se válido

    Raises:
        HTTPException: 404 se o tipo de processo não existir
    """
    if process_type not in PROCESS_TYPES:
        raise HTTPException(status_code=404, detail="Tipo de processo não encontrado")
    return process_type


def validate_process_expired(process: Process) -> None:
    """
    Valida que um processo está com status EXPIRADO.

    Padrão: Exceção (lança HTTPException 400 se não expirado)

    Usado para garantir que apenas processos expirados possam ser renovados.

    Args:
        process: Objeto ORM Process

    Raises:
        HTTPException: 400 se o processo não estiver expirado
    """
    if process.status != ProcessStatus.EXPIRADO:
        raise HTTPException(
            status_code=400, detail="Apenas processos expirados podem ser renovados"
        )
