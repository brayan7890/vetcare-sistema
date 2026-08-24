from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import HistorialClinico, Paciente, Usuario, ComprobantePago
from schemas import HistorialCreate, HistorialResponse
from dependencies import get_current_active_user, require_admin, require_veterinario

router = APIRouter(tags=["Historial Clinico"])


@router.get("/pacientes/{pid}/historial", response_model=list[HistorialResponse])
def listar_historial(pid: int, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    if not db.query(Paciente).filter(Paciente.id == pid).first():
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return (
        db.query(HistorialClinico)
        .filter(HistorialClinico.paciente_id == pid)
        .order_by(HistorialClinico.fecha.desc())
        .all()
    )


@router.get("/historial")
def listar_historial_global(db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    return (
        db.query(HistorialClinico)
        .order_by(HistorialClinico.fecha.desc())
        .all()
    )


@router.get("/historial/count")
def contar_historial(db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    return {"count": db.query(HistorialClinico).count()}


@router.get("/historial/{hid}", response_model=HistorialResponse)
def obtener_historial(hid: int, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    h = db.query(HistorialClinico).filter(HistorialClinico.id == hid).first()
    if not h:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return h


@router.post("/pacientes/{pid}/historial", response_model=HistorialResponse, status_code=201)
def crear_historial(
    pid: int,
    data: HistorialCreate,
    db: Session = Depends(get_db),
    vet: Usuario = Depends(require_veterinario),
):
    if not db.query(Paciente).filter(Paciente.id == pid).first():
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    if not data.veterinario_id:
        data.veterinario_id = vet.id
    db_obj = HistorialClinico(paciente_id=pid, **data.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.delete("/historial/{hid}", status_code=204)
def eliminar_historial(hid: int, db: Session = Depends(get_db), _a: Usuario = Depends(require_admin)):
    db_obj = db.query(HistorialClinico).filter(HistorialClinico.id == hid).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    db.delete(db_obj)
    db.commit()


@router.post("/historial/{hid}/facturar", response_model=HistorialResponse)
def vincular_factura(hid: int, data: dict, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    h = db.query(HistorialClinico).filter(HistorialClinico.id == hid).first()
    if not h:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    comprobante_id = data.get("comprobante_id")
    if not comprobante_id:
        raise HTTPException(status_code=400, detail="comprobante_id requerido")
    comp = db.query(ComprobantePago).filter(ComprobantePago.id == comprobante_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    h.comprobante_id = comprobante_id
    db.commit()
    db.refresh(h)
    return h
