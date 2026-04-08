import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import get_current_user, get_flash_messages
from models.category import Category
from models.item import InventoryItem
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/dashboard")
@router.get("/dashboard/")
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    if current_user.role != "admin":
        return RedirectResponse(url="/inventory/", status_code=303)

    flash_messages = await get_flash_messages(request)

    total_items_result = await db.execute(select(func.count(InventoryItem.id)))
    total_items = total_items_result.scalar() or 0

    total_categories_result = await db.execute(select(func.count(Category.id)))
    total_categories = total_categories_result.scalar() or 0

    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar() or 0

    low_stock_result = await db.execute(
        select(InventoryItem)
        .where(InventoryItem.quantity <= InventoryItem.reorder_level)
        .order_by(InventoryItem.quantity.asc())
    )
    low_stock_items = list(low_stock_result.scalars().all())

    recent_items_result = await db.execute(
        select(InventoryItem)
        .order_by(InventoryItem.updated_at.desc())
        .limit(10)
    )
    recent_items = list(recent_items_result.scalars().all())

    return templates.TemplateResponse(
        request,
        "dashboard/index.html",
        context={
            "user": current_user,
            "current_user": current_user,
            "total_items": total_items,
            "total_categories": total_categories,
            "total_users": total_users,
            "low_stock_items": low_stock_items,
            "recent_items": recent_items,
            "flash_messages": flash_messages,
            "current_year": datetime.now().year,
        },
    )