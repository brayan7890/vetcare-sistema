from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from urllib.parse import quote
import bcrypt, os, re

from jose import JWTError, jwt

from database import engine, get_db, Base
from models import Propietario, Paciente, Cita, HistorialClinico, Inventario, Usuario
from schemas import (
    PropietarioCreate, PropietarioResponse,
    PacienteCreate, PacienteResponse,
    CitaCreate, CitaResponse,
    HistorialCreate, HistorialResponse,
    InventarioCreate, InventarioResponse,
    UserRegister, UserResponse, TokenResponse,
    CitaPublicaCreate,
)

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Veterinaria API", version="3.0.0")

# ── Rate limiter ─────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Demasiadas peticiones. Intenta de nuevo en 60 segundos."})


# ── CORS restringido ────────────────────────────────────────────

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:8001").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# ── Headers de seguridad ────────────────────────────────────────

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response


# ── Auth config ──────────────────────────────────────────────────

SECRET_KEY = os.getenv("SECRET_KEY", "cambiar-esta-clave-en-produccion")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
MAX_LOGIN_ATTEMPTS = 5

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def verify_password(plain, hashed):
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict):
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesion invalida o expirada", headers={"WWW-Authenticate": "Bearer"})
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


def require_admin(current_user: Usuario = Depends(get_current_user)):
    if current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="Se requieren permisos de administrador")
    return current_user


# ── WhatsApp helper ──────────────────────────────────────────────

def build_whatsapp_link(telefono: str, mensaje: str) -> str:
    num = re.sub(r"[^0-9]", "", telefono)
    if num.startswith("0"):
        num = "52" + num[1:]
    elif len(num) == 10:
        num = "52" + num
    return f"https://wa.me/{num}?text={quote(mensaje)}"


# ═══════════════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════════════

@app.post("/auth/register", response_model=TokenResponse, status_code=201)
@limiter.limit("3/minute")
async def register(request: Request, data: UserRegister, db: Session = Depends(get_db)):
    if db.query(Usuario).filter(Usuario.username == data.username).first():
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    user_count = db.query(Usuario).count()
    user = Usuario(username=data.username, hashed_password=hash_password(data.password), nombre=data.nombre, rol="admin" if user_count == 0 else "usuario")
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": user.username, "rol": user.rol})
    return TokenResponse(access_token=token, token_type="bearer", user=UserResponse.model_validate(user))


@app.post("/auth/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.username == form.username).first()
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


@app.get("/auth/me", response_model=UserResponse)
def get_me(current_user: Usuario = Depends(get_current_user)):
    return current_user


# ── Root ─────────────────────────────────────────────────────────

@app.get("/")
def root():
    return FileResponse(Path(__file__).parent / "frontend" / "index.html")


@app.get("/landing")
def landing():
    return FileResponse(Path(__file__).parent / "frontend" / "landing.html")


@app.post("/citas/publica", status_code=201)
@limiter.limit("5/minute")
async def crear_cita_publica(request: Request, data: CitaPublicaCreate, db: Session = Depends(get_db)):
    propietario = db.query(Propietario).filter(Propietario.telefono == data.telefono).first()
    if not propietario:
        propietario = Propietario(nombre=data.nombre_propietario, telefono=data.telefono)
        db.add(propietario)
        db.commit()
        db.refresh(propietario)

    paciente = db.query(Paciente).filter(
        Paciente.nombre == data.nombre_mascota,
        Paciente.propietario_id == propietario.id
    ).first()
    if not paciente:
        paciente = Paciente(nombre=data.nombre_mascota, especie=data.especie, propietario_id=propietario.id)
        db.add(paciente)
        db.commit()
        db.refresh(paciente)

    cita = Cita(
        fecha=data.fecha_hora,
        motivo=data.motivo,
        paciente_id=paciente.id,
        estado="Pendiente",
    )
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


# ═══════════════════════════════════════════════════════════════════
# PROPIETARIOS
# ═══════════════════════════════════════════════════════════════════

@app.get("/propietarios", response_model=list[PropietarioResponse])
def listar_propietarios(db: Session = Depends(get_db), _u: Usuario = Depends(get_current_user)):
    return db.query(Propietario).all()


@app.get("/propietarios/{pid}", response_model=PropietarioResponse)
def obtener_propietario(pid: int, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_user)):
    p = db.query(Propietario).filter(Propietario.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="Propietario no encontrado")
    return p


@app.post("/propietarios", response_model=PropietarioResponse, status_code=201)
def crear_propietario(data: PropietarioCreate, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_user)):
    db_obj = Propietario(**data.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@app.put("/propietarios/{pid}", response_model=PropietarioResponse)
def actualizar_propietario(pid: int, data: PropietarioCreate, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_user)):
    db_obj = db.query(Propietario).filter(Propietario.id == pid).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Propietario no encontrado")
    for k, v in data.model_dump().items():
        setattr(db_obj, k, v)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@app.delete("/propietarios/{pid}", status_code=204)
def eliminar_propietario(pid: int, db: Session = Depends(get_db), _a: Usuario = Depends(require_admin)):
    db_obj = db.query(Propietario).filter(Propietario.id == pid).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Propietario no encontrado")
    db.delete(db_obj)
    db.commit()


# ═══════════════════════════════════════════════════════════════════
# PACIENTES
# ═══════════════════════════════════════════════════════════════════

@app.get("/pacientes", response_model=list[PacienteResponse])
def listar_pacientes(db: Session = Depends(get_db), _u: Usuario = Depends(get_current_user)):
    return db.query(Paciente).all()


@app.get("/pacientes/{pid}", response_model=PacienteResponse)
def obtener_paciente(pid: int, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_user)):
    p = db.query(Paciente).filter(Paciente.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return p


@app.post("/pacientes", response_model=PacienteResponse, status_code=201)
def crear_paciente(data: PacienteCreate, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_user)):
    if not db.query(Propietario).filter(Propietario.id == data.propietario_id).first():
        raise HTTPException(status_code=404, detail="Propietario no encontrado")
    db_obj = Paciente(**data.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@app.put("/pacientes/{pid}", response_model=PacienteResponse)
def actualizar_paciente(pid: int, data: PacienteCreate, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_user)):
    db_obj = db.query(Paciente).filter(Paciente.id == pid).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    for k, v in data.model_dump().items():
        setattr(db_obj, k, v)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@app.delete("/pacientes/{pid}", status_code=204)
def eliminar_paciente(pid: int, db: Session = Depends(get_db), _a: Usuario = Depends(require_admin)):
    db_obj = db.query(Paciente).filter(Paciente.id == pid).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    db.delete(db_obj)
    db.commit()


# ═══════════════════════════════════════════════════════════════════
# CITAS (con WhatsApp)
# ═══════════════════════════════════════════════════════════════════

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


@app.get("/citas", response_model=list[CitaResponse])
def listar_citas(db: Session = Depends(get_db), _u: Usuario = Depends(get_current_user)):
    return [cita_to_response(c, db) for c in db.query(Cita).all()]


@app.get("/citas/{cid}", response_model=CitaResponse)
def obtener_cita(cid: int, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_user)):
    c = db.query(Cita).filter(Cita.id == cid).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    return cita_to_response(c, db)


@app.post("/citas", response_model=CitaResponse, status_code=201)
def crear_cita(data: CitaCreate, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_user)):
    if not db.query(Paciente).filter(Paciente.id == data.paciente_id).first():
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    db_obj = Cita(**data.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return cita_to_response(db_obj, db)


@app.put("/citas/{cid}", response_model=CitaResponse)
def actualizar_cita(cid: int, data: CitaCreate, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_user)):
    db_obj = db.query(Cita).filter(Cita.id == cid).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    for k, v in data.model_dump().items():
        setattr(db_obj, k, v)
    db.commit()
    db.refresh(db_obj)
    return cita_to_response(db_obj, db)


@app.post("/citas/{cid}/whatsapp-notificar")
def notificar_whatsapp(cid: int, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_user)):
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


@app.post("/citas/{cid}/aprobar", response_model=CitaResponse)
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


@app.delete("/citas/{cid}", status_code=204)
def eliminar_cita(cid: int, db: Session = Depends(get_db), _a: Usuario = Depends(require_admin)):
    db_obj = db.query(Cita).filter(Cita.id == cid).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    db.delete(db_obj)
    db.commit()


# ═══════════════════════════════════════════════════════════════════
# HISTORIAL CLINICO
# ═══════════════════════════════════════════════════════════════════

@app.get("/pacientes/{pid}/historial", response_model=list[HistorialResponse])
def listar_historial(pid: int, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_user)):
    if not db.query(Paciente).filter(Paciente.id == pid).first():
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return db.query(HistorialClinico).filter(HistorialClinico.paciente_id == pid).order_by(HistorialClinico.fecha.desc()).all()


@app.get("/historial/count")
def contar_historial(db: Session = Depends(get_db), _u: Usuario = Depends(get_current_user)):
    return {"count": db.query(HistorialClinico).count()}


@app.get("/inventario/count")
def contar_inventario(db: Session = Depends(get_db), _u: Usuario = Depends(get_current_user)):
    total = db.query(Inventario).count()
    bajo = db.query(Inventario).filter(Inventario.stock <= Inventario.stock_minimo).count()
    return {"total": total, "bajo_stock": bajo}


@app.get("/historial/{hid}", response_model=HistorialResponse)
def obtener_historial(hid: int, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_user)):
    h = db.query(HistorialClinico).filter(HistorialClinico.id == hid).first()
    if not h:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return h


@app.post("/pacientes/{pid}/historial", response_model=HistorialResponse, status_code=201)
def crear_historial(pid: int, data: HistorialCreate, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_user)):
    if not db.query(Paciente).filter(Paciente.id == pid).first():
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    db_obj = HistorialClinico(paciente_id=pid, **data.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@app.delete("/historial/{hid}", status_code=204)
def eliminar_historial(hid: int, db: Session = Depends(get_db), _a: Usuario = Depends(require_admin)):
    db_obj = db.query(HistorialClinico).filter(HistorialClinico.id == hid).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    db.delete(db_obj)
    db.commit()


# ═══════════════════════════════════════════════════════════════════
# INVENTARIO
# ═══════════════════════════════════════════════════════════════════

@app.get("/inventario", response_model=list[InventarioResponse])
def listar_inventario(db: Session = Depends(get_db), _u: Usuario = Depends(get_current_user)):
    return db.query(Inventario).order_by(Inventario.nombre).all()


@app.get("/inventario/bajo-stock", response_model=list[InventarioResponse])
def listar_bajo_stock(db: Session = Depends(get_db), _u: Usuario = Depends(get_current_user)):
    return db.query(Inventario).filter(Inventario.stock <= Inventario.stock_minimo).order_by(Inventario.stock).all()


@app.get("/inventario/{iid}", response_model=InventarioResponse)
def obtener_inventario(iid: int, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_user)):
    item = db.query(Inventario).filter(Inventario.id == iid).first()
    if not item:
        raise HTTPException(status_code=404, detail="Articulo no encontrado")
    return item


@app.post("/inventario", response_model=InventarioResponse, status_code=201)
def crear_inventario(data: InventarioCreate, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_user)):
    db_obj = Inventario(**data.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@app.put("/inventario/{iid}", response_model=InventarioResponse)
def actualizar_inventario(iid: int, data: InventarioCreate, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_user)):
    db_obj = db.query(Inventario).filter(Inventario.id == iid).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Articulo no encontrado")
    for k, v in data.model_dump().items():
        setattr(db_obj, k, v)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@app.post("/inventario/{iid}/stock")
def ajustar_stock(iid: int, ajuste: dict, db: Session = Depends(get_db), _u: Usuario = Depends(get_current_user)):
    db_obj = db.query(Inventario).filter(Inventario.id == iid).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Articulo no encontrado")
    cantidad = ajuste.get("cantidad", 0)
    db_obj.stock = max(0, db_obj.stock + cantidad)
    db.commit()
    db.refresh(db_obj)
    return {"id": db_obj.id, "nombre": db_obj.nombre, "stock": db_obj.stock}


@app.delete("/inventario/{iid}", status_code=204)
def eliminar_inventario(iid: int, db: Session = Depends(get_db), _a: Usuario = Depends(require_admin)):
    db_obj = db.query(Inventario).filter(Inventario.id == iid).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Articulo no encontrado")
    db.delete(db_obj)
    db.commit()
