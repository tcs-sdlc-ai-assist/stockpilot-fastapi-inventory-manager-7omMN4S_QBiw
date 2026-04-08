import logging
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import (
    add_flash_message,
    get_current_user,
    get_flash_messages,
    require_auth,
    require_ownership,
)
from models.category import Category
from models.item import InventoryItem
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/inventory")
@router.get("/inventory/")
async def inventory_list(
    request: Request,
    search: Optional[str] = None,
    category: Optional[str] = None,
    sort: Optional[str] = "name",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> templates.TemplateResponse:
    flash_messages = await get_flash_messages(request)

    categories_result = await db.execute(select(Category).order_by(Category.name))
    categories = list(categories_result.scalars().all())

    query = select(InventoryItem)

    if search and search.strip():
        search_term = search.strip()
        query = query.where(InventoryItem.name.ilike(f"%{search_term}%"))

    if category and category.strip():
        try:
            category_id = int(category)
            query = query.where(InventoryItem.category_id == category_id)
        except (ValueError, TypeError):
            pass

    if sort == "date":
        query = query.order_by(InventoryItem.created_at.desc())
    elif sort == "quantity":
        query = query.order_by(InventoryItem.quantity.asc())
    elif sort == "price":
        query = query.order_by(InventoryItem.unit_price.desc())
    else:
        query = query.order_by(InventoryItem.name.asc())

    result = await db.execute(query)
    items = list(result.scalars().all())

    return templates.TemplateResponse(
        request,
        "inventory/list.html",
        context={
            "user": current_user,
            "current_user": current_user,
            "items": items,
            "categories": categories,
            "search": search or "",
            "selected_category": category or "",
            "sort": sort or "name",
            "flash_messages": flash_messages,
        },
    )


@router.get("/inventory/add")
async def inventory_add_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> templates.TemplateResponse:
    flash_messages = await get_flash_messages(request)

    categories_result = await db.execute(select(Category).order_by(Category.name))
    categories = list(categories_result.scalars().all())

    return templates.TemplateResponse(
        request,
        "inventory/form.html",
        context={
            "user": current_user,
            "current_user": current_user,
            "item": None,
            "categories": categories,
            "form_data": None,
            "errors": None,
            "field_errors": None,
            "form_action": "/inventory/add",
            "cancel_url": "/inventory",
            "flash_messages": flash_messages,
        },
    )


@router.post("/inventory/add")
async def inventory_add(
    request: Request,
    name: str = Form(""),
    sku: str = Form(""),
    description: str = Form(""),
    quantity: str = Form("0"),
    unit_price: str = Form("0.00"),
    reorder_level: str = Form("0"),
    category_id: str = Form(""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> RedirectResponse:
    errors: list[str] = []
    field_errors: dict[str, str] = {}

    name = name.strip()
    sku = sku.strip() if sku else ""
    description = description.strip() if description else ""

    if not name:
        errors.append("Name is required.")
        field_errors["name"] = "Name is required."

    try:
        quantity_val = int(quantity)
        if quantity_val < 0:
            errors.append("Quantity must be zero or greater.")
            field_errors["quantity"] = "Quantity must be zero or greater."
    except (ValueError, TypeError):
        quantity_val = 0
        errors.append("Quantity must be a valid integer.")
        field_errors["quantity"] = "Quantity must be a valid integer."

    try:
        unit_price_val = float(unit_price)
        if unit_price_val < 0:
            errors.append("Unit price must be zero or greater.")
            field_errors["unit_price"] = "Unit price must be zero or greater."
    except (ValueError, TypeError):
        unit_price_val = 0.0
        errors.append("Unit price must be a valid number.")
        field_errors["unit_price"] = "Unit price must be a valid number."

    try:
        reorder_level_val = int(reorder_level)
        if reorder_level_val < 0:
            errors.append("Reorder level must be zero or greater.")
            field_errors["reorder_level"] = "Reorder level must be zero or greater."
    except (ValueError, TypeError):
        reorder_level_val = 0
        errors.append("Reorder level must be a valid integer.")
        field_errors["reorder_level"] = "Reorder level must be a valid integer."

    category_id_val: Optional[int] = None
    if category_id and category_id.strip():
        try:
            category_id_val = int(category_id)
            cat_result = await db.execute(select(Category).where(Category.id == category_id_val))
            if cat_result.scalar_one_or_none() is None:
                errors.append("Selected category does not exist.")
                field_errors["category_id"] = "Selected category does not exist."
        except (ValueError, TypeError):
            errors.append("Invalid category selection.")
            field_errors["category_id"] = "Invalid category selection."
    else:
        errors.append("Category is required.")
        field_errors["category_id"] = "Category is required."

    if sku:
        sku_result = await db.execute(
            select(InventoryItem).where(InventoryItem.sku == sku)
        )
        if sku_result.scalar_one_or_none() is not None:
            errors.append("An item with this SKU already exists.")
            field_errors["sku"] = "An item with this SKU already exists."

    if errors:
        flash_messages = await get_flash_messages(request)
        categories_result = await db.execute(select(Category).order_by(Category.name))
        categories = list(categories_result.scalars().all())

        form_data = {
            "name": name,
            "sku": sku,
            "description": description,
            "quantity": quantity,
            "unit_price": unit_price,
            "reorder_level": reorder_level,
            "category_id": category_id,
        }

        return templates.TemplateResponse(
            request,
            "inventory/form.html",
            context={
                "user": current_user,
                "current_user": current_user,
                "item": None,
                "categories": categories,
                "form_data": type("FormData", (), form_data)(),
                "errors": errors,
                "field_errors": field_errors,
                "form_action": "/inventory/add",
                "cancel_url": "/inventory",
                "flash_messages": flash_messages,
            },
            status_code=422,
        )

    item = InventoryItem(
        name=name,
        sku=sku if sku else None,
        description=description if description else None,
        quantity=quantity_val,
        unit_price=unit_price_val,
        reorder_level=reorder_level_val,
        category_id=category_id_val,
        created_by_id=current_user.id,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)

    response = RedirectResponse(url=f"/inventory/{item.id}", status_code=303)
    add_flash_message(response, request, "Item created successfully.", "success")
    return response


@router.get("/inventory/{item_id}")
async def inventory_detail(
    request: Request,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> templates.TemplateResponse:
    flash_messages = await get_flash_messages(request)

    result = await db.execute(
        select(InventoryItem).where(InventoryItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if item is None:
        return templates.TemplateResponse(
            request,
            "errors/404.html",
            context={
                "user": current_user,
                "flash_messages": [],
            },
            status_code=404,
        )

    is_owner = require_ownership(current_user, item.created_by_id)

    return templates.TemplateResponse(
        request,
        "inventory/detail.html",
        context={
            "user": current_user,
            "current_user": current_user,
            "item": item,
            "is_owner": is_owner,
            "flash_messages": flash_messages,
        },
    )


@router.get("/inventory/{item_id}/edit")
async def inventory_edit_form(
    request: Request,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> templates.TemplateResponse:
    flash_messages = await get_flash_messages(request)

    result = await db.execute(
        select(InventoryItem).where(InventoryItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if item is None:
        return templates.TemplateResponse(
            request,
            "errors/404.html",
            context={
                "user": current_user,
                "flash_messages": [],
            },
            status_code=404,
        )

    if not require_ownership(current_user, item.created_by_id):
        response = RedirectResponse(url="/inventory", status_code=303)
        add_flash_message(response, request, "You do not have permission to edit this item.", "error")
        return response

    categories_result = await db.execute(select(Category).order_by(Category.name))
    categories = list(categories_result.scalars().all())

    return templates.TemplateResponse(
        request,
        "inventory/form.html",
        context={
            "user": current_user,
            "current_user": current_user,
            "item": item,
            "categories": categories,
            "form_data": None,
            "errors": None,
            "field_errors": None,
            "form_action": f"/inventory/{item.id}/edit",
            "cancel_url": f"/inventory/{item.id}",
            "flash_messages": flash_messages,
        },
    )


@router.post("/inventory/{item_id}/edit")
async def inventory_edit(
    request: Request,
    item_id: int,
    name: str = Form(""),
    sku: str = Form(""),
    description: str = Form(""),
    quantity: str = Form("0"),
    unit_price: str = Form("0.00"),
    reorder_level: str = Form("0"),
    category_id: str = Form(""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> RedirectResponse:
    result = await db.execute(
        select(InventoryItem).where(InventoryItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if item is None:
        return templates.TemplateResponse(
            request,
            "errors/404.html",
            context={
                "user": current_user,
                "flash_messages": [],
            },
            status_code=404,
        )

    if not require_ownership(current_user, item.created_by_id):
        response = RedirectResponse(url="/inventory", status_code=303)
        add_flash_message(response, request, "You do not have permission to edit this item.", "error")
        return response

    errors: list[str] = []
    field_errors: dict[str, str] = {}

    name = name.strip()
    sku = sku.strip() if sku else ""
    description = description.strip() if description else ""

    if not name:
        errors.append("Name is required.")
        field_errors["name"] = "Name is required."

    try:
        quantity_val = int(quantity)
        if quantity_val < 0:
            errors.append("Quantity must be zero or greater.")
            field_errors["quantity"] = "Quantity must be zero or greater."
    except (ValueError, TypeError):
        quantity_val = 0
        errors.append("Quantity must be a valid integer.")
        field_errors["quantity"] = "Quantity must be a valid integer."

    try:
        unit_price_val = float(unit_price)
        if unit_price_val < 0:
            errors.append("Unit price must be zero or greater.")
            field_errors["unit_price"] = "Unit price must be zero or greater."
    except (ValueError, TypeError):
        unit_price_val = 0.0
        errors.append("Unit price must be a valid number.")
        field_errors["unit_price"] = "Unit price must be a valid number."

    try:
        reorder_level_val = int(reorder_level)
        if reorder_level_val < 0:
            errors.append("Reorder level must be zero or greater.")
            field_errors["reorder_level"] = "Reorder level must be zero or greater."
    except (ValueError, TypeError):
        reorder_level_val = 0
        errors.append("Reorder level must be a valid integer.")
        field_errors["reorder_level"] = "Reorder level must be a valid integer."

    category_id_val: Optional[int] = None
    if category_id and category_id.strip():
        try:
            category_id_val = int(category_id)
            cat_result = await db.execute(select(Category).where(Category.id == category_id_val))
            if cat_result.scalar_one_or_none() is None:
                errors.append("Selected category does not exist.")
                field_errors["category_id"] = "Selected category does not exist."
        except (ValueError, TypeError):
            errors.append("Invalid category selection.")
            field_errors["category_id"] = "Invalid category selection."
    else:
        errors.append("Category is required.")
        field_errors["category_id"] = "Category is required."

    if sku:
        sku_result = await db.execute(
            select(InventoryItem).where(
                InventoryItem.sku == sku,
                InventoryItem.id != item_id,
            )
        )
        if sku_result.scalar_one_or_none() is not None:
            errors.append("An item with this SKU already exists.")
            field_errors["sku"] = "An item with this SKU already exists."

    if errors:
        flash_messages = await get_flash_messages(request)
        categories_result = await db.execute(select(Category).order_by(Category.name))
        categories = list(categories_result.scalars().all())

        form_data = {
            "name": name,
            "sku": sku,
            "description": description,
            "quantity": quantity,
            "unit_price": unit_price,
            "reorder_level": reorder_level,
            "category_id": category_id,
        }

        return templates.TemplateResponse(
            request,
            "inventory/form.html",
            context={
                "user": current_user,
                "current_user": current_user,
                "item": item,
                "categories": categories,
                "form_data": type("FormData", (), form_data)(),
                "errors": errors,
                "field_errors": field_errors,
                "form_action": f"/inventory/{item.id}/edit",
                "cancel_url": f"/inventory/{item.id}",
                "flash_messages": flash_messages,
            },
            status_code=422,
        )

    item.name = name
    item.sku = sku if sku else None
    item.description = description if description else None
    item.quantity = quantity_val
    item.unit_price = unit_price_val
    item.reorder_level = reorder_level_val
    item.category_id = category_id_val

    await db.flush()
    await db.refresh(item)

    response = RedirectResponse(url=f"/inventory/{item.id}", status_code=303)
    add_flash_message(response, request, "Item updated successfully.", "success")
    return response


@router.post("/inventory/{item_id}/delete")
async def inventory_delete(
    request: Request,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> RedirectResponse:
    result = await db.execute(
        select(InventoryItem).where(InventoryItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if item is None:
        return templates.TemplateResponse(
            request,
            "errors/404.html",
            context={
                "user": current_user,
                "flash_messages": [],
            },
            status_code=404,
        )

    if not require_ownership(current_user, item.created_by_id):
        response = RedirectResponse(url="/inventory", status_code=303)
        add_flash_message(response, request, "You do not have permission to delete this item.", "error")
        return response

    item_name = item.name
    await db.delete(item)
    await db.flush()

    response = RedirectResponse(url="/inventory", status_code=303)
    add_flash_message(response, request, f'Item "{item_name}" deleted successfully.', "success")
    return response