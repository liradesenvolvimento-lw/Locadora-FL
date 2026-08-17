import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Usa o Postgres do Railway (DATABASE_URL) quando disponível; caso contrário,
# cai para um SQLite local na mesma pasta do projeto (uso em desenvolvimento).
DB_PATH = os.path.join(os.path.dirname(__file__), "logmais_fleet.db")
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

# O Railway fornece a URL no formato "postgres://", mas o SQLAlchemy/psycopg2
# exige o prefixo "postgresql://".
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace(
        "postgres://", "postgresql://", 1
    )

# Configuração do Engine do SQLAlchemy
connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=connect_args
)

# Criação da Sessão do Banco
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Classe Base para os Modelos
Base = declarative_base()

# Dependência para obter a sessão do banco de dados nas rotas
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()