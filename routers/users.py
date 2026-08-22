from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Usuario
from schemas import UserRegister, UserResponse
from dependencies import hash_password, require_admin

router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.get("/", response_model=list[UserResponse])
def listar_usuarios(db: Session = Depends(get_db), _admin: Usuario = Depends(require_admin)):
    return db.query(Usuario).order_by(Usuario.id).all()


@router.get("/{uid}", response_model=UserResponse)
def obtener_usuario(uid: int, db: Session = Depends(get_db), _admin: Usuario = Depends(require_admin)):
    user = db.query(Usuario).filter(Usuario.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@router.post("/", response_model=UserResponse, status_code=201)
def crear_usuario(data: UserRegister, db: Session = Depends(get_db), _admin: Usuario = Depends(require_admin)):
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
    return user


@router.put("/{uid}/rol")
def cambiar_rol(uid: int, body: dict, db: Session = Depends(get_db), _admin: Usuario = Depends(require_admin)):
    user = db.query(Usuario).filter(Usuario.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    nuevo_rol = body.get("rol")
    if nuevo_rol not in ("admin", "veterinario", "recepcionista"):
        raise HTTPException(status_code=400, detail="Rol invalido")
    user.rol = nuevo_rol
    db.commit()
    return {"mensaje": "Rol actualizado", "rol": nuevo_rol}


@router.post("/{uid}/desbloquear")
def desbloquear_usuario(uid: int, db: Session = Depends(get_db), _admin: Usuario = Depends(require_admin)):
    user = db.query(Usuario).filter(Usuario.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user.bloqueado = 0
    user.intentos_fallidos = 0
    db.commit()
    return {"mensaje": "Usuario desbloqueado"}


@router.delete("/{uid}", status_code=204)
def eliminar_usuario(uid: int, db: Session = Depends(get_db), admin: Usuario = Depends(require_admin)):
    user = db.query(Usuario).filter(Usuario.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta")
    db.delete(user)
    db.commit()
