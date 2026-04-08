from routes.auth import router as auth_router
from routes.inventory import router as inventory_router
from routes.categories import router as categories_router
from routes.dashboard import router as dashboard_router
from routes.users import router as users_router
from routes.landing import router as landing_router

__all__ = [
    "auth_router",
    "inventory_router",
    "categories_router",
    "dashboard_router",
    "users_router",
    "landing_router",
]