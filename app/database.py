"""
Configuração de Banco de Dados e Gerenciamento de Sessão

Padrão de Gerenciamento de Transação:
- Este módulo é o ÚNICO lugar que faz commit de transações (via get_db())
- Services usam db.add() para preparar mudanças e db.flush() para escrever na transação
- Rotas chamam services e podem fazer flush se necessário para consultas
- A dependência get_db() faz commit automático ao final de cada requisição
- Isso garante gerenciamento de transações centralizado e consistente em toda a aplicação

Por que Flush Manual?
- Autoflush pode causar problemas com dependências de chave estrangeira
- Flush manual dá controle explícito sobre quando objetos são escritos
- Garante que objetos pai são feitos flush antes de filhos que os referenciam
"""

from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

# Database engine configuration
# SQLite needs check_same_thread=False for multi-threading
engine_args: dict[str, Any] = {
    "echo": settings.DEBUG,
}

if settings.DATABASE_URL.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}
elif settings.DATABASE_URL.startswith("postgresql"):
    engine_args["pool_pre_ping"] = True
    if settings.LOW_MEMORY_MODE:
        engine_args["pool_size"] = 3
        engine_args["max_overflow"] = 2
    else:
        engine_args["pool_size"] = 10
        engine_args["max_overflow"] = 20
    engine_args["pool_recycle"] = 3600
else:
    engine_args["pool_pre_ping"] = True

# Create sync engine
engine = create_engine(settings.DATABASE_URL, **engine_args)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,  # Manual flush for better control over transaction boundaries
    bind=engine,
)


class Base(DeclarativeBase):
    """Classe base para todos os modelos de banco de dados"""

    pass


def get_db():
    """
    Dependência para obter sessão do banco de dados.

    Gerenciamento de Transação:
    - Autoflush está desabilitado - flush manual quando necessário para dependências de chave estrangeira
    - Services e rotas usam db.flush() antes de operações que precisam de objetos feitos flush
    - Commit na conclusão bem-sucedida. Para operações apenas leitura isso é inofensivo.
    - Para operações de escrita isso garante que os dados sejam persistidos.
    - Rollback em erro para transações atômicas.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Inicializa tabelas do banco de dados"""
    Base.metadata.create_all(bind=engine)


def close_db():
    """Fecha conexões do banco de dados"""
    engine.dispose()
