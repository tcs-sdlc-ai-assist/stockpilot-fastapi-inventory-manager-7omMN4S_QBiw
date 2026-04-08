import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import create_tables
from dependencies import get_current_user, get_db
from seed import seed_database

logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting StockPilot application...")
    await create_tables()
    logger.info("Database tables created.")
    await seed_database()
    logger.info("Database seeding complete.")
    yield
    logger.info("Shutting down StockPilot application.")


app = FastAPI(
    title="StockPilot",
    description="Smart inventory management for small and medium businesses.",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="static"), name="static")

from routes import (
    auth_router,
    categories_router,
    dashboard_router,
    inventory_router,
    landing_router,
    users_router,
)

app.include_router(landing_router)
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(inventory_router)
app.include_router(categories_router)
app.include_router(users_router)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc) -> HTMLResponse:
    user = None
    try:
        async for db in get_db():
            user = await get_current_user(request, db)
            break
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        "errors/404.html",
        context={
            "user": user,
            "flash_messages": [],
        },
        status_code=404,
    )