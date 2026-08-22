import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from database import engine, Base
from dependencies import create_access_token, hash_password, verify_password

load_dotenv()

# -- Create tables + sync schema --
Base.metadata.create_all(bind=engine)


def _sync_schema():
    """Add missing columns to existing tables (safe for SQLite & PostgreSQL)."""
    from sqlalchemy import text, inspect as sa_inspect

    is_pg = "postgresql" in str(engine.url)
    insp = sa_inspect(engine)

    migrations = {
        "propietarios": [
            ("direccion", "VARCHAR(200)", "VARCHAR(200)"),
            ("ruc_dni", "VARCHAR(20)", "VARCHAR(20)"),
        ],
        "pacientes": [
            ("fecha_nacimiento", "VARCHAR(20)", "VARCHAR(20)"),
            ("sexo", "VARCHAR(10)", "VARCHAR(10)"),
            ("esterilizado", "BOOLEAN DEFAULT 0", "BOOLEAN DEFAULT FALSE"),
            ("peso", "FLOAT", "DOUBLE PRECISION"),
            ("notas", "TEXT", "TEXT"),
        ],
        "citas": [
            ("veterinario_id", "INTEGER", "INTEGER"),
            ("notificado_whatsapp", "INTEGER DEFAULT 0", "INTEGER DEFAULT 0"),
            ("estado", "VARCHAR(20) DEFAULT 'Pendiente'", "VARCHAR(20) DEFAULT 'Pendiente'"),
        ],
        "historial_clinico": [
            ("observaciones", "TEXT", "TEXT"),
            ("frecuencia_cardiaca", "VARCHAR(20)", "VARCHAR(20)"),
            ("peso_kg", "FLOAT", "DOUBLE PRECISION"),
            ("proxima_cita", "DATETIME", "TIMESTAMP"),
            ("veterinario_id", "INTEGER", "INTEGER"),
        ],
        "inventario": [
            ("descripcion", "TEXT", "TEXT"),
            ("fecha_caducidad", "VARCHAR(20)", "VARCHAR(20)"),
        ],
        "usuarios": [
            ("intentos_fallidos", "INTEGER DEFAULT 0", "INTEGER DEFAULT 0"),
            ("bloqueado", "INTEGER DEFAULT 0", "INTEGER DEFAULT 0"),
        ],
        "servicios_productos": [],
        "comprobantes_pago": [],
        "detalles_comprobante": [],
    }

    with engine.connect() as conn:
        for table, columns in migrations.items():
            if table not in insp.get_table_names():
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            for col_name, sqlite_type, pg_type in columns:
                if col_name in existing:
                    continue
                col_type = pg_type if is_pg else sqlite_type
                try:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"))
                    conn.commit()
                    print(f">>> Migration: added {table}.{col_name}")
                except Exception:
                    pass


_sync_schema()

app = FastAPI(title="Veterinaria API", version="4.0.0")

# -- Rate limiter --
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Demasiadas peticiones. Intenta de nuevo en 60 segundos."})


# -- CORS --
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:8001").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# -- Security headers --
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


# -- Seed admin user if no users exist --
@app.on_event("startup")
def seed_admin():
    from models import Usuario
    from database import SessionLocal
    db = SessionLocal()
    try:
        if db.query(Usuario).count() == 0:
            admin = Usuario(
                username="admin",
                hashed_password=hash_password("Admin123!"),
                nombre="Administrador",
                rol="admin",
            )
            db.add(admin)
            db.commit()
            print(">>> Admin user created: admin / Admin123!")
        else:
            admin = db.query(Usuario).filter(Usuario.username == "admin").first()
            if admin:
                admin.hashed_password = hash_password("Admin123!")
                admin.intentos_fallidos = 0
                admin.bloqueado = 0
                db.commit()
                print(">>> Admin user reset: admin / Admin123!")
    finally:
        db.close()


# -- Include routers --
from routers.auth import router as auth_router
from routers.users import router as users_router
from routers.owners import router as owners_router
from routers.pets import router as pets_router
from routers.appointments import router as appointments_router
from routers.medical_history import router as medical_history_router
from routers.inventory import router as inventory_router
from routers.billing import router as billing_router

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(owners_router)
app.include_router(pets_router)
app.include_router(appointments_router)
app.include_router(medical_history_router)
app.include_router(inventory_router)
app.include_router(billing_router)


# -- Static files --
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "frontend" / "static"), name="static")


# -- Static routes --
@app.get("/")
def root():
    return FileResponse(Path(__file__).parent / "frontend" / "index.html")


@app.get("/landing")
def landing():
    return FileResponse(Path(__file__).parent / "frontend" / "landing.html")
