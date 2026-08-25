from pydantic import BaseModel, field_validator, ConfigDict
from datetime import datetime
import re


# -- Auth / Users --

class UserRegister(BaseModel):
    username: str
    password: str
    nombre: str
    rol: str = "recepcionista"

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        v = v.strip().lower()
        if len(v) < 4:
            raise ValueError("El usuario debe tener minimo 4 caracteres")
        if not re.match(r"^[a-z0-9_]+$", v):
            raise ValueError("Solo letras, numeros y guion bajo (sin espacios)")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
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

    @field_validator("rol")
    @classmethod
    def validate_rol(cls, v):
        valid = ["admin", "veterinario", "recepcionista"]
        if v not in valid:
            raise ValueError(f"Rol invalido. Opciones: {', '.join(valid)}")
        return v


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    nombre: str
    rol: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# -- Propietario --

class PropietarioCreate(BaseModel):
    nombre: str
    telefono: str
    email: str | None = None
    direccion: str | None = None
    ruc_dni: str | None = None


class PropietarioResponse(PropietarioCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


# -- Paciente --

class PacienteCreate(BaseModel):
    nombre: str
    especie: str
    raza: str | None = None
    fecha_nacimiento: str | None = None
    sexo: str | None = None
    esterilizado: bool = False
    peso: float | None = None
    notas: str | None = None
    propietario_id: int


class PacienteResponse(PacienteCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


# -- Cita --

class CitaCreate(BaseModel):
    fecha: datetime
    motivo: str
    diagnostico: str | None = None
    tratamiento: str | None = None
    paciente_id: int
    veterinario_id: int | None = None


class CitaResponse(CitaCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    notificado_whatsapp: int = 0
    estado: str = "Pendiente"
    whatsapp_link: str | None = None


# -- Historial Clinico --

class HistorialCreate(BaseModel):
    motivo_consulta: str
    diagnostico: str
    tratamiento: str | None = None
    observaciones: str | None = None
    temperatura: str | None = None
    frecuencia_cardiaca: str | None = None
    peso_kg: float | None = None
    proxima_cita: datetime | None = None
    veterinario_id: int | None = None


class HistorialResponse(HistorialCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fecha: datetime
    paciente_id: int
    comprobante_id: int | None = None


# -- Inventario --

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
    model_config = ConfigDict(from_attributes=True)
    id: int


# -- Cita Publica (landing) --

class CitaPublicaCreate(BaseModel):
    nombre_propietario: str
    telefono: str
    nombre_mascota: str
    especie: str
    fecha_hora: datetime
    motivo: str


# -- Servicio / Producto --

class ServicioProductoCreate(BaseModel):
    nombre: str
    precio: float
    tipo: str = "servicio"

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v):
        if v not in ("servicio", "producto"):
            raise ValueError("Tipo debe ser 'servicio' o 'producto'")
        return v


class ServicioProductoResponse(ServicioProductoCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    activo: bool = True


# -- Comprobante / Facturacion --

class DetalleComprobanteCreate(BaseModel):
    servicio_producto_id: int | None = None
    inventario_id: int | None = None
    cantidad: int = 1
    precio_unitario: float


class DetalleComprobanteResponse(DetalleComprobanteCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    subtotal: float


class ComprobanteCreate(BaseModel):
    tipo_documento: str = "boleta"
    cliente_nombre: str
    cliente_ruc_dni: str | None = None
    propietario_id: int | None = None
    detalles: list[DetalleComprobanteCreate]

    @field_validator("tipo_documento")
    @classmethod
    def validate_tipo_doc(cls, v):
        if v not in ("boleta", "factura"):
            raise ValueError("Tipo de documento debe ser 'boleta' o 'factura'")
        return v


class ComprobanteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    serie: str
    numero: int
    tipo_documento: str
    fecha_emision: datetime
    cliente_nombre: str
    cliente_ruc_dni: str | None = None
    subtotal: float
    igv: float
    total: float
    estado: str
    usuario_id: int | None = None
    propietario_id: int | None = None
    detalles: list[DetalleComprobanteResponse] = []


# -- Stock adjust --
class StockAdjust(BaseModel):
    cantidad: int
