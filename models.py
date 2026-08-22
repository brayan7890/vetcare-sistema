from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from database import Base


class Propietario(Base):
    __tablename__ = "propietarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    telefono = Column(String(20), nullable=False)
    email = Column(String(100))
    direccion = Column(String(200))
    ruc_dni = Column(String(20))

    mascotas = relationship("Paciente", back_populates="propietario")
    comprobantes = relationship("ComprobantePago", back_populates="propietario")


class Paciente(Base):
    __tablename__ = "pacientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    especie = Column(String(50), nullable=False)
    raza = Column(String(50))
    fecha_nacimiento = Column(String(20))
    sexo = Column(String(10))
    esterilizado = Column(Boolean, default=False)
    peso = Column(Float)
    notas = Column(Text)
    propietario_id = Column(Integer, ForeignKey("propietarios.id"), nullable=False)

    propietario = relationship("Propietario", back_populates="mascotas")
    citas = relationship("Cita", back_populates="paciente")
    historial = relationship("HistorialClinico", back_populates="paciente", cascade="all, delete-orphan")


class Cita(Base):
    __tablename__ = "citas"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, nullable=False)
    motivo = Column(String(200), nullable=False)
    diagnostico = Column(Text)
    tratamiento = Column(Text)
    paciente_id = Column(Integer, ForeignKey("pacientes.id"), nullable=False)
    veterinario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    notificado_whatsapp = Column(Integer, nullable=False, default=0)
    estado = Column(String(20), nullable=False, default="Pendiente")

    paciente = relationship("Paciente", back_populates="citas")
    veterinario = relationship("Usuario", foreign_keys=[veterinario_id])


class HistorialClinico(Base):
    __tablename__ = "historial_clinico"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    motivo_consulta = Column(String(200), nullable=False)
    diagnostico = Column(Text, nullable=False)
    tratamiento = Column(Text)
    observaciones = Column(Text)
    temperatura = Column(String(10))
    frecuencia_cardiaca = Column(String(20))
    peso_kg = Column(Float)
    proxima_cita = Column(DateTime)
    paciente_id = Column(Integer, ForeignKey("pacientes.id"), nullable=False)
    veterinario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    paciente = relationship("Paciente", back_populates="historial")
    veterinario = relationship("Usuario", foreign_keys=[veterinario_id])


class Inventario(Base):
    __tablename__ = "inventario"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    categoria = Column(String(50), nullable=False)
    descripcion = Column(Text)
    stock = Column(Integer, nullable=False, default=0)
    stock_minimo = Column(Integer, nullable=False, default=5)
    precio_compra = Column(Float, nullable=False, default=0.0)
    precio_venta = Column(Float, nullable=False, default=0.0)
    proveedor = Column(String(100))
    fecha_caducidad = Column(String(20))


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(200), nullable=False)
    nombre = Column(String(100), nullable=False)
    rol = Column(String(20), nullable=False, default="recepcionista")
    intentos_fallidos = Column(Integer, nullable=False, default=0)
    bloqueado = Column(Integer, nullable=False, default=0)


class ServicioProducto(Base):
    __tablename__ = "servicios_productos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    precio = Column(Float, nullable=False, default=0.0)
    tipo = Column(String(20), nullable=False, default="servicio")
    activo = Column(Boolean, nullable=False, default=True)

    detalles = relationship("DetalleComprobante", back_populates="servicio_producto")


class ComprobantePago(Base):
    __tablename__ = "comprobantes_pago"

    id = Column(Integer, primary_key=True, index=True)
    serie = Column(String(10), nullable=False)
    numero = Column(Integer, nullable=False)
    tipo_documento = Column(String(20), nullable=False, default="boleta")
    fecha_emision = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    cliente_nombre = Column(String(150), nullable=False)
    cliente_ruc_dni = Column(String(20))
    subtotal = Column(Float, nullable=False, default=0.0)
    igv = Column(Float, nullable=False, default=0.0)
    total = Column(Float, nullable=False, default=0.0)
    estado = Column(String(20), nullable=False, default="Pagado")
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    propietario_id = Column(Integer, ForeignKey("propietarios.id"), nullable=True)

    propietario = relationship("Propietario", back_populates="comprobantes")
    usuario = relationship("Usuario")
    detalles = relationship("DetalleComprobante", back_populates="comprobante", cascade="all, delete-orphan")


class DetalleComprobante(Base):
    __tablename__ = "detalles_comprobante"

    id = Column(Integer, primary_key=True, index=True)
    comprobante_id = Column(Integer, ForeignKey("comprobantes_pago.id"), nullable=False)
    servicio_producto_id = Column(Integer, ForeignKey("servicios_productos.id"), nullable=False)
    cantidad = Column(Integer, nullable=False, default=1)
    precio_unitario = Column(Float, nullable=False, default=0.0)
    subtotal = Column(Float, nullable=False, default=0.0)

    comprobante = relationship("ComprobantePago", back_populates="detalles")
    servicio_producto = relationship("ServicioProducto", back_populates="detalles")
