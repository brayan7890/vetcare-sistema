from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import ServicioProducto, ComprobantePago, DetalleComprobante, Usuario
from schemas import (
    ServicioProductoCreate,
    ServicioProductoResponse,
    ComprobanteCreate,
    ComprobanteResponse,
)
from dependencies import get_current_active_user, require_admin

router = APIRouter(prefix="/facturacion", tags=["Facturacion"])

IGV_RATE = 0.18


def _next_number(db: Session, tipo: str) -> tuple[str, int]:
    prefix = "B001" if tipo == "boleta" else "F001"
    last = (
        db.query(ComprobantePago)
        .filter(ComprobantePago.serie == prefix)
        .order_by(ComprobantePago.numero.desc())
        .first()
    )
    next_num = (last.numero + 1) if last else 1
    return prefix, next_num


# ── Servicios / Productos ──────────────────────────────────────

@router.get("/servicios", response_model=list[ServicioProductoResponse])
def listar_servicios(db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    return db.query(ServicioProducto).filter(ServicioProducto.activo == True).order_by(ServicioProducto.nombre).all()


@router.post("/servicios", response_model=ServicioProductoResponse, status_code=201)
def crear_servicio(data: ServicioProductoCreate, db: Session = Depends(get_db), _a: Usuario = Depends(require_admin)):
    db_obj = ServicioProducto(**data.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.put("/servicios/{sid}", response_model=ServicioProductoResponse)
def actualizar_servicio(sid: int, data: ServicioProductoCreate, db: Session = Depends(get_db), _a: Usuario = Depends(require_admin)):
    db_obj = db.query(ServicioProducto).filter(ServicioProducto.id == sid).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(db_obj, k, v)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.delete("/servicios/{sid}", status_code=204)
def eliminar_servicio(sid: int, db: Session = Depends(get_db), _a: Usuario = Depends(require_admin)):
    db_obj = db.query(ServicioProducto).filter(ServicioProducto.id == sid).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    db_obj.activo = False
    db.commit()


# ── Comprobantes ───────────────────────────────────────────────

@router.get("/comprobantes", response_model=list[ComprobanteResponse])
def listar_comprobantes(db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    return (
        db.query(ComprobantePago)
        .order_by(ComprobantePago.id.desc())
        .all()
    )


@router.get("/comprobantes/{cid}", response_model=ComprobanteResponse)
def obtener_comprobante(cid: int, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    comp = db.query(ComprobantePago).filter(ComprobantePago.id == cid).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    return comp


@router.post("/comprobantes", response_model=ComprobanteResponse, status_code=201)
def crear_comprobante(data: ComprobanteCreate, db: Session = Depends(get_db), user: Usuario = Depends(get_current_active_user)):
    if not data.detalles:
        raise HTTPException(status_code=400, detail="El comprobante debe tener al menos un item")

    for det in data.detalles:
        sp = db.query(ServicioProducto).filter(ServicioProducto.id == det.servicio_producto_id).first()
        if not sp:
            raise HTTPException(status_code=404, detail=f"Servicio/Producto ID {det.servicio_producto_id} no encontrado")

    serie, numero = _next_number(db, data.tipo_documento)

    total_bruto = sum(d.cantidad * d.precio_unitario for d in data.detalles)
    subtotal = round(total_bruto / (1 + IGV_RATE), 2)
    igv = round(total_bruto - subtotal, 2)

    comprobante = ComprobantePago(
        serie=serie,
        numero=numero,
        tipo_documento=data.tipo_documento,
        cliente_nombre=data.cliente_nombre,
        cliente_ruc_dni=data.cliente_ruc_dni,
        subtotal=subtotal,
        igv=igv,
        total=total_bruto,
        estado="Pagado",
        usuario_id=user.id,
        propietario_id=data.propietario_id,
    )
    db.add(comprobante)
    db.flush()

    for det in data.detalles:
        det_subtotal = det.cantidad * det.precio_unitario
        detalle = DetalleComprobante(
            comprobante_id=comprobante.id,
            servicio_producto_id=det.servicio_producto_id,
            cantidad=det.cantidad,
            precio_unitario=det.precio_unitario,
            subtotal=det_subtotal,
        )
        db.add(detalle)

    db.commit()
    db.refresh(comprobante)
    return comprobante


@router.post("/comprobantes/{cid}/anular")
def anular_comprobante(cid: int, db: Session = Depends(get_db), _a: Usuario = Depends(require_admin)):
    comp = db.query(ComprobantePago).filter(ComprobantePago.id == cid).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    if comp.estado == "Anulado":
        raise HTTPException(status_code=400, detail="El comprobante ya esta anulado")
    comp.estado = "Anulado"
    db.commit()
    return {"mensaje": "Comprobante anulado"}
