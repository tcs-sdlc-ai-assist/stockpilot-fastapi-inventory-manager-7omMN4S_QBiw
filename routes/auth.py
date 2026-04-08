import logging
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import (
    create_session_response,
    clear_session_response,
    get_current_user,
    get_flash_messages,
    hash_password,
    verify_password,
)
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/login")
async def login_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user:
        if user.role == "admin":
            return RedirectResponse(url="/dashboard", status_code=303)
        return RedirectResponse(url="/inventory/", status_code=303)

    flash_messages = await get_flash_messages(request)
    return templates.TemplateResponse(
        request,
        "auth/login.html",
        context={
            "user": None,
            "error": None,
            "username": "",
            "flash_messages": flash_messages,
        },
    )


@router.post("/login")
async def login_submit(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "")

    if not username or not password:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            context={
                "user": None,
                "error": "Please enter both username and password.",
                "username": username,
                "flash_messages": [],
            },
        )

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        logger.warning("Failed login attempt for username: %s", username)
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            context={
                "user": None,
                "error": "Invalid username or password.",
                "username": username,
                "flash_messages": [],
            },
        )

    logger.info("User '%s' logged in successfully.", username)

    if user.role == "admin":
        redirect_url = "/dashboard"
    else:
        redirect_url = "/inventory/"

    return create_session_response(
        user=user,
        redirect_url=redirect_url,
        flash_message=f"Welcome back, {user.display_name}!",
        flash_category="success",
    )


@router.get("/register")
async def register_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user:
        if user.role == "admin":
            return RedirectResponse(url="/dashboard", status_code=303)
        return RedirectResponse(url="/inventory/", status_code=303)

    flash_messages = await get_flash_messages(request)
    return templates.TemplateResponse(
        request,
        "auth/register.html",
        context={
            "user": None,
            "error": None,
            "errors": {},
            "form_data": {},
            "flash_messages": flash_messages,
        },
    )


@router.post("/register")
async def register_submit(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    display_name = form.get("display_name", "").strip()
    username = form.get("username", "").strip()
    password = form.get("password", "")
    confirm_password = form.get("confirm_password", "")

    form_data = {
        "display_name": display_name,
        "username": username,
    }
    errors: dict[str, str] = {}

    if not display_name:
        errors["display_name"] = "Display name is required."
    elif len(display_name) > 100:
        errors["display_name"] = "Display name must be 100 characters or fewer."

    if not username:
        errors["username"] = "Username is required."
    elif len(username) > 50:
        errors["username"] = "Username must be 50 characters or fewer."

    if not password:
        errors["password"] = "Password is required."
    elif len(password) < 4:
        errors["password"] = "Password must be at least 4 characters."

    if not confirm_password:
        errors["confirm_password"] = "Please confirm your password."
    elif password != confirm_password:
        errors["confirm_password"] = "Passwords do not match."

    if not errors.get("username") and username:
        result = await db.execute(select(User).where(User.username == username))
        existing_user = result.scalar_one_or_none()
        if existing_user is not None:
            errors["username"] = "Username already exists. Please choose another."

    if errors:
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            context={
                "user": None,
                "error": "Please correct the errors below.",
                "errors": errors,
                "form_data": form_data,
                "flash_messages": [],
            },
        )

    hashed = hash_password(password)
    new_user = User(
        username=username,
        display_name=display_name,
        hashed_password=hashed,
        role="staff",
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)

    logger.info("New user '%s' registered successfully.", username)

    return create_session_response(
        user=new_user,
        redirect_url="/inventory/",
        flash_message=f"Welcome to StockPilot, {display_name}!",
        flash_category="success",
    )


@router.get("/logout")
async def logout(request: Request):
    logger.info("User logged out.")
    return clear_session_response(redirect_url="/")