import json
import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.user import User

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SESSION_COOKIE_NAME = "session"
SESSION_MAX_AGE = 86400 * 7  # 7 days


class SessionManager:
    def __init__(self, secret_key: str) -> None:
        self._serializer = URLSafeTimedSerializer(secret_key)

    def create_session(self, user_id: int, flash_messages: Optional[list[dict]] = None) -> str:
        data: dict = {"user_id": user_id}
        if flash_messages:
            data["flash_messages"] = flash_messages
        return self._serializer.dumps(data)

    def get_session(self, cookie: Optional[str]) -> Optional[dict]:
        if not cookie:
            return None
        try:
            data = self._serializer.loads(cookie, max_age=SESSION_MAX_AGE)
            if isinstance(data, dict) and "user_id" in data:
                return data
            return None
        except SignatureExpired:
            logger.warning("Session cookie expired")
            return None
        except BadSignature:
            logger.warning("Invalid session cookie signature")
            return None
        except Exception:
            logger.exception("Unexpected error decoding session cookie")
            return None

    def clear_session(self, response: Response) -> Response:
        response.delete_cookie(
            SESSION_COOKIE_NAME,
            path="/",
            httponly=True,
            samesite="lax",
        )
        return response

    def set_cookie(self, response: Response, token: str) -> Response:
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=token,
            max_age=SESSION_MAX_AGE,
            path="/",
            httponly=True,
            samesite="lax",
        )
        return response

    def set_flash(self, session_data: dict, message: str, category: str = "info") -> dict:
        flash_messages = session_data.get("flash_messages", [])
        flash_messages.append({"text": message, "category": category})
        session_data["flash_messages"] = flash_messages
        return session_data

    def pop_flash(self, session_data: dict) -> tuple[dict, list[dict]]:
        flash_messages = session_data.pop("flash_messages", [])
        return session_data, flash_messages

    def update_session_cookie(self, response: Response, session_data: dict) -> Response:
        token = self._serializer.dumps(session_data)
        self.set_cookie(response, token)
        return response


session_manager = SessionManager(settings.SECRET_KEY)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


async def get_session_data(request: Request) -> Optional[dict]:
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if not cookie:
        return None
    return session_manager.get_session(cookie)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    session_data = await get_session_data(request)
    if not session_data:
        return None
    user_id = session_data.get("user_id")
    if not user_id:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    return user


async def require_auth(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


async def require_admin(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await require_auth(request, db)
    if user.role != "admin":
        raise HTTPException(status_code=303, headers={"Location": "/inventory/"})
    return user


def require_ownership(user: User, item_owner_id: int) -> bool:
    if user.role == "admin":
        return True
    return user.id == item_owner_id


async def get_flash_messages(request: Request) -> list[dict]:
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if not cookie:
        return []
    session_data = session_manager.get_session(cookie)
    if not session_data:
        return []
    _, flash_messages = session_manager.pop_flash(session_data)
    return flash_messages


def add_flash_message(
    response: Response,
    request: Request,
    message: str,
    category: str = "info",
) -> Response:
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    session_data: dict = {}
    if cookie:
        data = session_manager.get_session(cookie)
        if data:
            session_data = data

    session_data = session_manager.set_flash(session_data, message, category)
    session_manager.update_session_cookie(response, session_data)
    return response


def create_session_response(
    user: User,
    redirect_url: str,
    flash_message: Optional[str] = None,
    flash_category: str = "success",
) -> RedirectResponse:
    flash_messages: list[dict] = []
    if flash_message:
        flash_messages.append({"text": flash_message, "category": flash_category})
    token = session_manager.create_session(user.id, flash_messages=flash_messages)
    response = RedirectResponse(url=redirect_url, status_code=303)
    session_manager.set_cookie(response, token)
    return response


def clear_session_response(redirect_url: str = "/login") -> RedirectResponse:
    response = RedirectResponse(url=redirect_url, status_code=303)
    session_manager.clear_session(response)
    return response