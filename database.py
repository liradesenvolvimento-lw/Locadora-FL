import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Define o caminho do banco SQLite local na mesma pasta do projeto
DB_PATH = os.path.join(os.path.dirname(__file__), "logmais_fleet.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# Configuração do Engine do SQLAlchemy
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
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