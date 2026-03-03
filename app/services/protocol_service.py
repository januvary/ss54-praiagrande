"""
Serviço de Protocolos

Gerencia a geração de números de protocolo de forma thread-safe.
Usa bloqueios em nível de banco de dados para prevenir condições de corrida.
"""

from sqlalchemy.orm import Session
from typing import Optional

from app.models.protocol_counter import ProtocolCounter


def get_or_create_counter(db: Session, year: int) -> ProtocolCounter:
    """
    Obtém ou cria o contador de protocolo para um determinado ano.
    Usa bloqueios em nível de banco de dados para prevenir condições de corrida.

    Args:
        db: Sessão do banco de dados
        year: Ano para obter ou criar contador

    Returns:
        Objeto ProtocolCounter com o contador obtido ou criado

    Raises:
        ValueError: Se falhar ao criar contador devido a erro de concorrência
    """
    counter = db.query(ProtocolCounter).filter_by(year=year).with_for_update().first()

    if not counter:
        try:
            counter = ProtocolCounter(year=year, last_sequence=0)
            db.add(counter)
            db.flush()
        except Exception as e:
            db.rollback()
            counter = (
                db.query(ProtocolCounter).filter_by(year=year).with_for_update().first()
            )
            if not counter:
                raise ValueError(f"Falha ao criar contador de protocolo: {e}")

    return counter


def generate_protocol_number(
    db: Session, year: int, suffix: Optional[str] = None
) -> str:
    """
    Gera um número de protocolo único para o ano determinado.

    Usa bloqueios em nível de linha na tabela protocol_counters para prevenir
    condições de corrida. Formato: SS54-YYYY-XXXXX ou SS54-YYYY-XXXXX-R para
    renovações.

    Thread-safe: Chamadas concorrentes múltiplas serão bloqueadas e serializadas.

    Args:
        db: Sessão do banco de dados
        year: Ano para gerar protocolo
        suffix: Sufixo opcional para o número de protocolo (ex: "R" para renovações)

    Returns:
        String com o número de protocolo gerado

    Example:
        >>> generate_protocol_number(db, 2024)
        "SS54-2024-00001"
        >>> generate_protocol_number(db, 2024, suffix="R")
        "SS54-2024-00002-R"
    """
    counter = get_or_create_counter(db, year)

    counter.last_sequence += 1

    protocol = f"SS54-{year}-{counter.last_sequence:05d}"
    if suffix:
        protocol += f"-{suffix}"

    return protocol
