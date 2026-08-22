from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Paciente, Propietario, Usuario
from schemas import PacienteCreate, PacienteResponse
from dependencies import get_current_active_user, require_admin

router = APIRouter(prefix="/pacientes", tags=["Pacientes"])


@router.get("/", response_model=list[PacienteResponse])
def listar_pacientes(db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    return db.query(Paciente).order_by(Paciente.id).all()


@router.get("/count")
def contar_pacientes(db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    return {"total": db.query(Paciente).count()}


@router.get("/{pid}", response_model=PacienteResponse)
def obtener_paciente(pid: int, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    p = db.query(Paciente).filter(Paciente.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return p


@router.post("/", response_model=PacienteResponse, status_code=201)
def crear_paciente(data: PacienteCreate, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    if not db.query(Propietario).filter(Propietario.id == data.propietario_id).first():
        raise HTTPException(status_code=404, detail="Propietario no encontrado")
    db_obj = Paciente(**data.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.put("/{pid}", response_model=PacienteResponse)
def actualizar_paciente(pid: int, data: PacienteCreate, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    db_obj = db.query(Paciente).filter(Paciente.id == pid).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(db_obj, k, v)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.delete("/{pid}", status_code=204)
def eliminar_paciente(pid: int, db: Session = Depends(get_db), _a: Usuario = Depends(require_admin)):
    db_obj = db.query(Paciente).filter(Paciente.id == pid).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    db.delete(db_obj)
    db.commit()
