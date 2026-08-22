from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Inventario, Usuario
from schemas import InventarioCreate, InventarioResponse, StockAdjust
from dependencies import get_current_active_user, require_admin

router = APIRouter(prefix="/inventario", tags=["Inventario"])


@router.get("/", response_model=list[InventarioResponse])
def listar_inventario(db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    return db.query(Inventario).order_by(Inventario.nombre).all()


@router.get("/count")
def contar_inventario(db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    total = db.query(Inventario).count()
    bajo = db.query(Inventario).filter(Inventario.stock <= Inventario.stock_minimo).count()
    return {"total": total, "bajo_stock": bajo}


@router.get("/bajo-stock", response_model=list[InventarioResponse])
def listar_bajo_stock(db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    return db.query(Inventario).filter(Inventario.stock <= Inventario.stock_minimo).order_by(Inventario.stock).all()


@router.get("/{iid}", response_model=InventarioResponse)
def obtener_inventario(iid: int, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    item = db.query(Inventario).filter(Inventario.id == iid).first()
    if not item:
        raise HTTPException(status_code=404, detail="Articulo no encontrado")
    return item


@router.post("/", response_model=InventarioResponse, status_code=201)
def crear_inventario(data: InventarioCreate, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    db_obj = Inventario(**data.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.put("/{iid}", response_model=InventarioResponse)
def actualizar_inventario(iid: int, data: InventarioCreate, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    db_obj = db.query(Inventario).filter(Inventario.id == iid).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Articulo no encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(db_obj, k, v)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.post("/{iid}/stock")
def ajustar_stock(iid: int, ajuste: StockAdjust, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_active_user)):
    db_obj = db.query(Inventario).filter(Inventario.id == iid).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Articulo no encontrado")
    db_obj.stock = max(0, db_obj.stock + ajuste.cantidad)
    db.commit()
    db.refresh(db_obj)
    return {"id": db_obj.id, "nombre": db_obj.nombre, "stock": db_obj.stock}


@router.delete("/{iid}", status_code=204)
def eliminar_inventario(iid: int, db: Session = Depends(get_db), _a: Usuario = Depends(require_admin)):
    db_obj = db.query(Inventario).filter(Inventario.id == iid).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Articulo no encontrado")
    db.delete(db_obj)
    db.commit()
