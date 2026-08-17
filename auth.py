import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

import models
from database import get_db

# Em produção, defina a variável de ambiente JWT_SECRET_KEY no Railway.
# Sem ela, é usado um valor padrão (não use isso em produção real).
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "logmais-fleet-dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def authenticate_user(db: Session, username: str, password: str) -> Optional[models.Usuario]:
    user = db.query(models.Usuario).filter(models.Usuario.username == username).first()
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.Usuario).filter(models.Usuario.username == username).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def seed_default_admin(db: Session) -> None:
    """Cria um usuário administrador padrão caso nenhum usuário exista ainda."""
    if db.query(models.Usuario).count() > 0:
        return

    default_username = os.getenv("ADMIN_USERNAME", "admin")
    default_password = os.getenv("ADMIN_PASSWORD", "admin123")

    admin = models.Usuario(
        username=default_username,
        hashed_password=get_password_hash(default_password),
        nome_completo="Administrador",
        is_active=True,
    )
    db.add(admin)
    db.commit()
    print(
        f"[auth] Usuário administrador padrão criado: '{default_username}'. "
        "Defina ADMIN_USERNAME/ADMIN_PASSWORD e troque a senha em produção."
    )
