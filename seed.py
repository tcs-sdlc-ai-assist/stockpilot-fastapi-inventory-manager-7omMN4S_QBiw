import asyncio
import logging

from sqlalchemy import select

from config import settings
from database import async_session, create_tables
from models.category import Category
from models.user import User

logger = logging.getLogger(__name__)

try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(password: str) -> str:
        return pwd_context.hash(password)
except Exception:
    import bcrypt

    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


DEFAULT_CATEGORIES = [
    {"name": "Electronics", "color": "#3b82f6"},
    {"name": "Clothing", "color": "#10b981"},
    {"name": "Food & Beverage", "color": "#f59e0b"},
    {"name": "Office Supplies", "color": "#8b5cf6"},
    {"name": "Raw Materials", "color": "#ef4444"},
]


async def seed_default_admin(session) -> None:
    result = await session.execute(
        select(User).where(User.username == settings.DEFAULT_ADMIN_USERNAME)
    )
    existing_admin = result.scalars().first()

    if existing_admin is not None:
        logger.info("Default admin user '%s' already exists, skipping.", settings.DEFAULT_ADMIN_USERNAME)
        return

    hashed = hash_password(settings.DEFAULT_ADMIN_PASSWORD)
    admin_user = User(
        username=settings.DEFAULT_ADMIN_USERNAME,
        display_name=settings.DEFAULT_ADMIN_DISPLAY_NAME,
        hashed_password=hashed,
        role="admin",
    )
    session.add(admin_user)
    await session.flush()
    logger.info("Default admin user '%s' created successfully.", settings.DEFAULT_ADMIN_USERNAME)


async def seed_default_categories(session) -> None:
    for cat_data in DEFAULT_CATEGORIES:
        result = await session.execute(
            select(Category).where(Category.name == cat_data["name"])
        )
        existing = result.scalars().first()

        if existing is not None:
            logger.info("Category '%s' already exists, skipping.", cat_data["name"])
            continue

        category = Category(
            name=cat_data["name"],
            color=cat_data["color"],
        )
        session.add(category)
        await session.flush()
        logger.info("Category '%s' created successfully.", cat_data["name"])


async def seed_database() -> None:
    await create_tables()

    async with async_session() as session:
        try:
            await seed_default_admin(session)
            await seed_default_categories(session)
            await session.commit()
            logger.info("Database seeding completed successfully.")
        except Exception:
            await session.rollback()
            logger.exception("Database seeding failed.")
            raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_database())