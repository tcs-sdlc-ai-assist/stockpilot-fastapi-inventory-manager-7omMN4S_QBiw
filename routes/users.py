import logging
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from dependencies import (
    get_current_user,
    get_flash_messages,
    hash_password,
    require_admin,
    add_flash_message,
    session_manager,
    SESSION_COOKIE_NAME,
)
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/users/")
async def list_users(
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    flash_messages = await get_flash_messages(request)

    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()

    import datetime

    response = templates.TemplateResponse(
        request,
        "users/list.html",
        context={
            "user": current_user,
            "current_user": current_user,
            "users": users,
            "flash_messages": flash_messages,
            "current_year": datetime.datetime.now().year,
            "error": None,
            "success": None,
        },
    )

    if flash_messages:
        cookie = request.cookies.get(SESSION_COOKIE_NAME)
        if cookie:
            session_data = session_manager.get_session(cookie)
            if session_data:
                session_data.pop("flash_messages", None)
                session_manager.update_session_cookie(response, session_data)

    return response


@router.post("/users/create")
async def create_user(
    request: Request,
    display_name: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form("staff"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    import datetime

    errors: list[str] = []

    display_name = display_name.strip()
    username = username.strip()

    if not display_name:
        errors.append("Display name is required.")
    elif len(display_name) > 100:
        errors.append("Display name must be 100 characters or fewer.")

    if not username:
        errors.append("Username is required.")
    elif len(username) > 50:
        errors.append("Username must be 50 characters or fewer.")

    if not password:
        errors.append("Password is required.")
    elif len(password) < 4:
        errors.append("Password must be at least 4 characters.")

    if role not in ("admin", "staff"):
        errors.append("Role must be either 'admin' or 'staff'.")

    if not errors:
        result = await db.execute(select(User).where(User.username == username))
        existing_user = result.scalar_one_or_none()
        if existing_user is not None:
            errors.append(f"Username '{username}' already exists.")

    if errors:
        result = await db.execute(select(User).order_by(User.created_at.desc()))
        users = result.scalars().all()

        return templates.TemplateResponse(
            request,
            "users/list.html",
            context={
                "user": current_user,
                "current_user": current_user,
                "users": users,
                "flash_messages": [],
                "current_year": datetime.datetime.now().year,
                "error": " ".join(errors),
                "success": None,
            },
        )

    hashed = hash_password(password)
    new_user = User(
        display_name=display_name,
        username=username,
        hashed_password=hashed,
        role=role,
    )
    db.add(new_user)
    await db.flush()

    logger.info("User '%s' created by admin '%s'.", username, current_user.username)

    response = RedirectResponse(url="/users/", status_code=303)
    response = add_flash_message(
        response, request, f"User '{display_name}' created successfully.", "success"
    )
    return response


@router.post("/users/{user_id}/delete")
async def delete_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    import datetime

    result = await db.execute(select(User).where(User.id == user_id))
    user_to_delete = result.scalar_one_or_none()

    if user_to_delete is None:
        response = RedirectResponse(url="/users/", status_code=303)
        response = add_flash_message(
            response, request, "User not found.", "error"
        )
        return response

    if user_to_delete.username == settings.DEFAULT_ADMIN_USERNAME:
        response = RedirectResponse(url="/users/", status_code=303)
        response = add_flash_message(
            response, request, "The default admin account cannot be deleted.", "error"
        )
        return response

    if user_to_delete.id == current_user.id:
        response = RedirectResponse(url="/users/", status_code=303)
        response = add_flash_message(
            response, request, "You cannot delete your own account.", "error"
        )
        return response

    deleted_name = user_to_delete.display_name
    await db.delete(user_to_delete)
    await db.flush()

    logger.info(
        "User '%s' (id=%d) deleted by admin '%s'.",
        deleted_name,
        user_id,
        current_user.username,
    )

    response = RedirectResponse(url="/users/", status_code=303)
    response = add_flash_message(
        response, request, f"User '{deleted_name}' has been deleted.", "success"
    )
    return response