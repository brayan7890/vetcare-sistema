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

# -- Create/sync schema --
Base.metadata.create_all(bind=engine)


def _sync_schema():
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


# -- Seed admin + datos de prueba --
@app.on_event("startup")
def seed_admin():
    from models import Usuario, Propietario, Paciente, Cita, HistorialClinico, Inventario, ServicioProducto, ComprobantePago, DetalleComprobante
    from database import SessionLocal
    from datetime import datetime, timedelta, timezone

    db = SessionLocal()
    try:
        # --- Admin ---
        if db.query(Usuario).count() == 0:
            admin = Usuario(
                username="admin",
                hashed_password=hash_password("Admin123!"),
                nombre="Administrador",
                rol="admin",
            )
            vet = Usuario(
                username="vet01",
                hashed_password=hash_password("Vet1234!"),
                nombre="Dra. Carolina Mendez",
                rol="veterinario",
            )
            recep = Usuario(
                username="recep01",
                hashed_password=hash_password("Recep1234!"),
                nombre="Maria Lopez",
                rol="recepcionista",
            )
            db.add_all([admin, vet, recep])
            db.commit()
            print(">>> Usuarios creados: admin / Admin123! | vet01 / Vet1234! | recep01 / Recep1234!")
        else:
            admin = db.query(Usuario).filter(Usuario.username == "admin").first()
            if admin:
                admin.hashed_password = hash_password("Admin123!")
                admin.intentos_fallidos = 0
                admin.bloqueado = 0
                db.commit()
                print(">>> Admin user reset: admin / Admin123!")

        # --- Datos de prueba solo si propietarios esta vacio ---
        if db.query(Propietario).count() > 0:
            print(">>> Ya existen datos de prueba, omitiendo seeding.")
            return

        now = datetime.now(timezone.utc)

        # Propietarios
        props_data = [
            {"nombre": "Carlos Ramirez Torres", "telefono": "982127669", "email": "carlos.ramirez@gmail.com", "direccion": "Av. Javier Prado Este 4600, Santiago de Surco", "ruc_dni": "45218963"},
            {"nombre": "Ana Maria Gutierrez", "telefono": "912345678", "email": "ana.gutierrez@outlook.com", "direccion": "Jr. de la Union 520, Cercado de Lima", "ruc_dni": "70123456"},
            {"nombre": "Luis Fernando Castillo", "telefono": "945612378", "email": "luis.castillo@hotmail.com", "direccion": "Calle Los Olivos 123, San Martin de Porres", "ruc_dni": "10325678"},
            {"nombre": "Maria Elena Diaz Vargas", "telefono": "978456123", "email": "maria.diaz@yahoo.com", "direccion": "Av. La Marina 2050, San Miguel", "ruc_dni": "20456789"},
            {"nombre": "Jorge Luis Mendoza", "telefono": "963258741", "email": "jorge.mendoza@gmail.com", "direccion": "Calle Belen 890, Breña", "ruc_dni": "41987654"},
        ]
        props = []
        for pd in props_data:
            p = Propietario(**pd)
            db.add(p)
            props.append(p)
        db.flush()

        # Mascotas
        mascotas_data = [
            {"nombre": "Max", "especie": "Perro", "raza": "Golden Retriever", "fecha_nacimiento": "2021-03-15", "sexo": "Macho", "esterilizado": True, "peso": 32.5, "notas": "Muy activo, le gusta jugar", "propietario_id": props[0].id},
            {"nombre": "Luna", "especie": "Gato", "raza": "Siamés", "fecha_nacimiento": "2022-07-20", "sexo": "Hembra", "esterilizado": True, "peso": 4.2, "notas": "Gato domestico, vacunas al dia", "propietario_id": props[0].id},
            {"nombre": "Rocky", "especie": "Perro", "raza": "Pastor Aleman", "fecha_nacimiento": "2020-11-05", "sexo": "Macho", "esterilizado": False, "peso": 38.0, "notas": "Guardian, requiere paseos diarios", "propietario_id": props[1].id},
            {"nombre": "Mishi", "especie": "Gato", "raza": "Persa", "fecha_nacimiento": "2023-01-10", "sexo": "Hembra", "esterilizado": False, "peso": 3.8, "notas": "Pelo largo, necesita cepillado semanal", "propietario_id": props[2].id},
            {"nombre": "Toby", "especie": "Perro", "raza": "Labrador", "fecha_nacimiento": "2022-05-22", "sexo": "Macho", "esterilizado": True, "peso": 29.0, "notas": "Sobrepeso, dieta controlada", "propietario_id": props[2].id},
            {"nombre": "Nina", "especie": "Perro", "raza": "French Poodle", "fecha_nacimiento": "2023-09-01", "sexo": "Hembra", "esterilizado": True, "peso": 6.5, "notas": "Pelo rizado, sensible al calor", "propietario_id": props[3].id},
            {"nombre": "Simba", "especie": "Gato", "raza": "Maine Coon", "fecha_nacimiento": "2021-12-25", "sexo": "Macho", "esterilizado": True, "peso": 7.1, "notas": "Gato grande, muy carinoso", "propietario_id": props[4].id},
        ]
        mascotas = []
        for md in mascotas_data:
            m = Paciente(**md)
            db.add(m)
            mascotas.append(m)
        db.flush()

        # Citas
        vets = db.query(Usuario).filter(Usuario.rol == "veterinario").all()
        vet_id = vets[0].id if vets else None
        citas_data = [
            {"fecha": now - timedelta(days=14, hours=3), "motivo": "Vacunacion anual", "diagnostico": "Paciente sano", "tratamiento": "Aplicacion de vacuna antirrabica", "paciente_id": mascotas[0].id, "veterinario_id": vet_id, "notificado_whatsapp": 1, "estado": "Atendido"},
            {"fecha": now - timedelta(days=10, hours=2), "motivo": "Control de peso", "diagnostico": "Sobrepeso leve", "tratamiento": "Dieta balanceada, reducir racion 20%", "paciente_id": mascotas[4].id, "veterinario_id": vet_id, "notificado_whatsapp": 1, "estado": "Atendido"},
            {"fecha": now - timedelta(days=7, hours=1), "motivo": "Vacuna triple felina", "diagnostico": "Saludable", "tratamiento": "Aplicacion vacuna trivalente felina", "paciente_id": mascotas[1].id, "veterinario_id": vet_id, "notificado_whatsapp": 1, "estado": "Atendido"},
            {"fecha": now - timedelta(days=3, hours=4), "motivo": "Corte de uñas y limpieza dental", "diagnostico": "Leve sarro dental", "tratamiento": "Profilaxis dental, limpieza de oidos", "paciente_id": mascotas[6].id, "veterinario_id": vet_id, "notificado_whatsapp": 0, "estado": "Cancelado"},
            {"fecha": now + timedelta(hours=3), "motivo": "Consulta por diarrea", "diagnostico": None, "tratamiento": None, "paciente_id": mascotas[2].id, "veterinario_id": vet_id, "notificado_whatsapp": 0, "estado": "Pendiente"},
            {"fecha": now + timedelta(days=1, hours=2), "motivo": "Desparasitacion interna", "diagnostico": None, "tratamiento": None, "paciente_id": mascotas[3].id, "veterinario_id": vet_id, "notificado_whatsapp": 0, "estado": "Pendiente"},
            {"fecha": now + timedelta(days=2, hours=5), "motivo": "Revision post-operatoria esterilizacion", "diagnostico": None, "tratamiento": None, "paciente_id": mascotas[5].id, "veterinario_id": vet_id, "notificado_whatsapp": 0, "estado": "Pendiente"},
            {"fecha": now + timedelta(days=4, hours=1), "motivo": "Control vacunas cachorro", "diagnostico": None, "tratamiento": None, "paciente_id": mascotas[3].id, "veterinario_id": vet_id, "notificado_whatsapp": 0, "estado": "Pendiente"},
        ]
        for cd in citas_data:
            db.add(Cita(**cd))
        db.flush()

        # Historial clinico
        hist_data = [
            {"fecha": now - timedelta(days=14), "motivo_consulta": "Vacunacion anual", "diagnostico": "Paciente sano, sin signos clinicos de enfermedad. Peso adecuado para raza y edad.", "tratamiento": "Aplicacion vacuna antirrabica. Reforzar calendario de vacunacion proximo anio.", "temperatura": "38.5", "frecuencia_cardiaca": "90 lpm", "peso_kg": 32.5, "paciente_id": mascotas[0].id, "veterinario_id": vet_id},
            {"fecha": now - timedelta(days=10), "motivo_consulta": "Control de peso - labrador con sobrepeso", "diagnostico": "Sobrepeso leve (IMC 28.3). Sin problemas articulares.", "tratamiento": "Dieta HP Metabolic Hill's, 180g c/12h. Paseos 45min diarios. Control en 30 dias.", "temperatura": "38.8", "frecuencia_cardiaca": "95 lpm", "peso_kg": 29.0, "proxima_cita": now + timedelta(days=20), "paciente_id": mascotas[4].id, "veterinario_id": vet_id},
            {"fecha": now - timedelta(days=7), "motivo_consulta": "Vacuna triple felina", "diagnostico": "Gato sano, peso ideal. Se observa良好的 estado corporal.", "tratamiento": "Aplicacion vacuna trivalente felina (Panleucopenia, Calicivirus, Herpesvirus). Proxima dosis en 4 semanas.", "temperatura": "38.2", "frecuencia_cardiaca": "180 lpm", "peso_kg": 4.2, "paciente_id": mascotas[1].id, "veterinario_id": vet_id},
            {"fecha": now - timedelta(days=3), "motivo_consulta": "Profilaxis dental yRevision general", "diagnostico": "Sarro dental grado II. Gingivitis leve. Oidos limpios.", "tratamiento": "Profilaxis dental completa. Enjuague con clorhexidina 7 dias. Control en 6 meses.", "temperatura": "38.4", "frecuencia_cardiaca": "140 lpm", "peso_kg": 7.1, "paciente_id": mascotas[6].id, "veterinario_id": vet_id},
            {"fecha": now - timedelta(days=5), "motivo_consulta": "Revisar piel - alopecia en zona lumbar", "diagnostico": "Dermatitis alergica leve. Sin infeccion secundaria.", "tratamiento": "Shampoo medicado con clorhexidina 2x/semana. Suplemento omega-3. Reevaluar en 15 dias.", "temperatura": "38.6", "frecuencia_cardiaca": "100 lpm", "peso_kg": 38.0, "paciente_id": mascotas[2].id, "veterinario_id": vet_id},
            {"fecha": now - timedelta(days=2), "motivo_consulta": "Dolor abdominal leve", "diagnostico": "Gastroenteritis aguda. Sin cuerpo extraño en radiografia.", "tratamiento": "Metronidazol 250mg c/12h x 5 dias. Dieta blanca (arroz + pollo) x 3 dias. Hidratacion oral frecuente.", "temperatura": "39.1", "frecuencia_cardiaca": "110 lpm", "peso_kg": 6.5, "proxima_cita": now + timedelta(days=3), "paciente_id": mascotas[5].id, "veterinario_id": vet_id},
        ]
        for hd in hist_data:
            db.add(HistorialClinico(**hd))
        db.flush()

        # Servicios / Productos
        servicios_data = [
            {"nombre": "Consulta General", "precio": 40.0, "tipo": "servicio", "activo": True},
            {"nombre": "Vacuna Antirrabica", "precio": 35.0, "tipo": "servicio", "activo": True},
            {"nombre": "Vacuna Triple Felina", "precio": 55.0, "tipo": "servicio", "activo": True},
            {"nombre": "Desparasitacion Interna", "precio": 25.0, "tipo": "servicio", "activo": True},
            {"nombre": "Profilaxis Dental", "precio": 120.0, "tipo": "servicio", "activo": True},
            {"nombre": "Esterilizacion Canina", "precio": 250.0, "tipo": "servicio", "activo": True},
        ]
        servicios = []
        for sd in servicios_data:
            s = ServicioProducto(**sd)
            db.add(s)
            servicios.append(s)
        db.flush()

        # Inventario
        inv_data = [
            {"nombre": "Amoxicilina 500mg", "categoria": "Medicamento", "descripcion": "Antibiotico de amplio espectro", "stock": 45, "stock_minimo": 10, "precio_compra": 2.5, "precio_venta": 5.0, "proveedor": "Instituto Peruano de Farmacia", "fecha_caducidad": "2026-08-15"},
            {"nombre": "Metronidazol 250mg", "categoria": "Medicamento", "descripcion": "Antiparasitario y antibacteriano", "stock": 30, "stock_minimo": 10, "precio_compra": 1.8, "precio_venta": 4.0, "proveedor": "Instituto Peruano de Farmacia", "fecha_caducidad": "2026-11-20"},
            {"nombre": "Vacuna Antirrabica (frasco)", "categoria": "Vacuna", "descripcion": "Vacuna antirrabica para caninos y felinos", "stock": 20, "stock_minimo": 5, "precio_compra": 15.0, "precio_venta": 35.0, "proveedor": "Zoetis Peru", "fecha_caducidad": "2025-12-01"},
            {"nombre": "Vacuna Trivalente Felina", "categoria": "Vacuna", "descripcion": "Panleucopenia, Calicivirus, Herpesvirus", "stock": 12, "stock_minimo": 5, "precio_compra": 25.0, "precio_venta": 55.0, "proveedor": "Zoetis Peru", "fecha_caducidad": "2025-10-30"},
            {"nombre": "Drontal Plus (antiparasitario)", "categoria": "Antiparasitario", "descripcion": "Comprimidos para desparasitacion canina", "stock": 35, "stock_minimo": 10, "precio_compra": 8.0, "precio_venta": 18.0, "proveedor": "Bayer Animal Health", "fecha_caducidad": "2026-06-15"},
            {"nombre": "Advantage 25mg (perros pequenos)", "categoria": "Antiparasitario", "descripcion": "Pipeta antipulgas y garrapatas", "stock": 18, "stock_minimo": 8, "precio_compra": 22.0, "precio_venta": 42.0, "proveedor": "Bayer Animal Health", "fecha_caducidad": "2026-09-20"},
            {"nombre": "Hills Prescription c/d", "categoria": "Alimento", "descripcion": "Alimento veterinario para salud urinaria", "stock": 8, "stock_minimo": 5, "precio_compra": 95.0, "precio_venta": 150.0, "proveedor": "Hills Pet Nutrition", "fecha_caducidad": "2026-03-10"},
            {"nombre": "Royal Canin Mini Adult", "categoria": "Alimento", "descripcion": "Alimento para perros de razas pequenas adultas", "stock": 15, "stock_minimo": 5, "precio_compra": 65.0, "precio_venta": 105.0, "proveedor": "Royal Canin Peru", "fecha_caducidad": "2026-05-25"},
            {"nombre": "Ibuprofeno Veterinario 400mg", "categoria": "Medicamento", "descripcion": "Antiinflamatorio y analgesico", "stock": 3, "stock_minimo": 10, "precio_compra": 1.5, "precio_venta": 3.5, "proveedor": "Instituto Peruano de Farmacia", "fecha_caducidad": "2026-01-30"},
            {"nombre": "Clorhexidina Spray 250ml", "categoria": "Medicamento", "descripcion": "Antiseptico para heridas y piel", "stock": 22, "stock_minimo": 5, "precio_compra": 12.0, "precio_venta": 25.0, "proveedor": "Instituto Peruano de Farmacia", "fecha_caducidad": "2027-04-01"},
        ]
        for item in inv_data:
            db.add(Inventario(**item))
        db.flush()

        # Comprobantes de pago
        comp1_total = 95.0
        comp1_sub = round(comp1_total / 1.18, 2)
        comp1_igv = round(comp1_total - comp1_sub, 2)
        comp2_total = 175.0
        comp2_sub = round(comp2_total / 1.18, 2)
        comp2_igv = round(comp2_total - comp2_sub, 2)

        comps_data = [
            {"serie": "B001", "numero": 1, "tipo_documento": "boleta", "fecha_emision": now - timedelta(days=14), "cliente_nombre": "Carlos Ramirez Torres", "cliente_ruc_dni": "45218963", "subtotal": round(75.0/1.18,2), "igv": round(75.0 - round(75.0/1.18,2),2), "total": 75.0, "estado": "Pagado", "usuario_id": vet_id, "propietario_id": props[0].id},
            {"serie": "B001", "numero": 2, "tipo_documento": "boleta", "fecha_emision": now - timedelta(days=10), "cliente_nombre": "Luis Fernando Castillo", "cliente_ruc_dni": "10325678", "subtotal": round(65.0/1.18,2), "igv": round(65.0 - round(65.0/1.18,2),2), "total": 65.0, "estado": "Pagado", "usuario_id": vet_id, "propietario_id": props[2].id},
            {"serie": "B001", "numero": 3, "tipo_documento": "boleta", "fecha_emision": now - timedelta(days=7), "cliente_nombre": "Ana Maria Gutierrez", "cliente_ruc_dni": "70123456", "subtotal": round(95.0/1.18,2), "igv": round(95.0 - round(95.0/1.18,2),2), "total": 95.0, "estado": "Pagado", "usuario_id": vet_id, "propietario_id": props[1].id},
            {"serie": "F001", "numero": 1, "tipo_documento": "factura", "fecha_emision": now - timedelta(days=5), "cliente_nombre": "Maria Elena Diaz Vargas", "cliente_ruc_dni": "20456789", "subtotal": round(120.0/1.18,2), "igv": round(120.0 - round(120.0/1.18,2),2), "total": 120.0, "estado": "Pagado", "usuario_id": vet_id, "propietario_id": props[3].id},
            {"serie": "B001", "numero": 4, "tipo_documento": "boleta", "fecha_emision": now - timedelta(days=2), "cliente_nombre": "Jorge Luis Mendoza", "cliente_ruc_dni": "41987654", "subtotal": round(65.0/1.18,2), "igv": round(65.0 - round(65.0/1.18,2),2), "total": 65.0, "estado": "Pagado", "usuario_id": vet_id, "propietario_id": props[4].id},
        ]
        comps = []
        for comp_data in comps_data:
            c = ComprobantePago(**comp_data)
            db.add(c)
            comps.append(c)
        db.flush()

        # Detalles de comprobantes
        detalles_data = [
            {"comprobante_id": comps[0].id, "servicio_producto_id": servicios[0].id, "cantidad": 1, "precio_unitario": 40.0, "subtotal": 40.0},
            {"comprobante_id": comps[0].id, "servicio_producto_id": servicios[1].id, "cantidad": 1, "precio_unitario": 35.0, "subtotal": 35.0},
            {"comprobante_id": comps[1].id, "servicio_producto_id": servicios[0].id, "cantidad": 1, "precio_unitario": 40.0, "subtotal": 40.0},
            {"comprobante_id": comps[1].id, "servicio_producto_id": servicios[3].id, "cantidad": 1, "precio_unitario": 25.0, "subtotal": 25.0},
            {"comprobante_id": comps[2].id, "servicio_producto_id": servicios[2].id, "cantidad": 1, "precio_unitario": 55.0, "subtotal": 55.0},
            {"comprobante_id": comps[2].id, "servicio_producto_id": servicios[0].id, "cantidad": 1, "precio_unitario": 40.0, "subtotal": 40.0},
            {"comprobante_id": comps[3].id, "servicio_producto_id": servicios[4].id, "cantidad": 1, "precio_unitario": 120.0, "subtotal": 120.0},
            {"comprobante_id": comps[4].id, "servicio_producto_id": servicios[0].id, "cantidad": 1, "precio_unitario": 40.0, "subtotal": 40.0},
            {"comprobante_id": comps[4].id, "servicio_producto_id": servicios[1].id, "cantidad": 1, "precio_unitario": 25.0, "subtotal": 25.0},
        ]
        for dd in detalles_data:
            db.add(DetalleComprobante(**dd))

        db.commit()
        print(">>> Datos de prueba insertados correctamente.")
    except Exception as e:
        db.rollback()
        print(f">>> Error insertando datos de prueba: {e}")
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


# -- Dashboard API --
@app.get("/api/dashboard")
def dashboard_data():
    from models import Propietario, Paciente, Cita, HistorialClinico, Inventario, ComprobantePago, DetalleComprobante, ServicioProducto
    from database import SessionLocal
    from sqlalchemy import func, extract
    from datetime import datetime, timedelta, timezone

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        month_names = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

        # KPIs
        total_propietarios = db.query(func.count(Propietario.id)).scalar() or 0
        total_pacientes = db.query(func.count(Paciente.id)).scalar() or 0
        total_citas = db.query(func.count(Cita.id)).scalar() or 0
        citas_pendientes = db.query(func.count(Cita.id)).filter(Cita.estado == "Pendiente").scalar() or 0
        citas_atendidas = db.query(func.count(Cita.id)).filter(Cita.estado == "Atendido").scalar() or 0
        total_historial = db.query(func.count(HistorialClinico.id)).scalar() or 0
        total_inventario = db.query(func.count(Inventario.id)).scalar() or 0
        bajo_stock = db.query(func.count(Inventario.id)).filter(Inventario.stock <= Inventario.stock_minimo).scalar() or 0

        # Ingresos del mes actual
        current_month_total = db.query(func.coalesce(func.sum(ComprobantePago.total), 0.0)).filter(
            extract("year", ComprobantePago.fecha_emision) == now.year,
            extract("month", ComprobantePago.fecha_emision) == now.month,
            ComprobantePago.estado == "Pagado"
        ).scalar() or 0.0

        # Ingresos mes anterior (para tendencia)
        prev_month = now.month - 1 if now.month > 1 else 12
        prev_year = now.year if now.month > 1 else now.year - 1
        prev_month_total = db.query(func.coalesce(func.sum(ComprobantePago.total), 0.0)).filter(
            extract("year", ComprobantePago.fecha_emision) == prev_year,
            extract("month", ComprobantePago.fecha_emision) == prev_month,
            ComprobantePago.estado == "Pagado"
        ).scalar() or 0.0

        ingreso_tendencia = round(((current_month_total - prev_month_total) / prev_month_total * 100), 1) if prev_month_total > 0 else 0

        # Ingresos ultimos 6 meses
        ingresos_mensuales = []
        for i in range(5, -1, -1):
            m = now.month - i
            y = now.year
            while m <= 0:
                m += 12
                y -= 1
            total = db.query(func.coalesce(func.sum(ComprobantePago.total), 0.0)).filter(
                extract("year", ComprobantePago.fecha_emision) == y,
                extract("month", ComprobantePago.fecha_emision) == m,
                ComprobantePago.estado == "Pagado"
            ).scalar() or 0.0
            ingresos_mensuales.append({"mes": month_names[m - 1], "total": round(float(total), 2)})

        # Distribucion de especies
        especies_raw = db.query(Paciente.especie, func.count(Paciente.id)).group_by(Paciente.especie).all()
        especies = [{"especie": e[0] or "Otro", "cantidad": e[1]} for e in especies_raw]

        # Top servicios (por cantidad de detalles en comprobantes pagados)
        top_servicios_raw = (
            db.query(ServicioProducto.nombre, func.sum(DetalleComprobante.cantidad).label("total_vendido"))
            .join(DetalleComprobante, DetalleComprobante.servicio_producto_id == ServicioProducto.id)
            .join(ComprobantePago, ComprobantePago.id == DetalleComprobante.comprobante_id)
            .filter(ComprobantePago.estado == "Pagado")
            .group_by(ServicioProducto.nombre)
            .order_by(func.sum(DetalleComprobante.cantidad).desc())
            .limit(6)
            .all()
        )
        top_servicios = [{"nombre": s[0], "cantidad": int(s[1])} for s in top_servicios_raw]

        # Proximas citas (hoy y futuras)
        hoy = now.replace(hour=0, minute=0, second=0, microsecond=0)
        proximas_citas_raw = (
            db.query(Cita)
            .filter(Cita.fecha >= hoy, Cita.estado == "Pendiente")
            .order_by(Cita.fecha.asc())
            .limit(6)
            .all()
        )
        paciente_ids = [c.paciente_id for c in proximas_citas_raw]
        pacientes_map = {p.id: p.nombre for p in db.query(Paciente).filter(Paciente.id.in_(paciente_ids)).all()} if paciente_ids else {}
        proximas_citas = []
        for c in proximas_citas_raw:
            proximas_citas.append({
                "id": c.id,
                "fecha": c.fecha.isoformat(),
                "motivo": c.motivo,
                "estado": c.estado,
                "paciente_nombre": pacientes_map.get(c.paciente_id, f"Mascota #{c.paciente_id}")
            })

        # Alertas inventario (bajo stock + proximos a caducar)
        alertas_stock = []
        for inv in db.query(Inventario).filter(Inventario.stock <= Inventario.stock_minimo).all():
            alertas_stock.append({"id": inv.id, "nombre": inv.nombre, "stock": inv.stock, "stock_minimo": inv.stock_minimo, "tipo": "bajo_stock"})
        for inv in db.query(Inventario).filter(Inventario.fecha_caducidad != None).all():
            try:
                cad = datetime.strptime(inv.fecha_caducidad, "%Y-%m-%d")
                if (cad - now.replace(tzinfo=None)).days <= 90:
                    alertas_stock.append({"id": inv.id, "nombre": inv.nombre, "fecha_caducidad": inv.fecha_caducidad, "tipo": "caducidad"})
            except Exception:
                pass

        return {
            "kpi": {
                "propietarios": total_propietarios,
                "pacientes": total_pacientes,
                "citas_total": total_citas,
                "citas_pendientes": citas_pendientes,
                "citas_atendidas": citas_atendidas,
                "historial": total_historial,
                "inventario_total": total_inventario,
                "inventario_bajo_stock": bajo_stock,
                "ingresos_mes": round(float(current_month_total), 2),
                "ingresos_tendencia": ingreso_tendencia,
            },
            "ingresos_mensuales": ingresos_mensuales,
            "especies": especies,
            "top_servicios": top_servicios,
            "proximas_citas": proximas_citas,
            "alertas_inventario": alertas_stock,
        }
    finally:
        db.close()


# -- Static files --
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "frontend" / "static"), name="static")


# -- Static routes --
@app.get("/")
def root():
    return FileResponse(Path(__file__).parent / "frontend" / "index.html")


@app.get("/landing")
def landing():
    return FileResponse(Path(__file__).parent / "frontend" / "landing.html")
