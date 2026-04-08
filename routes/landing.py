import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import get_current_user
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def landing_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    user: Optional[User] = await get_current_user(request, db)

    flash_messages: list[dict] = []
    from dependencies import get_flash_messages, session_manager, SESSION_COOKIE_NAME
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie:
        session_data = session_manager.get_session(cookie)
        if session_data:
            session_data, flash_messages = session_manager.pop_flash(session_data)

    current_year = datetime.now().year

    response = templates.TemplateResponse(
        request,
        "landing.html",
        context={
            "user": user,
            "flash_messages": flash_messages,
            "current_year": current_year,
        },
    )

    if cookie and flash_messages:
        session_data_fresh = session_manager.get_session(cookie)
        if session_data_fresh:
            session_data_fresh.pop("flash_messages", None)
            session_manager.update_session_cookie(response, session_data_fresh)

    return response