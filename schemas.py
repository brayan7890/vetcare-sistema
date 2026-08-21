from pydantic import BaseModel, field_validator
from datetime import datetime
import re


# ── Auth ─────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    username: str
    password: str
    nombre: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        if len(v) < 4:
            raise ValueError("El usuario debe tener minimo 4 caracteres")
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Solo letras, numeros y guion bajo")
        return v

    @field_validator("password")
    @classmethod
    def validate_password_field(cls, v):
        errors = []
        if len(v) < 8:
            errors.append("Minimo 8 caracteres")
        if not re.search(r"[A-Z]", v):
            errors.append("Al menos una mayuscula")
        if not re.search(r"[a-z]", v):
            errors.append("Al menos una minuscula")
        if not re.search(r"\d", v):
            errors.append("Al menos un numero")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            errors.append("Al menos un caracter especial (!@#$%^&*)")
        if errors:
            raise ValueError("; ".join(errors))
        return v


class UserResponse(BaseModel):
    id: int
    username: str
    nombre: str
    rol: str
    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# ── Propietario ──────────────────────────────────────────────────

class PropietarioCreate(BaseModel):
    nombre: str
    telefono: str
    email: str | None = None
    direccion: str | None = None


class PropietarioResponse(PropietarioCreate):
    id: int
    model_config = {"from_attributes": True}


# ── Paciente ─────────────────────────────────────────────────────

class PacienteCreate(BaseModel):
    nombre: str
    especie: str
    raza: str | None = None
    edad: int | None = None
    peso: str | None = None
    notas: str | None = None
    propietario_id: int


class PacienteResponse(PacienteCreate):
    id: int
    model_config = {"from_attributes": True}


# ── Cita ─────────────────────────────────────────────────────────

class CitaCreate(BaseModel):
    fecha: datetime
    motivo: str
    diagnostico: str | None = None
    tratamiento: str | None = None
    paciente_id: int


class CitaResponse(CitaCreate):
    id: int
    notificado_whatsapp: int = 0
    estado: str = "Pendiente"
    whatsapp_link: str | None = None
    model_config = {"from_attributes": True}


# ── Historial Clinico ────────────────────────────────────────────

class HistorialCreate(BaseModel):
    motivo_consulta: str
    diagnostico: str
    tratamiento: str | None = None
    observaciones: str | None = None
    temperatura: str | None = None
    peso_kg: float | None = None
    proxima_cita: datetime | None = None


class HistorialResponse(HistorialCreate):
    id: int
    fecha: datetime
    paciente_id: int
    model_config = {"from_attributes": True}


# ── Inventario ───────────────────────────────────────────────────

class InventarioCreate(BaseModel):
    nombre: str
    categoria: str
    descripcion: str | None = None
    stock: int = 0
    stock_minimo: int = 5
    precio_compra: float = 0.0
    precio_venta: float = 0.0
    proveedor: str | None = None
    fecha_caducidad: str | None = None


class InventarioResponse(InventarioCreate):
    id: int
    model_config = {"from_attributes": True}


# ── Cita Publica (landing) ───────────────────────────────────────

class CitaPublicaCreate(BaseModel):
    nombre_propietario: str
    telefono: str
    nombre_mascota: str
    especie: str
    fecha_hora: datetime
    motivo: str
