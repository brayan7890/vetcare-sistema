import re
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from models import Cita, Paciente, Propietario, Usuario
from schemas import CitaCreate, CitaResponse, CitaPublicaCreate
from dependencies import get_current_active_user, require_admin

router = APIRouter(tags=["Citas"])

WA_NUM = "51982127669"


def build_whatsapp_link(telefono: str, mensaje: str) -> str:
    num = re.sub(r"[^0-9]", "", telefono)
    if num.startswith("0"):
        num = "52" + num[1:]
    elif len(num) == 10:
        num = "52" + num
    return f"https://wa.me/{num}?text={quote(mensaje)}"


def cita_to_response(cita: Cita, db: Session) -> CitaResponse:
    resp = CitaResponse.model_validate(cita)
    paciente = db.query(Paciente).filter(Paciente.id == cita.paciente_id).first()
    if paciente:
        propietario = db.query(Propietario).filter(Propietario.id == paciente.propietario_id).first()
        if propietario and propietario.telefono:
            fecha_str = cita.fecha.strftime("%d/%m/%Y a las %H:%M")
            msg = (
                f"Hola {propietario.nombre}, le recordamos que {paciente.nombre} "
                f"tiene una cita el {fecha_str}. Motivo: {cita.motivo}. "
                f"Veterinaria VetCare."
            )
            resp.whatsapp_link = build_whatsapp_link(propietario.telefono, msg)
    return resp


@router.get("/citas", response_model=list[CitaResponse])
def listar_citas(db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    return [cita_to_response(c, db) for c in db.query(Cita).order_by(Cita.fecha.desc()).all()]


@router.get("/citas/count")
def contar_citas(db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    return {"total": db.query(Cita).count()}


@router.get("/citas/{cid}", response_model=CitaResponse)
def obtener_cita(cid: int, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    c = db.query(Cita).filter(Cita.id == cid).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    return cita_to_response(c, db)


@router.post("/citas", response_model=CitaResponse, status_code=201)
def crear_cita(data: CitaCreate, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    if not db.query(Paciente).filter(Paciente.id == data.paciente_id).first():
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    if data.veterinario_id:
        vet = db.query(Usuario).filter(Usuario.id == data.veterinario_id, Usuario.rol == "veterinario").first()
        if not vet:
            raise HTTPException(status_code=404, detail="Veterinario no encontrado")
    db_obj = Cita(**data.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return cita_to_response(db_obj, db)


@router.put("/citas/{cid}", response_model=CitaResponse)
def actualizar_cita(cid: int, data: CitaCreate, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    db_obj = db.query(Cita).filter(Cita.id == cid).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(db_obj, k, v)
    db.commit()
    db.refresh(db_obj)
    return cita_to_response(db_obj, db)


@router.post("/citas/{cid}/aprobar", response_model=CitaResponse)
def aprobar_cita(cid: int, db: Session = Depends(get_db), admin: Usuario = Depends(require_admin)):
    cita = db.query(Cita).filter(Cita.id == cid).first()
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    if cita.estado == "Confirmada":
        raise HTTPException(status_code=400, detail="La cita ya esta confirmada")
    cita.estado = "Confirmada"
    db.commit()
    db.refresh(cita)
    return cita_to_response(cita, db)


@router.post("/citas/{cid}/whatsapp-notificar")
def notificar_whatsapp(cid: int, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    cita = db.query(Cita).filter(Cita.id == cid).first()
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    paciente = db.query(Paciente).filter(Paciente.id == cita.paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    propietario = db.query(Propietario).filter(Propietario.id == paciente.propietario_id).first()
    if not propietario or not propietario.telefono:
        raise HTTPException(status_code=400, detail="Propietario sin telefono")
    fecha_str = cita.fecha.strftime("%d/%m/%Y a las %H:%M")
    msg = (
        f"Hola {propietario.nombre}, le confirmamos la cita de {paciente.nombre} "
        f"el {fecha_str}. Motivo: {cita.motivo}. "
        f"Si necesita cancelar o reprogramar, responda a este mensaje. "
        f"Veterinaria VetCare."
    )
    link = build_whatsapp_link(propietario.telefono, msg)
    cita.notificado_whatsapp = 1
    db.commit()
    return {"whatsapp_link": link, "telefono": propietario.telefono, "notificado": True}


@router.post("/citas/publica", status_code=201)
def crear_cita_publica(data: CitaPublicaCreate, request: Request, db: Session = Depends(get_db)):
    propietario = db.query(Propietario).filter(Propietario.telefono == data.telefono).first()
    if not propietario:
        propietario = Propietario(nombre=data.nombre_propietario, telefono=data.telefono)
        db.add(propietario)
        db.commit()
        db.refresh(propietario)
    paciente = db.query(Paciente).filter(
        Paciente.nombre == data.nombre_mascota,
        Paciente.propietario_id == propietario.id,
    ).first()
    if not paciente:
        paciente = Paciente(nombre=data.nombre_mascota, especie=data.especie, propietario_id=propietario.id)
        db.add(paciente)
        db.commit()
        db.refresh(paciente)
    cita = Cita(fecha=data.fecha_hora, motivo=data.motivo, paciente_id=paciente.id, estado="Pendiente")
    db.add(cita)
    db.commit()
    db.refresh(cita)
    return {
        "mensaje": "Cita registrada exitosamente",
        "cita_id": cita.id,
        "estado": "Pendiente",
        "propietario": propietario.nombre,
        "mascota": paciente.nombre,
    }


@router.delete("/citas/{cid}", status_code=204)
def eliminar_cita(cid: int, db: Session = Depends(get_db), _a: Usuario = Depends(require_admin)):
    db_obj = db.query(Cita).filter(Cita.id == cid).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    db.delete(db_obj)
    db.commit()
