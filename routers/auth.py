from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import get_db
from models import Usuario
from schemas import UserRegister, TokenResponse, UserResponse
from dependencies import (
    hash_password,
    verify_password,
    create_access_token,
    require_admin,
    get_current_active_user,
    MAX_LOGIN_ATTEMPTS,
)

router = APIRouter(prefix="/auth", tags=["Autenticacion"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(data: UserRegister, db: Session = Depends(get_db), _admin: Usuario = Depends(require_admin)):
    username = data.username.strip().lower()
    if db.query(Usuario).filter(Usuario.username == username).first():
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    user = Usuario(
        username=username,
        hashed_password=hash_password(data.password),
        nombre=data.nombre.strip(),
        rol=data.rol,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": user.username, "rol": user.rol})
    return TokenResponse(access_token=token, token_type="bearer", user=UserResponse.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    username = form.username.strip().lower()
    user = db.query(Usuario).filter(Usuario.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario o contrasena incorrectos")
    if user.bloqueado:
        raise HTTPException(status_code=423, detail="Cuenta bloqueada por multiples intentos fallidos. Espera 15 minutos.")
    if not verify_password(form.password, user.hashed_password):
        user.intentos_fallidos += 1
        if user.intentos_fallidos >= MAX_LOGIN_ATTEMPTS:
            user.bloqueado = 1
            db.commit()
            raise HTTPException(status_code=423, detail=f"Cuenta bloqueada tras {MAX_LOGIN_ATTEMPTS} intentos fallidos.")
        db.commit()
        remaining = MAX_LOGIN_ATTEMPTS - user.intentos_fallidos
        raise HTTPException(status_code=401, detail=f"Contrasena incorrecta. Te quedan {remaining} intentos.")
    user.intentos_fallidos = 0
    user.bloqueado = 0
    db.commit()
    token = create_access_token({"sub": user.username, "rol": user.rol})
    return TokenResponse(access_token=token, token_type="bearer", user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
def get_me(current_user: Usuario = Depends(get_current_active_user)):
    return current_user
