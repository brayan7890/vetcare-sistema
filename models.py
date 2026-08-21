from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
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

    mascotas = relationship("Paciente", back_populates="propietario")


class Paciente(Base):
    __tablename__ = "pacientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    especie = Column(String(50), nullable=False)
    raza = Column(String(50))
    edad = Column(Integer)
    peso = Column(String(20))
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
    notificado_whatsapp = Column(Integer, nullable=False, default=0)
    estado = Column(String(20), nullable=False, default="Pendiente")

    paciente = relationship("Paciente", back_populates="citas")


class HistorialClinico(Base):
    __tablename__ = "historial_clinico"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    motivo_consulta = Column(String(200), nullable=False)
    diagnostico = Column(Text, nullable=False)
    tratamiento = Column(Text)
    observaciones = Column(Text)
    temperatura = Column(String(10))
    peso_kg = Column(Float)
    proxima_cita = Column(DateTime)
    paciente_id = Column(Integer, ForeignKey("pacientes.id"), nullable=False)

    paciente = relationship("Paciente", back_populates="historial")


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
    rol = Column(String(20), nullable=False, default="usuario")
    intentos_fallidos = Column(Integer, nullable=False, default=0)
    bloqueado = Column(Integer, nullable=False, default=0)
