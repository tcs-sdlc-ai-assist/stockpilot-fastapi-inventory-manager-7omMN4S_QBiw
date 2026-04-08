import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import (
    add_flash_message,
    get_flash_messages,
    require_admin,
)
from models.category import Category
from models.item import InventoryItem
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/categories/")
async def list_categories(
    request: Request,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    flash_messages = await get_flash_messages(request)

    result = await db.execute(select(Category).order_by(Category.name))
    categories = result.scalars().all()

    categories_with_counts = []
    for category in categories:
        count_result = await db.execute(
            select(func.count(InventoryItem.id)).where(
                InventoryItem.category_id == category.id
            )
        )
        item_count = count_result.scalar() or 0
        categories_with_counts.append(
            {
                "id": category.id,
                "name": category.name,
                "color": category.color,
                "item_count": item_count,
            }
        )

    return templates.TemplateResponse(
        request,
        "categories/list.html",
        context={
            "user": user,
            "categories": categories_with_counts,
            "flash_messages": flash_messages,
            "current_year": "2024",
        },
    )


@router.post("/categories/add")
async def add_category(
    request: Request,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str = Form(...),
    color: str = Form(default="#6366f1"),
):
    name = name.strip()

    if not name:
        response = RedirectResponse(url="/categories/", status_code=303)
        add_flash_message(response, request, "Category name is required.", "error")
        return response

    if len(name) > 50:
        response = RedirectResponse(url="/categories/", status_code=303)
        add_flash_message(
            response, request, "Category name must be 50 characters or less.", "error"
        )
        return response

    existing_result = await db.execute(
        select(Category).where(func.lower(Category.name) == name.lower())
    )
    existing = existing_result.scalar_one_or_none()

    if existing is not None:
        response = RedirectResponse(url="/categories/", status_code=303)
        add_flash_message(
            response,
            request,
            f'Category "{name}" already exists.',
            "error",
        )
        return response

    color = color.strip()
    if not color or len(color) != 7 or not color.startswith("#"):
        color = "#6366f1"

    category = Category(name=name, color=color)
    db.add(category)
    await db.flush()

    logger.info("Category '%s' created by user '%s'.", name, user.username)

    response = RedirectResponse(url="/categories/", status_code=303)
    add_flash_message(
        response, request, f'Category "{name}" created successfully.', "success"
    )
    return response


@router.post("/categories/{category_id}/delete")
async def delete_category(
    request: Request,
    category_id: int,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()

    if category is None:
        response = RedirectResponse(url="/categories/", status_code=303)
        add_flash_message(response, request, "Category not found.", "error")
        return response

    count_result = await db.execute(
        select(func.count(InventoryItem.id)).where(
            InventoryItem.category_id == category_id
        )
    )
    item_count = count_result.scalar() or 0

    if item_count > 0:
        response = RedirectResponse(url="/categories/", status_code=303)
        add_flash_message(
            response,
            request,
            f'Cannot delete "{category.name}" because it has {item_count} associated item{"s" if item_count != 1 else ""}. Please reassign or remove those items first.',
            "error",
        )
        return response

    category_name = category.name
    await db.delete(category)
    await db.flush()

    logger.info(
        "Category '%s' (id=%d) deleted by user '%s'.",
        category_name,
        category_id,
        user.username,
    )

    response = RedirectResponse(url="/categories/", status_code=303)
    add_flash_message(
        response,
        request,
        f'Category "{category_name}" deleted successfully.',
        "success",
    )
    return response