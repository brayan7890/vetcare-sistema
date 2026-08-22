import os
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
import bcrypt

from database import get_db
from models import Usuario

SECRET_KEY = os.getenv("SECRET_KEY", "cambiar-esta-clave-en-produccion")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
MAX_LOGIN_ATTEMPTS = 5

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sesion invalida o expirada",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(Usuario).filter(Usuario.username == username).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    if current_user.bloqueado:
        raise HTTPException(status_code=423, detail="Cuenta bloqueada")
    return current_user


def require_admin(current_user: Usuario = Depends(get_current_active_user)) -> Usuario:
    if current_user.rol not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Se requieren permisos de administrador")
    return current_user


def require_veterinario(current_user: Usuario = Depends(get_current_active_user)) -> Usuario:
    if current_user.rol not in ("admin", "superadmin", "veterinario"):
        raise HTTPException(status_code=403, detail="Se requieren permisos de veterinario")
    return current_user


def require_recepcionista(current_user: Usuario = Depends(get_current_active_user)) -> Usuario:
    if current_user.rol not in ("admin", "superadmin", "recepcionista"):
        raise HTTPException(status_code=403, detail="Se requieren permisos de recepcionista")
    return current_user
