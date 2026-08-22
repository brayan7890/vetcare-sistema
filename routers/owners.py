from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Propietario, Usuario
from schemas import PropietarioCreate, PropietarioResponse
from dependencies import get_current_active_user, require_admin

router = APIRouter(prefix="/propietarios", tags=["Propietarios"])


@router.get("/", response_model=list[PropietarioResponse])
def listar_propietarios(db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    return db.query(Propietario).order_by(Propietario.id).all()


@router.get("/count")
def contar_propietarios(db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    return {"total": db.query(Propietario).count()}


@router.get("/{pid}", response_model=PropietarioResponse)
def obtener_propietario(pid: int, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    p = db.query(Propietario).filter(Propietario.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="Propietario no encontrado")
    return p


@router.post("/", response_model=PropietarioResponse, status_code=201)
def crear_propietario(data: PropietarioCreate, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    db_obj = Propietario(**data.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.put("/{pid}", response_model=PropietarioResponse)
def actualizar_propietario(pid: int, data: PropietarioCreate, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    db_obj = db.query(Propietario).filter(Propietario.id == pid).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Propietario no encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(db_obj, k, v)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.delete("/{pid}", status_code=204)
def eliminar_propietario(pid: int, db: Session = Depends(get_db), _a: Usuario = Depends(require_admin)):
    db_obj = db.query(Propietario).filter(Propietario.id == pid).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Propietario no encontrado")
    db.delete(db_obj)
    db.commit()
