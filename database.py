import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Lee la variable de entorno DATABASE_URL (en Render) o usa SQLite por defecto (en tu PC)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./veterinaria.db")

# 2. Corrección de compatibilidad para URLs de Render (postgres:// -> postgresql://)
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 3. Configuración del motor según la base de datos detectada
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 4. Tu función de sesión (se mantiene intacta)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
