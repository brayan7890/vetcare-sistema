from routers.auth import router as auth_router
from routers.users import router as users_router
from routers.owners import router as owners_router
from routers.pets import router as pets_router
from routers.appointments import router as appointments_router
from routers.medical_history import router as medical_history_router
from routers.inventory import router as inventory_router
from routers.billing import router as billing_router

__all__ = [
    "auth_router",
    "users_router",
    "owners_router",
    "pets_router",
    "appointments_router",
    "medical_history_router",
    "inventory_router",
    "billing_router",
]
